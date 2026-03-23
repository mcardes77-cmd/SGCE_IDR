
from flask import Flask, render_template, request, jsonify, make_response
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.pagesizes import A4
import os

load_dotenv()
app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def db():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gestao_ocorrencia")
def gestao():
    return render_template("gestao_ocorrencia.html")

@app.route("/gestao_ocorrencia_nova")
def nova():
    return render_template("gestao_ocorrencia_nova.html")

@app.route("/gestao_ocorrencia_editar")
def editar():
    return render_template("gestao_ocorrencia_editar.html")

@app.route("/api/professores")
def professores():
    r = db().table("d_funcionarios").select("*").order("nome").execute()
    return jsonify(r.data or [])

@app.route("/api/salas_por_professor/<int:id>")
def salas(id):
    r = db().table("d_salas").select("*").order("nome").execute()
    return jsonify(r.data or [])

@app.route("/api/alunos_por_sala/<int:id>")
def alunos(id):
    r = db().table("d_alunos").select("*").eq("sala_id", id).execute()
    return jsonify(r.data or [])

@app.route("/api/ocorrencias_todas")
def ocorrencias():
    r = db().table("ocorrencias").select("*").order("numero", desc=True).execute()
    return jsonify(r.data or [])

@app.route("/api/ocorrencia_detalhes")
def detalhe():
    numero = request.args.get("numero")
    r = db().table("ocorrencias").select("*").eq("numero", numero).execute()
    return jsonify(r.data[0] if r.data else {})

@app.route("/api/registrar_ocorrencia", methods=["POST"])
def registrar():
    data = request.get_json()
    ultimo = db().table("ocorrencias").select("numero").order("numero", desc=True).limit(1).execute()
    numero = (ultimo.data[0]["numero"] + 1) if ultimo.data else 1

    payload = {
        "numero": numero,
        "data_hora": datetime.utcnow().isoformat(),
        "aluno_id": data["aluno_id"],
        "aluno_nome": data.get("aluno_nome"),
        "professor_nome": data.get("professor_nome"),
        "descricao": data["descricao"],
        "atendimento_professor": data["atendimento_professor"],
        "pendencia": data.get("destino","FINALIZADA").upper(),
        "status": "ATENDIMENTO"
    }

    db().table("ocorrencias").insert(payload).execute()
    return jsonify({"success": True, "numero": numero})

@app.route("/api/ocorrencias/<int:id>/atendimento", methods=["PUT"])
def atendimento(id):
    data = request.get_json()
    updates = {}

    if data["tipo"] == "tutor":
        updates["atendimento_tutor"] = data["texto"]
    elif data["tipo"] == "coordenacao":
        updates["atendimento_coordenacao"] = data["texto"]
    elif data["tipo"] == "gestao":
        updates["atendimento_gestao"] = data["texto"]
    elif data["tipo"] == "responsavel":
        updates["atendimento_responsavel"] = data["texto"]

    if data["acao"] == "finalizar":
        updates["status"] = "FINALIZADA"
        updates["pendencia"] = "FINALIZADA"

    db().table("ocorrencias").update(updates).eq("id", id).execute()
    return jsonify({"success": True})

@app.route("/api/gerar_pdf_ocorrencias", methods=["POST"])
def pdf():
    numeros = request.json["numeros"]
    resp = db().table("ocorrencias").select("*").in_("numero", numeros).execute()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    conteudo = []

    for oc in resp.data:
        conteudo.append(Paragraph(f"Ocorrência {oc['numero']} - {oc.get('aluno_nome','')}", None))

    doc.build(conteudo)
    buffer.seek(0)

    return make_response(buffer.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename=ocorrencias.pdf'
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
