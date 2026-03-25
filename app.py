from flask import Flask, render_template, request, jsonify, redirect
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import os

load_dotenv()
app = Flask(__name__)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def json_error(message, status=500):
    return jsonify({"success": False, "error": str(message)}), status


def now_iso():
    return datetime.utcnow().isoformat()


def safe_str(value):
    return "" if value is None else str(value).strip()


def parse_dt(value):
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
            try:
                return datetime.strptime(text, fmt)
            except Exception:
                pass
    return None


def normalize_occurrence(row):
    item = dict(row or {})
    pendencia = safe_str(item.get("pendencia")).upper()
    status = safe_str(item.get("status")).upper()

    if pendencia == "":
        if item.get("solicitado_responsavel") and not safe_str(item.get("atendimento_responsavel")):
            pendencia = "RESPONSAVEL"
        elif item.get("solicitado_gestao") and not safe_str(item.get("atendimento_gestao")):
            pendencia = "GESTAO"
        elif item.get("solicitado_coordenacao") and not safe_str(item.get("atendimento_coordenacao")):
            pendencia = "COORDENACAO"
        elif item.get("solicitado_tutor") and not safe_str(item.get("atendimento_tutor")):
            pendencia = "TUTOR"
        else:
            pendencia = "FINALIZADA"

    if status == "":
        status = "FINALIZADA" if pendencia == "FINALIZADA" else "ATENDIMENTO"

    item["pendencia"] = pendencia
    item["status"] = status
    item["id"] = item.get("numero")
    return item


def get_next_numero_ocorrencia():
    db = get_supabase()
    resp = db.table("ocorrencias").select("numero").order("numero", desc=True).limit(1).execute()
    if resp.data:
        return int(resp.data[0]["numero"]) + 1
    return 1


def fetch_all_occurrences():
    db = get_supabase()
    resp = db.table("ocorrencias").select("*").order("numero", desc=True).execute()
    return [normalize_occurrence(item) for item in (resp.data or [])]


def compute_dashboard_data(rows):
    today = datetime.now().date()
    daily_counts = Counter()
    total_counts = Counter()
    room_counts = Counter()
    weekly_by_room = defaultdict(Counter)
    weekly_total = Counter()

    for row in rows:
        pendencia = safe_str(row.get("pendencia")).upper() or "FINALIZADA"
        total_counts[pendencia] += 1

        dt = parse_dt(row.get("data_hora") or row.get("data"))
        if dt and dt.date() == today:
            daily_counts[pendencia] += 1

        sala = safe_str(row.get("sala_nome")) or "Não informada"
        room_counts[sala] += 1

        if dt:
            monday = (dt.date() - timedelta(days=dt.weekday())).strftime("%d/%m")
            weekly_by_room[sala][monday] += 1
            weekly_total[monday] += 1

    ranking = [
        {"sala": sala, "total": total}
        for sala, total in room_counts.most_common()
    ]

    top_rooms = [name for name, _ in room_counts.most_common(5)]
    week_labels = sorted(
        weekly_total.keys(),
        key=lambda x: datetime.strptime(x + f"/{datetime.now().year}", "%d/%m/%Y")
    )
    week_labels = week_labels[-8:]

    weekly_series = []
    for room in top_rooms:
        weekly_series.append({
            "label": room,
            "data": [weekly_by_room[room].get(label, 0) for label in week_labels]
        })

    return {
        "diario": {
            "tutor": daily_counts.get("TUTOR", 0),
            "coordenacao": daily_counts.get("COORDENACAO", 0),
            "gestao": daily_counts.get("GESTAO", 0),
            "responsavel": daily_counts.get("RESPONSAVEL", 0),
            "finalizadas": daily_counts.get("FINALIZADA", 0),
            "total": sum(daily_counts.values())
        },
        "acumulado": {
            "tutor": total_counts.get("TUTOR", 0),
            "coordenacao": total_counts.get("COORDENACAO", 0),
            "gestao": total_counts.get("GESTAO", 0),
            "responsavel": total_counts.get("RESPONSAVEL", 0),
            "finalizadas": total_counts.get("FINALIZADA", 0),
            "total": sum(total_counts.values())
        },
        "ranking_salas": ranking,
        "semanal_salas": {
            "labels": week_labels,
            "datasets": weekly_series
        },
        "status_chart": {
            "labels": ["Tutor", "Coordenação", "Gestão", "Responsável", "Finalizadas"],
            "data": [
                total_counts.get("TUTOR", 0),
                total_counts.get("COORDENACAO", 0),
                total_counts.get("GESTAO", 0),
                total_counts.get("RESPONSAVEL", 0),
                total_counts.get("FINALIZADA", 0),
            ]
        }
    }


