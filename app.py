from flask import Flask, render_template, request, jsonify, redirect, session, url_for, make_response
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
from datetime import datetime, timedelta, date
import os
import unicodedata
import pytz

from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


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

def _find_sala_by_nome(db, sala_nome):
    sala_nome = (sala_nome or "").strip()
    if not sala_nome:
        return None
    resp = db.table("d_salas").select("*").eq("sala", sala_nome).limit(1).execute()
    dados = resp.data or []
    if dados:
        return dados[0]
    resp = db.table("d_salas").select("*").eq("nome", sala_nome).limit(1).execute()
    dados = resp.data or []
    return dados[0] if dados else None

def _find_tutor_by_nome(db, tutor_nome):
    tutor_nome = (tutor_nome or "").strip()
    if not tutor_nome:
        return None
    resp = db.table("d_funcionarios").select("id,nome").eq("nome", tutor_nome).limit(1).execute()
    dados = resp.data or []
    return dados[0] if dados else None

def resolver_relacoes_aluno(db, data):
    data = dict(data or {})

    sala_nome = (data.get("sala_nome") or "").strip()
    sala_id = data.get("sala_id")
    if sala_id in ("", "None"):
        sala_id = None

    sala = None
    if sala_id not in (None, ""):
        try:
            resp = db.table("d_salas").select("*").eq("id", int(sala_id)).limit(1).execute()
            dados = resp.data or []
            sala = dados[0] if dados else None
        except Exception:
            sala = None

    if not sala and sala_nome:
        sala = _find_sala_by_nome(db, sala_nome)

    if sala:
        data["sala_id"] = sala.get("id")
        data["sala_nome"] = normalize_sala_nome(sala) or sala_nome
    else:
        data["sala_id"] = None if sala_id in (None, "") else sala_id
        data["sala_nome"] = sala_nome

    tutor_nome = (data.get("tutor_nome") or data.get("nome_tutor") or "").strip()
    tutor_id = data.get("tutor_id") or data.get("id_tutor")
    if tutor_id in ("", "None"):
        tutor_id = None

    tutor = None
    if tutor_id not in (None, ""):
        try:
            resp = db.table("d_funcionarios").select("id,nome").eq("id", int(tutor_id)).limit(1).execute()
            dados = resp.data or []
            tutor = dados[0] if dados else None
        except Exception:
            tutor = None

    if not tutor and tutor_nome:
        tutor = _find_tutor_by_nome(db, tutor_nome)

    if tutor:
        data["tutor_id"] = tutor.get("id")
        data["id_tutor"] = tutor.get("id")
        data["tutor_nome"] = tutor.get("nome")
        data["nome_tutor"] = tutor.get("nome")
    else:
        data["tutor_id"] = None if tutor_id in (None, "") else tutor_id
        data["id_tutor"] = None if tutor_id in (None, "") else tutor_id
        data["tutor_nome"] = tutor_nome
        data["nome_tutor"] = tutor_nome

    return data

def buscar_alunos_ativos_da_sala(db, sala_id):
    sala_resp = db.table("d_salas").select("*").eq("id", sala_id).limit(1).execute()
    sala_data = sala_resp.data or []
    sala_nome = normalize_sala_nome(sala_data[0]) if sala_data else ""

    por_id = db.table("d_alunos").select("*").eq("sala_id", sala_id).eq("situacao_aluno", "ATIVO").order("nome").execute().data or []
    por_nome = []
    if sala_nome:
        por_nome = db.table("d_alunos").select("*").eq("sala_nome", sala_nome).eq("situacao_aluno", "ATIVO").order("nome").execute().data or []

    unicos = {}
    for item in por_id + por_nome:
        chave = item.get("id") or f"{normalize_aluno_nome(item)}|{item.get('sala_nome') or ''}"
        if chave not in unicos:
            unicos[chave] = item

    dados = list(unicos.values())
    for item in dados:
        item["nome"] = normalize_aluno_nome(item)
        if not item.get("sala_id") and sala_id not in (None, ""):
            item["sala_id"] = sala_id
        if not item.get("sala_nome") and sala_nome:
            item["sala_nome"] = sala_nome
    dados.sort(key=lambda x: normalize_aluno_nome(x))
    return dados

def get_next_numero_ocorrencia():
    db = get_supabase()
    resp = db.table("ocorrencias").select("numero").order("numero", desc=True).limit(1).execute()
    if resp.data:
        return int(resp.data[0]["numero"]) + 1
    return 1

SP_TZ = pytz.timezone("America/Sao_Paulo")

