from flask import Flask, render_template, jsonify
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY não configurados.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def json_error(message, status=500):
    return jsonify({"success": False, "error": str(message)}), status

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK"

@app.route("/teste")
def teste():
    return "TESTE OK"

@app.route("/api/debug_url")
def api_debug_url():
    return jsonify({
        "SUPABASE_URL": SUPABASE_URL,
        "supabase_configurado": bool(SUPABASE_URL and SUPABASE_KEY)
    })

@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    return render_template("gestao_ocorrencia.html")

@app.route("/gestao_ocorrencia_nova")
def gestao_ocorrencia_nova():
    return render_template("gestao_ocorrencia_nova.html")

@app.route("/api/professores")
def api_professores():
    try:
        db = get_supabase()
        resp = db.table("d_funcionarios").select("*").order("nome").execute()
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
        # provisório: retorna todas as salas
        resp = db.table("d_salas").select("*").order("nome").execute()
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

from datetime import datetime
from flask import request

def now_iso():
    return datetime.utcnow().isoformat()

def get_next_numero_ocorrencia():
    db = get_supabase()
    resp = (
        db.table("ocorrencias")
        .select("numero")
        .order("numero", desc=True)
        .limit(1)
        .execute()
    )
    if resp.data:
        return int(resp.data[0]["numero"]) + 1
    return 1

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
        destino = (data.get("destino") or "nenhum").lower().strip()

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

        resp_aluno = (
            db.table("d_alunos")
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
        elif destino == "nenhum":
            pendencia = "FINALIZADA"
            status = "FINALIZADA"

        payload = {
            "numero": get_next_numero_ocorrencia(),
            "data_hora": now_iso(),
            "aluno_id": aluno.get("id"),
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
            "impressao_pdf": False
        }

        resp = db.table("ocorrencias").insert(payload).execute()

        numero = None
        if resp.data and len(resp.data) > 0:
            numero = resp.data[0].get("numero")

        return jsonify({
            "success": True,
            "numero": numero
        })

    except Exception as e:
        return json_error(e)

@app.route("/api/ocorrencias_todas")
def api_ocorrencias_todas():
    try:
        db = get_supabase()
        resp = (
            db.table("ocorrencias")
            .select("*")
            .order("numero", desc=True)
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
