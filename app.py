from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
from datetime import datetime, timedelta, date
import os
import unicodedata
from zoneinfo import ZoneInfo

# =========================================================
# CONFIG
# =========================================================
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "sgce_secret_change_me")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def json_error(message, status=500):
    return jsonify({"success": False, "error": str(message)}), status

def now_iso():
    return now_sp_iso()

def normalize_aluno_nome(aluno):
    return aluno.get("nome") or aluno.get("aluno_nome") or ""

def normalize_sala_nome(item):
    return item.get("sala_nome") or item.get("nome") or item.get("sala") or ""

def get_next_numero_ocorrencia():
    db = get_supabase()
    resp = db.table("ocorrencias").select("numero").order("numero", desc=True).limit(1).execute()
    if resp.data:
        return int(resp.data[0]["numero"]) + 1
    return 1

def now_sp():
    return datetime.now(ZoneInfo("America/Sao_Paulo"))

def now_sp_iso():
    return now_sp().isoformat()

USUARIOS_ACESSO_TOTAL = {
    "ELAINE CRISTINA ARIEDE KACA DO CARMO",
    "MARCELO ANDRE NOGUEIRA CARDES",
    "GRAZIELLE DA SILVA FEIJO VIANA",
    "MARCILENE MANTOVANI COSSENZO PUPIM",
    "MARCOS DE BRITO BORTOLOSSI",
}

def nome_usuario_limpo():
    nome = ((session.get("user") or {}).get("nome") or "").strip().upper()
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    return nome

def acesso_total():
    return nome_usuario_limpo() in USUARIOS_ACESSO_TOTAL

def bloquear_cadastro():
    if not acesso_total():
        return json_error("Acesso restrito aos usuários autorizados.", 403)
    return None

def nome_usuario_limpo():
    nome = ((session.get("user") or {}).get("nome") or "").strip().upper()
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    return nome

def acesso_total():
    return nome_usuario_limpo() in USUARIOS_ACESSO_TOTAL

def bloquear_cadastro():
    if not acesso_total():
        return json_error("Acesso restrito aos usuários autorizados.", 403)
    return None


@app.route("/gestao_cadastro")
def gestao_cadastro():
    if not acesso_total():
        return redirect("/dashboard_geral")
    return render_template("gestao_cadastro.html")


# EXEMPLOS DE BLOQUEIO NAS APIS DE CADASTRO
# Repita o mesmo padrão em TODAS as rotas /api/cadastro/*

@app.route("/api/cadastro/alunos_por_sala_nome")
def api_cadastro_alunos_por_sala_nome():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        sala_nome = (request.args.get("sala_nome") or "").strip()
        if not sala_nome:
            return jsonify([])

        resp = (
            db.table("d_alunos")
            .select("*")
            .eq("sala_nome", sala_nome)
            .eq("situacao_aluno", "ATIVO")
            .order("nome")
            .execute()
        )
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/aluno", methods=["POST"])
def api_cadastro_aluno():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        payload = {
            "nome": data.get("nome"),
            "aluno_nome": data.get("aluno_nome"),
            "sala_nome": data.get("sala_nome"),
            "tutor_id": data.get("tutor_id"),
            "id_tutor": data.get("id_tutor"),
            "tutor_nome": data.get("tutor_nome"),
            "nome_tutor": data.get("nome_tutor"),
            "projeto_de_vida": data.get("projeto_de_vida"),
        }
        resp = db.table("d_alunos").insert(payload).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/aluno/<int:aluno_id>", methods=["PUT"])
