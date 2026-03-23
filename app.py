from flask import Flask, render_template, request, jsonify, redirect
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import os

# 👇 IMPORT DOS MÓDULOS NOVOS
from modulos_profissionais import registrar_modulos_profissionais

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE não configurado")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# FUNÇÕES BASE
# =========================================================

def now_iso():
    return datetime.utcnow().isoformat()

def json_error(message, status=500):
    return jsonify({"success": False, "error": str(message)}), status


# 👇 REGISTRA OS MÓDULOS NOVOS (DASHBOARD, CADASTRO, TUTORIA, FREQUÊNCIA)
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
# OCORRÊNCIAS (SEU MÓDULO ORIGINAL)
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


# =========================================================
# APIs BÁSICAS
# =========================================================

@app.route("/api/professores")
def api_professores():
    try:
        resp = supabase.table("d_funcionarios").select("*").order("nome").execute()
        dados = resp.data or []

        professores = []
        for item in dados:
            funcao = (item.get("funcao") or "").upper()
            tipo = (item.get("tipo") or "").upper()

            if "PROFESSOR" in funcao or tipo == "DOCENTE":
                professores.append(item)

        return jsonify(professores)

    except Exception as e:
        return json_error(e)


@app.route("/api/salas_por_professor/<int:professor_id>")
def api_salas_por_professor(professor_id):
    try:
        resp = supabase.table("d_salas").select("*").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos_por_sala/<int:sala_id>")
def api_alunos_por_sala(sala_id):
    try:
        resp = (
            supabase.table("d_alunos")
            .select("*")
            .eq("sala_id", sala_id)
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


# =========================================================
# REGISTRAR OCORRÊNCIA
# =========================================================

@app.route("/api/registrar_ocorrencia", methods=["POST"])
def registrar_ocorrencia():
    try:
        data = request.get_json()

        numero = int(datetime.now().timestamp())

        payload = {
            "numero": numero,
            "data_hora": now_iso(),
            "aluno_id": data.get("aluno_id"),
            "professor_id": data.get("professor_id"),
            "professor_nome": data.get("professor_nome"),
            "descricao": data.get("descricao"),
            "atendimento_professor": data.get("atendimento_professor"),
            "status": "ATENDIMENTO",
            "pendencia": "TUTOR",
        }

        supabase.table("ocorrencias").insert(payload).execute()

        return jsonify({"success": True, "numero": numero})

    except Exception as e:
        return json_error(e)


# =========================================================
# LISTAR OCORRÊNCIAS
# =========================================================

@app.route("/api/ocorrencias")
def listar_ocorrencias():
    try:
        resp = supabase.table("ocorrencias").select("*").order("numero", desc=True).execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


# =========================================================
# DETALHE OCORRÊNCIA
# =========================================================

@app.route("/api/ocorrencia/<int:numero>")
def detalhe_ocorrencia(numero):
    try:
        resp = supabase.table("ocorrencias").select("*").eq("numero", numero).execute()
        return jsonify(resp.data[0] if resp.data else {})
    except Exception as e:
        return json_error(e)


# =========================================================
# SALVAR ATENDIMENTO (COM RESPONSÁVEL)
# =========================================================

@app.route("/api/salvar_atendimento", methods=["POST"])
def salvar_atendimento():
    try:
        data = request.get_json()

        numero = data.get("numero")
        tipo = data.get("tipo")
        texto = data.get("texto")

        campo = f"atendimento_{tipo}"

        update = {
            campo: texto,
            "status": "FINALIZADA",
            "pendencia": None
        }

        supabase.table("ocorrencias").update(update).eq("numero", numero).execute()

        return jsonify({"success": True})

    except Exception as e:
        return json_error(e)


# =========================================================
# PDF (MARCAR COMO IMPRESSO)
# =========================================================

@app.route("/api/gerar_pdf_ocorrencias", methods=["POST"])
def gerar_pdf():
    try:
        data = request.get_json()
        numeros = data.get("numeros", [])

        supabase.table("ocorrencias").update({
            "impressao_pdf": True
        }).in_("numero", numeros).execute()

        return jsonify({"success": True})

    except Exception as e:
        return json_error(e)


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