def now_sp():
    return datetime.now(SP_TZ)

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
        payload = resolver_relacoes_aluno(db, {
            "nome": data.get("nome"),
            "aluno_nome": data.get("aluno_nome"),
            "sala_id": data.get("sala_id"),
            "sala_nome": data.get("sala_nome"),
            "tutor_id": data.get("tutor_id"),
            "id_tutor": data.get("id_tutor"),
            "tutor_nome": data.get("tutor_nome"),
            "nome_tutor": data.get("nome_tutor"),
            "situacao_aluno": data.get("situacao_aluno") or "ATIVO",
            "projeto_de_vida": data.get("projeto_de_vida"),
        })
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
        payload = resolver_relacoes_aluno(db, {
            "nome": data.get("nome"),
            "aluno_nome": data.get("aluno_nome"),
            "sala_id": data.get("sala_id"),
            "sala_nome": data.get("sala_nome"),
            "tutor_id": data.get("tutor_id"),
            "id_tutor": data.get("id_tutor"),
            "tutor_nome": data.get("tutor_nome"),
            "nome_tutor": data.get("nome_tutor"),
            "situacao_aluno": data.get("situacao_aluno") or "ATIVO",
            "projeto_de_vida": data.get("projeto_de_vida"),
        })
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
    "ELAINE CRISTINA ARIEDE KACA DO CARMO",
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
        "ELAINE CRISTINA ARIEDE KACA DO CARMO",
        "MARCELO ANDRE NOGUEIRA CARDES",
        "MARCILENE MANTOVANI COSSENZO PUPIM",
    }

def usuario_pode_ver_coordenacao():
    return usuario_logado_nome() in {
        "ELAINE CRISTINA ARIEDE KACA DO CARMO",
        "MARCELO ANDRE NOGUEIRA CARDES",
        "GRAZIELLE DA SILVA FEIJO VIANA",
        "MARCOS DE BRITO BORTOLOSSI",
        "MARCILENE MANTOVANI COSSENZO PUPIM",
    }

def usuario_pode_ver_responsavel():
    return usuario_logado_nome() in {
        "ELAINE CRISTINA ARIEDE KACA DO CARMO",
        "MARCELO ANDRE NOGUEIRA CARDES",
        "MARCILENE MANTOVANI COSSENZO PUPIM",
    }



def _parse_date_only(value):
    s = str(value or '').strip()[:10]
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None

def _is_weekday_value(value):
    d = _parse_date_only(value)
    return bool(d and d.weekday() < 5)

def _status_presenca_dashboard_geral(status):
    return (status or '').strip().upper() in {'P', 'PA', 'PS', 'PSA'}

def _status_presenca_dashboard_frequencia(status):
    return (status or '').strip().upper() == 'P'

def _status_falta(status):
    return (status or '').strip().upper() == 'F'