def api_editar_aluno(aluno_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        payload = {
            "nome": data.get("nome"),
            "aluno_nome": data.get("aluno_nome"),
            "sala_nome": data.get("sala_nome"),
            "tutor_id": data.get("tutor_id"),
            "id_tutor": data.get("id_tutor"),
            "tutor_nome": data.get("tutor_nome"),
            "nome_tutor": data.get("nome_tutor"),
            "projeto_de_vida": data.get("projeto_de_vida"),
        }
        db.table("d_alunos").update(payload).eq("id", aluno_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/aluno/<int:aluno_id>", methods=["DELETE"])
def api_excluir_aluno(aluno_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        db.table("d_alunos").delete().eq("id", aluno_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/funcionario", methods=["POST"])
def api_cadastro_funcionario():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        resp = db.table("d_funcionarios").insert(data).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/funcionario/<int:func_id>", methods=["PUT"])
def api_editar_funcionario(func_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        db.table("d_funcionarios").update(data).eq("id", func_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/funcionario/<int:func_id>", methods=["DELETE"])
def api_excluir_funcionario(func_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        db.table("d_funcionarios").delete().eq("id", func_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/clube", methods=["POST"])
def api_cadastro_clube():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        resp = db.table("d_clubes_juvenis").insert(data).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/clube/<int:item_id>", methods=["PUT"])
def api_editar_clube(item_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        db.table("d_clubes_juvenis").update(data).eq("id", item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/clube/<int:item_id>", methods=["DELETE"])
def api_excluir_clube(item_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        db.table("d_clubes_juvenis").delete().eq("id", item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/eletiva", methods=["POST"])
def api_cadastro_eletiva():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        resp = db.table("d_eletivas").insert(data).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/eletiva/<int:item_id>", methods=["PUT"])
def api_editar_eletiva(item_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        db.table("d_eletivas").update(data).eq("id", item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/eletiva/<int:item_id>", methods=["DELETE"])
def api_excluir_eletiva(item_id):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        db.table("d_eletivas").delete().eq("id", item_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)



@app.route("/api/cadastro/tutores_com_ocorrencia")
def api_cadastro_tutores_com_ocorrencia():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio
    try:
        db = get_supabase()
        sala_nome = (request.args.get("sala_nome") or "").strip()
        ocorr = db.table("ocorrencias").select("tutor_nome,sala_nome").execute().data or []
        mapa = {}
        for o in ocorr:
            s = (o.get("sala_nome") or "").strip()
            t = (o.get("tutor_nome") or "").strip()
            if not t:
                continue
            if sala_nome and s != sala_nome:
                continue
            mapa[t] = {"id": t, "nome": t}
        return jsonify(sorted(mapa.values(), key=lambda x: x["nome"]))
    except Exception as e:
        return json_error(e)

@app.route("/api/cadastro/alunos_com_ocorrencia")
def api_cadastro_alunos_com_ocorrencia():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio
    try:
        db = get_supabase()
        sala_nome = (request.args.get("sala_nome") or "").strip()
        tutor_nome = (request.args.get("tutor_nome") or "").strip()
        ocorr = db.table("ocorrencias").select("aluno_id,aluno_nome,sala_nome,tutor_nome").execute().data or []
        mapa = {}
        for o in ocorr:
            s = (o.get("sala_nome") or "").strip()
            t = (o.get("tutor_nome") or "").strip()
            if sala_nome and s != sala_nome:
                continue
            if tutor_nome and t != tutor_nome:
                continue
            aluno_id = o.get("aluno_id")
            aluno_nome = (o.get("aluno_nome") or "").strip()
            key = str(aluno_id) if aluno_id is not None else aluno_nome
            if not aluno_nome:
                continue
            mapa[key] = {"id": aluno_id, "nome": aluno_nome}
        return jsonify(sorted(mapa.values(), key=lambda x: (x.get("nome") or "").upper()))
    except Exception as e:
        return json_error(e)

@app.route("/api/cadastro/ocorrencias_do_aluno")
def api_cadastro_ocorrencias_do_aluno():
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio
    try:
        db = get_supabase()
        aluno_id = request.args.get("aluno_id")
        aluno_nome = (request.args.get("aluno_nome") or "").strip()
        query = db.table("ocorrencias").select("numero,data_hora,aluno_nome,sala_nome").order("numero", desc=True)
        data = query.execute().data or []
        rows = []
        for o in data:
            if aluno_id and str(o.get("aluno_id")) == str(aluno_id):
                rows.append(o)
            elif aluno_nome and (o.get("aluno_nome") or "").strip() == aluno_nome:
                rows.append(o)
        return jsonify(rows)
    except Exception as e:
        return json_error(e)

@app.route("/api/atendimentos_por_tutor_detalhe")
def api_atendimentos_por_tutor_detalhe():
    try:
        db = get_supabase()
        tutor = (request.args.get("tutor") or "").strip()
        dados = db.table("atendimentos_tutoria").select("*").order("data_registro", desc=True).execute().data or []
        if tutor:
            dados = [x for x in dados if (x.get("tutor_nome") or "").strip() == tutor]
        detalhe = [{
            "aluno_nome": x.get("aluno_nome"),
            "data_registro": x.get("data_registro"),
            "tipo_atendimento": x.get("tipo_atendimento"),
        } for x in dados]
        return jsonify({"success": True, "rows": detalhe})
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/ocorrencia/<int:numero>", methods=["PUT"])
def api_editar_ocorrencia_cadastro(numero):
    bloqueio = bloquear_cadastro()
    if bloqueio:
        return bloqueio

    try:
        db = get_supabase()
        data = request.get_json() or {}
        db.table("ocorrencias").update(data).eq("numero", numero).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)

USUARIOS_ACESSO_TOTAL = {
    "ELAINE CRISTINA ARIEDE KAÇA DO CARMO",
    "MARCELO ANDRE NOGUEIRA CARDES",
    "GRAZIELLE DA SILVA FEIJO VIANA",
    "MARCILENE MANTOVANI COSSENZO PUPIM",
    "MARCOS DE BRITO BORTOLOSSI",
}

def _usuario_nome_limpo():
    nome = ((session.get("user") or {}).get("nome") or "").strip().upper()
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    return nome

def _eh_acesso_total():
    return _usuario_nome_limpo() in USUARIOS_ACESSO_TOTAL

def _upper_noaccent(v):
    v = (v or "").strip().upper()
    v = unicodedata.normalize("NFD", v)
    return "".join(c for c in v if unicodedata.category(c) != "Mn")
def normalizar_texto(txt):
    return (txt or "").strip().upper()

def usuario_logado_nome():
    user = session.get("user") or {}
    return normalizar_texto(user.get("nome"))

def usuario_tem_acesso_total():
    return usuario_logado_nome() in USUARIOS_ACESSO_TOTAL

def usuario_pode_ver_gestao():
    return usuario_logado_nome() in {
        "ELAINE CRISTINA ARIEDE KAÇA DO CARMO",
        "MARCELO ANDRE NOGUEIRA CARDES",
        "MARCILENE MANTOVANI COSSENZO PUPIM",
    }

def usuario_pode_ver_coordenacao():
    return usuario_logado_nome() in {
        "MARCELO ANDRE NOGUEIRA CARDES",
        "GRAZIELLE DA SILVA FEIJO VIANA",
        "MARCOS DE BRITO BORTOLOSSI",
    }

def usuario_pode_ver_responsavel():
    return usuario_logado_nome() in {
        "ELAINE CRISTINA ARIEDE KAÇA DO CARMO",
        "MARCELO ANDRE NOGUEIRA CARDES",
        "MARCILENE MANTOVANI COSSENZO PUPIM",
    }

def sala_para_serie(sala_nome):
    sala = normalizar_texto(sala_nome)
    if sala.startswith("6º") or sala.startswith("6°"):
        return "6º ANO"
    if sala.startswith("7º") or sala.startswith("7°"):
        return "7º ANO"
    if sala.startswith("8º") or sala.startswith("8°"):
        return "8º ANO"
    if sala.startswith("9º") or sala.startswith("9°"):
        return "9º ANO"
    if sala.startswith("1ª") or sala.startswith("1A") or sala.startswith("1º"):
        return "1ª SÉRIE"
    if sala.startswith("2ª") or sala.startswith("2A") or sala.startswith("2º"):
        return "2ª SÉRIE"
    if sala.startswith("3ª") or sala.startswith("3A") or sala.startswith("3º"):
        return "3ª SÉRIE"
    return sala_nome or ""

# =========================================================
# LOGIN / SEGURANÇA
# =========================================================
ROTAS_LIVRES = {
    "/login",
    "/primeiro_acesso",
    "/api/login",
    "/api/funcionarios_primeiro_acesso",
    "/api/primeiro_acesso",
    "/health",
    "/logout",
}

@app.before_request
def proteger_rotas():
    caminho = request.path or "/"
    if caminho.startswith("/static/"):
        return
    if caminho in ROTAS_LIVRES:
        return
    if "user" not in session:
        return redirect("/login")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/primeiro_acesso")
def primeiro_acesso():
    return render_template("primeiro_acesso.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/api/funcionarios_primeiro_acesso")
def api_funcionarios_primeiro_acesso():
    try:
        db = get_supabase()
        resp = (
            db.table("d_funcionarios")
            .select("id,nome,funcao,tipo")
            .eq("conta_ativada", False)
            .order("nome")
            .execute()
        )
        return jsonify({"success": True, "data": resp.data or []})
    except Exception as e:
        return json_error(e)

@app.route("/api/primeiro_acesso", methods=["POST"])
def api_primeiro_acesso():
    try:
        db = get_supabase()
        data = request.get_json(silent=True) or {}
        funcionario_id = data.get("funcionario_id")
        username = (data.get("username") or "").strip().lower()
        senha = (data.get("senha") or "").strip()
        confirmar = (data.get("confirmar_senha") or "").strip()

        if not funcionario_id:
            return json_error("Selecione o funcionário.", 400)
        if not username or len(username) < 3:
            return json_error("O nome de usuário deve ter pelo menos 3 caracteres.", 400)
        if not senha or len(senha) < 6:
            return json_error("A senha deve ter pelo menos 6 caracteres.", 400)
        if senha != confirmar:
            return json_error("As senhas não conferem.", 400)

        existente = (
            db.table("d_funcionarios")
            .select("id")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        if existente.data:
            return json_error("Esse nome de usuário já está em uso.", 409)

        funcionario = (
            db.table("d_funcionarios")
            .select("id,nome,conta_ativada")
            .eq("id", funcionario_id)
            .limit(1)
            .execute()
        )
        if not funcionario.data:
            return json_error("Funcionário não encontrado.", 404)
        if funcionario.data[0].get("conta_ativada") is True:
            return json_error("Essa conta já foi ativada.", 409)

        db.table("d_funcionarios").update({
            "username": username,
            "senha": senha,
            "conta_ativada": True,
            "primeiro_login": False,
            "updated_at": now_iso()
        }).eq("id", funcionario_id).execute()

        return jsonify({
            "success": True,
            "message": "Conta criada com sucesso.",
            "redirect": "/login"
        })
    except Exception as e:
        return json_error(e)

@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        db = get_supabase()
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip().lower()
        senha = (data.get("senha") or "").strip()

        if not username or not senha:
            return json_error("Informe usuário e senha.", 400)

        resp = (
            db.table("d_funcionarios")
            .select("*")
            .eq("username", username)
            .eq("senha", senha)
            .eq("conta_ativada", True)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return json_error("Usuário ou senha inválidos.", 401)

        user = resp.data[0]
        session["user"] = {
            "id": user.get("id"),
            "nome": user.get("nome"),
            "username": user.get("username"),
            "funcao": user.get("funcao"),
            "tipo": user.get("tipo"),
            "is_tutor": user.get("is_tutor", False),
        }

        return jsonify({"success": True, "redirect": "/dashboard_geral"})
    except Exception as e:
        return json_error(e)

# =========================================================
# HOME
# =========================================================
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return redirect("/dashboard_geral")

@app.route("/health")
def health():
    return "OK"

@app.route("/gestao_notas")
def gestao_notas():
    return render_template("gestao_notas.html")

@app.route("/api/disciplinas_todas")
def disciplinas():
    db = get_supabase()
    r = db.table("d_disciplinas").select("nome").execute()
    nomes = sorted({x['nome'] for x in (r.data or [])})
    return jsonify([{"nome":n} for n in nomes])
# =========================================================
# TELAS PRINCIPAIS
# =========================================================
@app.route("/dashboard_ocorrencias")
def dashboard_ocorrencias():
    return render_template("dashboard_ocorrencias.html")

@app.route("/dashboard_geral")
def dashboard_geral():
    return render_template("dashboard_geral.html")

@app.route("/dashboard_frequencia")
def dashboard_frequencia():
    return render_template("dashboard_frequencia.html")

@app.route("/gestao_relatorios")
def gestao_relatorios():
    return render_template("gestao_relatorios_profissional.html")


@app.route("/gestao_frequencia_avancada")
def gestao_frequencia_avancada():
    return render_template("gestao_frequencia_avancada.html")

@app.route("/gestao_frequencia_lancamento")
def gestao_frequencia_lancamento():
    return render_template("gestao_frequencia_lancamento.html")

@app.route("/gestao_frequencia_atraso")
def gestao_frequencia_atraso():
    return render_template("gestao_frequencia_atraso.html")

@app.route("/gestao_frequencia_saida")
def gestao_frequencia_saida():
    return render_template("gestao_frequencia_saida.html")

@app.route("/api/agendamento_tutoria/<int:agendamento_id>/concluir", methods=["PUT"])
def api_concluir_agendamento_tutoria(agendamento_id):
    try:
        db = get_supabase()
        db.table("agendamentos_tutoria").update({
            "status": "CONCLUIDO",
            "updated_at": now_iso()
        }).eq("id", agendamento_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)

@app.route("/gestao_relatorio_frequencia_avancado")
def gestao_relatorio_frequencia_avancado():
    return render_template("gestao_relatorio_frequencia_avancado.html")

@app.route("/gestao_tutoria")
def gestao_tutoria():
    return render_template("gestao_tutoria.html")

@app.route("/gestao_tutoria_agendamento")
def gestao_tutoria_agendamento():
    return render_template("gestao_tutoria_agendamento.html")

@app.route("/gestao_tutoria_atendimento")
def gestao_tutoria_atendimento():
    return render_template("gestao_tutoria_atendimento.html")

@app.route("/gestao_tutoria_ficha")
def gestao_tutoria_ficha():
    return render_template("gestao_tutoria_ficha.html")

@app.route("/gestao_tutoria_evolucao")
def gestao_tutoria_evolucao():
    return render_template("gestao_tutoria_evolucao.html")

# =========================================================
# OCORRÊNCIAS - TELAS E PDF
# =========================================================
@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    pendencia = normalizar_texto(request.args.get("pendencia"))
    if pendencia == "GESTAO" and not usuario_pode_ver_gestao():
        return redirect("/dashboard_geral")
    if pendencia == "COORDENACAO" and not usuario_pode_ver_coordenacao():
        return redirect("/dashboard_geral")
    if pendencia == "RESPONSAVEL" and not usuario_pode_ver_responsavel():
        return redirect("/dashboard_geral")
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
            data_geracao=datetime.now().strftime("%d/%m/%Y %H:%M"),
        )
    except Exception as e:
        return f"Erro ao abrir relatório: {e}", 500

# =========================================================
# APIs BÁSICAS / CADASTRO
# =========================================================
@app.route("/api/me")
def api_me():
    return jsonify({"success": True, "user": session.get("user")})

@app.route("/api/professores")
def api_professores():
    try:
        db = get_supabase()
        resp = db.table("d_funcionarios").select("id,nome,tipo,funcao,ativo,email").order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/salas")
@app.route("/api/cadastro/salas")
def api_salas():
    try:
        db = get_supabase()
        resp = db.table("d_salas").select("*").order("nome").execute()
        dados = resp.data or []
        for item in dados:
            item["nome"] = normalize_sala_nome(item)
        return jsonify(dados)
    except Exception as e:
        return json_error(e)

@app.route("/api/cadastro/alunos")
@app.route("/api/alunos")
def api_alunos():
    try:
        db = get_supabase()
        resp = db.table("d_alunos").select("*").order("nome").execute()
        dados = resp.data or []
        for item in dados:
            item["nome"] = normalize_aluno_nome(item)
        return jsonify(dados)
    except Exception as e:
        return json_error(e)

@app.route("/api/cadastro/funcionarios")
def api_cadastro_funcionarios():
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
        resp = db.table("d_salas").select("*").order("nome").execute()
        dados = resp.data or []
        for item in dados:
            item["nome"] = normalize_sala_nome(item)
        return jsonify(dados)
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
            .eq("situacao_aluno", "ATIVO")
            .order("nome")
            .execute()
        )
        dados = resp.data or []
        for item in dados:
            item["nome"] = normalize_aluno_nome(item)
        return jsonify(dados)
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencias_todas")
def api_ocorrencias_todas():
    try:
        db = get_supabase()
        resp = db.table("ocorrencias").select("*").order("numero", desc=True).execute()
        dados = resp.data or []

        pendencia = normalizar_texto(request.args.get("pendencia"))
        status = normalizar_texto(request.args.get("status"))

        if not usuario_tem_acesso_total():
            nome = usuario_logado_nome()
            dados = [x for x in dados if normalizar_texto(x.get("tutor_nome")) == nome]

        if pendencia:
            dados = [x for x in dados if normalizar_texto(x.get("pendencia")) == pendencia]
        if status:
            dados = [x for x in dados if normalizar_texto(x.get("status")) == status]

        return jsonify(dados)
    except Exception as e:
        return json_error(e)


@app.route("/api/ocorrencias_por_aluno/<int:aluno_id>")
def api_ocorrencias_por_aluno(aluno_id):
    try:
        db = get_supabase()
        resp = db.table("ocorrencias").select("*").eq("aluno_id", aluno_id).order("numero", desc=True).execute()
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
        item = resp.data[0]
        item["id"] = item.get("numero")
        return jsonify(item)
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
            "aluno_nome": normalize_aluno_nome(aluno),
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
        resp = db.table("ocorrencias").insert(payload).execute()
        numero = resp.data[0].get("numero") if resp.data else None
        return jsonify({"success": True, "numero": numero})
    except Exception as e:
        return json_error(e)

@app.route("/api/ocorrencias/<int:numero>/atendimento", methods=["PUT"])
def api_salvar_atendimento(numero):
    try:
        db = get_supabase()
        data = request.get_json(silent=True) or {}
        tipo = (data.get("tipo") or "").strip().lower()
        texto = (data.get("texto") or "").strip()
        acao = (data.get("acao") or "").strip().lower()

        if not texto:
            return json_error("Texto do atendimento é obrigatório", 400)

        resp_atual = db.table("ocorrencias").select("*").eq("numero", numero).limit(1).execute()
        if not resp_atual.data:
            return json_error("Ocorrência não encontrada", 404)

        ocorrencia = resp_atual.data[0]
        pendencia_atual = (ocorrencia.get("pendencia") or "FINALIZADA").strip().upper()

        updates = {}
        campo_por_tipo = {
            "tutor": "atendimento_tutor",
            "coordenacao": "atendimento_coordenacao",
            "gestao": "atendimento_gestao",
            "responsavel": "atendimento_responsavel",
        }
        campo_dt_por_tipo = {
            "tutor": "dt_atendimento_tutor",
            "coordenacao": "dt_atendimento_coordenacao",
            "gestao": "dt_atendimento_gestao",
        }

        if tipo not in campo_por_tipo:
            return json_error("Tipo inválido", 400)

        updates[campo_por_tipo[tipo]] = texto
        if tipo in campo_dt_por_tipo:
            updates[campo_dt_por_tipo[tipo]] = now_iso()

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
            updates["dt_finalizacao"] = now_iso()
        elif acao == "encaminhar_tutor":
            updates["pendencia"] = "TUTOR"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_tutor"] = True
            updates["dt_finalizacao"] = None
        elif acao == "encaminhar_coordenacao":
            updates["pendencia"] = "COORDENACAO"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_coordenacao"] = True
            updates["dt_finalizacao"] = None
        elif acao == "encaminhar_gestao":
            updates["pendencia"] = "GESTAO"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_gestao"] = True
            updates["dt_finalizacao"] = None
        elif acao == "convocar_responsavel":
            updates["pendencia"] = "RESPONSAVEL"
            updates["status"] = "ATENDIMENTO"
            updates["solicitado_responsavel"] = True
            updates["responsavel_convocado"] = True
            updates["dt_convocacao_responsavel"] = now_iso()
            updates["dt_finalizacao"] = None

        db.table("ocorrencias").update(updates).eq("numero", numero).execute()

        resp_final = db.table("ocorrencias").select("*").eq("numero", numero).limit(1).execute()
        data_final = resp_final.data[0] if resp_final.data else {}
        data_final["id"] = data_final.get("numero")

        return jsonify({
            "success": True,
            "message": "Atendimento salvo com sucesso",
            "data": data_final,
        })
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


# =========================================================
# DASHBOARD DE OCORRÊNCIAS
# =========================================================
@app.route("/api/dashboard_ocorrencias")
def api_dashboard_ocorrencias():
    try:
        db = get_supabase()
        dados = db.table("ocorrencias").select("*").order("numero", desc=True).execute().data or []

        def semana_seg_sex(ref_date):
            inicio = ref_date - timedelta(days=ref_date.weekday())
            fim = inicio + timedelta(days=4)
            return inicio, fim

        datas_validas = []
        for item in dados:
            data_hora = str(item.get("data_hora") or "")[:10]
            try:
                if data_hora:
                    datas_validas.append(datetime.strptime(data_hora, "%Y-%m-%d").date())
            except Exception:
                pass

        referencia = max(datas_validas) if datas_validas else datetime.now().date()
        ultima_segunda = referencia - timedelta(days=referencia.weekday())

        semanas = []
        for i in range(3, -1, -1):
            ini = ultima_segunda - timedelta(days=i * 7)
            fim = ini + timedelta(days=4)
            semanas.append((ini, fim))

        pizza = {
            "finalizadas": 0,
            "tutor": 0,
            "gestao": 0,
            "coordenacao": 0,
            "responsavel": 0
        }

        ranking_salas = {}

        for item in dados:
            status = (item.get("status") or "").upper().strip()
            pendencia = (item.get("pendencia") or "").upper().strip()
            sala = (item.get("sala_nome") or "SEM SALA").strip()
            data_hora = str(item.get("data_hora") or "")[:10]

            if sala not in ranking_salas:
                ranking_salas[sala] = {
                    "semana_1": 0,
                    "semana_2": 0,
                    "semana_3": 0,
                    "semana_4": 0,
                    "acumulado": 0
                }

            ranking_salas[sala]["acumulado"] += 1

            if status == "FINALIZADA":
                pizza["finalizadas"] += 1
            elif pendencia == "TUTOR" and status == "ATENDIMENTO":
                pizza["tutor"] += 1
            elif pendencia == "GESTAO" and status == "ATENDIMENTO":
                pizza["gestao"] += 1
            elif pendencia == "COORDENACAO" and status == "ATENDIMENTO":
                pizza["coordenacao"] += 1
            elif pendencia == "RESPONSAVEL" and status == "ATENDIMENTO":
                pizza["responsavel"] += 1

            try:
                if data_hora:
                    dt = datetime.strptime(data_hora, "%Y-%m-%d").date()
                    for idx, (ini, fim) in enumerate(semanas, start=1):
                        if ini <= dt <= fim:
                            ranking_salas[sala][f"semana_{idx}"] += 1
                            break
            except Exception:
                pass

        ranking_lista = sorted(
            [
                {
                    "sala": sala,
                    "semana_1": vals["semana_1"],
                    "semana_2": vals["semana_2"],
                    "semana_3": vals["semana_3"],
                    "semana_4": vals["semana_4"],
                    "acumulado": vals["acumulado"]
                }
                for sala, vals in ranking_salas.items()
            ],
            key=lambda x: (-x["acumulado"], x["sala"])
        )

        return jsonify({
            "success": True,
            "data": {
                "pizza": pizza,
                "ranking_salas_semanal": ranking_lista,
                "semanas_legenda": [
                    f"{ini.strftime('%d/%m')} a {fim.strftime('%d/%m')}"
                    for ini, fim in semanas
                ]
            }
        })
    except Exception as e:
        return json_error(e)




# =========================================================
# DASHBOARD GERAL
# =========================================================
@app.route("/api/dashboard_geral")
def api_dashboard_geral():
    try:
        db = get_supabase()
        hoje = datetime.now().strftime("%Y-%m-%d")

        ocorr_data = db.table("ocorrencias").select("*").execute().data or []
        freq_data = db.table("f_frequencia").select("*").execute().data or []
        atend_data = db.table("atendimentos_tutoria").select("*").execute().data or []
        salas_data = db.table("d_salas").select("*").execute().data or []

        alunos_ativos_resp = (
            db.table("d_alunos")
            .select("id,nome,aluno_nome,sala_nome", count="exact")
            .eq("situacao_aluno", "ATIVO")
            .execute()
        )
        alunos_ativos = alunos_ativos_resp.data or []
        alunos_total = alunos_ativos_resp.count or len(alunos_ativos)
        ids_ativos = {str(x.get("id")) for x in alunos_ativos if x.get("id") is not None}

        # frequência do dashboard geral considera somente alunos ativos atuais
        freq_filtrada = []
        for item in freq_data:
            aluno_id = item.get("aluno_id")
            if aluno_id is None:
                freq_filtrada.append(item)
            elif str(aluno_id) in ids_ativos:
                freq_filtrada.append(item)

        ocorrencias_dia = len([
            x for x in ocorr_data
            if str(x.get("data_hora") or "")[:10] == hoje
        ])
        ocorrencias_gerais = len(ocorr_data)

        freq_hoje = [
            x for x in freq_filtrada
            if str(x.get("data") or "")[:10] == hoje
        ]

        presentes_hoje = len([
            x for x in freq_hoje
            if (x.get("status") or "").upper() != "F"
        ])

        frequencia_percentual = round((presentes_hoje / alunos_total) * 100, 2) if alunos_total > 0 else 0
        atendimento_tutoria = len(atend_data)

        pend_tutor = len([
            x for x in ocorr_data
            if (x.get("pendencia") or "").upper() == "TUTOR"
            and (x.get("status") or "").upper() == "ATENDIMENTO"
        ])
        pend_coord = len([
            x for x in ocorr_data
            if (x.get("pendencia") or "").upper() == "COORDENACAO"
            and (x.get("status") or "").upper() == "ATENDIMENTO"
        ])
        pend_gestao = len([
            x for x in ocorr_data
            if (x.get("pendencia") or "").upper() == "GESTAO"
            and (x.get("status") or "").upper() == "ATENDIMENTO"
        ])
        pend_responsavel = len([
            x for x in ocorr_data
            if (x.get("pendencia") or "").upper() == "RESPONSAVEL"
            and (x.get("status") or "").upper() == "ATENDIMENTO"
        ])

        nomes_salas = []
        for s in salas_data:
            nome = s.get("nome") or s.get("sala") or s.get("sala_nome") or ""
            nome = str(nome).strip()
            if nome:
                nomes_salas.append(nome)

        mapa_ocorr = {nome: 0 for nome in nomes_salas}
        for x in ocorr_data:
            sala = str(x.get("sala_nome") or "").strip()
            if sala:
                mapa_ocorr[sala] = mapa_ocorr.get(sala, 0) + 1

        ranking_ocorrencias = sorted(
            [{"sala": sala, "total": total} for sala, total in mapa_ocorr.items()],
            key=lambda x: (-x["total"], x["sala"])
        )

        mapa_presenca = {sala: {"presentes": 0, "total": 0, "percentual": 0} for sala in nomes_salas}
        for x in freq_hoje:
            sala = str(x.get("sala_nome") or "").strip()
            if not sala:
                continue
            if sala not in mapa_presenca:
                mapa_presenca[sala] = {"presentes": 0, "total": 0, "percentual": 0}

            mapa_presenca[sala]["total"] += 1
            if (x.get("status") or "").upper() != "F":
                mapa_presenca[sala]["presentes"] += 1

        ranking_presenca = []
        for sala, dados in mapa_presenca.items():
            total = dados["total"]
            presentes = dados["presentes"]
            percentual = round((presentes / total) * 100, 2) if total > 0 else 0
            ranking_presenca.append({
                "sala": sala,
                "presentes": presentes,
                "total": total,
                "percentual": percentual
            })
        ranking_presenca.sort(key=lambda x: (-x["percentual"], x["sala"]))

        return jsonify({
            "success": True,
            "data": {
                "cards": {
                    "ocorrencias_dia": ocorrencias_dia,
                    "ocorrencias_gerais": ocorrencias_gerais,
                    "presentes_hoje": presentes_hoje,
                    "alunos_cadastrados": alunos_total,
                    "frequencia_percentual": frequencia_percentual,
                    "atendimento_tutoria": atendimento_tutoria,
                    "pend_tutor": pend_tutor,
                    "pend_coord": pend_coord,
                    "pend_gestao": pend_gestao,
                    "pend_responsavel": pend_responsavel
                },
                "ranking_ocorrencias": ranking_ocorrencias,
                "ranking_presenca": ranking_presenca
            }
        })
    except Exception as e:
        return json_error(e)


@app.route("/api/relatorios_ocorrencias")
def api_relatorios_ocorrencias():
    try:
        db = get_supabase()

        inicio = (request.args.get("inicio") or "").strip()
        fim = (request.args.get("fim") or "").strip()
        sala = (request.args.get("sala") or "").strip()
        status = (request.args.get("status") or "").strip().upper()
        pendencia = (request.args.get("pendencia") or "").strip().upper()

        query = db.table("ocorrencias").select("*").order("numero", desc=True)

        if inicio:
            query = query.gte("data_hora", f"{inicio}T00:00:00")
        if fim:
            query = query.lte("data_hora", f"{fim}T23:59:59")
        if sala:
            query = query.eq("sala_nome", sala)
        if status:
            query = query.eq("status", status)
        if pendencia:
            query = query.eq("pendencia", pendencia)

        resp = query.execute()
        dados = resp.data or []

        total = len(dados)
        atendimento = len([x for x in dados if (x.get("status") or "").upper() == "ATENDIMENTO"])
        finalizadas = len([x for x in dados if (x.get("status") or "").upper() == "FINALIZADA"])
        assinadas = len([x for x in dados if (x.get("status") or "").upper() == "ASSINADA"])

        tutor = len([x for x in dados if (x.get("pendencia") or "").upper() == "TUTOR"])
        coordenacao = len([x for x in dados if (x.get("pendencia") or "").upper() == "COORDENACAO"])
        gestao = len([x for x in dados if (x.get("pendencia") or "").upper() == "GESTAO"])
        responsavel = len([x for x in dados if (x.get("pendencia") or "").upper() == "RESPONSAVEL"])

        por_sala = {}
        por_aluno = {}
        por_dia = {}

        for item in dados:
            sala_nome = item.get("sala_nome") or "SEM SALA"
            aluno_nome = item.get("aluno_nome") or "SEM ALUNO"
            data_hora = str(item.get("data_hora") or "")
            dia = data_hora[:10] if len(data_hora) >= 10 else "SEM DATA"

            por_sala[sala_nome] = por_sala.get(sala_nome, 0) + 1
            por_aluno[aluno_nome] = por_aluno.get(aluno_nome, 0) + 1
            por_dia[dia] = por_dia.get(dia, 0) + 1

        ranking_salas = sorted(
            [{"nome": k, "total": v} for k, v in por_sala.items()],
            key=lambda x: x["total"],
            reverse=True
        )[:10]

        ranking_alunos = sorted(
            [{"nome": k, "total": v} for k, v in por_aluno.items()],
            key=lambda x: x["total"],
            reverse=True
        )[:10]

        dias_ordenados = sorted([k for k in por_dia.keys() if k != "SEM DATA"])
        serie_diaria = [por_dia[d] for d in dias_ordenados]

        salas_resp = db.table("d_salas").select("*").order("nome").execute()
        salas = []
        for s in (salas_resp.data or []):
            nome = normalize_sala_nome(s)
            if nome:
                salas.append(nome)

        ultimas = []
        for x in dados[:20]:
            ultimas.append({
                "numero": x.get("numero"),
                "data_hora": x.get("data_hora"),
                "aluno_nome": x.get("aluno_nome"),
                "sala_nome": x.get("sala_nome"),
                "professor_nome": x.get("professor_nome"),
                "status": x.get("status"),
                "pendencia": x.get("pendencia"),
            })

        return jsonify({
            "success": True,
            "data": {
                "cards": {
                    "total": total,
                    "atendimento": atendimento,
                    "finalizadas": finalizadas,
                    "assinadas": assinadas,
                    "tutor": tutor,
                    "coordenacao": coordenacao,
                    "gestao": gestao,
                    "responsavel": responsavel
                },
                "filtros": {
                    "salas": salas
                },
                "graficos": {
                    "status": {
                        "labels": ["ATENDIMENTO", "FINALIZADA", "ASSINADA"],
                        "data": [atendimento, finalizadas, assinadas]
                    },
                    "pendencias": {
                        "labels": ["TUTOR", "COORDENAÇÃO", "GESTÃO", "RESPONSÁVEL"],
                        "data": [tutor, coordenacao, gestao, responsavel]
                    },
                    "diario": {
                        "labels": dias_ordenados,
                        "data": serie_diaria
                    }
                },
                "ranking_salas": ranking_salas,
                "ranking_alunos": ranking_alunos,
                "ultimas": ultimas
            }
        })
    except Exception as e:
        return json_error(e)

# =========================================================
# FREQUÊNCIA
# =========================================================
@app.route("/api/frequencia/listar")
def api_frequencia_listar():
    try:
        db = get_supabase()
        sala_id = request.args.get("sala_id")
        data_ref = request.args.get("data")
        query = db.table("f_frequencia").select("*")
        if sala_id:
            query = query.eq("sala_id", sala_id)
        if data_ref:
            query = query.eq("data", data_ref)
        resp = query.execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/frequencia/salvar", methods=["POST"])
def api_frequencia_salvar():
    try:
        db = get_supabase()
        registros = request.get_json() or []
        resp = db.table("f_frequencia").upsert(registros, on_conflict="aluno_id,data").execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)

@app.route("/api/frequencia/relatorio")
def api_frequencia_relatorio():
    try:
        db = get_supabase()
        sala_id = request.args.get("sala_id")
        resp = db.table("f_frequencia").select("*").eq("sala_id", sala_id).execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/frequencia_premium")
def api_frequencia_premium():
    try:
        db = get_supabase()
        sala_id = request.args.get("sala_id")
        data_ref = request.args.get("data")

        salas_resp = db.table("d_salas").select("*").order("nome").execute()
        salas = []
        for s in (salas_resp.data or []):
            salas.append({
                "id": s.get("id"),
                "nome": normalize_sala_nome(s)
            })

        query = db.table("f_frequencia").select("*")
        if sala_id:
            query = query.eq("sala_id", sala_id)
        if data_ref:
            query = query.eq("data", data_ref)

        resp = query.execute()
        dados = resp.data or []

        resumo = {
            "P": len([x for x in dados if (x.get("status") or "").upper() == "P"]),
            "F": len([x for x in dados if (x.get("status") or "").upper() == "F"]),
            "PA": len([x for x in dados if (x.get("status") or "").upper() == "PA"]),
            "PS": len([x for x in dados if (x.get("status") or "").upper() == "PS"]),
            "PSA": len([x for x in dados if (x.get("status") or "").upper() == "PSA"])
        }

        return jsonify({
            "success": True,
            "data": {
                "salas": salas,
                "resumo": resumo,
                "registros": dados
            }
        })
    except Exception as e:
        return json_error(e)
@app.route("/gestao_relatorio_frequencia")
def gestao_relatorio_frequencia():
    return render_template("gestao_relatorio_frequencia.html")

@app.route("/api/dashboard_frequencia_mensal")
def api_dashboard_frequencia_mensal():
    try:
        db = get_supabase()
        mes = (request.args.get("mes") or datetime.now().strftime("%Y-%m")).strip()
        inicio = datetime.strptime(mes + "-01", "%Y-%m-%d").date()
        if inicio.month == 12:
            fim = date(inicio.year + 1, 1, 1) - timedelta(days=1)
        else:
            fim = date(inicio.year, inicio.month + 1, 1) - timedelta(days=1)

        dados = db.table("f_frequencia").select("*").gte("data", str(inicio)).lte("data", str(fim)).execute().data or []

        def cstatus(items, key):
            return len([x for x in items if (x.get("status") or "").upper() == key])

        cards = {
            "p_total": cstatus(dados, "P"),
            "f_total": cstatus(dados, "F"),
            "pa_total": cstatus(dados, "PA"),
            "ps_total": cstatus(dados, "PS"),
            "psa_total": cstatus(dados, "PSA"),
        }

        por_dia_total = {}
        por_dia_presentes = {}
        dia = inicio
        while dia <= fim:
            key = dia.strftime("%Y-%m-%d")
            por_dia_total[key] = 0
            por_dia_presentes[key] = 0
            dia += timedelta(days=1)

        for item in dados:
            d = str(item.get("data") or "")[:10]
            if d in por_dia_total:
                por_dia_total[d] += 1
                if (item.get("status") or "").upper() != "F":
                    por_dia_presentes[d] += 1

        labels = []
        percentuais = []
        for d in sorted(por_dia_total.keys()):
            labels.append(datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m"))
            total = por_dia_total[d]
            presentes = por_dia_presentes[d]
            percentual = round((presentes / total) * 100, 2) if total > 0 else 0
            percentuais.append(percentual)

        return jsonify({
            "success": True,
            "data": {
                "cards": cards,
                "grafico_presenca": {
                    "labels": labels,
                    "data": percentuais
                }
            }
        })
    except Exception as e:
        return json_error(e)

@app.route("/api/relatorio_frequencia")
def api_relatorio_frequencia():
    try:
        db = get_supabase()
        sala_id = request.args.get("sala_id")
        mes = (request.args.get("mes") or datetime.now().strftime("%Y-%m")).strip()
        if not sala_id:
            return json_error("Sala não informada.", 400)

        inicio = datetime.strptime(mes + "-01", "%Y-%m-%d").date()
        if inicio.month == 12:
            fim = date(inicio.year + 1, 1, 1) - timedelta(days=1)
        else:
            fim = date(inicio.year, inicio.month + 1, 1) - timedelta(days=1)

        alunos = db.table("d_alunos").select("*").eq("sala_id", sala_id).order("nome").execute().data or []
        frequencias = db.table("f_frequencia").select("*").eq("sala_id", sala_id).gte("data", str(inicio)).lte("data", str(fim)).execute().data or []

        dias = []
        d = inicio
        while d <= fim:
            dias.append(d.strftime("%d"))
            d += timedelta(days=1)

        mapa = {}
        for f in frequencias:
            aluno_id = f.get("aluno_id")
            data_ref = str(f.get("data") or "")[:10]
            dia_ref = data_ref[-2:] if len(data_ref) >= 10 else ""
            mapa[(aluno_id, dia_ref)] = f.get("status") or ""

        linhas = []
        for a in alunos:
            nome = a.get("nome") or a.get("aluno_nome") or ""
            registros = []
            for dia_num in dias:
                registros.append(mapa.get((a.get("id"), dia_num), ""))
            linhas.append({"nome": nome, "registros": registros})

        sala_resp = db.table("d_salas").select("*").eq("id", sala_id).limit(1).execute().data or []
        sala_nome = ""
        if sala_resp:
            sala_nome = sala_resp[0].get("nome") or sala_resp[0].get("sala") or sala_resp[0].get("sala_nome") or ""

        return jsonify({
            "success": True,
            "data": {
                "sala_nome": sala_nome,
                "mes": mes,
                "dias": dias,
                "alunos": linhas
            }
        })
    except Exception as e:
        return json_error(e)

@app.route("/api/relatorio_frequencia_pdf", methods=["POST"])
def api_relatorio_frequencia_pdf():
    try:
        data = request.get_json() or {}
        sala_id = data.get("sala_id")
        mes = data.get("mes")
        if not sala_id or not mes:
            return json_error("Sala e mês são obrigatórios.", 400)
        return jsonify({
            "success": True,
            "pdf_url": f"/relatorio_frequencia_pdf?sala_id={sala_id}&mes={mes}"
        })
    except Exception as e:
        return json_error(e)

@app.route("/relatorio_frequencia_pdf")
def relatorio_frequencia_pdf():
    try:
        db = get_supabase()
        sala_id = request.args.get("sala_id")
        mes = (request.args.get("mes") or datetime.now().strftime("%Y-%m")).strip()
        if not sala_id:
            return "Sala não informada.", 400

        inicio = datetime.strptime(mes + "-01", "%Y-%m-%d").date()
        if inicio.month == 12:
            fim = date(inicio.year + 1, 1, 1) - timedelta(days=1)
        else:
            fim = date(inicio.year, inicio.month + 1, 1) - timedelta(days=1)

        alunos = db.table("d_alunos").select("*").eq("sala_id", sala_id).order("nome").execute().data or []
        frequencias = db.table("f_frequencia").select("*").eq("sala_id", sala_id).gte("data", str(inicio)).lte("data", str(fim)).execute().data or []
        sala_resp = db.table("d_salas").select("*").eq("id", sala_id).limit(1).execute().data or []

        sala_nome = ""
        if sala_resp:
            sala_nome = sala_resp[0].get("nome") or sala_resp[0].get("sala") or sala_resp[0].get("sala_nome") or ""

        dias = []
        d = inicio
        while d <= fim:
            dias.append(d.strftime("%d"))
            d += timedelta(days=1)

        mapa = {}
        for f in frequencias:
            aluno_id = f.get("aluno_id")
            data_ref = str(f.get("data") or "")[:10]
            dia_ref = data_ref[-2:] if len(data_ref) >= 10 else ""
            mapa[(aluno_id, dia_ref)] = f.get("status") or ""

        linhas = []
        for a in alunos:
            nome = a.get("nome") or a.get("aluno_nome") or ""
            registros = []
            for dia_num in dias:
                registros.append(mapa.get((a.get("id"), dia_num), ""))
            linhas.append({"nome": nome, "registros": registros})

        return render_template(
            "relatorio_frequencia_pdf.html",
            sala_nome=sala_nome,
            mes=mes,
            dias=dias,
            alunos=linhas
        )
    except Exception as e:
        return f"Erro ao gerar PDF: {e}", 500



# =========================================================
# DASHBOARD FREQUÊNCIA
# =========================================================
@app.route("/api/dashboard_frequencia")
def api_dashboard_frequencia():
    try:
        db = get_supabase()
        dados = db.table("f_frequencia").select("*").execute().data or []

        def cstatus(items, key):
            return len([x for x in items if normalizar_texto(x.get("status")) == key])

        hoje = datetime.now().strftime("%Y-%m-%d")
        hoje_registros = [x for x in dados if str(x.get("data") or "")[:10] == hoje]

        cards = {
            "p_total": cstatus(dados, "P"),
            "f_total": cstatus(dados, "F"),
            "pa_total": cstatus(dados, "PA"),
            "ps_total": cstatus(dados, "PS"),
            "psa_total": cstatus(dados, "PSA"),
            "p_hoje": cstatus(hoje_registros, "P"),
            "f_hoje": cstatus(hoje_registros, "F"),
            "pa_hoje": cstatus(hoje_registros, "PA"),
            "ps_hoje": cstatus(hoje_registros, "PS"),
            "psa_hoje": cstatus(hoje_registros, "PSA"),
        }
        return jsonify({"success": True, "data": {"cards": cards}})
    except Exception as e:
        return json_error(e)


# =========================================================
# TUTORIA
# =========================================================
@app.route("/api/tutores")
def api_tutores():
    try:
        db = get_supabase()
        resp = (
            db.table("d_funcionarios")
            .select("id,nome,funcao,email,is_tutor")
            .or_("funcao.ilike.%TUTOR%,is_tutor.eq.true")
            .order("nome")
            .execute()
        )
        dados = resp.data or []
        if usuario_tem_acesso_total():
            return jsonify(dados)
        nome = usuario_logado_nome()
        return jsonify([x for x in dados if normalizar_texto(x.get("nome")) == nome])
    except Exception as e:
        return json_error(e)


@app.route("/api/alunos_tutoria")
def api_alunos_tutoria():
    try:
        db = get_supabase()
        tutor_id = request.args.get("tutor_id")
        query = db.table("d_alunos").select("*").order("nome")
        if tutor_id:
            query = query.eq("tutor_id", tutor_id)
        resp = query.execute()
        dados = resp.data or []
        for item in dados:
            item["nome"] = normalize_aluno_nome(item)
        return jsonify(dados)
    except Exception as e:
        return json_error(e)

@app.route("/api/dashboard_tutoria")
def api_dashboard_tutoria():
    try:
        db = get_supabase()

        tutores_resp = (
            db.table("d_funcionarios")
            .select("id,nome,funcao,is_tutor")
            .or_("funcao.ilike.%TUTOR%,is_tutor.eq.true")
            .execute()
        )

        alunos_resp = db.table("d_alunos").select("id,tutor_id,tutor_nome").execute()
        agend_resp = db.table("agendamentos_tutoria").select("id,status", count="exact").execute()
        atend_resp = db.table("atendimentos_tutoria").select("id", count="exact").execute()

        tutores = tutores_resp.data or []
        alunos = alunos_resp.data or []
        agendamentos = agend_resp.data or []

        alunos_com_tutor = len([
            a for a in alunos
            if a.get("tutor_id") or (a.get("tutor_nome") or "").strip()
        ])

        agendados = len([
            x for x in agendamentos
            if (x.get("status") or "").upper() == "AGENDADO"
        ])

        concluidos = len([
            x for x in agendamentos
            if (x.get("status") or "").upper() == "CONCLUIDO"
        ])

        return jsonify({
            "total_tutores": len(tutores),
            "total_alunos": len(alunos),
            "alunos_com_tutor": alunos_com_tutor,
            "total_agendamentos": agend_resp.count or 0,
            "agendados": agendados,
            "concluidos": concluidos,
            "total_atendimentos": atend_resp.count or 0
        })
    except Exception as e:
        return json_error(e)


@app.route("/api/agendamentos_tutoria")
def api_agendamentos_tutoria():
    try:
        db = get_supabase()
        tutor_id = request.args.get("tutor_id")
        aluno_id = request.args.get("aluno_id")
        query = db.table("agendamentos_tutoria").select("*").order("data_agendamento").order("hora_agendamento")
        if tutor_id:
            query = query.eq("tutor_id", tutor_id)
        if aluno_id:
            query = query.eq("aluno_id", aluno_id)
        resp = query.execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/agendar_tutoria", methods=["POST"])
def api_agendar_tutoria():
    try:
        db = get_supabase()
        data = request.get_json() or {}
        payload = {
            "tutor_id": data.get("tutor_id"),
            "tutor_nome": data.get("tutor_nome"),
            "aluno_id": data.get("aluno_id"),
            "aluno_nome": data.get("aluno_nome"),
            "sala_nome": data.get("sala_nome"),
            "tema": data.get("tema"),
            "observacao": data.get("observacao"),
            "status": data.get("status") or "AGENDADO",
            "data_agendamento": data.get("data"),
            "hora_agendamento": data.get("hora"),
            "created_at": now_iso()
        }
        if not payload["tutor_id"] or not payload["aluno_id"] or not payload["data_agendamento"] or not payload["hora_agendamento"]:
            return json_error("Preencha tutor, aluno, data e hora.", 400)
        resp = db.table("agendamentos_tutoria").insert(payload).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)

@app.route("/api/atendimentos_tutoria")
def api_atendimentos_tutoria():
    try:
        db = get_supabase()
        tutor_id = request.args.get("tutor_id")
        aluno_id = request.args.get("aluno_id")
        query = db.table("atendimentos_tutoria").select("*").order("data_registro", desc=True)
        if tutor_id:
            query = query.eq("tutor_id", tutor_id)
        if aluno_id:
            query = query.eq("aluno_id", aluno_id)
        resp = query.execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/salvar_atendimento_tutoria", methods=["POST"])
def api_salvar_atendimento_tutoria():
    try:
        db = get_supabase()
        data = request.get_json() or {}
        payload = {
            "tutor_id": data.get("tutor_id"),
            "tutor_nome": data.get("tutor_nome"),
            "aluno_id": data.get("aluno_id"),
            "aluno_nome": data.get("aluno_nome"),
            "sala_nome": data.get("sala_nome"),
            "tipo_atendimento": data.get("tipo_atendimento"),
            "encaminhamento": data.get("encaminhamento"),
            "registro": data.get("registro"),
            "proximos_passos": data.get("proximos_passos"),
            "data_registro": now_sp_iso()
        }
        if not payload["tutor_id"] or not payload["aluno_id"] or not payload["registro"]:
            return json_error("Preencha tutor, aluno e registro.", 400)
        resp = db.table("atendimentos_tutoria").insert(payload).execute()
        return jsonify({"success": True, "data": resp.data})
    except Exception as e:
        return json_error(e)

@app.route("/api/alunos_do_tutor/<int:tutor_id>")
def api_alunos_do_tutor(tutor_id):
    try:
        db = get_supabase()

        tutor_resp = (
            db.table("d_funcionarios")
            .select("id,nome")
            .eq("id", tutor_id)
            .limit(1)
            .execute()
        )

        if not tutor_resp.data:
            return json_error("Tutor não encontrado.", 404)

        tutor = tutor_resp.data[0]
        tutor_nome = (tutor.get("nome") or "").strip()

        # usuário comum só pode ver os próprios alunos
        if not usuario_tem_acesso_total() and normalizar_texto(tutor_nome) != usuario_logado_nome():
            return jsonify([])

        # busca por tutor_id
        resp_id = (
            db.table("d_alunos")
            .select("*")
            .eq("tutor_id", tutor_id)
            .order("nome")
            .execute()
        )
        dados_id = resp_id.data or []

        # busca por tutor_nome
        resp_nome = (
            db.table("d_alunos")
            .select("*")
            .eq("tutor_nome", tutor_nome)
            .order("nome")
            .execute()
        )
        dados_nome = resp_nome.data or []

        # junta sem duplicar
        mapa = {}
        for item in dados_id + dados_nome:
            aluno_id = item.get("id")
            if aluno_id is not None:
                mapa[aluno_id] = item

        dados = list(mapa.values())

        for item in dados:
            item["nome"] = item.get("nome") or item.get("aluno_nome") or ""

        dados.sort(key=lambda x: (x.get("nome") or "").upper())
        return jsonify(dados)

    except Exception as e:
        return json_error(e)


@app.route("/api/ficha_tutoria/<int:aluno_id>")
def api_ficha_tutoria(aluno_id):
    try:
        db = get_supabase()
        aluno_resp = db.table("d_alunos").select("*").eq("id", aluno_id).limit(1).execute()
        if not aluno_resp.data:
            return json_error("Aluno não encontrado", 404)

        aluno = aluno_resp.data[0]
        aluno_nome = (aluno.get("nome") or aluno.get("aluno_nome") or "").strip()
        sala_nome = (aluno.get("sala_nome") or "").strip()

        ocorr_resp = db.table("ocorrencias").select("numero,data_hora,descricao,status,pendencia").eq("aluno_id", aluno_id).order("numero", desc=True).limit(50).execute()
        atend_resp = db.table("atendimentos_tutoria").select("*").eq("aluno_id", aluno_id).order("data_registro", desc=True).limit(50).execute()
        agend_resp = db.table("agendamentos_tutoria").select("*").eq("aluno_id", aluno_id).order("data_agendamento", desc=True).limit(50).execute()
        freq_resp = db.table("f_frequencia").select("*").eq("aluno_id", aluno_id).order("data", desc=True).limit(100).execute()
        notas_resp = db.table("notas_aluno").select("*").eq("aluno_id", aluno_id).execute()

        destaque = False
        evolucao = False
        if sala_nome and aluno_nome:
            conselhos = db.table("f_conselho_classe").select("aluno_destaque,aluno_evolucao,bimestre").eq("sala_nome", sala_nome).execute().data or []
            nome_norm = normalizar_texto(aluno_nome)
            for c in conselhos:
                if normalizar_texto(c.get("aluno_destaque")) == nome_norm:
                    destaque = True
                if normalizar_texto(c.get("aluno_evolucao")) == nome_norm:
                    evolucao = True

        return jsonify({
            "aluno": aluno,
            "ocorrencias": ocorr_resp.data or [],
            "atendimentos": atend_resp.data or [],
            "agendamentos": agend_resp.data or [],
            "frequencia": freq_resp.data or [],
            "notas": notas_resp.data or [],
            "aluno_destaque": destaque,
            "aluno_evolucao": evolucao
        })
    except Exception as e:
        return json_error(e)

@app.route("/api/evolucao_aluno/<int:aluno_id>")
def api_evolucao_aluno(aluno_id):
    try:
        from collections import defaultdict
        from datetime import datetime, timedelta

        db = get_supabase()
        aluno_resp = db.table("d_alunos").select("*").eq("id", aluno_id).limit(1).execute()
        if not aluno_resp.data:
            return json_error("Aluno não encontrado.", 404)

        aluno = aluno_resp.data[0]
        aluno_nome = (aluno.get("nome") or aluno.get("aluno_nome") or "").strip()
        sala_nome = (aluno.get("sala_nome") or "").strip()

        freq = db.table("f_frequencia").select("*").eq("aluno_id", aluno_id).order("data", desc=False).execute().data or []
        if not freq and aluno_nome:
            all_freq = db.table("f_frequencia").select("*").execute().data or []
            freq = [x for x in all_freq if (x.get("aluno_nome") or "").strip() == aluno_nome]

        ocorr = db.table("ocorrencias").select("numero,data_hora,descricao,status").eq("aluno_id", aluno_id).order("data_hora", desc=False).execute().data or []
        if not ocorr and aluno_nome:
            all_oc = db.table("ocorrencias").select("numero,data_hora,descricao,status,aluno_nome").execute().data or []
            ocorr = [x for x in all_oc if (x.get("aluno_nome") or "").strip() == aluno_nome]

        atend = db.table("atendimentos_tutoria").select("*").eq("aluno_id", aluno_id).order("data_registro", desc=False).execute().data or []
        notas = db.table("f_notas").select("*").eq("aluno_id", aluno_id).execute().data or []

        def semana_inicio(dt):
            return dt - timedelta(days=dt.weekday())

        freq_sem = defaultdict(lambda: {"presentes":0, "faltas":0})
        for x in freq:
            d = str(x.get("data") or "")[:10]
            if not d:
                continue
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            key = semana_inicio(dt)
            if (x.get("status") or "").upper() == "F":
                freq_sem[key]["faltas"] += 1
            else:
                freq_sem[key]["presentes"] += 1

        ocorr_sem = defaultdict(int)
        for x in ocorr:
            d = str(x.get("data_hora") or "")[:10]
            if not d:
                continue
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            ocorr_sem[semana_inicio(dt)] += 1

        atend_sem = defaultdict(int)
        for x in atend:
            d = str(x.get("data_registro") or "")[:10]
            if not d:
                continue
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            atend_sem[semana_inicio(dt)] += 1

        semanas = sorted(set(list(freq_sem.keys()) + list(ocorr_sem.keys()) + list(atend_sem.keys())))
        labels = [f"{s.strftime('%d/%m')}" for s in semanas]

        nota_1b = nota_2b = nota_3b = nota_4b = None
        if notas:
            reg = notas[0]
            nota_1b = reg.get("nota_1b")
            nota_2b = reg.get("nota_2b")
            nota_3b = reg.get("nota_3b")
            nota_4b = reg.get("nota_4b")

        return jsonify({
            "success": True,
            "aluno": {
                "id": aluno.get("id"),
                "nome": aluno_nome,
                "sala_nome": sala_nome,
                "tutor_nome": aluno.get("tutor_nome") or aluno.get("nome_tutor") or ""
            },
            "graficos": {
                "frequencia": {
                    "labels": labels,
                    "presentes": [freq_sem[s]["presentes"] for s in semanas],
                    "faltas": [freq_sem[s]["faltas"] for s in semanas]
                },
                "ocorrencias": {
                    "labels": labels,
                    "data": [ocorr_sem[s] for s in semanas]
                },
                "atendimentos": {
                    "labels": labels,
                    "data": [atend_sem[s] for s in semanas]
                },
                "notas": {
                    "labels": ["1º Bim", "2º Bim", "3º Bim", "4º Bim"],
                    "data": [nota_1b or 0, nota_2b or 0, nota_3b or 0, nota_4b or 0]
                }
            }
        })
    except Exception as e:
        return json_error(e)

@app.route("/api/tutoria_premium")
def api_tutoria_premium():
    try:
        db = get_supabase()
        tutor_id = request.args.get("tutor_id")
        aluno_id = request.args.get("aluno_id")

        tutores_resp = db.table("d_funcionarios").select("id,nome,funcao,email,is_tutor").or_("funcao.ilike.%TUTOR%,is_tutor.eq.true").order("nome").execute()

        alunos_query = db.table("d_alunos").select("*").order("nome")
        if tutor_id:
            alunos_query = alunos_query.eq("tutor_id", tutor_id)
        alunos_resp = alunos_query.execute()

        ag_query = db.table("agendamentos_tutoria").select("*").order("data_agendamento", desc=True)
        at_query = db.table("atendimentos_tutoria").select("*").order("data_registro", desc=True)

        if tutor_id:
            ag_query = ag_query.eq("tutor_id", tutor_id)
            at_query = at_query.eq("tutor_id", tutor_id)
        if aluno_id:
            ag_query = ag_query.eq("aluno_id", aluno_id)
            at_query = at_query.eq("aluno_id", aluno_id)

        ag_resp = ag_query.execute()
        at_resp = at_query.execute()
        ag_data = ag_resp.data or []
        at_data = at_resp.data or []

        return jsonify({
            "success": True,
            "data": {
                "tutores": tutores_resp.data or [],
                "alunos": alunos_resp.data or [],
                "cards": {
                    "tutores": len(tutores_resp.data or []),
                    "alunos": len(alunos_resp.data or []),
                    "agendamentos": len(ag_data),
                    "atendimentos": len(at_data),
                    "agendados": len([x for x in ag_data if (x.get("status") or "").upper() == "AGENDADO"]),
                    "concluidos": len([x for x in ag_data if (x.get("status") or "").upper() == "CONCLUIDO"])
                },
                "agendamentos": ag_data[:20],
                "atendimentos": at_data[:20]
            }
        })
    except Exception as e:
        return json_error(e)


@app.route("/api/clubes_juvenis")
def api_clubes_juvenis():
    try:
        db = get_supabase()
        semestre = request.args.get("semestre")
        query = db.table("d_clubes_juvenis").select("*").eq("ativo", True).order("nome")
        if semestre:
            query = query.eq("semestre", int(semestre))
        return jsonify(query.execute().data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/eletivas")
def api_eletivas():
    try:
        db = get_supabase()
        semestre = request.args.get("semestre")
        query = db.table("d_eletivas").select("*").eq("ativo", True).order("nome")
        if semestre:
            query = query.eq("semestre", int(semestre))
        return jsonify(query.execute().data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/aluno_detalhe/<int:aluno_id>")
def api_aluno_detalhe(aluno_id):
    try:
        db = get_supabase()
        resp = db.table("d_alunos").select("*").eq("id", aluno_id).limit(1).execute()
        if not resp.data:
            return json_error("Aluno não encontrado.", 404)
        return jsonify(resp.data[0])
    except Exception as e:
        return json_error(e)

@app.route("/api/salvar_tutoria_ficha", methods=["POST"])
def api_salvar_tutoria_ficha():
    try:
        db = get_supabase()
        data = request.get_json() or {}

        aluno_id = data.get("aluno_id")
        if not aluno_id:
            return json_error("Aluno não informado.", 400)

        payload = {
            "clube_1_semestre": data.get("clube_1_semestre"),
            "clube_2_semestre": data.get("clube_2_semestre"),
            "eletiva_1_semestre": data.get("eletiva_1_semestre"),
            "eletiva_2_semestre": data.get("eletiva_2_semestre"),
            "projeto_de_vida": data.get("projeto_de_vida"),
            "telefone_aluno": data.get("telefone_aluno"),
            "responsavel_nome": data.get("responsavel_nome"),
            "responsavel_telefone": data.get("responsavel_telefone"),
            "updated_at": now_iso()
        }

        db.table("d_alunos").update(payload).eq("id", aluno_id).execute()

        return jsonify({
            "success": True,
            "message": "Ficha salva com sucesso."
        })
    except Exception as e:
        return json_error(e)

@app.route("/api/disciplinas_por_sala")
def api_disciplinas_por_sala():
    try:
        db = get_supabase()
        sala = request.args.get("sala")
        serie = sala_para_serie(sala)
        resp = db.table("d_disciplinas").select("*").eq("serie", serie).order("nome").execute()
        return jsonify(resp.data or [])
    except Exception as e:
        return json_error(e)

@app.route("/api/salas_do_professor/<int:professor_id>")
def api_salas_do_professor(professor_id):
    try:
        db = get_supabase()
        resp = db.table("d_professor_disciplina").select("sala_nome").eq("professor_id", professor_id).execute()
        salas = sorted({(x.get("sala_nome") or "").strip() for x in (resp.data or []) if (x.get("sala_nome") or "").strip()})
        return jsonify([{"nome": s} for s in salas])
    except Exception as e:
        return json_error(e)

@app.route("/api/disciplinas_do_professor")
def api_disciplinas_do_professor():
    try:
        db = get_supabase()
        professor_id = request.args.get("professor_id")
        sala_nome = request.args.get("sala_nome")
        query = db.table("d_professor_disciplina").select("disciplina")
        if professor_id:
            query = query.eq("professor_id", professor_id)
        if sala_nome:
            query = query.eq("sala_nome", sala_nome)
        resp = query.execute()
        disciplinas = sorted({(x.get("disciplina") or "").strip() for x in (resp.data or []) if (x.get("disciplina") or "").strip()})
        return jsonify([{"nome": d} for d in disciplinas])
    except Exception as e:
        return json_error(e)

@app.route("/api/notas_turma")
def api_notas_turma():
    try:
        db = get_supabase()
        sala = request.args.get("sala")
        disciplina = request.args.get("disciplina")
        alunos = db.table("d_alunos").select("*").eq("sala_nome", sala).order("nome").execute().data or []
        notas = db.table("f_notas").select("*").eq("sala_nome", sala).eq("disciplina", disciplina).execute().data or []
        mapa = {n.get("aluno_id"): n for n in notas}
        resultado = []
        for a in alunos:
            n = mapa.get(a.get("id"), {})
            resultado.append({
                "aluno_id": a.get("id"),
                "aluno_nome": a.get("nome") or a.get("aluno_nome") or "",
                "sala_nome": a.get("sala_nome"),
                "disciplina": disciplina,
                "nota_1b": n.get("nota_1b"),
                "nota_2b": n.get("nota_2b"),
                "nota_3b": n.get("nota_3b"),
                "nota_4b": n.get("nota_4b")
            })
        return jsonify(resultado)
    except Exception as e:
        return json_error(e)


@app.route("/api/boletim/<int:aluno_id>")
def api_boletim(aluno_id):
    try:
        db = get_supabase()
        aluno_resp = db.table("d_alunos").select("id,nome,aluno_nome,sala_nome").eq("id", aluno_id).limit(1).execute()
        if not aluno_resp.data:
            return json_error("Aluno não encontrado.", 404)
        aluno = aluno_resp.data[0]
        serie = sala_para_serie(aluno.get("sala_nome"))
        disciplinas = db.table("d_disciplinas").select("*").eq("serie", serie).order("nome").execute().data or []
        notas = db.table("f_notas").select("*").eq("aluno_id", aluno_id).execute().data or []
        mapa = {n.get("disciplina"): n for n in notas}
        result = []
        for d in disciplinas:
            nome = d.get("nome")
            nota_reg = mapa.get(nome, {})
            vals = [nota_reg.get("nota_1b"), nota_reg.get("nota_2b"), nota_reg.get("nota_3b"), nota_reg.get("nota_4b")]
            nums = [float(x) for x in vals if x not in (None, "", "null")]
            media = round(sum(nums)/len(nums), 2) if nums else None
            status = "-"
            if media is not None:
                status = "APROVADO" if media >= 5 else "REPROVADO"
            result.append({
                "disciplina": nome,
                "nota_1b": nota_reg.get("nota_1b"),
                "nota_2b": nota_reg.get("nota_2b"),
                "nota_3b": nota_reg.get("nota_3b"),
                "nota_4b": nota_reg.get("nota_4b"),
                "media": media,
                "status": status
            })
        return jsonify(result)
    except Exception as e:
        return json_error(e)

@app.route("/relatorio_aluno_pdf")
def relatorio_aluno_pdf():
    try:
        db = get_supabase()
        aluno_id = request.args.get("aluno_id")
        if not aluno_id:
            return "Aluno não informado.", 400

        aluno_resp = db.table("d_alunos").select("*").eq("id", aluno_id).limit(1).execute()
        if not aluno_resp.data:
            return "Aluno não encontrado.", 404

        aluno = aluno_resp.data[0]
        aluno_nome = aluno.get("nome") or aluno.get("aluno_nome") or ""
        sala_nome = aluno.get("sala_nome") or ""
        tutor_nome = aluno.get("tutor_nome") or ""
        projeto_vida = aluno.get("projeto_de_vida") or aluno.get("projeto_vida") or aluno.get("eletiva_1_semestre") or ""

        ocorrencias = db.table("ocorrencias").select("*").eq("aluno_id", aluno_id).order("numero", desc=True).execute().data or []
        if not ocorrencias and aluno_nome:
            todas_oc = db.table("ocorrencias").select("*").execute().data or []
            ocorrencias = [x for x in todas_oc if (x.get("aluno_nome") or "").strip() == aluno_nome.strip()]

        atendimentos = db.table("atendimentos_tutoria").select("*").eq("aluno_id", aluno_id).order("data_registro", desc=True).execute().data or []
        frequencia = db.table("f_frequencia").select("*").eq("aluno_id", aluno_id).order("data", desc=True).execute().data or []
        if not frequencia and aluno_nome:
            todas_freq = db.table("f_frequencia").select("*").execute().data or []
            frequencia = [x for x in todas_freq if (x.get("aluno_nome") or "").strip() == aluno_nome.strip()]

        faltas = len([x for x in frequencia if (x.get("status") or "").upper() == "F"])
        atrasos = len([x for x in frequencia if (x.get("status") or "").upper() == "PA"])
        saidas = len([x for x in frequencia if (x.get("status") or "").upper() in ["PS", "PSA"]])
        total_freq = len(frequencia)
        presencas = total_freq - faltas
        frequencia_percentual = round((presencas / total_freq) * 100, 2) if total_freq > 0 else 0

        serie = sala_para_serie(sala_nome)
        disciplinas = db.table("d_disciplinas").select("*").eq("serie", serie).order("nome").execute().data or []
        notas = db.table("f_notas").select("*").eq("aluno_id", aluno_id).execute().data or []
        mapa_notas = {(n.get("disciplina") or "").strip(): n for n in notas}

        boletim = []
        for d in disciplinas:
            nome_disc = (d.get("nome") or "").strip()
            reg = mapa_notas.get(nome_disc, {})
            vals = [reg.get("nota_1b"), reg.get("nota_2b"), reg.get("nota_3b"), reg.get("nota_4b")]
            nums = [float(v) for v in vals if v not in (None, "", "null")]
            media = round(sum(nums) / len(nums), 2) if nums else None
            status = "-"
            if media is not None:
                status = "APROVADO" if media >= 5 else "REPROVADO"

            boletim.append({
                "disciplina": nome_disc,
                "nota_1b": reg.get("nota_1b"),
                "nota_2b": reg.get("nota_2b"),
                "nota_3b": reg.get("nota_3b"),
                "nota_4b": reg.get("nota_4b"),
                "media": media,
                "status": status
            })

        aluno_destaque = False
        aluno_evolucao = False
        if sala_nome and aluno_nome:
            conselhos = db.table("f_conselho_classe").select("aluno_destaque,aluno_evolucao").eq("sala_nome", sala_nome).execute().data or []
            nome_norm = normalizar_texto(aluno_nome)
            for c in conselhos:
                if normalizar_texto(c.get("aluno_destaque")) == nome_norm:
                    aluno_destaque = True
                if normalizar_texto(c.get("aluno_evolucao")) == nome_norm:
                    aluno_evolucao = True

        return render_template(
            "relatorio_aluno_profissional.html",
            titulo_relatorio="FICHA PROFISSIONAL DO ALUNO",
            aluno_nome=aluno_nome,
            sala_nome=sala_nome,
            tutor_nome=tutor_nome,
            projeto_vida=projeto_vida,
            data_emissao=datetime.now().strftime("%d/%m/%Y"),
            frequencia_percentual=frequencia_percentual,
            faltas=faltas,
            atrasos=atrasos,
            saidas=saidas,
            ocorrencias=ocorrencias,
            atendimentos=atendimentos,
            boletim=boletim,
            aluno_destaque=aluno_destaque,
            aluno_evolucao=aluno_evolucao
        )
    except Exception as e:
        return f"Erro ao gerar relatório: {e}", 500


@app.route("/gestao_relatorios_profissional")
def gestao_relatorios_profissional():
    return render_template("gestao_relatorios_profissional.html")


def _parse_mes_intervalo(mes_str):
    from datetime import datetime, date, timedelta
    mes = (mes_str or datetime.now().strftime("%Y-%m")).strip()
    inicio = datetime.strptime(mes + "-01", "%Y-%m-%d").date()
    if inicio.month == 12:
        fim = date(inicio.year + 1, 1, 1) - timedelta(days=1)
    else:
        fim = date(inicio.year, inicio.month + 1, 1) - timedelta(days=1)
    return inicio, fim

def _status_presenca(status):
    return (status or "").upper() != "F"

@app.route("/api/relatorios_dashboard/<report_name>")
def api_relatorios_dashboard(report_name):
    try:
        db = get_supabase()

        sala = (request.args.get("sala") or "").strip()
        tutor = (request.args.get("tutor") or "").strip()
        professor = (request.args.get("professor") or "").strip()
        periodo = (request.args.get("periodo") or "acumulado").strip()
        mes = (request.args.get("mes") or "").strip()

        ocorr = db.table("ocorrencias").select("*").execute().data or []
        freq = db.table("f_frequencia").select("*").execute().data or []
        atend = db.table("atendimentos_tutoria").select("*").execute().data or []
        alunos = db.table("d_alunos").select("*").eq("situacao_aluno", "ATIVO").execute().data or []

        if sala:
            ocorr = [x for x in ocorr if (x.get("sala_nome") or "") == sala]
            freq = [x for x in freq if (x.get("sala_nome") or "") == sala]
            atend = [x for x in atend if (x.get("sala_nome") or "") == sala]
            alunos = [x for x in alunos if (x.get("sala_nome") or "") == sala]

        if tutor:
            ocorr = [x for x in ocorr if (x.get("tutor_nome") or "") == tutor]
            atend = [x for x in atend if (x.get("tutor_nome") or "") == tutor]
            alunos = [x for x in alunos if ((x.get("tutor_nome") or x.get("nome_tutor") or "") == tutor)]

        if professor:
            ocorr = [x for x in ocorr if (x.get("professor_nome") or "") == professor]

        if report_name == "ocorrencias_por_sala":
            mapa = {}
            for x in ocorr:
                k = x.get("sala_nome") or "SEM SALA"
                mapa[k] = mapa.get(k, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Ocorrência por Sala",
                "chart_type": "pie",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Ocorrências"},
                "table": {"headers": ["Sala", "Ocorrências"], "rows": [[k, v] for k, v in ordered]}
            }})

        if report_name == "frequencia_por_sala":
            mapa = {}
            for x in freq:
                k = x.get("sala_nome") or "SEM SALA"
                mapa.setdefault(k, {"presentes": 0, "total": 0})
                mapa[k]["total"] += 1
                if _status_presenca(x.get("status")):
                    mapa[k]["presentes"] += 1
            ordered = []
            for k, v in mapa.items():
                p = round((v["presentes"] / v["total"]) * 100, 2) if v["total"] else 0
                ordered.append((k, p, v["presentes"], v["total"]))
            ordered.sort(key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Frequência por Sala",
                "chart_type": "bar",
                "chart": {"labels": [x[0] for x in ordered], "data": [x[1] for x in ordered], "dataset_label": "Frequência %"},
                "table": {"headers": ["Sala", "Frequência %", "Presentes", "Total"], "rows": [[x[0], x[1], x[2], x[3]] for x in ordered]}
            }})

        if report_name == "ocorrencias_por_tutor":
            mapa = {}
            for x in ocorr:
                k = x.get("tutor_nome") or "SEM TUTOR"
                mapa[k] = mapa.get(k, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Ocorrência por Tutor",
                "chart_type": "bar",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Ocorrências"},
                "table": {"headers": ["Tutor", "Ocorrências"], "rows": [[k, v] for k, v in ordered]}
            }})

        if report_name == "alunos_por_tutor":
            mapa = {}
            for x in alunos:
                k = x.get("tutor_nome") or x.get("nome_tutor") or "SEM TUTOR"
                mapa[k] = mapa.get(k, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Alunos por Tutor",
                "chart_type": "pie",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Alunos"},
                "table": {"headers": ["Tutor", "Alunos"], "rows": [[k, v] for k, v in ordered]}
            }})

        if report_name == "atendimentos_por_tutor":
            mapa = {}
            detalhes = {}
            for x in atend:
                tutor_nome = x.get("tutor_nome") or "SEM TUTOR"
                mapa.setdefault(tutor_nome, set()).add(x.get("aluno_nome") or "")
                detalhes.setdefault(tutor_nome, []).append({
                    "aluno_nome": x.get("aluno_nome") or "",
                    "data_registro": x.get("data_registro") or "",
                    "tipo_atendimento": x.get("tipo_atendimento") or "",
                })
            ordered = sorted([(k, len(v)) for k, v in mapa.items()], key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Atendimentos por Tutor",
                "chart_type": "bar",
                "chart": {"labels": [x[0] for x in ordered], "data": [x[1] for x in ordered], "dataset_label": "Qtd. atendimentos"},
                "table": {"headers": ["Tutor", "Quantidade", "Ação"], "rows": [[x[0], x[1], "VER DETALHE"] for x in ordered]},
                "detalhes": detalhes
            }})

        if report_name == "frequencia_periodo":
            from datetime import datetime, timedelta, date
            def intervalo_mes(mes_str):
                if mes_str:
                    inicio = datetime.strptime(mes_str + "-01", "%Y-%m-%d").date()
                else:
                    hoje = date.today()
                    inicio = hoje.replace(day=1)
                if inicio.month == 12:
                    prox = date(inicio.year + 1, 1, 1)
                else:
                    prox = date(inicio.year, inicio.month + 1, 1)
                fim = prox - timedelta(days=1)
                return inicio, fim

            inicio, fim = intervalo_mes(mes)
            labels, values = [], []

            if periodo == "semanal":
                base = inicio
                while base <= fim:
                    fim_sem = min(base + timedelta(days=6), fim)
                    subset = [x for x in freq if x.get("data") and base <= datetime.strptime(str(x.get("data"))[:10], "%Y-%m-%d").date() <= fim_sem]
                    total = len(subset)
                    pres = len([x for x in subset if _status_presenca(x.get("status"))])
                    labels.append(f"{base.strftime('%d/%m')} a {fim_sem.strftime('%d/%m')}")
                    values.append(round((pres / total) * 100, 2) if total else 0)
                    base = fim_sem + timedelta(days=1)
            else:
                cur = inicio
                while cur <= fim:
                    dstr = cur.strftime("%Y-%m-%d")
                    subset = [x for x in freq if str(x.get("data"))[:10] == dstr]
                    total = len(subset)
                    pres = len([x for x in subset if _status_presenca(x.get("status"))])
                    labels.append(cur.strftime("%d/%m"))
                    values.append(round((pres / total) * 100, 2) if total else 0)
                    cur += timedelta(days=1)

            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Frequência Semanal, Mensal e Acumulado",
                "chart_type": "line",
                "chart": {"labels": labels, "data": values, "dataset_label": "Frequência %"},
                "table": {"headers": ["Período", "Frequência %"], "rows": [[labels[i], values[i]] for i in range(len(labels))]}
            }})

        if report_name == "ranking_frequencia_alunos":
            mapa = {}
            for x in freq:
                k = x.get("aluno_nome") or "SEM ALUNO"
                mapa.setdefault(k, {"presentes": 0, "total": 0, "sala": x.get("sala_nome") or ""})
                mapa[k]["total"] += 1
                if _status_presenca(x.get("status")):
                    mapa[k]["presentes"] += 1
            ordered = []
            for k, v in mapa.items():
                pct = round((v["presentes"] / v["total"]) * 100, 2) if v["total"] else 0
                ordered.append((k, v["sala"], pct, v["presentes"], v["total"]))
            ordered.sort(key=lambda i: (-i[2], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Ranking de Alunos com Mais Frequência",
                "chart_type": "bar",
                "chart": {"labels": [x[0] for x in ordered[:20]], "data": [x[2] for x in ordered[:20]], "dataset_label": "Frequência %"},
                "table": {"headers": ["Aluno", "Sala", "Frequência %", "Presenças", "Total"], "rows": [[*x] for x in ordered]}
            }})

        if report_name == "ocorrencias_por_professor":
            mapa = {}
            for x in ocorr:
                k = x.get("professor_nome") or "SEM PROFESSOR"
                mapa[k] = mapa.get(k, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Ocorrência por Professor",
                "chart_type": "bar",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Ocorrências"},
                "table": {"headers": ["Professor", "Ocorrências"], "rows": [[k, v] for k, v in ordered]}
            }})

        if report_name == "alunos_baixa_presenca":
            mapa = {}
            for x in freq:
                k = x.get("aluno_nome") or "SEM ALUNO"
                mapa.setdefault(k, {"presentes": 0, "total": 0, "sala": x.get("sala_nome") or ""})
                mapa[k]["total"] += 1
                if _status_presenca(x.get("status")):
                    mapa[k]["presentes"] += 1
            rows = []
            for k, v in mapa.items():
                pct = round((v["presentes"] / v["total"]) * 100, 2) if v["total"] else 0
                if pct < 85:
                    rows.append((k, v["sala"], pct, v["presentes"], v["total"]))
            rows.sort(key=lambda i: (i[2], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Alunos com Presença abaixo de 85%",
                "chart_type": "bar",
                "chart": {"labels": [x[0] for x in rows[:20]], "data": [x[2] for x in rows[:20]], "dataset_label": "Frequência %"},
                "table": {"headers": ["Aluno", "Sala", "Frequência %", "Presenças", "Total"], "rows": [[*x] for x in rows]}
            }})

        if report_name == "atrasos_saidas":
            mapa = {}
            for x in freq:
                status = (x.get("status") or "").upper()
                if status in ["PA", "PS", "PSA"]:
                    k = x.get("aluno_nome") or "SEM ALUNO"
                    mapa.setdefault(k, {"sala": x.get("sala_nome") or "", "pa": 0, "ps": 0, "psa": 0})
                    if status == "PA":
                        mapa[k]["pa"] += 1
                    if status == "PS":
                        mapa[k]["ps"] += 1
                    if status == "PSA":
                        mapa[k]["psa"] += 1
            ordered = []
            for k, v in mapa.items():
                total = v["pa"] + v["ps"] + v["psa"]
                ordered.append((k, v["sala"], v["pa"], v["ps"], v["psa"], total))
            ordered.sort(key=lambda i: (-i[5], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Relatório de Atraso e Saída Antecipada",
                "chart_type": "bar",
                "chart": {"labels": [x[0] for x in ordered[:20]], "data": [x[5] for x in ordered[:20]], "dataset_label": "Ocorrências de atraso/saída"},
                "table": {"headers": ["Aluno", "Sala", "PA", "PS", "PSA", "Total"], "rows": [[*x] for x in ordered]}
            }})

        if report_name == "alunos_sem_tutor":
            linhas = []
            for a in alunos:
                tutor_nome = ((a.get("tutor_nome") or "").strip())
                tutor_id = a.get("tutor_id")
                if not tutor_nome and not tutor_id:
                    linhas.append([a.get("nome") or a.get("aluno_nome"), a.get("sala_nome"), a.get("id")])

            return jsonify({"success": True, "data": {
                "titulo": "Lista de Alunos sem Tutor",
                "chart_type": "bar",
                "chart": {"labels": ["Sem Tutor"], "data": [len(linhas)], "dataset_label": "Qtd. alunos"},
                "table": {"headers": ["Aluno", "Sala", "ID"], "rows": linhas}
            }})

        if report_name == "alunos_por_tutor_detalhado":
            mapa = {}
            for a in alunos:
                tutor_nome = (a.get("tutor_nome") or a.get("nome_tutor") or "SEM TUTOR").strip() or "SEM TUTOR"
                mapa[tutor_nome] = mapa.get(tutor_nome, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Quantidade de Alunos por Tutor",
                "chart_type": "bar",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Qtd. alunos"},
                "table": {"headers": ["Tutor", "Quantidade", "Ação"], "rows": [[k, v] for k, v in ordered]}
            }})

        return json_error("Relatório não encontrado.", 404)

    except Exception as e:
        return json_error(str(e))


