# =============================================================
# APP UNIFICADO - GESTÃO ESCOLAR (VERSÃO FINAL COMPLETA)
# Módulos: Ocorrência, Frequência, Tecnologia, Tutoria, Cadastro
# =============================================================

from flask import Flask, render_template, Blueprint, request, jsonify, send_file, redirect
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import logging
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# -------------------------------------------------------------------
# Configuração de logs
# -------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Carregar variáveis do arquivo .env
# -------------------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL:
    logger.warning("⚠️ SUPABASE_URL não encontrada no .env.")
if not SUPABASE_KEY:
    logger.warning("⚠️ SUPABASE_KEY não encontrada no .env.")

_supabase_client: Client | None = None

# -------------------------------------------------------------------
# Inicializador do Supabase
# -------------------------------------------------------------------
def _init_supabase_client(retries: int = 3, backoff: float = 1.0):
    global _supabase_client
    if _supabase_client:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Não é possível inicializar Supabase: URL ou KEY ausentes.")
        return None

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Tentando inicializar Supabase (tentativa {attempt}/{retries})...")
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

            try:
                _supabase_client.table('d_funcionarios').select('*').limit(1).execute()
                logger.info("✅ Conexão Supabase estabelecida com sucesso.")
            except Exception as e:
                logger.warning(f"Conexão estabelecida, mas teste falhou: {e}")

            return _supabase_client

        except Exception as e:
            logger.error(f"Erro ao criar client Supabase (tentativa {attempt}): {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                logger.error("❌ Não foi possível inicializar Supabase após várias tentativas.")
                return None

def handle_supabase_response(response):
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Erro Supabase: {response.error}")
    if hasattr(response, 'status_code') and response.status_code >= 400:
        raise Exception(f"Erro Supabase: status_code={response.status_code} - {response.data}")
    return getattr(response, 'data', response)

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = _init_supabase_client()
    return _supabase_client

supabase = get_supabase()

# =============================================================
# INICIALIZAÇÃO DO FLASK
# =============================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')

def now_iso():
    return datetime.utcnow().isoformat()

# =============================================================
# FUNÇÕES AUXILIARES
# =============================================================
def get_salas():
    try:
        if supabase:
            response = supabase.table('d_salas').select('*').eq('ativa', True).execute()
            return handle_supabase_response(response)
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar salas: {e}")
        return []

def get_d_alunos():
    try:
        if supabase:
            response = supabase.table('d_alunos').select('*').execute()
            return handle_supabase_response(response)
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar d_alunos: {e}")
        return []

def get_alunos_por_sala(sala_id):
    try:
        if supabase:
            response = supabase.table('d_alunos').select('*').eq('sala_id', sala_id).execute()
            return handle_supabase_response(response)
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar alunos por sala: {e}")
        return []

def get_professores():
    try:
        if supabase:
            response = supabase.table('d_funcionarios').select('*').execute()
            return handle_supabase_response(response)
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar professores: {e}")
        return []

def get_ocorrencias():
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('*').order('numero', desc=True).execute()
            return handle_supabase_response(response)
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar ocorrências: {e}")
        return []

def get_ocorrencia_por_numero(numero):
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('*').eq('numero', numero).execute()
            data = handle_supabase_response(response)
            return data[0] if data else None
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar ocorrência: {e}")
        return None

# =============================================================
# APIs de OCORRÊNCIAS
# =============================================================
@app.route('/api/professores')
def api_professores():
    try:
        if supabase:
            # Seleciona apenas id e nome (a coluna 'funcao' não é usada no frontend)
            response = supabase.table('d_funcionarios').select('id, nome').execute()
            professores = handle_supabase_response(response)
            return jsonify(professores)
        return jsonify([])
    except Exception as e:
        logger.exception("Erro ao buscar professores")
        return jsonify({'error': str(e)}), 500

@app.route('/api/salas_por_professor/<int:professor_id>')
def api_salas_por_professor(professor_id):
    try:
        if supabase:
            response = supabase.table('d_salas').select('id, nome').eq('ativa', True).execute()
            salas = handle_supabase_response(response)
            return jsonify(salas)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos_por_sala/<int:sala_id>')
def api_alunos_por_sala(sala_id):
    try:
        response = supabase.table('d_alunos') \
            .select('id, nome, tutor_nome') \
            .eq('sala_id', sala_id) \
            .order('nome', desc=False) \
            .execute()
        alunos = handle_supabase_response(response)
        return jsonify(alunos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tutor_por_aluno/<int:aluno_id>')
def api_tutor_por_aluno(aluno_id):
    try:
        if supabase:
            response_aluno = supabase.table('d_alunos').select('tutor_nome').eq('id', aluno_id).execute()
            aluno_data = handle_supabase_response(response_aluno)
            if not aluno_data:
                return jsonify({'tutor': ''})
            tutor_nome = aluno_data[0].get('tutor_nome')
            return jsonify({'tutor': tutor_nome or ''})
        return jsonify({'tutor': ''})
    except Exception as e:
        return jsonify({'tutor': ''})

@app.route("/api/registrar_ocorrencia", methods=["POST"])
def api_registrar_ocorrencia():
    supabase = get_supabase()
    try:
        payload = request.json or {}
        aluno_id = payload.get("aluno_id")
        professor_id = payload.get("professor_id")
        professor_nome = payload.get("professor_nome")
        descricao = payload.get("descricao")
        atendimento_professor = payload.get("atendimento_professor")
        if not all([aluno_id, professor_id, professor_nome, descricao, atendimento_professor]):
            return jsonify({"success": False, "error": "Dados obrigatórios faltando"}), 400
        resp_aluno = supabase.table("d_alunos").select("nome, sala_id, sala_nome, tutor_nome").eq("id", aluno_id).execute()
        if not resp_aluno.data:
            return jsonify({"success": False, "error": "Aluno não encontrado"}), 404
        aluno_data = resp_aluno.data[0]
        aluno_nome = aluno_data.get("nome")
        sala_nome = aluno_data.get("sala_nome")
        tutor_nome = aluno_data.get("tutor_nome", payload.get("tutor_nome", ""))
        resp_numero = supabase.table("ocorrencias").select("numero").order("numero", desc=True).limit(1).execute()
        ultimo_numero = 0
        if resp_numero.data and len(resp_numero.data) > 0:
            ultimo_numero = resp_numero.data[0].get("numero", 0)
        proximo_numero = ultimo_numero + 1
        ocorrencia_data = {
            "numero": proximo_numero,
            "aluno_id": aluno_id,
            "aluno_nome": aluno_nome,
            "sala_nome": sala_nome,
            "professor_id": professor_id,
            "professor_nome": professor_nome,
            "tutor_nome": tutor_nome,
            "descricao": descricao,
            "atendimento_professor": atendimento_professor,
            "solicitado_tutor": payload.get("solicitar_tutor", False),
            "solicitado_coordenacao": payload.get("solicitar_coordenacao", False),
            "solicitado_gestao": payload.get("solicitar_gestao", False),
            "status": "ATENDIMENTO",
            "data_hora": now_iso()
        }
        resp = supabase.table("ocorrencias").insert(ocorrencia_data).execute()
        data = handle_supabase_response(resp)
        if data and len(data) > 0:
            return jsonify({"success": True, "numero": data[0].get("numero"), "data": data[0]})
        else:
            return jsonify({"success": False, "error": "Nenhum dado retornado"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/ocorrencia_detalhes")
def ocorrencia_detalhes():
    numero = request.args.get("numero")
    if not numero:
        return jsonify({"error": "Número da ocorrência não informado"}), 400
    try:
        ocorrencia = get_ocorrencia_por_numero(int(numero))
        if not ocorrencia:
            return jsonify({"error": "Ocorrência não encontrada"}), 404
        return jsonify(ocorrencia)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/ocorrencia/<int:numero>', methods=['GET'])
def api_buscar_ocorrencia_por_numero(numero):
    try:
        ocorrencia = get_ocorrencia_por_numero(numero)
        if not ocorrencia:
            return jsonify({'error': f'Ocorrência #{numero} não encontrada'}), 404
        return jsonify(ocorrencia)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/salvar_atendimento", methods=["POST"])
def salvar_atendimento():
    data = request.json or {}
    numero = data.get("numero")
    nivel = data.get("nivel")
    texto = data.get("texto")
    if not (numero and nivel and texto is not None):
        return jsonify({"success": False, "error": "Parâmetros incompletos"}), 400
    MAPA_ATENDIMENTO = {
        "tutor": ("atendimento_tutor", "dt_atendimento_tutor"),
        "coordenacao": ("atendimento_coordenacao", "dt_atendimento_coordenacao"),
        "gestao": ("atendimento_gestao", "dt_atendimento_gestao")
    }
    if nivel not in MAPA_ATENDIMENTO:
        return jsonify({"success": False, "error": "Nível inválido"}), 400
    campo_texto, campo_data = MAPA_ATENDIMENTO[nivel]
    try:
        update_payload = {campo_texto: texto, campo_data: datetime.now().isoformat()}
        resp = supabase.table('ocorrencias').update(update_payload).eq('numero', numero).execute()
        handle_supabase_response(resp)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/ocorrencias_todas')
def api_ocorrencias_todas():
    try:
        ocorrencias = get_ocorrencias()
        return jsonify(ocorrencias)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocorrencias_filtrar')
def api_ocorrencias_filtrar():
    try:
        sala_id = request.args.get('sala_id', '')
        tutor_id = request.args.get('tutor_id', '')
        status = request.args.get('status', '')
        aluno_id = request.args.get('aluno_id', '')
        query = supabase.table('ocorrencias').select('*')
        if sala_id and sala_id != 'all':
            query = query.eq('sala_id', sala_id)
        if tutor_id and tutor_id != 'all':
            query = query.eq('tutor_id', tutor_id)
        if status and status != 'all':
            query = query.eq('status', status)
        if aluno_id and aluno_id != 'all':
            query = query.eq('aluno_id', aluno_id)
        response = query.execute()
        return jsonify(handle_supabase_response(response))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gerar_pdf_ocorrencias', methods=['POST'])
def api_gerar_pdf_ocorrencias():
    supabase = get_supabase()
    try:
        dados = request.get_json()
        if not dados or 'numeros' not in dados:
            return jsonify({"error": "Lista de ocorrências não fornecida"}), 400
        numeros_selecionados = dados['numeros']
        if not numeros_selecionados:
            return jsonify({"error": "Nenhuma ocorrência selecionada"}), 400
        resp = supabase.table("ocorrencias").select("*").in_("numero", numeros_selecionados).order("data_hora").execute()
        ocorrencias_selecionadas = handle_supabase_response(resp)
        if not ocorrencias_selecionadas:
            return jsonify({"error": "Nenhuma ocorrência encontrada"}), 404
        ocorrencias_selecionadas = sorted(ocorrencias_selecionadas, key=lambda x: x.get('data_hora', ''))
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch,
                                leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("RELATÓRIO DE OCORRÊNCIAS - ASSINATURA", styles['Title']))
        elements.append(Spacer(1, 0.2*inch))
        elements.append(Paragraph("<b>E.E. PEI PROFESSOR IRENE DIAS RIBEIRO</b>", styles['Heading2']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(f"<b>Data do Relatório:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        for i, oc in enumerate(ocorrencias_selecionadas):
            elements.append(Paragraph(f"<b>OCORRÊNCIA Nº: {oc.get('numero', 'N/A')}</b>", styles['Heading2']))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(f"<b>Aluno:</b> {oc.get('aluno_nome', 'N/A')}", styles['Normal']))
            data_hora = oc.get('data_hora', '')
            if data_hora:
                try:
                    dt = datetime.fromisoformat(data_hora.replace('Z', '+00:00'))
                    elements.append(Paragraph(f"<b>Data:</b> {dt.strftime('%d/%m/%Y')}    <b>Hora:</b> {dt.strftime('%H:%M:%S')}", styles['Normal']))
                except:
                    elements.append(Paragraph(f"<b>Data/Hora:</b> {data_hora}", styles['Normal']))
            else:
                elements.append(Paragraph("<b>Data/Hora:</b> N/A", styles['Normal']))
            elements.append(Paragraph(f"<b>Professor:</b> {oc.get('professor_nome', 'N/A')}", styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph("<b>Descrição da Ocorrência:</b>", styles['Heading3']))
            elements.append(Paragraph(oc.get('descricao', 'Nenhuma descrição fornecida'), styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph("<b>Atendimento Professor:</b>", styles['Heading3']))
            elements.append(Paragraph(oc.get('atendimento_professor', 'Nenhum atendimento registrado'), styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
            for nivel, nome in [('Tutor', 'tutor'), ('Coordenação', 'coordenacao'), ('Gestão', 'gestao')]:
                elements.append(Paragraph(f"<b>Atendimento {nivel}:</b>", styles['Heading3']))
                if oc.get(f'solicitado_{nome}'):
                    atendimento = oc.get(f'atendimento_{nome}', 'Pendente')
                    if not atendimento or atendimento.strip() == '':
                        atendimento = 'Pendente'
                else:
                    atendimento = 'Atendimento Não Solicitado'
                elements.append(Paragraph(atendimento, styles['Normal']))
                elements.append(Spacer(1, 0.1*inch))
            elements.append(Paragraph(f"<b>Sala:</b> {oc.get('sala_nome', 'N/A')}    <b>Tutor:</b> {oc.get('tutor_nome', 'N/A')}", styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            if i == len(ocorrencias_selecionadas)-1:
                elements.append(Paragraph("<b>Assinatura do Responsável: _____</b>", styles['Heading3']))
                elements.append(Spacer(1, 0.1*inch))
                elements.append(Paragraph("<b>Data: _____ /_____/_____</b>", styles['Heading3']))
            else:
                elements.append(Spacer(1, 0.2*inch))
        doc.build(elements)
        for numero in numeros_selecionados:
            supabase.table("ocorrencias").update({"impressao_pdf": True}).eq("numero", numero).execute()
        buffer.seek(0)
        nome_arquivo = f"ocorrencias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(buffer, as_attachment=True, download_name=nome_arquivo, mimetype='application/pdf')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ocorrencias", methods=["GET"])
def api_list_ocorrencias():
    supabase = get_supabase()
    try:
        q = supabase.table("ocorrencias")
        tutor = request.args.get("tutor")
        sala = request.args.get("sala")
        aluno = request.args.get("aluno")
        status = request.args.get("status")
        if tutor:
            q = q.eq("tutor_nome", tutor)
        if sala:
            q = q.eq("sala_nome", sala)
        if aluno:
            q = q.eq("aluno_nome", aluno)
        if status:
            q = q.eq("status", status)
        resp = q.order("data_hora", desc=True).execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/d_funcionarios", methods=["GET"])
def api_d_funcionarios():
    supabase = get_supabase()
    try:
        resp = supabase.table("d_funcionarios").select("id, nome").order("nome").execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/d_salas", methods=["GET"])
def api_d_salas():
    supabase = get_supabase()
    try:
        resp = supabase.table("d_salas").select("id, nome").eq('ativa', True).order("nome").execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/d_alunos", methods=["GET"])
def api_d_alunos():
    supabase = get_supabase()
    try:
        sala_id = request.args.get("sala_id")
        q = supabase.table("d_alunos").select("id, nome, tutor_nome, sala_id")
        if sala_id:
            q = q.eq("sala_id", int(sala_id))
        resp = q.order("nome").execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/ocorrencias", methods=["POST"])
def api_create_ocorrencia():
    supabase = get_supabase()
    try:
        payload = request.json or {}
        professor_nome = payload.get("professor_nome")
        sala_nome = payload.get("sala_nome")
        aluno_nome = payload.get("aluno_nome")
        tutor_nome = payload.get("tutor_nome")
        atendimento_professor = payload.get("atendimento_professor", "")
        solicitado_tutor = bool(payload.get("solicitado_tutor", False))
        solicitado_coordenacao = bool(payload.get("solicitado_coordenacao", False))
        solicitado_gestao = bool(payload.get("solicitado_gestao", False))
        status = payload.get("status", "aberta")
        data_hora = now_iso()
        record = {
            "professor_nome": professor_nome,
            "sala_nome": sala_nome,
            "aluno_nome": aluno_nome,
            "tutor_nome": tutor_nome,
            "data_hora": data_hora,
            "atendimento_professor": atendimento_professor,
            "solicitado_tutor": solicitado_tutor,
            "solicitado_coordenacao": solicitado_coordenacao,
            "solicitado_gestao": solicitado_gestao,
            "status": status
        }
        resp = supabase.table("ocorrencias").insert(record).execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/ocorrencias/<int:oc_id>/atendimento", methods=["PUT"])
def api_update_atendimento(oc_id):
    supabase = get_supabase()
    try:
        payload = request.json or {}
        tipo = payload.get("tipo")
        texto = payload.get("texto", "")
        if tipo not in ("tutor", "coordenacao", "gestao"):
            return jsonify({"ok": False, "error": "tipo inválido"}), 400
        
        field_text = f"atendimento_{tipo}"
        field_dt = f"dt_atendimento_{tipo}"
        updates = {field_text: texto, field_dt: now_iso()}
        
        # Se for gestão e não solicitou responsável, finalizar a ocorrência
        if tipo == "gestao":
            solicitar_responsavel = payload.get("solicitar_responsavel", False)
            if not solicitar_responsavel:
                updates["status"] = "FINALIZADA"
        
        resp = supabase.table("ocorrencias").update(updates).eq("id", oc_id).execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# =============================================================
# ROTAS DE FREQUÊNCIA
# =============================================================
@app.route('/api/alunos_por_sala/<int:sala_id>', methods=['GET'])
def get_alunos_por_sala_route(sala_id):
    try:
        response = supabase.table('d_alunos').select('*').eq('sala_id', sala_id).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia/status', methods=['GET'])
def get_status_frequencia():
    try:
        sala_id = request.args.get('sala_id')
        data = request.args.get('data')
        if not sala_id or not data:
            return jsonify({'error': 'sala_id e data são obrigatórios'}), 400
        sala_response = supabase.table('d_salas').select('nome').eq('id', sala_id).execute()
        if not sala_response.data:
            return jsonify({'error': 'Sala não encontrada'}), 404
        sala_nome = sala_response.data[0]['nome']
        response = supabase.table('f_frequencia').select('id').eq('sala_nome', sala_nome).eq('data', data).execute()
        return jsonify({'registrada': len(response.data) > 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_frequencia_unificada', methods=['POST'])
def salvar_frequencia_unificada():
    try:
        dados = request.get_json()
        if not isinstance(dados, list):
            return jsonify({'error': 'Dados devem ser uma lista'}), 400
        resultados = []
        for registro in dados:
            sala_nome = registro.get('sala_nome')
            if not sala_nome and 'sala_id' in registro:
                sala_response = supabase.table('d_salas').select('nome').eq('id', registro['sala_id']).execute()
                if sala_response.data:
                    sala_nome = sala_response.data[0]['nome']
                else:
                    resultados.append({'error': f'Sala com id {registro["sala_id"]} não encontrada'})
                    continue
            aluno_nome = registro.get('aluno_nome')
            if not aluno_nome and 'aluno_id' in registro:
                aluno_response = supabase.table('d_alunos').select('nome').eq('id', registro['aluno_id']).execute()
                if aluno_response.data:
                    aluno_nome = aluno_response.data[0]['nome']
                else:
                    resultados.append({'error': f'Aluno com id {registro["aluno_id"]} não encontrado'})
                    continue
            if not aluno_nome or not sala_nome:
                resultados.append({'error': 'Nome do aluno e sala são obrigatórios'})
                continue
            existing = supabase.table('f_frequencia')\
                .select('*')\
                .eq('aluno_nome', aluno_nome)\
                .eq('data', registro['data'])\
                .execute()
            status = determinar_status(registro, existing.data[0] if existing.data else None)
            dados_frequencia = {
                'aluno_nome': aluno_nome,
                'sala_nome': sala_nome,
                'data': registro['data'],
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            campos_opcionais = [
                'hora_entrada', 'motivo_atraso', 'hora_saida',
                'motivo_saida', 'responsavel_nome', 'responsavel_telefone'
            ]
            for campo in campos_opcionais:
                if campo in registro:
                    dados_frequencia[campo] = registro[campo]
            if existing.data:
                result = supabase.table('f_frequencia')\
                    .update(dados_frequencia)\
                    .eq('id', existing.data[0]['id'])\
                    .execute()
            else:
                dados_frequencia['created_at'] = datetime.now().isoformat()
                result = supabase.table('f_frequencia')\
                    .insert(dados_frequencia)\
                    .execute()
            if result.data:
                resultados.append(result.data[0])
            else:
                resultados.append({'error': 'Falha ao salvar'})
        return jsonify({'message': 'Dados salvos com sucesso', 'data': resultados}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def determinar_status(novo_registro, registro_existente):
    if registro_existente:
        status_atual = registro_existente.get('status', 'P')
    else:
        status_atual = novo_registro.get('status', 'P')
    if 'status' in novo_registro and novo_registro['status'] in ['P', 'F']:
        return novo_registro['status']
    tem_atraso = 'hora_entrada' in novo_registro and novo_registro['hora_entrada']
    tem_saida = 'hora_saida' in novo_registro and novo_registro['hora_saida']
    if not tem_atraso and not tem_saida and 'status' in novo_registro:
        return novo_registro['status']
    if tem_atraso and tem_saida:
        return 'PSA'
    elif tem_atraso:
        if registro_existente and registro_existente.get('hora_saida'):
            return 'PSA'
        return 'PA'
    elif tem_saida:
        if registro_existente and registro_existente.get('hora_entrada'):
            return 'PSA'
        return 'PS'
    return status_atual

@app.route('/api/frequencia', methods=['GET'])
def get_frequencia_relatorio():
    try:
        sala_id = request.args.get('sala')
        mes = request.args.get('mes')
        ano = datetime.now().year
        if not sala_id or not mes:
            return jsonify({'error': 'sala e mes são obrigatórios'}), 400
        sala_response = supabase.table('d_salas').select('nome').eq('id', sala_id).execute()
        if not sala_response.data:
            return jsonify({'error': 'Sala não encontrada'}), 404
        sala_nome = sala_response.data[0]['nome']
        alunos_response = supabase.table('d_alunos')\
            .select('id, nome')\
            .eq('sala_id', sala_id)\
            .execute()
        if not alunos_response.data:
            return jsonify([])
        data_inicio = f"{ano}-{mes.zfill(2)}-01"
        data_fim = f"{ano}-{mes.zfill(2)}-31"
        frequencia_response = supabase.table('f_frequencia')\
            .select('*')\
            .in_('aluno_nome', [aluno['nome'] for aluno in alunos_response.data])\
            .eq('sala_nome', sala_nome)\
            .gte('data', data_inicio)\
            .lte('data', data_fim)\
            .execute()
        resultado = []
        for aluno in alunos_response.data:
            frequencia_aluno = {}
            for freq in frequencia_response.data:
                if freq['aluno_nome'] == aluno['nome']:
                    frequencia_aluno[freq['data']] = {
                        'status': freq['status'],
                        'hora_entrada': freq.get('hora_entrada'),
                        'motivo_atraso': freq.get('motivo_atraso'),
                        'hora_saida': freq.get('hora_saida'),
                        'motivo_saida': freq.get('motivo_saida'),
                        'responsavel_nome': freq.get('responsavel_nome'),
                        'responsavel_telefone': freq.get('responsavel_telefone')
                    }
            resultado.append({
                'id': aluno['id'],
                'nome': aluno['nome'],
                'frequencia': frequencia_aluno
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/frequencia_detalhes/<int:aluno_id>/<data>", methods=["GET"])
def frequencia_detalhes(aluno_id, data):
    try:
        result = supabase.table("f_frequencia") \
            .select("aluno_id, aluno_nome, data, status, hora_entrada, motivo_atraso, hora_saida, motivo_saida") \
            .eq("aluno_id", aluno_id) \
            .eq("data", data) \
            .limit(1) \
            .execute()
        if not result.data:
            return jsonify({"error": "Registro não encontrado"}), 404
        registro = result.data[0]
        return jsonify({
            "aluno_id": registro.get("aluno_id"),
            "aluno_nome": registro.get("aluno_nome"),
            "data": registro.get("data"),
            "status": registro.get("status"),
            "hora_entrada": registro.get("hora_entrada"),
            "motivo_atraso": registro.get("motivo_atraso"),
            "hora_saida": registro.get("hora_saida"),
            "motivo_saida": registro.get("motivo_saida"),
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/frequencia_diaria', methods=['GET'])
def get_frequencia_diaria():
    try:
        sala_id = request.args.get('sala_id')
        data = request.args.get('data')
        if not sala_id or not data:
            return jsonify({'error': 'sala_id e data são obrigatórios'}), 400
        sala_response = supabase.table('d_salas').select('nome').eq('id', sala_id).execute()
        if not sala_response.data:
            return jsonify({'error': 'Sala não encontrada'}), 404
        sala_nome = sala_response.data[0]['nome']
        alunos_response = supabase.table('d_alunos')\
            .select('id, nome')\
            .eq('sala_id', sala_id)\
            .execute()
        frequencia_response = supabase.table('f_frequencia')\
            .select('*')\
            .in_('aluno_nome', [aluno['nome'] for aluno in alunos_response.data])\
            .eq('sala_nome', sala_nome)\
            .eq('data', data)\
            .execute()
        resultado = []
        for aluno in alunos_response.data:
            freq_aluno = next((f for f in frequencia_response.data if f['aluno_nome'] == aluno['nome']), None)
            resultado.append({
                'aluno_id': aluno['id'],
                'aluno_nome': aluno['nome'],
                'status': freq_aluno['status'] if freq_aluno else 'P',
                'hora_entrada': freq_aluno.get('hora_entrada') if freq_aluno else None,
                'hora_saida': freq_aluno.get('hora_saida') if freq_aluno else None
            })
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================
# ALIASES PARA COMPATIBILIDADE (endpoints adicionais)
# =============================================================
@app.route('/api/salas', methods=['GET'])
def api_salas_alias():
    return api_d_salas()

@app.route('/api/salvar_atraso', methods=['POST'])
def api_salvar_atraso():
    return salvar_frequencia_unificada()

@app.route('/api/salvar_saida_antecipada', methods=['POST'])
def api_salvar_saida_antecipada():
    return salvar_frequencia_unificada()

@app.route('/api/salvar_frequencia', methods=['POST'])
def api_salvar_frequencia():
    return salvar_frequencia_unificada()

@app.route('/api/ocorrencias_abertas', methods=['GET'])
def api_ocorrencias_abertas():
    supabase = get_supabase()
    try:
        resp = supabase.table('ocorrencias').select('*').eq('status', 'ATENDIMENTO').order('data_hora', desc=True).execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocorrencias_finalizadas', methods=['GET'])
def api_ocorrencias_finalizadas():
    supabase = get_supabase()
    try:
        resp = supabase.table('ocorrencias').select('*').in_('status', ['FINALIZADA', 'ASSINADA']).order('data_hora', desc=True).execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos_com_ocorrencias_por_sala/<int:sala_id>', methods=['GET'])
def api_alunos_com_ocorrencias_por_sala(sala_id):
    supabase = get_supabase()
    try:
        resp = supabase.table('ocorrencias').select('aluno_id, aluno_nome').eq('sala_id', sala_id).execute()
        ocorrencias = handle_supabase_response(resp)
        alunos_unicos = {}
        for occ in ocorrencias:
            if occ.get('aluno_id') and occ.get('aluno_nome'):
                alunos_unicos[occ['aluno_id']] = occ['aluno_nome']
        resultado = [{'id': k, 'nome': v} for k, v in alunos_unicos.items()]
        return jsonify(resultado)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocorrencias_por_aluno/<int:aluno_id>', methods=['GET'])
def api_ocorrencias_por_aluno(aluno_id):
    supabase = get_supabase()
    try:
        resp = supabase.table('ocorrencias').select('*').eq('aluno_id', aluno_id).order('data_hora', desc=True).execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================
# MÓDULO TUTORIA
# =============================================================
@app.route('/api/funcionarios', methods=['GET'])
def api_funcionarios():
    supabase = get_supabase()
    try:
        resp = supabase.table('d_funcionarios').select('id, nome, funcao').order('nome').execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos_por_tutor/<int:tutor_id>', methods=['GET'])
def api_alunos_por_tutor(tutor_id):
    supabase = get_supabase()
    try:
        tutor_resp = supabase.table('d_funcionarios').select('nome').eq('id', tutor_id).execute()
        tutor_data = handle_supabase_response(tutor_resp)
        if not tutor_data:
            return jsonify([])
        tutor_nome = tutor_data[0]['nome']
        resp = supabase.table('d_alunos').select('id, nome').eq('tutor_nome', tutor_nome).order('nome').execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agendar_tutoria', methods=['POST'])
def api_agendar_tutoria():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'tutor_id': data['tutor_id'],
            'aluno_id': data['aluno_id'],
            'data_agendamento': data['data_agendamento'],
            'hora_agendamento': data['hora_agendamento'],
            'status': 'agendado',
            'created_at': now_iso()
        }
        resp = supabase.table('agendamentos_tutoria').insert(record).execute()
        return jsonify({'ok': True, 'data': handle_supabase_response(resp)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_registro_atendimento', methods=['POST'])
def api_salvar_registro_atendimento():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'tutor_id': data['tutor_id'],
            'aluno_id': data['aluno_id'],
            'registro': data['registro'],
            'data_registro': data.get('data_registro', now_iso().split('T')[0]),
            'created_at': now_iso()
        }
        resp = supabase.table('atendimentos_tutoria').insert(record).execute()
        return jsonify({'ok': True, 'data': handle_supabase_response(resp)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ficha_tutoria/<int:aluno_id>', methods=['GET'])
def api_ficha_tutoria(aluno_id):
    supabase = get_supabase()
    try:
        aluno_resp = supabase.table('d_alunos').select('*').eq('id', aluno_id).execute()
        aluno = handle_supabase_response(aluno_resp)
        if not aluno:
            return jsonify({'error': 'Aluno não encontrado'}), 404
        aluno = aluno[0]
        ocorrencias_resp = supabase.table('ocorrencias').select('*').eq('aluno_nome', aluno['nome']).order('data_hora', desc=True).limit(5).execute()
        ocorrencias = handle_supabase_response(ocorrencias_resp)
        atendimentos_resp = supabase.table('atendimentos_tutoria').select('*').eq('aluno_id', aluno_id).order('data_registro', desc=True).limit(5).execute()
        atendimentos = handle_supabase_response(atendimentos_resp)
        notas_resp = supabase.table('notas_aluno').select('*').eq('aluno_id', aluno_id).order('bimestre').execute()
        notas = handle_supabase_response(notas_resp)
        return jsonify({
            'aluno_nome': aluno['nome'],
            'ra': aluno.get('ra', ''),
            'tutor_nome': aluno.get('tutor_nome', ''),
            'sala_nome': aluno.get('sala_nome', ''),
            'ocorrencias': ocorrencias,
            'atendimentos': atendimentos,
            'notas': notas
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_notas_tutoria', methods=['POST'])
def api_salvar_notas_tutoria():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'aluno_id': data['aluno_id'],
            'tutor_id': data['tutor_id'],
            'bimestre': data['bimestre'],
            'notas': data['notas'],
            'created_at': now_iso()
        }
        resp = supabase.table('notas_aluno').insert(record).execute()
        return jsonify({'ok': True, 'data': handle_supabase_response(resp)}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================
# MÓDULO TECNOLOGIA
# =============================================================
@app.route('/api/agendar_equipamento', methods=['POST'])
def api_agendar_equipamento():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'professor_id': data['professor_id'],
            'sala_id': data['sala_id'],
            'data_uso': data['data_uso'],
            'aula_id': data['aula_id'],
            'quantidade': data['quantidade'],
            'status': 'agendado',
            'created_at': now_iso()
        }
        resp = supabase.table('agendamentos_equipamentos').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/agendamentos_pendentes/<int:professor_id>', methods=['GET'])
def api_agendamentos_pendentes(professor_id):
    supabase = get_supabase()
    try:
        resp = supabase.table('agendamentos_equipamentos')\
            .select('id, data_uso, sala_id, quantidade')\
            .eq('professor_id', professor_id)\
            .eq('status', 'agendado')\
            .order('data_uso')\
            .execute()
        agendamentos = handle_supabase_response(resp)
        for ag in agendamentos:
            sala_resp = supabase.table('d_salas').select('nome').eq('id', ag['sala_id']).execute()
            sala_data = handle_supabase_response(sala_resp)
            ag['sala_nome'] = sala_data[0]['nome'] if sala_data else 'Desconhecida'
        return jsonify(agendamentos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/finalizar_retirada_equipamento', methods=['POST'])
def api_finalizar_retirada():
    supabase = get_supabase()
    try:
        data = request.json
        agendamento_id = data['agendamento_id']
        supabase.table('agendamentos_equipamentos')\
            .update({'status': 'retirado', 'data_retirada': now_iso()})\
            .eq('id', agendamento_id)\
            .execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/finalizar_devolucao_equipamento', methods=['POST'])
def api_finalizar_devolucao():
    supabase = get_supabase()
    try:
        data = request.json
        agendamento_id = data['agendamento_id']
        supabase.table('agendamentos_equipamentos')\
            .update({'status': 'devolvido', 'data_devolucao': now_iso()})\
            .eq('id', agendamento_id)\
            .execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/registrar_ocorrencia_equipamento', methods=['POST'])
def api_ocorrencia_equipamento():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'equipamento_id': data['equipamento_id'],
            'professor_id': data['professor_id'],
            'data_ocorrencia': data['data_ocorrencia'],
            'descricao': data['descricao'],
            'acao': data.get('acao', ''),
            'created_at': now_iso()
        }
        resp = supabase.table('ocorrencias_equipamentos').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================
# MÓDULO CADASTRO (CRUD)
# =============================================================
# ----- Funcionários -----
@app.route('/api/funcionarios', methods=['POST'])
def api_criar_funcionario():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'funcao': data['funcao'],
            'data_nascimento': data['data_nascimento'],
            'telefone': data['telefone'],
            'created_at': now_iso()
        }
        resp = supabase.table('d_funcionarios').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/funcionarios/<int:id>', methods=['PUT'])
def api_atualizar_funcionario(id):
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'funcao': data['funcao'],
            'data_nascimento': data['data_nascimento'],
            'telefone': data['telefone'],
            'updated_at': now_iso()
        }
        resp = supabase.table('d_funcionarios').update(record).eq('id', id).execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/funcionarios/<int:id>', methods=['DELETE'])
def api_deletar_funcionario(id):
    supabase = get_supabase()
    try:
        supabase.table('d_funcionarios').delete().eq('id', id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Alunos -----
@app.route('/api/alunos', methods=['GET'])
def api_listar_alunos():
    supabase = get_supabase()
    try:
        sala_id = request.args.get('sala_id')
        q = supabase.table('d_alunos').select('*')
        if sala_id:
            q = q.eq('sala_id', int(sala_id))
        resp = q.order('nome').execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos', methods=['POST'])
def api_criar_aluno():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'data_nascimento': data['data_nascimento'],
            'telefone': data['telefone'],
            'responsavel': data.get('responsavel'),
            'telefone_responsavel': data.get('telefone_responsavel'),
            'tutor_id': data.get('tutor_id'),
            'sala_id': data.get('sala_id'),
            'created_at': now_iso()
        }
        resp = supabase.table('d_alunos').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos/<int:id>', methods=['PUT'])
def api_atualizar_aluno(id):
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'data_nascimento': data['data_nascimento'],
            'telefone': data['telefone'],
            'responsavel': data.get('responsavel'),
            'telefone_responsavel': data.get('telefone_responsavel'),
            'tutor_id': data.get('tutor_id'),
            'sala_id': data.get('sala_id'),
            'updated_at': now_iso()
        }
        resp = supabase.table('d_alunos').update(record).eq('id', id).execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos/<int:id>', methods=['DELETE'])
def api_deletar_aluno(id):
    supabase = get_supabase()
    try:
        supabase.table('d_alunos').delete().eq('id', id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Equipamentos -----
@app.route('/api/equipamentos', methods=['GET'])
def api_listar_equipamentos():
    supabase = get_supabase()
    try:
        resp = supabase.table('equipamentos').select('*').order('nome').execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipamentos', methods=['POST'])
def api_criar_equipamento():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'patrimonio': data['patrimonio'],
            'estado': data['estado'],
            'created_at': now_iso()
        }
        resp = supabase.table('equipamentos').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipamentos/<int:id>', methods=['PUT'])
def api_atualizar_equipamento(id):
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'patrimonio': data['patrimonio'],
            'estado': data['estado'],
            'updated_at': now_iso()
        }
        resp = supabase.table('equipamentos').update(record).eq('id', id).execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/equipamentos/<int:id>', methods=['DELETE'])
def api_deletar_equipamento(id):
    supabase = get_supabase()
    try:
        supabase.table('equipamentos').delete().eq('id', id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Clubes -----
@app.route('/api/clubes', methods=['GET'])
def api_listar_clubes():
    supabase = get_supabase()
    try:
        resp = supabase.table('clubes').select('*').order('nome').execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clubes', methods=['POST'])
def api_criar_clube():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'semestre': data['semestre'],
            'created_at': now_iso()
        }
        resp = supabase.table('clubes').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clubes/<int:id>', methods=['DELETE'])
def api_deletar_clube(id):
    supabase = get_supabase()
    try:
        supabase.table('clubes').delete().eq('id', id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Disciplinas -----
@app.route('/api/disciplinas', methods=['GET'])
def api_listar_disciplinas():
    supabase = get_supabase()
    try:
        resp = supabase.table('disciplinas').select('*').order('nome').execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/disciplinas', methods=['POST'])
def api_criar_disciplina():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'abreviacao': data['abreviacao'],
            'created_at': now_iso()
        }
        resp = supabase.table('disciplinas').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/disciplinas/<int:id>', methods=['DELETE'])
def api_deletar_disciplina(id):
    supabase = get_supabase()
    try:
        supabase.table('disciplinas').delete().eq('id', id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Eletivas -----
@app.route('/api/eletivas', methods=['GET'])
def api_listar_eletivas():
    supabase = get_supabase()
    try:
        resp = supabase.table('eletivas').select('*').order('nome').execute()
        return jsonify(handle_supabase_response(resp))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/eletivas', methods=['POST'])
def api_criar_eletiva():
    supabase = get_supabase()
    try:
        data = request.json
        record = {
            'nome': data['nome'],
            'semestre': data['semestre'],
            'created_at': now_iso()
        }
        resp = supabase.table('eletivas').insert(record).execute()
        return jsonify(handle_supabase_response(resp)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/eletivas/<int:id>', methods=['DELETE'])
def api_deletar_eletiva(id):
    supabase = get_supabase()
    try:
        supabase.table('eletivas').delete().eq('id', id).execute()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================
# ROTAS HTML (Blueprint principal)
# =============================================================
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/gestao_ocorrencia')
def gestao_ocorrencia():
    return render_template('gestao_ocorrencia.html')

@main_bp.route('/gestao_ocorrencia_nova')
def gestao_ocorrencia_nova():
    return render_template('gestao_ocorrencia_nova.html')

@main_bp.route('/gestao_ocorrencia_abertas')
def gestao_ocorrencia_abertas():
    return render_template('gestao_ocorrencia_aberta.html')

@main_bp.route('/gestao_ocorrencia_finalizadas')
def gestao_ocorrencia_finalizadas():
    return render_template('gestao_ocorrencia_finalizada.html')

@main_bp.route('/gestao_ocorrencia_editar')
def gestao_ocorrencia_editar():
    return render_template('gestao_ocorrencia_editar.html')

@main_bp.route('/gestao_relatorio_impressao')
def gestao_relatorio_impressao():
    return render_template('gestao_relatorio_impressao.html')

@main_bp.route('/gestao_frequencia')
def gestao_frequencia():
    return render_template('gestao_frequencia.html')

@main_bp.route('/gestao_frequencia_registro')
def gestao_frequencia_registro():
    return render_template('gestao_frequencia_registro.html')

@main_bp.route('/gestao_frequencia_atraso')
def gestao_frequencia_atraso():
    return render_template('gestao_frequencia_atraso.html')

@main_bp.route('/gestao_frequencia_saida')
def gestao_frequencia_saida():
    return render_template('gestao_frequencia_saida.html')

@main_bp.route('/gestao_relatorio_frequencia')
def gestao_relatorio_frequencia():
    return render_template('gestao_relatorio_frequencia.html')

@main_bp.route('/gestao_tutoria')
def gestao_tutoria():
    return render_template('gestao_tutoria.html')

@main_bp.route('/gestao_tutoria_ficha')
def gestao_tutoria_ficha():
    return render_template('gestao_tutoria_ficha.html')

@main_bp.route('/gestao_validacao_documentos')
def gestao_validacao_documentos():
    return render_template('gestao_validacao_documentos.html')

@main_bp.route('/gestao_tutoria_agendamento')
def gestao_tutoria_agendamento():
    return render_template('gestao_tutoria_agendamento.html')

@main_bp.route('/gestao_tutoria_registro')
def gestao_tutoria_registro():
    return render_template('gestao_tutoria_registro.html')

@main_bp.route('/gestao_tutoria_notas')
def gestao_tutoria_notas():
    return render_template('gestao_tutoria_notas.html')

@main_bp.route('/gestao_relatorio_tutoria')
def gestao_relatorio_tutoria():
    return render_template('gestao_relatorio_tutoria.html')

@main_bp.route('/gestao_cadastro')
def gestao_cadastro():
    return render_template('gestao_cadastro.html')

@main_bp.route('/gestao_cadastro_professor_funcionario')
def gestao_cadastro_professor_funcionario():
    return render_template('gestao_cadastro_professor_funcionario.html')

@main_bp.route('/gestao_cadastro_aluno')
def gestao_cadastro_aluno():
    return render_template('gestao_cadastro_aluno.html')

@main_bp.route('/gestao_cadastro_tutor')
def gestao_cadastro_tutor():
    return render_template('gestao_cadastro_tutor.html')

@main_bp.route('/gestao_cadastro_sala')
def gestao_cadastro_sala():
    return render_template('gestao_cadastro_sala.html')

@main_bp.route('/gestao_cadastro_disciplinas')
def gestao_cadastro_disciplinas():
    return render_template('gestao_cadastro_disciplinas.html')

@main_bp.route('/gestao_cadastro_eletiva')
def gestao_cadastro_eletiva():
    return render_template('gestao_cadastro_eletiva.html')

@main_bp.route('/gestao_cadastro_clube')
def gestao_cadastro_clube():
    return render_template('gestao_cadastro_clube.html')

@main_bp.route('/gestao_cadastro_equipamento')
def gestao_cadastro_equipamento():
    return render_template('gestao_cadastro_equipamento.html')

@main_bp.route('/gestao_cadastro_vinculacao_tutor_aluno')
def gestao_cadastro_vinculacao_tutor_aluno():
    return render_template('gestao_cadastro_vinculacao_tutor_aluno.html')

@main_bp.route('/gestao_cadastro_vinculacao_disciplina_sala')
def gestao_cadastro_vinculacao_disciplina_sala():
    return render_template('gestao_cadastro_vinculacao_disciplina_sala.html')

@main_bp.route('/gestao_aulas')
def gestao_aulas():
    return render_template('gestao_aulas.html')

@main_bp.route('/gestao_aulas_plano')
def gestao_aulas_plano():
    return render_template('gestao_aulas_plano.html')

@main_bp.route('/gestao_aulas_guia')
def gestao_aulas_guia():
    return render_template('gestao_aulas_guia.html')

@main_bp.route('/gestao_tecnologia')
def gestao_tecnologia():
    return render_template('gestao_tecnologia.html')

@main_bp.route('/gestao_aulas_menu')
def gestao_aulas_menu():
    return render_template('gestao_aulas.html')

@main_bp.route('/gestao_tecnologia_agendamento')
def gestao_tecnologia_agendamento():
    return render_template('gestao_tecnologia_agendamento.html')

@main_bp.route('/gestao_tecnologia_historico')
def gestao_tecnologia_historico():
    return render_template('gestao_tecnologia_historico.html')

@main_bp.route('/gestao_tecnologia_ocorrencia')
def gestao_tecnologia_ocorrencia():
    return render_template('gestao_tecnologia_ocorrencia.html')

# Redirecionamento para compatibilidade (caso o index.html chame /cadastro)
@main_bp.route('/cadastro')
def cadastro_redirect():
    return redirect('/gestao_cadastro')

app.register_blueprint(main_bp, url_prefix='/')

# =============================================================
# Execução
# =============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)



