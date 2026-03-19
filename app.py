from flask import Flask, render_template, request, jsonify, redirect
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY não configurados.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================
# FUNÇÕES AUXILIARES
# =========================

def now_iso():
    return datetime.utcnow().isoformat()


def get_next_numero_ocorrencia():
    resp = (
        supabase.table("ocorrencias")
        .select("numero")
        .order("numero", desc=True)
        .limit(1)
        .execute()
    )
    if resp.data:
        return int(resp.data[0]["numero"]) + 1
    return 1


def json_error(message, status=500):
    return jsonify({"success": False, "error": str(message)}), status


# =========================
# ROTAS DE TELA
# =========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return "OK"


@app.route("/dashboard_ocorrencias")
def dashboard_ocorrencias():
    return render_template("dashboard_ocorrencias.html")


# -------- OCORRÊNCIAS --------

@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    return render_template("gestao_ocorrencia.html")


@app.route("/gestao_ocorrencia_nova")
def gestao_ocorrencia_nova():
    return render_template("gestao_ocorrencia_nova.html")


@app.route("/gestao_ocorrencia_editar")
def gestao_ocorrencia_editar():
    return render_template("gestao_ocorrencia_editar.html")


@app.route("/gestao_relatorio_impressao")
def gestao_relatorio_impressao():
    return redirect("/gestao_ocorrencia")


# aliases antigos -> redireciona para a tela única
@app.route("/gestao_ocorrencia_aberta")
@app.route("/gestao_ocorrencia_abertas")
@app.route("/gestao_ocorrencia_finalizada")
@app.route("/gestao_ocorrencia_finalizadas")
def aliases_ocorrencias():
    return redirect("/gestao_ocorrencia")


# -------- FREQUÊNCIA --------

@app.route("/gestao_frequencia")
def gestao_frequencia():
    return render_template("gestao_frequencia.html")


@app.route("/gestao_frequencia_registro")
def gestao_frequencia_registro():
    return render_template("gestao_frequencia_registro.html")


@app.route("/gestao_frequencia_atraso")
def gestao_frequencia_atraso():
    return render_template("gestao_frequencia_atraso.html")


@app.route("/gestao_frequencia_saida")
def gestao_frequencia_saida():
    return render_template("gestao_frequencia_saida.html")


@app.route("/gestao_relatorio_frequencia")
def gestao_relatorio_frequencia():
    return render_template("gestao_relatorio_frequencia.html")


# -------- TECNOLOGIA --------

@app.route("/gestao_tecnologia")
def gestao_tecnologia():
    return render_template("gestao_tecnologia.html")


# -------- TUTORIA --------

@app.route("/gestao_tutoria")
def gestao_tutoria():
    return render_template("gestao_tutoria.html")


# -------- CADASTRO --------

@app.route("/gestao_cadastro")
def gestao_cadastro():
    return render_template("gestao_cadastro.html")


# =========================
# APIS BASE - SUPABASE
# =========================