@app.route("/relatorio_dashboard_pdf/<report_name>")
def relatorio_dashboard_pdf(report_name):
    try:
        sala = (request.args.get("sala") or "").strip()
        tutor = (request.args.get("tutor") or "").strip()
        professor = (request.args.get("professor") or "").strip()
        periodo = (request.args.get("periodo") or "acumulado").strip()
        mes = (request.args.get("mes") or "").strip()

        with app.test_request_context(
            f"/api/relatorios_dashboard/{report_name}?sala={sala}&tutor={tutor}&professor={professor}&periodo={periodo}&mes={mes}"
        ):
            resp = api_relatorios_dashboard(report_name)

        data = resp.get_json()
        if not data or not data.get("success"):
            return "Erro ao gerar relatório PDF.", 500

        payload = data["data"]
        return render_template(
            "relatorio_dashboard_pdf.html",
            titulo_relatorio=payload.get("titulo", "Relatório"),
            sala=sala,
            tutor=tutor,
            professor=professor,
            mes=mes,
            headers=payload.get("table", {}).get("headers", []),
            rows=payload.get("table", {}).get("rows", [])
        )
    except Exception as e:
        return f"Erro ao gerar PDF: {e}", 500


@app.route("/api/relatorios_geral")
def api_relatorios_geral():
    try:
        db = get_supabase()

        ocorr = db.table("ocorrencias").select("*").execute().data or []
        freq = db.table("f_frequencia").select("*").execute().data or []
        atend = db.table("atendimentos_tutoria").select("*").execute().data or []

        total_oc = len(ocorr)
        total_freq = len(freq)
        faltas = len([x for x in freq if x.get("status") == "F"])
        presencas = total_freq - faltas
        perc = round((presencas/total_freq)*100,2) if total_freq else 0

        por_sala = {}
        freq_sala = {}

        for o in ocorr:
            s = o.get("sala_nome") or "SEM"
            por_sala[s] = por_sala.get(s,0)+1

        for f in freq:
            s = f.get("sala_nome") or "SEM"
            freq_sala.setdefault(s,{"p":0,"t":0})
            freq_sala[s]["t"] +=1
            if f.get("status")!="F":
                freq_sala[s]["p"] +=1

        ranking=[]
        for s in por_sala:
            p = freq_sala.get(s,{"p":0,"t":1})
            pr = round((p["p"]/p["t"])*100,2) if p["t"] else 0
            ranking.append({"sala":s,"ocorrencias":por_sala[s],"frequencia":pr})

        ranking = sorted(ranking,key=lambda x:-x["ocorrencias"])

        return jsonify({
            "ocorrencias": total_oc,
            "frequencia": perc,
            "atendimentos": len(atend),
            "ocorrencias_por_sala":{
                "labels":[x["sala"] for x in ranking],
                "data":[x["ocorrencias"] for x in ranking]
            },
            "frequencia_dias":{
                "labels":["Geral"],
                "data":[perc]
            },
            "ranking": ranking
        })
    except Exception as e:
        return json_error(e)