def _week_bounds_sp(ref_date=None):
    ref_date = ref_date or now_sp().date()
    monday = ref_date - timedelta(days=ref_date.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def _fetch_all_rows(db, table_name, select_cols="*", page_size=1000, order_col="id"):
    registros = []
    inicio = 0
    while True:
        query = db.table(table_name).select(select_cols)
        if order_col:
            query = query.order(order_col)
        resp = query.range(inicio, inicio + page_size - 1).execute()
        lote = resp.data or []
        if not lote:
            break
        registros.extend(lote)
        if len(lote) < page_size:
            break
        inicio += page_size
    return registros

def _dedupe_frequencia_registros(registros):
    mapa = {}
    for item in registros or []:
        data_ref = str(item.get('data') or '')[:10]
        sala = str(item.get('sala_nome') or '').strip()
        aluno_id = item.get('aluno_id')
        aluno_nome = str(item.get('aluno_nome') or '').strip().upper()
        chave = (data_ref, str(aluno_id) if aluno_id is not None else f'NOME::{aluno_nome}', sala)
        mapa[chave] = item
    return list(mapa.values())


def _parse_date_generic(value):
    txt = str(value or "").strip()
    if not txt:
        return None
    txt = txt[:10]
    try:
        return datetime.strptime(txt, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.strptime(txt, "%d/%m/%Y").date()
        except Exception:
            return None

def _filtrar_periodo_registros(registros, campo_data, data_inicio=None, data_fim=None):
    if not data_inicio and not data_fim:
        return list(registros or [])
    di = _parse_date_generic(data_inicio) if data_inicio else None
    df = _parse_date_generic(data_fim) if data_fim else None
    filtrados = []
    for item in registros or []:
        d = _parse_date_generic(item.get(campo_data))
        if not d:
            continue
        if di and d < di:
            continue
        if df and d > df:
            continue
        filtrados.append(item)
    return filtrados

def _coletar_opcoes_semestre(db, table_name):
    registros = _fetch_all_rows(db, table_name, "*", order_col="id")
    vistos = set()
    opcoes = []
    chaves = ["nome", "descricao", "titulo", "clube", "eletiva"]
    for item in registros:
        valor = ""
        for chave in chaves:
            valor = str(item.get(chave) or "").strip()
            if valor:
                break
        if not valor:
            continue
        valor_norm = normalizar_texto(valor)
        if valor_norm in vistos:
            continue
        vistos.add(valor_norm)
        opcoes.append({"id": item.get("id"), "nome": valor})
    opcoes.sort(key=lambda x: x["nome"])
    return opcoes

def _pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SGCETitle", parent=styles["Heading1"], fontSize=16, leading=20, textColor=colors.HexColor("#065f46"), spaceAfter=8))
    styles.add(ParagraphStyle(name="SGCESubtitle", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#334155"), spaceAfter=4))
    styles.add(ParagraphStyle(name="SGCESection", parent=styles["Heading2"], fontSize=11, leading=14, textColor=colors.HexColor("#0f172a"), spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle(name="SGCESmall", parent=styles["Normal"], fontSize=8.5, leading=11))
    return styles

def _build_table(data_rows, header=True, col_widths=None, repeat_rows=1):
    table = Table(data_rows, colWidths=col_widths, repeatRows=repeat_rows if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#94a3b8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header and data_rows:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    table.setStyle(TableStyle(style))
    return table

def _pdf_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(15 * mm, 10 * mm, "SGCE - Sistema de Gestão de Convivência Escolar")
    canvas.drawRightString(doc.pagesize[0] - 15 * mm, 10 * mm, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()

def _pdf_response(filename, story, pagesize=A4):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=16 * mm,
    )
    doc.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer)
    pdf = buffer.getvalue()
    buffer.close()
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

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
    return render_template(
        "gestao_tutoria_ficha.html",
        usuario_nome=usuario_logado_nome(),
        acesso_total=usuario_tem_acesso_total()
    )


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
        resp = db.table("d_salas").select("*").order("sala").execute()
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
        resp = db.table("d_salas").select("*").order("sala").execute()
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
        dados = buscar_alunos_ativos_da_sala(db, sala_id)
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
        hoje = now_sp().date()
        hoje_str = hoje.strftime("%Y-%m-%d")

        ocorr_data = _fetch_all_rows(db, "ocorrencias", "*", order_col="numero")
        freq_data = _fetch_all_rows(db, "f_frequencia", "status,data,sala_nome,aluno_id,aluno_nome,updated_at,created_at,id", order_col="id")
        freq_data = _dedupe_frequencia_registros(freq_data)
        atend_data = _fetch_all_rows(db, "atendimentos_tutoria", "*", order_col="id")
        salas_data = _fetch_all_rows(db, "d_salas", "*", order_col="id")

        alunos_ativos_resp = (
            db.table("d_alunos")
            .select("id,nome,aluno_nome,sala_nome", count="exact")
            .eq("situacao_aluno", "ATIVO")
            .execute()
        )
        alunos_ativos = alunos_ativos_resp.data or []
        alunos_total = alunos_ativos_resp.count or len(alunos_ativos)
        ids_ativos = {str(x.get("id")) for x in alunos_ativos if x.get("id") is not None}

        freq_filtrada = []
        for item in freq_data:
            aluno_id = item.get("aluno_id")
            if aluno_id is None or str(aluno_id) in ids_ativos:
                freq_filtrada.append(item)

        freq_semana = [x for x in freq_filtrada if _is_weekday_value(x.get("data"))]
        freq_hoje = [x for x in freq_semana if str(x.get("data") or "")[:10] == hoje_str]

        presentes_hoje = len([x for x in freq_hoje if _status_presenca_dashboard_geral(x.get("status"))])
        total_freq_semana = len(freq_semana)
        total_presencas_semana = len([x for x in freq_semana if _status_presenca_dashboard_geral(x.get("status"))])
        frequencia_percentual = round((total_presencas_semana / total_freq_semana) * 100, 2) if total_freq_semana > 0 else 0

        ocorrencias_dia = len([x for x in ocorr_data if str(x.get("data_hora") or "")[:10] == hoje_str])
        ocorrencias_gerais = len(ocorr_data)
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
        for x in freq_semana:
            sala = str(x.get("sala_nome") or "").strip()
            if not sala:
                continue
            if sala not in mapa_presenca:
                mapa_presenca[sala] = {"presentes": 0, "total": 0, "percentual": 0}
            mapa_presenca[sala]["total"] += 1
            if _status_presenca_dashboard_geral(x.get("status")):
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

        salas_resp = db.table("d_salas").select("*").order("sala").execute()
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

        alunos = buscar_alunos_ativos_da_sala(db, int(sala_id))
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

        alunos = buscar_alunos_ativos_da_sala(db, int(sala_id))
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
        hoje_date = now_sp().date()
        hoje = hoje_date.strftime("%Y-%m-%d")
        segunda, sexta = _week_bounds_sp(hoje_date)

        dados = _fetch_all_rows(db, "f_frequencia", "id,status,data,sala_nome,aluno_id,aluno_nome,updated_at,created_at", order_col="id")

        dados_pf = [x for x in dados if (x.get("status") or "").strip().upper() in {"P", "F"}]
        dados_pf = _dedupe_frequencia_registros(dados_pf)

        dados_semana = []
        for x in dados_pf:
            d = _parse_date_only(x.get("data"))
            if d and segunda <= d <= sexta and d.weekday() < 5:
                dados_semana.append(x)

        hoje_registros = [x for x in dados_semana if str(x.get("data") or "")[:10] == hoje]
        presentes = [x for x in hoje_registros if _status_presenca_dashboard_frequencia(x.get("status"))]
        faltas = [x for x in hoje_registros if _status_falta(x.get("status"))]

        ranking_map = {}
        for x in dados_semana:
            sala = (x.get("sala_nome") or "SEM SALA").strip()
            ranking_map.setdefault(sala, {"presentes": 0, "faltas": 0, "total": 0})
            ranking_map[sala]["total"] += 1
            if _status_presenca_dashboard_frequencia(x.get("status")):
                ranking_map[sala]["presentes"] += 1
            elif _status_falta(x.get("status")):
                ranking_map[sala]["faltas"] += 1

        ranking = []
        for sala, info in ranking_map.items():
            pct = round((info["presentes"] / info["total"]) * 100, 2) if info["total"] else 0
            ranking.append({
                "nome": sala,
                "frequencia": pct,
                "presentes": info["presentes"],
                "faltas": info["faltas"],
                "total": info["total"]
            })
        ranking.sort(key=lambda x: (-x["frequencia"], -x["presentes"], x["nome"]))

        total_hoje = len(hoje_registros)
        frequencia_dia = round((len(presentes) / total_hoje) * 100, 2) if total_hoje else 0
        total_geral = len(dados_semana)
        frequencia_geral = round((sum(1 for x in dados_semana if _status_presenca_dashboard_frequencia(x.get("status"))) / total_geral) * 100, 2) if total_geral else 0

        return jsonify({
            "success": True,
            "data": {
                "cards": {
                    "presenca_dia": len(presentes),
                    "faltas_dia": len(faltas),
                    "frequencia_dia": frequencia_dia,
                    "frequencia_geral": frequencia_geral,
                    "total_registros_dia": total_hoje
                },
                "ranking_salas": ranking,
                "periodo_semanal": {
                    "inicio": segunda.strftime("%d/%m/%Y"),
                    "fim": sexta.strftime("%d/%m/%Y")
                }
            }
        })
    except Exception as e:
        return json_error(e)


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



@app.route("/api/tutoria/opcoes_clube_juvenil")
def api_tutoria_opcoes_clube_juvenil():
    try:
        db = get_supabase()
        return jsonify(_coletar_opcoes_semestre(db, "d_clubes_juvenis"))
    except Exception as e:
        return json_error(e)

@app.route("/api/tutoria/opcoes_eletiva")
def api_tutoria_opcoes_eletiva():
    try:
        db = get_supabase()
        return jsonify(_coletar_opcoes_semestre(db, "d_eletivas"))
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

        alunos_resp = db.table("d_alunos").select("id,tutor_id,tutor_nome,situacao_aluno").execute()
        agend_resp = db.table("agendamentos_tutoria").select("id,status", count="exact").execute()
        atend_resp = db.table("atendimentos_tutoria").select("id", count="exact").execute()

        tutores = tutores_resp.data or []
        alunos = [
            a for a in (alunos_resp.data or [])
            if (str(a.get("situacao_aluno") or "").strip().upper() in {"ATIVO", "ATIVA", ""})
        ]
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


@app.route("/api/tutoria/alunos_ficha")
def api_tutoria_alunos_ficha():
    try:
        db = get_supabase()
        tutor_id = (request.args.get("tutor_id") or "").strip()
        tutor_nome = (request.args.get("tutor_nome") or "").strip()

        if not usuario_tem_acesso_total():
            tutor_nome = (session.get("user") or {}).get("nome") or ""
            tutor_id = ""

        if tutor_id:
            tutor_resp = db.table("d_funcionarios").select("id,nome").eq("id", tutor_id).limit(1).execute().data or []
            if tutor_resp:
                tutor_nome = tutor_resp[0].get("nome") or tutor_nome

        if not tutor_nome:
            return jsonify({"success": True, "data": [], "meta": {"modo_tutor": not usuario_tem_acesso_total()}})

        by_id = []
        if tutor_id:
            by_id = db.table("d_alunos").select("*").eq("tutor_id", int(tutor_id)).eq("situacao_aluno", "ATIVO").order("nome").execute().data or []

        by_nome = db.table("d_alunos").select("*").eq("tutor_nome", tutor_nome).eq("situacao_aluno", "ATIVO").order("nome").execute().data or []

        mapa = {}
        for a in by_id + by_nome:
            mapa[str(a.get("id"))] = a
        alunos = list(mapa.values())

        def first_nonempty(*vals):
            for v in vals:
                if v not in (None, "", "null"):
                    return v
            return ""

        aluno_ids = [a.get("id") for a in alunos if a.get("id") is not None]
        ocorrencias = []
        if aluno_ids:
            try:
                ocorrencias = db.table("ocorrencias").select("numero,aluno_id,pendencia,status").in_("aluno_id", aluno_ids).execute().data or []
            except Exception:
                ocorrencias = db.table("ocorrencias").select("numero,aluno_id,pendencia,status").execute().data or []
                ocorrencias = [o for o in ocorrencias if o.get("aluno_id") in aluno_ids]

        pendencias_por_aluno = {}
        for o in ocorrencias:
            if (o.get("pendencia") or "").strip().upper() != "TUTOR":
                continue
            if (o.get("status") or "").strip().upper() != "ATENDIMENTO":
                continue
            aid = str(o.get("aluno_id"))
            pendencias_por_aluno.setdefault(aid, []).append(o.get("numero"))

        linhas = []
        for a in alunos:
            projeto_vida = first_nonempty(a.get("projeto_de_vida"), a.get("projeto_vida"))
            clube = first_nonempty(a.get("clube_1_semestre"), a.get("clube_juvenil"), a.get("clube"))
            eletiva = first_nonempty(a.get("eletiva_1_semestre"), a.get("eletiva"))
            telefone = first_nonempty(a.get("telefone_aluno"), a.get("telefone"))
            responsavel = first_nonempty(a.get("responsavel_nome"), a.get("nome_responsavel"))
            telefone_resp = first_nonempty(a.get("responsavel_telefone"), a.get("telefone_responsavel"))
            ficha_ok = all([
                str(projeto_vida).strip(),
                str(clube).strip(),
                str(eletiva).strip(),
                str(telefone).strip(),
                str(responsavel).strip(),
                str(telefone_resp).strip()
            ])
            pendencias = pendencias_por_aluno.get(str(a.get("id")), [])
            linhas.append({
                "id": a.get("id"),
                "tutor_id": a.get("tutor_id"),
                "nome": a.get("nome") or a.get("aluno_nome") or "",
                "sala": a.get("sala_nome") or "",
                "projeto_vida": projeto_vida,
                "clube_1_semestre": clube,
                "eletiva_1_semestre": eletiva,
                "telefone": telefone,
                "responsavel": responsavel,
                "telefone_responsavel": telefone_resp,
                "ficha_ok": ficha_ok,
                "pendencia_tutor": len(pendencias),
                "pendencia_numeros": pendencias
            })

        linhas.sort(key=lambda x: (x["sala"], x["nome"]))
        return jsonify({
            "success": True,
            "data": linhas,
            "meta": {
                "modo_tutor": not usuario_tem_acesso_total(),
                "tutor_nome": tutor_nome
            }
        })
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

        # tenta notas em f_notas; se não houver, tenta notas_aluno
        notas = []
        try:
            notas = db.table("f_notas").select("*").eq("aluno_id", aluno_id).execute().data or []
        except Exception:
            try:
                notas = db.table("notas_aluno").select("*").eq("aluno_id", aluno_id).execute().data or []
            except Exception:
                notas = []

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

        ocorrencias = ocorr_resp.data or []
        for o in ocorrencias:
            o["pode_responder_tutor"] = (o.get("pendencia") or "").strip().upper() == "TUTOR"

        frequencia = freq_resp.data or []
        total_freq = len(frequencia)
        frequencia_util = [x for x in frequencia if _is_weekday_value(x.get("data"))]
        total_freq = len(frequencia_util)
        presencas = len([x for x in frequencia_util if _status_presenca_dashboard_geral(x.get("status"))])
        frequencia_percentual = round((presencas / total_freq) * 100, 2) if total_freq else 0

        return jsonify({
            "success": True,
            "aluno": aluno,
            "ocorrencias": ocorrencias,
            "atendimentos": atend_resp.data or [],
            "agendamentos": agend_resp.data or [],
            "frequencia": frequencia,
            "notas": notas,
            "frequencia_percentual": frequencia_percentual,
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

        styles = _pdf_styles()
        story = [
            Paragraph("SGCE - Ficha Profissional do Aluno", styles["SGCETitle"]),
            Paragraph(aluno_nome, styles["Heading2"]),
            Paragraph(f"Emitido em {now_sp().strftime('%d/%m/%Y %H:%M')}", styles["SGCESubtitle"]),
            Spacer(1, 4),
            _build_table([
                ["Aluno", aluno_nome, "Sala", sala_nome],
                ["Tutor", tutor_nome, "Projeto de Vida", projeto_vida],
                ["Frequência", f"{frequencia_percentual}%", "Faltas / Atrasos / Saídas", f"{faltas} / {atrasos} / {saidas}"],
            ], header=False),
            Spacer(1, 8),
            Paragraph("Boletim", styles["SGCESection"]),
        ]

        boletim_rows = [["Disciplina", "1º", "2º", "3º", "4º", "Média", "Status"]]
        for b in boletim:
            boletim_rows.append([
                str(b.get("disciplina") or ""),
                str(b.get("nota_1b") or ""),
                str(b.get("nota_2b") or ""),
                str(b.get("nota_3b") or ""),
                str(b.get("nota_4b") or ""),
                str(b.get("media") or ""),
                str(b.get("status") or ""),
            ])
        story.append(_build_table(boletim_rows))
        story.append(Spacer(1, 8))

        story.append(Paragraph("Atendimentos", styles["SGCESection"]))
        atend_rows = [["Data", "Tipo", "Registro"]]
        for a in atendimentos[:40]:
            atend_rows.append([
                str(a.get("data_registro") or "")[:16],
                str(a.get("tipo_atendimento") or ""),
                str(a.get("registro") or "")[:160],
            ])
        if len(atend_rows) == 1:
            atend_rows.append(["", "", "Sem atendimentos registrados."])
        story.append(_build_table(atend_rows))
        story.append(Spacer(1, 8))

        story.append(Paragraph("Ocorrências", styles["SGCESection"]))
        ocorr_rows = [["Nº", "Data", "Status", "Descrição"]]
        for o in ocorrencias[:60]:
            ocorr_rows.append([
                str(o.get("numero") or ""),
                str(o.get("data_hora") or "")[:16],
                str(o.get("status") or ""),
                str(o.get("descricao") or "")[:180],
            ])
        if len(ocorr_rows) == 1:
            ocorr_rows.append(["", "", "", "Sem ocorrências registradas."])
        story.append(_build_table(ocorr_rows))

        return _pdf_response(f"ficha_profissional_aluno_{aluno_id}.pdf", story)
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


def _parse_date_any(value):
    from datetime import datetime
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def _week_range(ref=None):
    from datetime import timedelta
    ref = ref or now_sp().date()
    inicio = ref - timedelta(days=ref.weekday())
    fim = inicio + timedelta(days=4)
    return inicio, fim


def _report_period_range(periodo, mes, data_inicio, data_fim):
    hoje = now_sp().date()
    periodo = (periodo or "acumulado").strip().lower()
    if periodo == "dia":
        alvo = _parse_date_any(data_inicio) or _parse_date_any(data_fim) or hoje
        return alvo, alvo
    if periodo == "semana":
        alvo = _parse_date_any(data_inicio) or _parse_date_any(data_fim) or hoje
        return _week_range(alvo)
    if periodo == "mes":
        return _parse_mes_intervalo(mes)
    ini = _parse_date_any(data_inicio)
    fim = _parse_date_any(data_fim)
    if ini or fim:
        return ini, fim
    return None, None


def _weekday_dates_between(inicio, fim):
    from datetime import timedelta
    if not inicio or not fim:
        return []
    cur = inicio
    dias = []
    while cur <= fim:
        if cur.weekday() < 5:
            dias.append(cur)
        cur += timedelta(days=1)
    return dias


def _filtra_report_periodo(rows, campo, periodo, mes, data_inicio, data_fim):
    inicio, fim = _report_period_range(periodo, mes, data_inicio, data_fim)
    if not inicio and not fim:
        return rows
    filtrados = []
    for row in rows:
        d = _parse_date_any(row.get(campo))
        if not d:
            continue
        if inicio and d < inicio:
            continue
        if fim and d > fim:
            continue
        if periodo in ("semana", "mes") and d.weekday() >= 5:
            continue
        filtrados.append(row)
    return filtrados


def _periodo_label(periodo, mes, data_inicio, data_fim):
    inicio, fim = _report_period_range(periodo, mes, data_inicio, data_fim)
    if periodo == "dia" and inicio:
        return inicio.strftime("%d/%m/%Y")
    if inicio and fim:
        return f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"
    return "Acumulado"


def _indicador_cor(percentual):
    if percentual > 85:
        return "VERDE"
    if percentual >= 75:
        return "AMARELO"
    return "VERMELHO"


def _color_hex(percentual):
    if percentual > 85:
        return "#22c55e"
    if percentual >= 75:
        return "#f59e0b"
    return "#ef4444"


def _aluno_campo(a, *campos):
    for c in campos:
        v = a.get(c)
        if v not in (None, ""):
            return v
    return ""


@app.route("/api/relatorios_dashboard/<report_name>")
def api_relatorios_dashboard(report_name):
    try:
        db = get_supabase()

        sala = (request.args.get("sala") or "").strip()
        tutor = (request.args.get("tutor") or "").strip()
        professor = (request.args.get("professor") or "").strip()
        periodo = (request.args.get("periodo") or "acumulado").strip().lower()
        mes = (request.args.get("mes") or "").strip()
        data_inicio = (request.args.get("data_inicio") or "").strip()
        data_fim = (request.args.get("data_fim") or "").strip()

        ocorr = _fetch_all_rows(db, "ocorrencias", "*", order_col="numero")
        freq = _dedupe_frequencia_registros(_fetch_all_rows(db, "f_frequencia", "*", order_col="id"))
        atend = _fetch_all_rows(db, "atendimentos_tutoria", "*", order_col="id")
        alunos = _fetch_all_rows(db, "d_alunos", "*", order_col="id")
        alunos = [x for x in alunos if (x.get("situacao_aluno") or "ATIVO").strip().upper() == "ATIVO"]

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

        ocorr = _filtra_report_periodo(ocorr, "data_hora", periodo, mes, data_inicio, data_fim)
        freq = _filtra_report_periodo(freq, "data", periodo, mes, data_inicio, data_fim)
        atend = _filtra_report_periodo(atend, "data_registro", periodo, mes, data_inicio, data_fim)

        if report_name == "ocorrencias_por_sala":
            mapa = {}
            for x in ocorr:
                k = x.get("sala_nome") or "SEM SALA"
                mapa[k] = mapa.get(k, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": f"Relatório de Ocorrência - {periodo.title()} ({_periodo_label(periodo, mes, data_inicio, data_fim)})",
                "chart_type": "bar",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Ocorrências"},
                "table": {"headers": ["Sala", "Ocorrências"], "rows": [[k, v] for k, v in ordered]}
            }})

        if report_name == "frequencia_por_sala":
            mapa = {}
            for x in freq:
                k = x.get("sala_nome") or "SEM SALA"
                mapa.setdefault(k, {"presentes": 0, "faltas": 0, "total": 0})
                mapa[k]["total"] += 1
                if _status_presenca(x.get("status")):
                    mapa[k]["presentes"] += 1
                else:
                    mapa[k]["faltas"] += 1
            ordered = []
            for k, v in mapa.items():
                p = round((v["presentes"] / v["total"]) * 100, 2) if v["total"] else 0
                ordered.append((k, p, v["presentes"], v["faltas"], v["total"], _indicador_cor(p)))
            ordered.sort(key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": f"Relatório de Frequência - {periodo.title()} ({_periodo_label(periodo, mes, data_inicio, data_fim)})",
                "chart_type": "bar",
                "chart": {
                    "labels": [x[0] for x in ordered],
                    "data": [x[1] for x in ordered],
                    "dataset_label": "Frequência %",
                    "backgroundColor": [_color_hex(x[1]) for x in ordered]
                },
                "table": {"headers": ["Sala", "Frequência %", "Presenças", "Faltas", "Total", "Faixa"], "rows": [[x[0], x[1], x[2], x[3], x[4], x[5]] for x in ordered]}
            }})

        if report_name == "ocorrencias_por_tutor":
            mapa = {}
            for x in ocorr:
                k = x.get("tutor_nome") or "SEM TUTOR"
                mapa[k] = mapa.get(k, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": f"Ocorrência por Tutor ({_periodo_label(periodo, mes, data_inicio, data_fim)})",
                "chart_type": "bar",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Ocorrências"},
                "table": {"headers": ["Tutor", "Ocorrências"], "rows": [[k, v] for k, v in ordered]},
                "hide_filters": True
            }})

        if report_name == "atendimentos_por_tutor":
            mapa = {}
            detalhes = {}
            for x in atend:
                tutor_nome = x.get("tutor_nome") or "SEM TUTOR"
                mapa[tutor_nome] = mapa.get(tutor_nome, 0) + 1
                detalhes.setdefault(tutor_nome, []).append({
                    "aluno_nome": x.get("aluno_nome") or "",
                    "data_registro": x.get("data_registro") or "",
                    "tipo_atendimento": x.get("tipo_atendimento") or "",
                    "registro": x.get("registro") or "",
                    "proximos_passos": x.get("proximos_passos") or "",
                })
            ordered = sorted([(k, v) for k, v in mapa.items()], key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": f"Atendimentos por Tutor ({_periodo_label(periodo, mes, data_inicio, data_fim)})",
                "chart_type": "bar",
                "chart": {"labels": [x[0] for x in ordered], "data": [x[1] for x in ordered], "dataset_label": "Qtd. atendimentos"},
                "table": {"headers": ["Tutor", "Quantidade", "Ação"], "rows": [[x[0], x[1], "VER DETALHE"] for x in ordered]},
                "detalhes": detalhes
            }})

        if report_name == "frequencia_periodo":
            inicio, fim = _report_period_range(periodo, mes, data_inicio, data_fim)
            if not inicio and not fim:
                inicio, fim = _parse_mes_intervalo(mes)
            dias = _weekday_dates_between(inicio, fim)
            labels, values, rows, colors = [], [], [], []
            for dia in dias:
                subset = [x for x in freq if _parse_date_any(x.get("data")) == dia]
                if not subset:
                    rows.append([dia.strftime("%d/%m/%Y"), "FERIADO", "Sem chamada"])
                    continue
                total = len(subset)
                pres = len([x for x in subset if _status_presenca(x.get("status"))])
                pct = round((pres / total) * 100, 2) if total else 0
                labels.append(dia.strftime("%d/%m"))
                values.append(pct)
                colors.append(_color_hex(pct))
                rows.append([dia.strftime("%d/%m/%Y"), pct, _indicador_cor(pct)])
            return jsonify({"success": True, "data": {
                "titulo": f"Frequência Semanal/Mensal ({_periodo_label(periodo, mes, data_inicio, data_fim)})",
                "chart_type": "bar",
                "chart": {
                    "labels": labels,
                    "data": values,
                    "dataset_label": "Frequência %",
                    "backgroundColor": colors
                },
                "table": {"headers": ["Dia", "Frequência %", "Faixa"], "rows": rows}
            }})

        if report_name == "ocorrencias_por_professor":
            mapa = {}
            for x in ocorr:
                k = x.get("professor_nome") or "SEM PROFESSOR"
                mapa[k] = mapa.get(k, 0) + 1
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": f"Relatório de Ocorrência por Professor ({_periodo_label(periodo, mes, data_inicio, data_fim)})",
                "chart_type": "bar",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Ocorrências"},
                "table": {"headers": ["Professor", "Ocorrências"], "rows": [[k, v] for k, v in ordered]}
            }})

        if report_name == "alunos_por_tutor_detalhado":
            mapa = {}
            detalhes = {}
            for a in alunos:
                tutor_nome = (a.get("tutor_nome") or a.get("nome_tutor") or "SEM TUTOR").strip() or "SEM TUTOR"
                mapa[tutor_nome] = mapa.get(tutor_nome, 0) + 1
                detalhes.setdefault(tutor_nome, []).append([
                    _aluno_campo(a, "nome", "aluno_nome"),
                    _aluno_campo(a, "sala_nome"),
                    _aluno_campo(a, "projeto_de_vida", "projeto_vida"),
                    _aluno_campo(a, "telefone_aluno", "telefone"),
                    _aluno_campo(a, "responsavel_nome", "responsavel"),
                    _aluno_campo(a, "telefone_responsavel"),
                    _aluno_campo(a, "clube_1_semestre", "clube_juvenil_1_semestre"),
                    _aluno_campo(a, "eletiva_1_semestre"),
                ])
            ordered = sorted(mapa.items(), key=lambda i: (-i[1], i[0]))
            return jsonify({"success": True, "data": {
                "titulo": "Lista de Aluno por Tutor",
                "chart_type": "bar",
                "chart": {"labels": [k for k, _ in ordered], "data": [v for _, v in ordered], "dataset_label": "Qtd. alunos"},
                "table": {"headers": ["Tutor", "Quantidade", "Ação"], "rows": [[k, v, "BAIXAR PDF"] for k, v in ordered]},
                "detalhes_alunos": detalhes
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
        data_inicio = (request.args.get("data_inicio") or "").strip()
        data_fim = (request.args.get("data_fim") or "").strip()

        with app.test_request_context(
            f"/api/relatorios_dashboard/{report_name}?sala={sala}&tutor={tutor}&professor={professor}&periodo={periodo}&mes={mes}&data_inicio={data_inicio}&data_fim={data_fim}"
        ):
            resp = api_relatorios_dashboard(report_name)

        data = resp.get_json()
        if not data or not data.get("success"):
            return "Erro ao gerar relatório PDF.", 500

        payload = data["data"]
        styles = _pdf_styles()
        filtro_txt = []
        if sala: filtro_txt.append(f"Sala: {sala}")
        if tutor: filtro_txt.append(f"Tutor: {tutor}")
        if professor: filtro_txt.append(f"Professor: {professor}")
        if periodo: filtro_txt.append(f"Período: {periodo}")
        if mes: filtro_txt.append(f"Mês: {mes}")
        if data_inicio or data_fim: filtro_txt.append(f"Datas: {data_inicio or '-'} até {data_fim or '-'}")

        story = [
            Paragraph("SGCE - Relatório Profissional", styles["SGCETitle"]),
            Paragraph(payload.get("titulo", "Relatório"), styles["Heading2"]),
            Paragraph(f"Emitido em {now_sp().strftime('%d/%m/%Y %H:%M')}", styles["SGCESubtitle"]),
        ]
        if filtro_txt:
            story.append(Paragraph(" | ".join(filtro_txt), styles["SGCESmall"]))
        story.append(Spacer(1, 6))

        headers = payload.get("table", {}).get("headers", [])
        rows = payload.get("table", {}).get("rows", [])
        if report_name == "atendimentos_por_tutor" and tutor and payload.get("detalhes"):
            detalhes = payload.get("detalhes", {}).get(tutor, [])
            headers = ["Aluno", "Data", "Tipo", "Registro", "Próximos passos"]
            rows = [[x.get("aluno_nome", ""), str(x.get("data_registro", ""))[:16], x.get("tipo_atendimento", ""), x.get("registro", ""), x.get("proximos_passos", "")] for x in detalhes]
        table_rows = [[str(h) for h in headers]] + [[str(v) for v in row] for row in rows] if headers else [[str(v) for v in row] for row in rows]
        if not table_rows:
            table_rows = [["Sem dados para o filtro informado."]]
        story.append(_build_table(table_rows, header=bool(headers)))
        return _pdf_response(f"relatorio_{report_name}.pdf", story, pagesize=landscape(A4))
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