@app.route("/api/salas")
def api_salas():
    try:
        resp = (
            supabase.table("d_salas")
            .select("*")
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/funcionarios")
def api_funcionarios():
    try:
        resp = (
            supabase.table("d_funcionarios")
            .select("id,nome,tipo,funcao,ativo")
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/professores")
def api_professores():
    ...
    professores = []
    for item in dados:
        funcao = (item.get("funcao") or "").upper()
        tipo = (item.get("tipo") or "").upper()

        if (
            "PROFESSOR" in funcao
            or "TUTOR" in funcao
            or tipo == "DOCENTE"
        ):
            professores.append(item)


@app.route("/api/salas_por_professor/<int:professor_id>")
def api_salas_por_professor(professor_id):
    try:
        # provisório: retorna todas as salas
        resp = (
            supabase.table("d_salas")
            .select("id,nome")
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos")
def api_alunos():
    try:
        resp = (
            supabase.table("d_alunos")
            .select("*")
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos_por_sala/<int:sala_id>")
def api_alunos_por_sala(sala_id):
    try:
        resp = (
            supabase.table("d_alunos")
            .select("id,nome,tutor_id,tutor_nome,sala_id,sala_nome")
            .eq("sala_id", sala_id)
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos_por_tutor/<int:tutor_id>")
def api_alunos_por_tutor(tutor_id):
    try:
        resp = (
            supabase.table("d_alunos")
            .select("id,nome,tutor_id,tutor_nome,sala_id,sala_nome")
            .eq("tutor_id", tutor_id)
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/debug_url")
def debug_url():
    return {
        "SUPABASE_URL": SUPABASE_URL
    }


# =========================
# APIS - OCORRÊNCIAS
# =========================

@app.route("/api/ocorrencias_todas")
def api_ocorrencias_todas():
    try:
        resp = (
            supabase.table("ocorrencias")
            .select("*")
            .order("numero", desc=True)
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencia_detalhes")
def api_ocorrencia_detalhes():
    numero = request.args.get("numero")
    if not numero:
        return json_error("Número não informado", 400)

    try:
        resp = (
            supabase.table("ocorrencias")
            .select("*")
            .eq("numero", numero)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return json_error("Ocorrência não encontrada", 404)

        return jsonify(resp.data[0])
    except Exception as e:
        return json_error(e)


@app.route("/api/registrar_ocorrencia", methods=["POST"])
def api_registrar_ocorrencia():
    try:
        data = request.get_json() or {}

        aluno_id = data.get("aluno_id")
        professor_id = data.get("professor_id")
        professor_nome = data.get("professor_nome")
        descricao = data.get("descricao")
        atendimento_professor = data.get("atendimento_professor")
        destino = (data.get("destino") or "finalizar").lower().strip()

        if not all([aluno_id, professor_id, professor_nome, descricao, atendimento_professor]):
            return json_error("Campos obrigatórios faltando", 400)

        resp_aluno = (
            supabase.table("d_alunos")
            .select("id,nome,sala_id,sala_nome,tutor_id,tutor_nome")
            .eq("id", aluno_id)
            .limit(1)
            .execute()
        )

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
            "aluno_id": aluno["id"],
            "aluno_nome": aluno.get("nome"),
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
            "impressao_pdf": False,
        }

        resp = supabase.table("ocorrencias").insert(payload).execute()
        numero = resp.data[0]["numero"] if resp.data else None

        return jsonify({"success": True, "numero": numero})
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencias/<int:ocorrencia_id>/atendimento", methods=["PUT"])
def api_salvar_atendimento(ocorrencia_id):
    try:
        data = request.get_json() or {}
        tipo = (data.get("tipo") or "").strip().lower()
        texto = (data.get("texto") or "").strip()
        acao = (data.get("acao") or "").strip().lower()

        if not texto:
            return json_error("Texto do atendimento é obrigatório", 400)

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

        # fluxo profissional
        if acao == "finalizar":
            updates["pendencia"] = "FINALIZADA"
            updates["status"] = "FINALIZADA"
            updates["solicitado_tutor"] = False
            updates["solicitado_coordenacao"] = False
            updates["solicitado_gestao"] = False
            updates["solicitado_responsavel"] = False

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

        resp = (
            supabase.table("ocorrencias")
            .update(updates)
            .eq("id", ocorrencia_id)
            .execute()
        )

        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/gerar_pdf_ocorrencias", methods=["POST"])
def api_gerar_pdf_ocorrencias():
    try:
        data = request.get_json() or {}
        numeros = data.get("numeros", [])

        if not numeros:
            return json_error("Nenhuma ocorrência selecionada", 400)

        (
            supabase.table("ocorrencias")
            .update({"impressao_pdf": True})
            .in_("numero", numeros)
            .execute()
        )

        return jsonify({"success": True, "message": "Ocorrências marcadas como impressas."})
    except Exception as e:
        return json_error(e)


# =========================
# APIS - TUTORIA
# =========================

@app.route("/api/agendar_tutoria", methods=["POST"])
def api_agendar_tutoria():
    try:
        data = request.get_json() or {}
        payload = {
            "tutor_id": data.get("tutor_id"),
            "aluno_id": data.get("aluno_id"),
            "data_agendamento": data.get("data_agendamento"),
            "hora_agendamento": data.get("hora_agendamento"),
            "created_at": now_iso(),
        }
        resp = supabase.table("agendamentos_tutoria").insert(payload).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/salvar_registro_atendimento", methods=["POST"])
def api_salvar_registro_atendimento():
    try:
        data = request.get_json() or {}
        payload = {
            "tutor_id": data.get("tutor_id"),
            "aluno_id": data.get("aluno_id"),
            "registro": data.get("registro"),
            "data_registro": data.get("data_registro"),
            "created_at": now_iso(),
        }
        resp = supabase.table("atendimentos_tutoria").insert(payload).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/ficha_tutoria/<int:aluno_id>")
def api_ficha_tutoria(aluno_id):
    try:
        aluno_resp = (
            supabase.table("d_alunos")
            .select("*")
            .eq("id", aluno_id)
            .limit(1)
            .execute()
        )
        if not aluno_resp.data:
            return json_error("Aluno não encontrado", 404)

        aluno = aluno_resp.data[0]

        ocorr_resp = (
            supabase.table("ocorrencias")
            .select("numero,data_hora,descricao,status")
            .eq("aluno_id", aluno_id)
            .order("numero", desc=True)
            .limit(10)
            .execute()
        )

        return jsonify({
            "aluno_nome": aluno.get("nome"),
            "tutor_nome": aluno.get("tutor_nome"),
            "sala_nome": aluno.get("sala_nome"),
            "ra": aluno.get("id"),
            "ocorrencias": ocorr_resp.data or []
        })
    except Exception as e:
        return json_error(e)


@app.route("/api/salvar_notas_tutoria", methods=["POST"])
def api_salvar_notas_tutoria():
    try:
        data = request.get_json() or {}
        payload = {
            "tutor_id": data.get("tutor_id"),
            "aluno_id": data.get("aluno_id"),
            "bimestre": data.get("bimestre"),
            "notas": data.get("notas"),
            "created_at": now_iso(),
        }
        resp = supabase.table("notas_aluno").insert(payload).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


# =========================
# APIS - FREQUÊNCIA
# =========================

@app.route("/api/frequencia/status")
def api_frequencia_status():
    try:
        sala_id = request.args.get("sala_id")
        data_ref = request.args.get("data")

        resp = (
            supabase.table("f_frequencia")
            .select("id")
            .eq("sala_id", sala_id)
            .eq("data", data_ref)
            .limit(1)
            .execute()
        )

        return jsonify({"registrada": bool(resp.data)})
    except Exception as e:
        return json_error(e)


@app.route("/api/salvar_frequencia_unificada", methods=["POST"])
def api_salvar_frequencia_unificada():
    try:
        registros = request.get_json() or []
        if not isinstance(registros, list) or not registros:
            return json_error("Nenhum registro recebido", 400)

        resp = supabase.table("f_frequencia").insert(registros).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/frequencia")
def api_frequencia():
    try:
        sala = request.args.get("sala")
        mes = request.args.get("mes")

        alunos_resp = (
            supabase.table("d_alunos")
            .select("id,nome,sala_id")
            .eq("sala_id", sala)
            .order("nome")
            .execute()
        )
        alunos = alunos_resp.data or []

        freq_resp = (
            supabase.table("f_frequencia")
            .select("*")
            .eq("sala_id", sala)
            .execute()
        )
        frequencias = freq_resp.data or []

        resultado = []
        for aluno in alunos:
            mapa = {}
            for f in frequencias:
                if f.get("aluno_id") == aluno["id"]:
                    data_freq = f.get("data")
                    if data_freq:
                        mapa[data_freq] = {
                            "status": f.get("status"),
                            "hora_entrada": f.get("hora_entrada"),
                            "hora_saida": f.get("hora_saida"),
                            "motivo_atraso": f.get("motivo_atraso"),
                            "motivo_saida": f.get("motivo_saida"),
                        }

            resultado.append({
                "id": aluno["id"],
                "nome": aluno["nome"],
                "frequencia": mapa
            })

        return jsonify(resultado)
    except Exception as e:
        return json_error(e)


@app.route("/api/frequencia_detalhes/<int:aluno_id>/<data_ref>")
def api_frequencia_detalhes(aluno_id, data_ref):
    try:
        resp = (
            supabase.table("f_frequencia")
            .select("*")
            .eq("aluno_id", aluno_id)
            .eq("data", data_ref)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return json_error("Detalhe não encontrado", 404)

        return jsonify(resp.data[0])
    except Exception as e:
        return json_error(e)


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 