@app.route("/api/cadastro/ocorrencia/<int:numero>", methods=["PUT"])
def api_cadastro_editar_ocorrencia(numero):
    try:
        if not _eh_acesso_total():
            return json_error("Acesso restrito aos 5 usuários com acesso total.", 403)
        db = get_supabase()
        data = request.get_json() or {}
        db.table("ocorrencias").update({
            "descricao": data.get("descricao"),
            "atendimento_professor": data.get("atendimento_professor"),
            "atendimento_tutor": data.get("atendimento_tutor"),
            "atendimento_coordenacao": data.get("atendimento_coordenacao"),
            "atendimento_gestao": data.get("atendimento_gestao"),
            "atendimento_responsavel": data.get("atendimento_responsavel"),
        }).eq("numero", numero).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)

@app.route("/gestao_conselho_classe")
def gestao_conselho_classe():
    return render_template("gestao_conselho_classe.html")


@app.route("/api/conselho_classe")
def api_conselho_classe():
    try:
        db = get_supabase()
        sala = (request.args.get("sala") or "").strip()
        bimestre = int(request.args.get("bimestre") or 1)

        if not sala:
            return json_error("Sala não informada.", 400)

        alunos = db.table("d_alunos").select("*").eq("sala_nome", sala).order("nome").execute().data or []
        notas = db.table("f_notas").select("*").eq("sala_nome", sala).execute().data or []

        resumo_resp = db.table("f_conselho_classe").select("*").eq("sala_nome", sala).eq("bimestre", bimestre).limit(1).execute().data or []
        resumo = resumo_resp[0] if resumo_resp else {}

        criticos = []
        alunos_sala = []

        for a in alunos:
            nome = a.get("nome") or a.get("aluno_nome") or ""
            alunos_sala.append(nome)

        for n in notas:
            nota = n.get(f"nota_{bimestre}b")
            try:
                nota_num = float(nota) if nota not in (None, "", "null") else None
            except Exception:
                nota_num = None

            if nota_num is not None and nota_num < 5:
                conselho = n.get(f"conselho_{bimestre}b") or {}
                criticos.append({
                    "aluno_nome": n.get("aluno_nome"),
                    "disciplina": n.get("disciplina"),
                    "nota": nota_num,
                    "causas": conselho.get("causas", []),
                    "solucoes": conselho.get("solucoes", [])
                })

        criticos.sort(key=lambda x: ((x.get("aluno_nome") or "").upper(), (x.get("disciplina") or "").upper()))

        return jsonify({
            "success": True,
            "data": {
                "alunos_criticos": criticos,
                "alunos_sala": sorted(alunos_sala),
                "resumo": {
                    "pontos_fortes": resumo.get("pontos_fortes", ""),
                    "pontos_melhoria": resumo.get("pontos_melhoria", ""),
                    "aluno_destaque": resumo.get("aluno_destaque", ""),
                    "aluno_evolucao": resumo.get("aluno_evolucao", "")
                }
            }
        })
    except Exception as e:
        return json_error(e)