@app.route("/")
def home():
    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard_ocorrencias.html")


@app.route("/health")
def health():
    return "OK"


@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    return render_template("gestao_ocorrencia.html")


@app.route("/gestao_ocorrencia_nova")
def gestao_ocorrencia_nova():
    return render_template("gestao_ocorrencia_nova.html")


@app.route("/gestao_ocorrencia_editar")
@app.route("/gestao_ocorrencia_editar/<int:ocorrencia_id>")
def gestao_ocorrencia_editar(ocorrencia_id=None):
    return render_template("gestao_ocorrencia_editar.html", ocorrencia_id=ocorrencia_id)


@app.route("/gestao_relatorio_impressao")
def gestao_relatorio_impressao():
    return render_template("gestao_relatorio_impressao.html")


@app.route("/relatorio_ocorrencias_pdf")
def relatorio_ocorrencias_pdf():
    numeros_raw = request.args.get("numeros", "").strip()
    if not numeros_raw:
        return "Nenhuma ocorrência informada.", 400
    try:
        numeros = [int(x.strip()) for x in numeros_raw.split(",") if x.strip()]
        db = get_supabase()
        resp = db.table("ocorrencias").select("*").in_("numero", numeros).order("numero").execute()
        ocorrencias = resp.data or []
        nome_aluno = ocorrencias[0].get("aluno_nome", "") if ocorrencias else ""
        return render_template(
            "relatorio_ocorrencias_pdf.html",
            ocorrencias=ocorrencias,
            nome_aluno=nome_aluno,
            data_geracao=datetime.now().strftime("%d/%m/%Y %H:%M")
        )
    except Exception as e:
        return f"Erro ao abrir relatório: {e}", 500


@app.route("/api/professores")
def api_professores():
    try:
        db = get_supabase()
        resp = db.table("d_funcionarios").select("id,nome,tipo,funcao,ativo").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/salas")
def api_salas():
    try:
        db = get_supabase()
        resp = db.table("d_salas").select("*").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/salas_por_professor/<int:professor_id>")
def api_salas_por_professor(professor_id):
    try:
        db = get_supabase()
        resp = db.table("d_salas").select("*").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos_por_sala/<int:sala_id>")
def api_alunos_por_sala(sala_id):
    try:
        db = get_supabase()
        resp = db.table("d_alunos").select("*").eq("sala_id", sala_id).order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencias_todas")
def api_ocorrencias_todas():
    try:
        return jsonify(fetch_all_occurrences())
    except Exception as e:
        return json_error(e)


@app.route("/api/dashboard_ocorrencias")
def api_dashboard_ocorrencias():
    try:
        rows = fetch_all_occurrences()
        return jsonify({"success": True, "data": compute_dashboard_data(rows)})
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencias_por_aluno/<int:aluno_id>")
def api_ocorrencias_por_aluno(aluno_id):
    try:
        db = get_supabase()
        resp = db.table("ocorrencias").select("*").eq("aluno_id", aluno_id).order("numero", desc=True).execute()
        return jsonify([normalize_occurrence(item) for item in (resp.data or [])])
    except Exception as e:
        return json_error(e)


