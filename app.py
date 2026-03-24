from flask import Flask, render_template, request, jsonify, redirect
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import os

from modulos_profissionais import registrar_modulos_profissionais

load_dotenv()

app = Flask(_name_)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY não configurados.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def now_iso():
    return datetime.utcnow().isoformat()


def json_error(message, status=500):
    return jsonify({"success": False, "error": str(message)}), status


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


# =========================================================
# REGISTRA MÓDULOS PROFISSIONAIS
# =========================================================
registrar_modulos_profissionais(app, supabase, json_error, now_iso)


# =========================================================
# ROTAS PRINCIPAIS
# =========================================================
@app.route("/")
def home():
    return redirect("/dashboard_geral")


@app.route("/health")
def health():
    return "OK"


# =========================================================
# OCORRÊNCIAS - TELAS
# =========================================================
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
    return render_template("gestao_relatorio_impressao.html")


# =========================================================
# APIS BÁSICAS
# =========================================================
@app.route("/api/professores")
def api_professores():
    try:
        resp = supabase.table("d_funcionarios").select("*").execute()
        dados = resp.data or []

        professores = []
        for item in dados:
            nome = item.get("nome") or ""
            funcao = (item.get("funcao") or "").upper()
            tipo = (item.get("tipo") or "").upper()

            if (
                "PROFESSOR" in funcao
                or "DOCENTE" in funcao
                or tipo == "DOCENTE"
                or tipo == "PROFESSOR"
            ):
                professores.append({
                    "id": item.get("id"),
                    "nome": nome,
                    "funcao": item.get("funcao") or "",
                    "tipo": item.get("tipo") or ""
                })

        if not professores:
            professores = [
                {
                    "id": item.get("id"),
                    "nome": item.get("nome") or "",
                    "funcao": item.get("funcao") or "",
                    "tipo": item.get("tipo") or ""
                }
                for item in dados
                if item.get("nome")
            ]

        professores.sort(key=lambda x: x["nome"])
        return jsonify(professores)

    except Exception as e:
        return json_error(e)


@app.route("/api/salas_por_professor/<int:professor_id>")
def api_salas_por_professor(professor_id):
    try:
        resp = supabase.table("d_salas").select("*").execute()
        dados = resp.data or []

        salas = []
        for s in dados:
            salas.append({
                "id": s.get("id"),
                "nome": s.get("nome") or s.get("sala") or ""
            })

        salas.sort(key=lambda x: x["nome"])
        return jsonify(salas)
    except Exception as e:
        return json_error(e)


# =========================================================
# OCORRÊNCIAS - APIS
# =========================================================
@app.route("/api/ocorrencias")
@app.route("/api/ocorrencias_todas")
def listar_ocorrencias():
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


@app.route("/api/ocorrencia/<int:numero>")
def detalhe_ocorrencia(numero):
    try:
        resp = (
            supabase.table("ocorrencias")
            .select("*")
            .eq("numero", numero)
            .limit(1)
            .execute()
        )
        return jsonify(resp.data[0] if resp.data else {})
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
def registrar_ocorrencia():
    try:
        data = request.get_json() or {}

        aluno_id = data.get("aluno_id")
        professor_id = data.get("professor_id")
        professor_nome = data.get("professor_nome")
        descricao = data.get("descricao")
        atendimento_professor = data.get("atendimento_professor")
        destino = (data.get("destino") or "nenhum").lower().strip()

        if not aluno_id:
            return json_error("Aluno não informado", 400)
        if not professor_id:
            return json_error("Professor não informado", 400)
        if not professor_nome:
            return json_error("Professor não informado", 400)
        if not descricao:
            return json_error("Descrição não informada", 400)
        if not atendimento_professor:
            return json_error("Atendimento do professor não informado", 400)

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

        pendencia = "FINALIZADA"
        status = "FINALIZADA"
        solicitado_tutor = False
        solicitado_coordenacao = False
        solicitado_gestao = False
        solicitado_responsavel = False

        if destino == "tutor":
            pendencia = "TUTOR"
            status = "ATENDIMENTO"
            solicitado_tutor = True
        elif destino == "coordenacao":
            pendencia = "COORDENACAO"
            status = "ATENDIMENTO"
            solicitado_coordenacao = True
        elif destino == "gestao":
            pendencia = "GESTAO"
            status = "ATENDIMENTO"
            solicitado_gestao = True

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
            "pendencia": pendencia,
            "status": status,
            "solicitado_tutor": solicitado_tutor,
            "solicitado_coordenacao": solicitado_coordenacao,
            "solicitado_gestao": solicitado_gestao,
            "solicitado_responsavel": solicitado_responsavel,
            "impressao_pdf": False
        }

        resp = supabase.table("ocorrencias").insert(payload).execute()
        numero = resp.data[0]["numero"] if resp.data else None

        return jsonify({"success": True, "numero": numero})

    except Exception as e:
        return json_error(e)


@app.route("/api/salvar_atendimento", methods=["POST"])
def salvar_atendimento():
    try:
        data = request.get_json() or {}

        numero = data.get("numero")
        tipo = (data.get("tipo") or "").strip().lower()
        texto = data.get("texto")

        if not numero:
            return json_error("Número da ocorrência não informado", 400)
        if not tipo:
            return json_error("Tipo não informado", 400)
        if not texto:
            return json_error("Texto do atendimento não informado", 400)

        campo = f"atendimento_{tipo}"

        update = {
            campo: texto,
            "status": "FINALIZADA",
            "pendencia": "FINALIZADA",
            "solicitado_tutor": False,
            "solicitado_coordenacao": False,
            "solicitado_gestao": False,
            "solicitado_responsavel": False
        }

        supabase.table("ocorrencias").update(update).eq("numero", numero).execute()

        return jsonify({"success": True})

    except Exception as e:
        return json_error(e)


@app.route("/api/gerar_pdf_ocorrencias", methods=["POST"])
def gerar_pdf_ocorrencias():
    try:
        data = request.get_json() or {}
        numeros = data.get("numeros", [])

        if not numeros:
            return json_error("Nenhuma ocorrência selecionada", 400)

        supabase.table("ocorrencias").update({
            "impressao_pdf": True
        }).in_("numero", numeros).execute()

        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


# =========================================================
# RUN
# =========================================================
if _name_ == "_main_":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