@app.route("/api/salvar_conselho_classe", methods=["POST"])
def api_salvar_conselho_classe():
    try:
        db = get_supabase()
        data = request.get_json() or {}

        sala_nome = (data.get("sala_nome") or "").strip()
        bimestre = int(data.get("bimestre") or 0)
        if not sala_nome or not bimestre:
            return json_error("Sala e bimestre são obrigatórios.", 400)

        payload = {
            "sala_nome": sala_nome,
            "bimestre": bimestre,
            "pontos_fortes": data.get("pontos_fortes"),
            "pontos_melhoria": data.get("pontos_melhoria"),
            "aluno_destaque": data.get("aluno_destaque"),
            "aluno_evolucao": data.get("aluno_evolucao"),
            "updated_at": now_iso()
        }

        existente = db.table("f_conselho_classe").select("id").eq("sala_nome", sala_nome).eq("bimestre", bimestre).limit(1).execute().data or []
        if existente:
            db.table("f_conselho_classe").update(payload).eq("id", existente[0]["id"]).execute()
        else:
            payload["created_at"] = now_iso()
            db.table("f_conselho_classe").insert(payload).execute()

        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/api/disciplinas_todas")
def api_disciplinas_todas():
    try:
        db = get_supabase()
        r = db.table("d_disciplinas").select("nome").order("nome").execute()
        nomes = sorted({x.get("nome") for x in (r.data or []) if x.get("nome")})
        return jsonify([{"nome": n} for n in nomes])
    except Exception as e:
        return json_error(e)


