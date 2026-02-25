# =============================================================
# APP UNIFICADO - GESTÃO ESCOLAR (VERSÃO FINAL)
# Módulos: Ocorrência, Frequência, Tecnologia, Tutoria, Cadastro, Informativos
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
# ROTAS PARA INFORMATIVOS (já existentes, mantidas)
# =============================================================
@app.route('/api/informativos/<int:informativo_id>', methods=['DELETE'])
def api_delete_informativo(informativo_id):
    try:
        supabase = get_supabase()
        response = supabase.table('informativos').select('*').eq('id', informativo_id).execute()
        informativo = handle_supabase_response(response)
        if not informativo:
            return jsonify({'success': False, 'error': 'Informativo não encontrado'}), 404
        delete_response = supabase.table('informativos').delete().eq('id', informativo_id).execute()
        handle_supabase_response(delete_response)
        logger.info(f"Informativo {informativo_id} excluído com sucesso")
        return jsonify({'success': True, 'message': 'Informativo excluído com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao excluir informativo {informativo_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/informativos', methods=['GET'])
def api_get_informativos():
    try:
        supabase = get_supabase()
        response = supabase.table('informativos').select('*').order('criado_em', desc=True).execute()
        informativos = handle_supabase_response(response)
        return jsonify(informativos)
    except Exception as e:
        logger.error(f"Erro ao buscar informativos: {e}")
        return jsonify([])

@app.route('/api/informativos', methods=['POST'])
def api_create_informativo():
    try:
        supabase = get_supabase()
        data = request.get_json()
        if not data or not data.get('titulo') or not data.get('mensagem'):
            return jsonify({'error': 'Título e mensagem são obrigatórios'}), 400
        informativo_data = {
            'titulo': data['titulo'],
            'mensagem': data['mensagem'],
            'criado_em': datetime.now().isoformat(),
            'autor': data.get('autor', 'Sistema')
        }
        response = supabase.table('informativos').insert(informativo_data).execute()
        result = handle_supabase_response(response)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"Erro ao criar informativo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug')
def api_debug():
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'supabase_connected': supabase is not None
    })

@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

@app.route('/publicar_informativo')
def publicar_informativo():
    return redirect('/admin')

# =============================================================
# APIs DE OCORRÊNCIAS (consolidadas)
# =============================================================
@app.route('/api/professores')
def api_professores():
    try:
        if supabase:
            response = supabase.table('d_funcionarios').select('id, nome, tipo').execute()
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
        logger.exception("Erro ao buscar salas")
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
        logger.exception("Erro ao buscar alunos por sala")
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
        logger.exception("Erro ao buscar tutor do aluno")
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
        destino = payload.get("destino")  # 'tutor', 'coordenacao', 'gestao', 'nenhum'

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

        # Definir booleanos de solicitação com base no destino
        solicitado_tutor = (destino == 'tutor')
        solicitado_coordenacao = (destino == 'coordenacao')
        solicitado_gestao = (destino == 'gestao')
        solicitado_responsavel = False  # nunca é solicitado no registro inicial

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
            "solicitado_tutor": solicitado_tutor,
            "solicitado_coordenacao": solicitado_coordenacao,
            "solicitado_gestao": solicitado_gestao,
            "solicitado_responsavel": solicitado_responsavel,
            "status": "ATENDIMENTO",
            "data_hora": now_iso()
        }

        resp = supabase.table("ocorrencias").insert(ocorrencia_data).execute()
        data = handle_supabase_response(resp)
        if data and len(data) > 0:
            return jsonify({
                "success": True,
                "numero": data[0].get("numero"),
                "data": data[0]
            })
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
        logger.exception("Erro em ocorrencia_detalhes")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ocorrencia/<int:numero>', methods=['GET'])
def api_buscar_ocorrencia_por_numero(numero):
    try:
        ocorrencia = get_ocorrencia_por_numero(numero)
        if not ocorrencia:
            return jsonify({'error': f'Ocorrência #{numero} não encontrada'}), 404
        return jsonify(ocorrencia)
    except Exception as e:
        logger.exception("Erro ao buscar ocorrência")
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
        "gestao": ("atendimento_gestao", "dt_atendimento_gestao"),
        "responsavel": ("atendimento_responsavel", "dt_atendimento_responsavel")
    }
    if nivel not in MAPA_ATENDIMENTO:
        return jsonify({"success": False, "error": "Nível inválido"}), 400
    campo_texto, campo_data = MAPA_ATENDIMENTO[nivel]
    try:
        update_payload = {
            campo_texto: texto,
            campo_data: datetime.now().isoformat()
        }
        resp = supabase.table('ocorrencias').update(update_payload).eq('numero', numero).execute()
        _ = handle_supabase_response(resp)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Erro ao salvar atendimento")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/tutores_com_ocorrencias')