@app.route("/api/filtros_ocorrencias")
def api_filtros_ocorrencias():
    try:
        rows = fetch_all_occurrences()
        tutores = sorted({safe_str(i.get("tutor_nome")) for i in rows if safe_str(i.get("tutor_nome"))})
        salas = sorted({safe_str(i.get("sala_nome")) for i in rows if safe_str(i.get("sala_nome"))})
        alunos = sorted({safe_str(i.get("aluno_nome")) for i in rows if safe_str(i.get("aluno_nome"))})
        return jsonify({"success": True, "tutores": tutores, "salas": salas, "alunos": alunos})
    except Exception as e:
        return json_error(e)


@app.route("/api/salas_com_ocorrencias")
def api_salas_com_ocorrencias():
    try:
        rows = fetch_all_occurrences()
        salas = sorted({safe_str(i.get("sala_nome")) for i in rows if safe_str(i.get("sala_nome"))})
        return jsonify(salas)
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos_com_ocorrencias")
def api_alunos_com_ocorrencias():
    try:
        sala_nome = safe_str(request.args.get("sala_nome"))
        rows = fetch_all_occurrences()
        if sala_nome:
            rows = [row for row in rows if safe_str(row.get("sala_nome")) == sala_nome]
        alunos = sorted({safe_str(i.get("aluno_nome")) for i in rows if safe_str(i.get("aluno_nome"))})
        return jsonify(alunos)
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencia_detalhes")
def api_ocorrencia_detalhes():
    numero = request.args.get("numero")
    if not numero:
        return json_error("Número não informado", 400)
    try:
        db = get_supabase()
        resp = db.table("ocorrencias").select("*").eq("numero", numero).limit(1).execute()
        if not resp.data:
            return json_error("Ocorrência não encontrada", 404)
        return jsonify(normalize_occurrence(resp.data[0]))
    except Exception as e:
        return json_error(e)


