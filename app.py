from flask import Flask, render_template, request, jsonify, redirect
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def now_iso():
    return datetime.utcnow().isoformat()

def get_next_numero():
    resp = supabase.table("ocorrencias").select("numero").order("numero", desc=True).limit(1).execute()
    if resp.data:
        return int(resp.data[0]["numero"]) + 1
    return 1

@app.route("/api/ocorrencias_todas")
def api_ocorrencias_todas():
    try:
        resp = supabase.table("ocorrencias").select("*").order("numero", desc=True).execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ocorrencia_detalhes")
def api_ocorrencia_detalhes():
    numero = request.args.get("numero")
    if not numero:
        return jsonify({"error": "Número não informado"}), 400

    try:
        resp = supabase.table("ocorrencias").select("*").eq("numero", numero).limit(1).execute()
        if not resp.data:
            return jsonify({"error": "Ocorrência não encontrada"}), 404
        return jsonify(resp.data[0])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/registrar_ocorrencia", methods=["POST"])
def api_registrar_ocorrencia():
    try:
        data = request.get_json() or {}

        aluno_id = data.get("aluno_id")
        professor_id = data.get("professor_id")
        professor_nome = data.get("professor_nome")
        descricao = data.get("descricao")
        atendimento_professor = data.get("atendimento_professor")

        if not all([aluno_id, professor_id, professor_nome, descricao, atendimento_professor]):
            return jsonify({"success": False, "error": "Campos obrigatórios faltando"}), 400

        resp_aluno = (
            supabase.table("d_alunos")
            .select("id, nome, sala_id, sala_nome, tutor_id, tutor_nome")
            .eq("id", aluno_id)
            .limit(1)
            .execute()
        )

        if not resp_aluno.data:
            return jsonify({"success": False, "error": "Aluno não encontrado"}), 404

        aluno = resp_aluno.data[0]
        destino = (data.get("destino") or "").lower().strip()

        pendencia = "FINALIZADA"
        status = "FINALIZADA"
        solicitado_tutor = False
        solicitado_coordenacao = False
        solicitado_gestao = False

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
            "numero": get_next_numero(),
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
            "pendencia": pendencia,
            "status": status,
            "impressao_pdf": False,
        }

        resp = supabase.table("ocorrencias").insert(payload).execute()
        numero = resp.data[0]["numero"] if resp.data else None

        return jsonify({"success": True, "numero": numero})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ocorrencias/<int:ocorrencia_id>/atendimento", methods=["PUT"])
def api_salvar_atendimento(ocorrencia_id):
    try:
        data = request.get_json() or {}
        tipo = (data.get("tipo") or "").strip().lower()
        texto = (data.get("texto") or "").strip()
        acao = (data.get("acao") or "").strip().lower()

        if not texto:
            return jsonify({"ok": False, "error": "Texto do atendimento é obrigatório"}), 400

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
            return jsonify({"ok": False, "error": "Tipo inválido"}), 400

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

        resp = supabase.table("ocorrencias").update(updates).eq("id", ocorrencia_id).execute()
        return jsonify({"ok": True, "data": resp.data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK"

# Dashboard
@app.route("/dashboard_ocorrencias")
def dashboard_ocorrencias():
    return render_template("dashboard_ocorrencias.html")

# Ocorrências
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

# aliases antigos -> tela única de ocorrências
@app.route("/gestao_ocorrencia_aberta")
@app.route("/gestao_ocorrencia_abertas")
@app.route("/gestao_ocorrencia_finalizada")
@app.route("/gestao_ocorrencia_finalizadas")
def aliases_ocorrencias():
    return redirect("/gestao_ocorrencia")

# Frequência
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

# Tecnologia
@app.route("/gestao_tecnologia")
def gestao_tecnologia():
    return render_template("gestao_tecnologia.html")

# Tutoria
@app.route("/gestao_tutoria")
def gestao_tutoria():
    return render_template("gestao_tutoria.html")

# Cadastro
@app.route("/gestao_cadastro")
def gestao_cadastro():
    return render_template("gestao_cadastro.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
