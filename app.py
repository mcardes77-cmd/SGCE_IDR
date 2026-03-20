from flask import Flask, render_template, request, jsonify, redirect
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
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

def now_iso():
    return datetime.utcnow().isoformat()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    return render_template("gestao_ocorrencia.html")

@app.route("/gestao_ocorrencia_editar")
@app.route("/gestao_ocorrencia_editar/<int:ocorrencia_id>")
def gestao_ocorrencia_editar(ocorrencia_id=None):
    return render_template("gestao_ocorrencia_editar.html", ocorrencia_id=ocorrencia_id)

@app.route("/api/ocorrencias/<int:ocorrencia_id>/atendimento", methods=["PUT"])
def api_salvar_atendimento(ocorrencia_id):
    try:
        db = get_supabase()
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
        resp = db.table("ocorrencias").update(updates).eq("id", ocorrencia_id).execute()
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
        return jsonify({"success": True, "message": "Ocorrências marcadas como impressas."})
    except Exception as e:
        return json_error(e)