@app.route("/api/salvar_notas", methods=["POST"])
def api_salvar_notas():
    try:
        db = get_supabase()
        dados = request.get_json() or []

        for item in dados:
            aluno_id = item.get("aluno_id")
            disciplina = item.get("disciplina")

            existente = db.table("f_notas").select("id").eq("aluno_id", aluno_id).eq("disciplina", disciplina).limit(1).execute().data or []

            payload = {
                "aluno_id": aluno_id,
                "aluno_nome": item.get("aluno_nome"),
                "sala_nome": item.get("sala_nome"),
                "disciplina": disciplina,
                "nota_1b": item.get("nota_1b"),
                "nota_2b": item.get("nota_2b"),
                "nota_3b": item.get("nota_3b"),
                "nota_4b": item.get("nota_4b"),
                "conselho_1b": item.get("conselho_1b") or {},
                "conselho_2b": item.get("conselho_2b") or {},
                "conselho_3b": item.get("conselho_3b") or {},
                "conselho_4b": item.get("conselho_4b") or {},
                "updated_at": now_iso()
            }

            if existente:
                db.table("f_notas").update(payload).eq("id", existente[0]["id"]).execute()
            else:
                payload["created_at"] = now_iso()
                db.table("f_notas").insert(payload).execute()

        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)