def api_tutores_com_ocorrencias():
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('tutor_id').execute()
            dados = handle_supabase_response(response)
            tutor_ids = list(set([occ.get('tutor_id') for occ in dados if occ.get('tutor_id') is not None]))
            tutores_com_nomes = []
            for tutor_id in tutor_ids:
                resp = supabase.table('d_funcionarios').select('nome').eq('id', tutor_id).execute()
                tdata = handle_supabase_response(resp)
                if tdata:
                    tutores_com_nomes.append({'id': tutor_id, 'nome': tdata[0].get('nome', f'Tutor {tutor_id}')})
            return jsonify(tutores_com_nomes)
        return jsonify([])
    except Exception as e:
        logger.exception("Erro ao buscar tutores")
        return jsonify({'error': str(e)}), 500

@app.route('/api/salas_com_ocorrencias')
def api_salas_com_ocorrencias():
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('sala_id').execute()
            dados = handle_supabase_response(response)
            sala_ids = list(set([occ.get('sala_id') for occ in dados if occ.get('sala_id') is not None]))
            salas_com_ocorrencias = []
            for sala_id in sala_ids:
                sala_response = supabase.table('d_salas').select('*').eq('id', sala_id).execute()
                sala_data = handle_supabase_response(sala_response)
                if sala_data:
                    salas_com_ocorrencias.append(sala_data[0])
            return jsonify(salas_com_ocorrencias)
        return jsonify([])
    except Exception as e:
        logger.exception("Erro ao buscar salas com ocorrências")
        return jsonify([])

