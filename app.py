from flask import Flask, render_template, request, jsonify, redirect
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def json_error(message, status=500):
    return jsonify({"success": False, "error": str(message)}), status


def get_supabase():
    if supabase is None:
        raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY não configurados.")
    return supabase


# =========================
# ROTAS PRINCIPAIS
# =========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return "OK"


# =========================
# TELAS
# =========================

@app.route("/dashboard_ocorrencias")
def dashboard_ocorrencias():
    return render_template("dashboard_ocorrencias.html")


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


@app.route("/gestao_ocorrencia_aberta")
@app.route("/gestao_ocorrencia_abertas")
@app.route("/gestao_ocorrencia_finalizada")
@app.route("/gestao_ocorrencia_finalizadas")
def aliases_ocorrencias():
    return redirect("/gestao_ocorrencia")


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


@app.route("/gestao_tecnologia")
def gestao_tecnologia():
    return render_template("gestao_tecnologia.html")


@app.route("/gestao_tutoria")
def gestao_tutoria():
    return render_template("gestao_tutoria.html")


@app.route("/gestao_cadastro")
def gestao_cadastro():
    return render_template("gestao_cadastro.html")


# =========================
# DEBUG
# =========================

@app.route("/api/debug_url")
def debug_url():
    return jsonify({
        "SUPABASE_URL": SUPABASE_URL,
        "supabase_configurado": bool(SUPABASE_URL and SUPABASE_KEY)
    })


# =========================
# APIS BASE
# =========================

@app.route("/api/salas")
def api_salas():
    try:
        db = get_supabase()
        resp = db.table("d_salas").select("*").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/funcionarios")
def api_funcionarios():
    try:
        db = get_supabase()
        resp = db.table("d_funcionarios").select("*").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/professores")
def api_professores():
    try:
        db = get_supabase()
        resp = db.table("d_funcionarios").select("*").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/salas_por_professor/<int:professor_id>")
def api_salas_por_professor(professor_id):
    try:
        db = get_supabase()
        # provisório: retorna todas as salas
        resp = db.table("d_salas").select("id,nome").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos")
def api_alunos():
    try:
        db = get_supabase()
        resp = db.table("d_alunos").select("*").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos_por_sala/<int:sala_id>")
def api_alunos_por_sala(sala_id):
    try:
        db = get_supabase()
        resp = (
            db.table("d_alunos")
            .select("*")
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
        db = get_supabase()
        resp = (
            db.table("d_alunos")
            .select("*")
            .eq("tutor_id", tutor_id)
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


# =========================
# OCORRÊNCIAS - LEITURA
# =========================

@app.route("/api/ocorrencias_todas")
def api_ocorrencias_todas():
    try:
        db = get_supabase()
        resp = db.table("ocorrencias").select("*").order("numero", desc=True).execute()
        return jsonify(resp.data or [])
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

        return jsonify(resp.data[0])
    except Exception as e:
        return json_error(e)


# =========================
# TESTE
# =========================

@app.route("/teste")
def teste():
    return "TESTE OK"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