@app.route("/relatorio_conselho_classe_pdf")
def relatorio_conselho_classe_pdf():
    try:
        db = get_supabase()
        sala = (request.args.get("sala") or "").strip()
        bimestre = int(request.args.get("bimestre") or 1)

        if not sala:
            return "Sala não informada.", 400

        alunos = (
            db.table("d_alunos")
            .select("*")
            .eq("sala_nome", sala)
            .order("nome")
            .execute()
            .data or []
        )

        notas = (
            db.table("f_notas")
            .select("*")
            .eq("sala_nome", sala)
            .execute()
            .data or []
        )

        resumo_resp = (
            db.table("f_conselho_classe")
            .select("*")
            .eq("sala_nome", sala)
            .eq("bimestre", bimestre)
            .limit(1)
            .execute()
            .data or []
        )
        resumo = resumo_resp[0] if resumo_resp else {}

        disciplinas = sorted({n.get("disciplina") for n in notas if n.get("disciplina")})
        mapa = {}
        professores = []

        for n in notas:
            nome = n.get("aluno_nome") or ""
            mapa.setdefault(nome, {})
            mapa[nome][n.get("disciplina")] = n

            professor = n.get("professor_nome")
            if professor and professor not in professores:
                professores.append(professor)

        linhas = []
        qtd_menor_5 = 0
        qtd_maior_igual_5 = 0

        for a in alunos:
            nome = a.get("nome") or a.get("aluno_nome") or ""
            notas_aluno = []
            causas = []
            solucoes = []
            aluno_tem_menor_5 = False

            for d in disciplinas:
                reg = mapa.get(nome, {}).get(d, {})
                nota = reg.get(f"nota_{bimestre}b")

                try:
                    nota_num = float(nota) if nota not in (None, "", "null") else None
                except Exception:
                    nota_num = None

                notas_aluno.append(nota if nota not in (None, "", "null") else "")

                if nota_num is not None and nota_num < 5:
                    aluno_tem_menor_5 = True
                    conselho = reg.get(f"conselho_{bimestre}b") or {}
                    causas.extend(conselho.get("causas", []))
                    solucoes.extend(conselho.get("solucoes", []))

            if aluno_tem_menor_5:
                qtd_menor_5 += 1
            else:
                qtd_maior_igual_5 += 1

            linhas.append({
                "aluno_nome": nome,
                "notas": notas_aluno,
                "causas": ", ".join(sorted(set(causas))),
                "solucoes": ", ".join(sorted(set(solucoes)))
            })

        total_alunos = len(alunos)
        aproveitamento = round((qtd_maior_igual_5 / total_alunos) * 100, 2) if total_alunos > 0 else 0

        if not professores:
            professores = disciplinas

        return render_template(
            "relatorio_conselho_classe_pdf.html",
            sala_nome=sala,
            bimestre=bimestre,
            disciplinas=disciplinas,
            linhas=linhas,
            professores=professores,
            qtd_menor_5=qtd_menor_5,
            qtd_maior_igual_5=qtd_maior_igual_5,
            aproveitamento=aproveitamento,
            pontos_fortes=resumo.get("pontos_fortes", ""),
            pontos_melhoria=resumo.get("pontos_melhoria", ""),
            aluno_destaque=resumo.get("aluno_destaque", ""),
            aluno_evolucao=resumo.get("aluno_evolucao", "")
        )
    except Exception as e:
        return f"Erro ao gerar mapão: {e}", 500