@app.route("/api/registrar_ocorrencia", methods=["POST"])
def api_registrar_ocorrencia():
    try:
        db = get_supabase()
        data = request.get_json() or {}
        aluno_id = data.get("aluno_id")
        professor_id = data.get("professor_id")
        professor_nome = data.get("professor_nome")
        descricao = data.get("descricao")
        atendimento_professor = data.get("atendimento_professor")
        destino = safe_str(data.get("destino") or "nenhum").lower()

        if not aluno_id:
            return json_error("Aluno não informado", 400)
        if not professor_id:
            return json_error("Professor não informado", 400)
        if not professor_nome:
            return json_error("Nome do professor não informado", 400)
        if not descricao:
            return json_error("Descrição da ocorrência não informada", 400)
        if not atendimento_professor:
            return json_error("Atendimento do professor não informado", 400)

        resp_aluno = db.table("d_alunos").select("*").eq("id", aluno_id).limit(1).execute()
        if not resp_aluno.data:
            return json_error("Aluno não encontrado", 404)
        aluno = resp_aluno.data[0]

        solicitado_tutor = False
        solicitado_coordenacao = False
        solicitado_gestao = False
        solicitado_responsavel = False
        pendencia = "FINALIZADA"
        status = "FINALIZADA"
        if destino == "tutor":
            solicitado_tutor = True
            pendencia = "TUTOR"
            status = "ATENDIMENTO"
        elif destino == "coordenacao":
            solicitado_coordenacao = True
            pendencia = "COORDENACAO"
            status = "ATENDIMENTO"
        elif destino == "gestao":
            solicitado_gestao = True
            pendencia = "GESTAO"
            status = "ATENDIMENTO"

        payload = {
            "numero": get_next_numero_ocorrencia(),
            "data_hora": now_iso(),
            "aluno_id": aluno.get("id"),
            "aluno_nome": aluno.get("nome") or aluno.get("aluno_nome"),
            "sala_id": aluno.get("sala_id"),
            "sala_nome": aluno.get("sala_nome"),
            "professor_id": professor_id,
            "professor_nome": professor_nome,
            "tutor_id": aluno.get("tutor_id"),
            "tutor_nome": aluno.get("tutor_nome"),
            "descricao": descricao,
            "atendimento_professor": atendimento_professor,
            "solicitado_tutor": solicitado_tutor,
            "solicitado_coordenacao": solicitado_coordenacao,
            "solicitado_gestao": solicitado_gestao,
            "solicitado_responsavel": solicitado_responsavel,
            "pendencia": pendencia,
            "status": status,
            "impressao_pdf": False
        }
        resp = db.table("ocorrencias").insert(payload).execute()
        numero = resp.data[0].get("numero") if resp.data else None
        return jsonify({"success": True, "numero": numero})
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencias/<int:numero>/atendimento", methods=["PUT"])
def api_salvar_atendimento(numero):
    try:
        db = get_supabase()
        data = request.get_json() or {}
        tipo = safe_str(data.get("tipo")).lower()
        texto = safe_str(data.get("texto"))
        acao = safe_str(data.get("acao")).lower()
        if not texto:
            return json_error("Texto do atendimento é obrigatório", 400)

        resp_atual = db.table("ocorrencias").select("*").eq("numero", numero).limit(1).execute()
        if not resp_atual.data:
            return json_error("Ocorrência não encontrada", 404)

        ocorrencia = normalize_occurrence(resp_atual.data[0])
        pendencia_atual = safe_str(ocorrencia.get("pendencia")).upper() or "FINALIZADA"
        updates = {}

        if tipo == "tutor":
            updates["atendimento_tutor"] = texto
        elif tipo == "coordenacao":
            updates["atendimento_coordenacao"] = texto
        elif tipo == "gestao":
            updates["atendimento_gestao"] = texto
        elif tipo == "responsavel":
            updates["atendimento_responsavel"] = texto
        else:
            return json_error("Tipo inválido", 400)

        fluxo_permitido = {
            "TUTOR": {"finalizar", "encaminhar_coordenacao", "encaminhar_gestao"},
            "COORDENACAO": {"finalizar", "encaminhar_tutor", "encaminhar_gestao"},
            "GESTAO": {"finalizar", "encaminhar_tutor", "encaminhar_coordenacao", "convocar_responsavel"},
            "RESPONSAVEL": {"finalizar"},
            "FINALIZADA": set(),
        }
        if pendencia_atual not in fluxo_permitido:
            pendencia_atual = "FINALIZADA"
        if acao not in fluxo_permitido[pendencia_atual]:
            return json_error(f"Ação '{acao}' não permitida para pendência atual '{pendencia_atual}'", 400)

        updates["solicitado_tutor"] = False
        updates["solicitado_coordenacao"] = False
        updates["solicitado_gestao"] = False
        updates["solicitado_responsavel"] = False

        if acao == "finalizar":
            updates["pendencia"] = "FINALIZADA"
            updates["status"] = "FINALIZADA"
        elif acao == "encaminhar_tutor":
            updates["pendencia"] = "TUTOR"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_tutor"] = True
        elif acao == "encaminhar_coordenacao":
            updates["pendencia"] = "COORDENACAO"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_coordenacao"] = True
        elif acao == "encaminhar_gestao":
            updates["pendencia"] = "GESTAO"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_gestao"] = True
        elif acao == "convocar_responsavel":
            updates["pendencia"] = "RESPONSAVEL"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_responsavel"] = True

        resp = db.table("ocorrencias").update(updates).eq("numero", numero).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/gerar_pdf_ocorrencias", methods=["POST"])
def api_gerar_pdf_ocorrencias():
    try:
        db = get_supabase()
        data = request.get_json() or {}
        numeros = data.get("numeros", [])
        if not numeros:
            return json_error("Nenhuma ocorrência selecionada", 400)
        db.table("ocorrencias").update({"impressao_pdf": True}).in_("numero", numeros).execute()
        numeros_str = ",".join(str(n) for n in numeros)
        return jsonify({"success": True, "print_url": f"/relatorio_ocorrencias_pdf?numeros={numeros_str}"})
    except Exception as e:
        return json_error(e)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