@app.route('/api/ocorrencias_todas')
def api_ocorrencias_todas():
    try:
        ocorrencias = get_ocorrencias()
        return jsonify(ocorrencias)
    except Exception as e:
        logger.exception("Erro ao buscar ocorrências todas")
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
        logger.exception("Erro ao filtrar ocorrências")
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
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch
        )
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("RELATÓRIO DE OCORRÊNCIAS - ASSINATURA", styles['Title']))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("<b>E.E. PEI PROFESSOR IRENE DIAS RIBEIRO</b>", styles['Heading2']))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"<b>Data do Relatório:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))
        for i, oc in enumerate(ocorrencias_selecionadas):
            elements.append(Paragraph(f"<b>OCORRÊNCIA Nº: {oc.get('numero', 'N/A')}</b>", styles['Heading2']))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph(f"<b>Aluno:</b> {oc.get('aluno_nome', 'N/A')}", styles['Normal']))
            data_hora = oc.get('data_hora', '')
            if data_hora:
                try:
                    dt = datetime.fromisoformat(data_hora.replace('Z', '+00:00'))
                    data_formatada = dt.strftime('%d/%m/%Y')
                    hora_formatada = dt.strftime('%H:%M:%S')
                    elements.append(Paragraph(f"<b>Data:</b> {data_formatada}    <b>Hora:</b> {hora_formatada}", styles['Normal']))
                except:
                    elements.append(Paragraph(f"<b>Data/Hora:</b> {data_hora}", styles['Normal']))
            else:
                elements.append(Paragraph("<b>Data/Hora:</b> N/A", styles['Normal']))
            elements.append(Paragraph(f"<b>Professor:</b> {oc.get('professor_nome', 'N/A')}", styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("<b>Descrição da Ocorrência:</b>", styles['Heading3']))
            elements.append(Paragraph(oc.get('descricao', 'Nenhuma descrição fornecida'), styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("<b>Atendimento Professor:</b>", styles['Heading3']))
            elements.append(Paragraph(oc.get('atendimento_professor', 'Nenhum atendimento registrado'), styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))
            for nivel, nome in [('Tutor', 'tutor'), ('Coordenação', 'coordenacao'), ('Gestão', 'gestao'), ('Responsável', 'responsavel')]:
                elements.append(Paragraph(f"<b>Atendimento {nivel}:</b>", styles['Heading3']))
                if oc.get(f'solicitado_{nome}'):
                    atendimento = oc.get(f'atendimento_{nome}', 'Pendente')
                    if not atendimento or atendimento.strip() == '':
                        atendimento = 'Pendente'
                else:
                    atendimento = f'Atendimento Não Solicitado'
                elements.append(Paragraph(atendimento, styles['Normal']))
                elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph(f"<b>Sala:</b> {oc.get('sala_nome', 'N/A')}    <b>Tutor:</b> {oc.get('tutor_nome', 'N/A')}", styles['Normal']))
            elements.append(Spacer(1, 0.3 * inch))
            if i == len(ocorrencias_selecionadas) - 1:
                elements.append(Paragraph("<b>Assinatura do Responsável: _____</b>", styles['Heading3']))
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph("<b>Data: _____ /_____/_____</b>", styles['Heading3']))
            else:
                elements.append(Spacer(1, 0.2 * inch))
        doc.build(elements)
        for numero in numeros_selecionados:
            supabase.table("ocorrencias").update({"impressao_pdf": True}).eq("numero", numero).execute()
        buffer.seek(0)
        nome_arquivo = f"ocorrencias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Erro ao gerar PDF: {str(e)}")
        import traceback
        traceback.print_exc()
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
        solicitado_responsavel = bool(payload.get("solicitado_responsavel", False))
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
            "solicitado_responsavel": solicitado_responsavel,
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
        tipo = payload.get("tipo")  # 'tutor', 'coordenacao', 'gestao', 'responsavel'
        texto = payload.get("texto", "")
        acao = payload.get("acao")  # 'finalizar', 'encaminhar_tutor', 'encaminhar_coordenacao', 'encaminhar_gestao', 'convocar_responsavel'

        if tipo not in ("tutor", "coordenacao", "gestao", "responsavel"):
            return jsonify({"ok": False, "error": "tipo inválido"}), 400

        # Mapear campos de atendimento e data
        field_text = f"atendimento_{tipo}"
        field_dt = f"dt_atendimento_{tipo}"

        # Preparar updates básicos
        updates = {
            field_text: texto,
            field_dt: now_iso()
        }

        # Processar ação, se fornecida
        if acao:
            # Primeiro, resetar todos os solicitados (opcional, dependendo da regra)
            # Vamos zerar apenas os que não são o destino
            updates['solicitado_tutor'] = False
            updates['solicitado_coordenacao'] = False
            updates['solicitado_gestao'] = False
            updates['solicitado_responsavel'] = False

            if acao == 'finalizar':
                # Não solicita mais ninguém
                pass
            elif acao == 'encaminhar_tutor':
                updates['solicitado_tutor'] = True
            elif acao == 'encaminhar_coordenacao':
                updates['solicitado_coordenacao'] = True
            elif acao == 'encaminhar_gestao':
                updates['solicitado_gestao'] = True
            elif acao == 'convocar_responsavel':
                updates['solicitado_responsavel'] = True
            else:
                return jsonify({"ok": False, "error": "ação inválida"}), 400

        # Aplicar update
        resp = supabase.table("ocorrencias").update(updates).eq("id", oc_id).execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# =============================================================
# ROTAS DE FREQUÊNCIA (já existentes, mantidas)
# =============================================================
# ... (todo o código de frequência permanece igual, omitido por brevidade)
# Inclua aqui todas as rotas de frequência do arquivo original

# =============================================================
# NOVOS ENDPOINTS - MÓDULO TUTORIA (já existentes, mantidos)
# =============================================================
# ... (código de tutoria permanece igual)

# =============================================================
# NOVOS ENDPOINTS - MÓDULO TECNOLOGIA (já existentes, mantidos)
# =============================================================
# ... (código de tecnologia permanece igual)

# =============================================================
# NOVOS ENDPOINTS - MÓDULO CADASTRO (CRUD) (já existentes, mantidos)
# =============================================================
# ... (código de cadastro permanece igual)

# =============================================================
# ALIASES E ROTAS ADICIONAIS PARA COMPATIBILIDADE
# =============================================================
# ... (código de aliases permanece igual)

# =============================================================
# ROTAS HTML (Blueprint principal) (já existentes, mantidas)
# =============================================================
# ... (código de rotas HTML permanece igual)

# =============================================================
# Execução
# =============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)