@app.route("/api/cadastro/aluno/<int:aluno_id>")
def api_detalhe_aluno_cadastro(aluno_id):
    try:
        db = get_supabase()
        resp = db.table("d_alunos").select("*").eq("id", aluno_id).limit(1).execute()
        if not resp.data:
            return json_error("Aluno não encontrado.", 404)
        return jsonify(resp.data[0])
    except Exception as e:
        return json_error(e)

@app.route("/api/tutores_disponiveis_cadastro")
def api_tutores_disponiveis_cadastro():
    try:
        db = get_supabase()
        funcionarios = db.table("d_funcionarios").select("id,nome,tipo,funcao").order("nome").execute().data or []
        alunos = db.table("d_alunos").select("tutor_id,id_tutor").eq("situacao_aluno", "ATIVO").execute().data or []
        contagem = {}
        for a in alunos:
            tutor_id = a.get("tutor_id") or a.get("id_tutor")
            if tutor_id not in (None, "", "NULL"):
                try:
                    tutor_id = int(tutor_id)
                    contagem[tutor_id] = contagem.get(tutor_id, 0) + 1
                except Exception:
                    pass

        tutores = []
        for f in funcionarios:
            tipo = (f.get("tipo") or "").strip().upper()
            funcao = (f.get("funcao") or "").strip().upper()
            if tipo == "PROFESSOR" and "APOIO" not in funcao:
                qtd = contagem.get(int(f["id"]), 0)
                if qtd < 22:
                    tutores.append({"id": f["id"], "nome": f["nome"]})
        return jsonify(tutores)
    except Exception as e:
        return json_error(e)

@app.route("/api/salvar_tutor_aluno/<int:aluno_id>", methods=["PUT"])
def api_salvar_tutor_aluno(aluno_id):
    try:
        db = get_supabase()
        data = request.get_json() or {}
        payload = {
            "tutor_id": int(data.get("tutor_id")) if data.get("tutor_id") not in (None, "", "None") else None,
            "id_tutor": int(data.get("id_tutor")) if data.get("id_tutor") not in (None, "", "None") else None,
            "tutor_nome": data.get("tutor_nome"),
            "nome_tutor": data.get("nome_tutor")
        }
        db.table("d_alunos").update(payload).eq("id", aluno_id).execute()
        return jsonify({"success": True})
    except Exception as e:
        return json_error(e)

@app.route("/relatorio_alunos_tutor")
def relatorio_alunos_tutor():
    try:
        db = get_supabase()
        tutor = (request.args.get("tutor") or "").strip()
        if not tutor:
            return "Tutor não informado.", 400

        alunos = db.table("d_alunos").select("*").eq("situacao_aluno", "ATIVO").eq("tutor_nome", tutor).order("nome").execute().data or []
        if not alunos:
            alunos = db.table("d_alunos").select("*").eq("situacao_aluno", "ATIVO").eq("nome_tutor", tutor).order("nome").execute().data or []

        salas = sorted(list({(a.get("sala_nome") or "").strip() for a in alunos if (a.get("sala_nome") or "").strip()}))
        return render_template("relatorio_alunos_tutor.html", tutor=tutor, alunos=alunos, salas=salas)
    except Exception as e:
        return f"Erro ao abrir relatório: {e}", 500

@app.route("/relatorio_alunos_tutor_pdf")
def relatorio_alunos_tutor_pdf():
    try:
        db = get_supabase()
        tutor = (request.args.get("tutor") or "").strip()
        if not tutor:
            return "Tutor não informado.", 400

        alunos = db.table("d_alunos").select("*").eq("situacao_aluno", "ATIVO").eq("tutor_nome", tutor).order("nome").execute().data or []
        if not alunos:
            alunos = db.table("d_alunos").select("*").eq("situacao_aluno", "ATIVO").eq("nome_tutor", tutor).order("nome").execute().data or []

        return render_template("relatorio_alunos_tutor_pdf.html", tutor=tutor, alunos=alunos)
    except Exception as e:
        return f"Erro ao gerar PDF: {e}", 500

# =========================================================
# START
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
