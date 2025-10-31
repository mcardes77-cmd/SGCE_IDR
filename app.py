# =============================================================
# APP UNIFICADO - GESTÃO ESCOLAR (AJUSTADO)
# Conteúdo: merge de app (6).py + db_utils.py + routes_frequencia.py
# Ajustes: utiliza apenas d_alunos; compatível com f_frequencia
# Autor: gerado automaticamente (ajustes)
# =============================================================

from flask import Flask, render_template, Blueprint, request, jsonify, send_file
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import logging
import time
from datetime import datetime, date
from calendar import monthrange
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
# Inicializador do Supabase (sem proxy)
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

            # Teste rápido para confirmar conexão
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
    """
    Trata a resposta do Supabase e retorna os dados ou lança erro.
    Compatível com a versão atual do supabase-py.
    """
    # Se houver erro
    if hasattr(response, 'error') and response.error:
        raise Exception(f"Erro Supabase: {response.error}")

    # Alguns retornos recentes usam 'status_code' e 'data'
    if hasattr(response, 'status_code') and response.status_code >= 400:
        raise Exception(f"Erro Supabase: status_code={response.status_code} - {response.data}")

    # Retorna os dados normalmente
    return getattr(response, 'data', response)

# =============================================================
# CORREÇÕES - ADICIONAR APÓS A CONFIGURAÇÃO DO SUPABASE
# =============================================================

def get_supabase():
    """Obter cliente Supabase inicializado"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = _init_supabase_client()
    return _supabase_client

# Inicializar Supabase ao iniciar o app
supabase = get_supabase()


# =============================================================
# INICIALIZAÇÃO DO FLASK (base: app (6).py)
# =============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')

# Garanta que a instância global supabase esteja pronta
supabase = get_supabase()

# ---------- Util: gerar timestamp ISO ----------
def now_iso():
    return datetime.utcnow().isoformat()

# =============================================================
# Funções auxiliares do app original (mantidas)
# Ajustadas para utilizar d_alunos em vez de alunos
# =============================================================

def get_salas():
    try:
        if supabase:
            # CORREÇÃO: Usando 'd_salas' para consistência
            response = supabase.table('d_salas').select('*').execute()
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
# ROTAS PARA INFORMATIVOS
# =============================================================
@app.route('/api/informativos/<int:informativo_id>', methods=['DELETE'])
def api_delete_informativo(informativo_id):
    """Excluir um informativo"""
    try:
        supabase = get_supabase()
        
        # Verificar se o informativo existe
        response = supabase.table('informativos').select('*').eq('id', informativo_id).execute()
        informativo = handle_supabase_response(response)
        
        if not informativo:
            return jsonify({'success': False, 'error': 'Informativo não encontrado'}), 404
        
        # Excluir o informativo
        delete_response = supabase.table('informativos').delete().eq('id', informativo_id).execute()
        handle_supabase_response(delete_response)
        
        logger.info(f"Informativo {informativo_id} excluído com sucesso")
        return jsonify({'success': True, 'message': 'Informativo excluído com sucesso'})
        
    except Exception as e:
        logger.error(f"Erro ao excluir informativo {informativo_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/informativos', methods=['GET'])
def api_get_informativos():
    """Buscar todos os informativos"""
    try:
        supabase = get_supabase()
        response = supabase.table('informativos').select('*').order('criado_em', desc=True).execute()
        informativos = handle_supabase_response(response)
        return jsonify(informativos)
    except Exception as e:
        logger.error(f"Erro ao buscar informativos: {e}")
        return jsonify([])

# =============================================================
# ROTA ADMIN PARA PUBLICAR INFORMATIVOS
# =============================================================

@app.route('/api/debug')
def api_debug():
    """Rota de debug para testar a API"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'supabase_connected': supabase is not None
    })

@app.route('/admin')
def admin_panel():
    """Página administrativa para publicar informativos"""
    return render_template('admin.html')


@app.route('/api/informativos', methods=['POST'])
def api_create_informativo():
    """Criar novo informativo"""
    try:
        supabase = get_supabase()
        data = request.get_json()
        
        if not data or not data.get('titulo') or not data.get('mensagem'):
            return jsonify({'error': 'Título e mensagem são obrigatórios'}), 400
        
        # Preparar dados
        informativo_data = {
            'titulo': data['titulo'],
            'mensagem': data['mensagem'],
            'criado_em': datetime.now().isoformat(),
            'autor': data.get('autor', 'Sistema')
        }
        
        # Inserir no banco
        response = supabase.table('informativos').insert(informativo_data).execute()
        result = handle_supabase_response(response)
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"Erro ao criar informativo: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================
# ROTA PARA PÁGINA DE PUBLICAR INFORMATIVOS
# =============================================================

@app.route('/publicar_informativo')
def publicar_informativo():
    """Redireciona para a página admin"""
    return redirect('/admin')

# =============================================================
# APIs — nova ocorrência, buscas auxiliares e CRUD de ocorrências
# =============================================================

@app.route('/api/professores')
def api_professores():
    """Retorna todos os funcionários do tipo PROFESSOR (d_funcionarios)"""
    try:
        if supabase:
            response = supabase.table('d_funcionarios').select('id, nome, tipo').execute()
            professores = handle_supabase_response(response)
            # filtrar por tipo 'PROFESSOR' caso use esse campo
            # se quiser filtrar retire o comentário:
            # professores = [p for p in professores if p.get('tipo') == 'PROFESSOR']
            return jsonify(professores)
        return jsonify([])
    except Exception as e:
        logger.exception("Erro ao buscar professores")
        return jsonify({'error': str(e)}), 500

@app.route('/api/salas_por_professor/<int:professor_id>')
def api_salas_por_professor(professor_id):
    """Retorna todas as salas ativas (d_salas) - mantido para compatibilidade"""
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
    """Retorna o tutor de um aluno específico"""
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
    """
    Registrar uma nova ocorrência
    """
    supabase = get_supabase()
    try:
        payload = request.json or {}
        
        # Dados obrigatórios
        aluno_id = payload.get("aluno_id")
        professor_id = payload.get("professor_id")
        professor_nome = payload.get("professor_nome")
        descricao = payload.get("descricao")
        atendimento_professor = payload.get("atendimento_professor")
        
        if not all([aluno_id, professor_id, professor_nome, descricao, atendimento_professor]):
            return jsonify({"success": False, "error": "Dados obrigatórios faltando"}), 400

        # Buscar informações do aluno para obter nome e sala
        resp_aluno = supabase.table("d_alunos").select("nome, sala_id, sala_nome, tutor_nome").eq("id", aluno_id).execute()
        if not resp_aluno.data:
            return jsonify({"success": False, "error": "Aluno não encontrado"}), 404
        
        aluno_data = resp_aluno.data[0]
        aluno_nome = aluno_data.get("nome")
        sala_nome = aluno_data.get("sala_nome")
        tutor_nome = aluno_data.get("tutor_nome", payload.get("tutor_nome", ""))

        # Buscar o próximo número da ocorrência
        resp_numero = supabase.table("ocorrencias").select("numero").order("numero", desc=True).limit(1).execute()
        ultimo_numero = 0
        if resp_numero.data and len(resp_numero.data) > 0:
            ultimo_numero = resp_numero.data[0].get("numero", 0)
        proximo_numero = ultimo_numero + 1

        # Preparar dados para inserção
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

        # Inserir no banco
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
    """
    Retorna ocorrência buscada por 'numero' (query param).
    Compatível com o frontend que chama: /api/ocorrencia_detalhes?numero=123
    """
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
    """Busca os dados de uma ocorrência pelo número (rota alternativa)"""
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
    """
    Atualiza o campo de atendimento para um nível (tutor/coordenacao/gestao)
    Expects JSON: { "numero": <numero>, "nivel": "tutor"|"coordenacao"|"gestao", "texto": "..." }
    """
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
        update_payload = {
            campo_texto: texto,
            campo_data: datetime.now().isoformat()
        }
        # supabase update by numero
        resp = supabase.table('ocorrencias').update(update_payload).eq('numero', numero).execute()
        _ = handle_supabase_response(resp)
        return jsonify({"success": True})
    except Exception as e:
        logger.exception("Erro ao salvar atendimento")
        return jsonify({"success": False, "error": str(e)}), 500

# =============================================================
# APIs de ocorrência - filtros, listagens e geração de PDF
# =============================================================

@app.route('/api/tutores_com_ocorrencias')
def api_tutores_com_ocorrencias():
    """Retorna tutores que têm ocorrências"""
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('tutor_id').execute()
            dados = handle_supabase_response(response)
            tutor_ids = list(set([occ.get('tutor_id') for occ in dados if occ.get('tutor_id') is not None]))
            tutores_com_nomes = []
            for tutor_id in tutor_ids:
                resp = supabase.table('d_tutores').select('nome').eq('tutor_id', tutor_id).execute()
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
                sala_response = supabase.table('salas').select('*').eq('id', sala_id).execute()
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
    """Filtrar ocorrências por sala_id, tutor_id, status, aluno_id — usando 'numero' como chave de identificação nas respostas"""
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
    """
    Gerar PDF para as ocorrências selecionadas
    """
    supabase = get_supabase()
    try:
        dados = request.get_json()
        if not dados or 'numeros' not in dados:
            return jsonify({"error": "Lista de ocorrências não fornecida"}), 400

        numeros_selecionados = dados['numeros']
        print(f"Números recebidos para PDF: {numeros_selecionados}")
        
        if not numeros_selecionados:
            return jsonify({"error": "Nenhuma ocorrência selecionada"}), 400

        # Buscar as ocorrências selecionadas no banco de dados
        resp = supabase.table("ocorrencias").select("*").in_("numero", numeros_selecionados).order("data_hora").execute()
        ocorrencias_selecionadas = handle_supabase_response(resp)
        
        print(f"Ocorrências encontradas no banco: {len(ocorrencias_selecionadas)}")
        
        if not ocorrencias_selecionadas:
            return jsonify({"error": "Nenhuma ocorrência encontrada para os números fornecidos"}), 404

        # Ordenar por data (mais antiga primeiro) para o PDF
        ocorrencias_selecionadas = sorted(ocorrencias_selecionadas, key=lambda x: x.get('data_hora', ''))

        # Criar PDF
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

        # Título e cabeçalho
        elements.append(Paragraph("RELATÓRIO DE OCORRÊNCIAS - ASSINATURA", styles['Title']))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("<b>E.E. PEI PROFESSOR IRENE DIAS RIBEIRO</b>", styles['Heading2']))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"<b>Data do Relatório:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))

        # Adicionar cada ocorrência
        for i, oc in enumerate(ocorrencias_selecionadas):
            elements.append(Paragraph(f"<b>OCORRÊNCIA Nº: {oc.get('numero', 'N/A')}</b>", styles['Heading2']))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph(f"<b>Aluno:</b> {oc.get('aluno_nome', 'N/A')}", styles['Normal']))
            
            # Data e hora
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
            
            # Descrição
            elements.append(Paragraph("<b>Descrição da Ocorrência:</b>", styles['Heading3']))
            elements.append(Paragraph(oc.get('descricao', 'Nenhuma descrição fornecida'), styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))
            
            # Atendimento Professor
            elements.append(Paragraph("<b>Atendimento Professor:</b>", styles['Heading3']))
            elements.append(Paragraph(oc.get('atendimento_professor', 'Nenhum atendimento registrado'), styles['Normal']))
            elements.append(Spacer(1, 0.1 * inch))
            
            # Atendimentos solicitados
            for nivel, nome in [('Tutor', 'tutor'), ('Coordenação', 'coordenacao'), ('Gestão', 'gestao')]:
                elements.append(Paragraph(f"<b>Atendimento {nivel}:</b>", styles['Heading3']))
                if oc.get(f'solicitado_{nome}'):
                    atendimento = oc.get(f'atendimento_{nome}', 'Pendente')
                    if not atendimento or atendimento.strip() == '':
                        atendimento = 'Pendente'
                else:
                    atendimento = f'Atendimento Não Solicitado pelo Professor Responsável da Ocorrência'
                elements.append(Paragraph(atendimento, styles['Normal']))
                elements.append(Spacer(1, 0.1 * inch))
            
            # Sala e Tutor
            elements.append(Paragraph(f"<b>Sala:</b> {oc.get('sala_nome', 'N/A')}    <b>Tutor:</b> {oc.get('tutor_nome', 'N/A')}", styles['Normal']))
            elements.append(Spacer(1, 0.3 * inch))
            
            # Assinatura na última ocorrência
            if i == len(ocorrencias_selecionadas) - 1:
                elements.append(Paragraph("<b>Assinatura do Responsável: _____</b>", styles['Heading3']))
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph("<b>Data: _____ /_____/_____</b>", styles['Heading3']))
            else:
                elements.append(Spacer(1, 0.2 * inch))

        doc.build(elements)

        # Marcar como impresso no banco
        for numero in numeros_selecionados:
            supabase.table("ocorrencias").update({"impressao_pdf": True}).eq("numero", numero).execute()

        buffer.seek(0)
        
        # Retornar o PDF para download
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
        
# ---------- Listar ocorrências com filtros ----------
@app.route("/api/ocorrencias", methods=["GET"])
def api_list_ocorrencias():
    supabase: Client = get_supabase()
    try:
        q = supabase.table("ocorrencias")
        # filtros opcionais via query string
        tutor = request.args.get("tutor")
        sala = request.args.get("sala")
        aluno = request.args.get("aluno")
        status = request.args.get("status")
        # se vier vazio ou "todos", ignora
        if tutor:
            q = q.eq("tutor_nome", tutor)
        if sala:
            q = q.eq("sala_nome", sala)
        if aluno:
            q = q.eq("aluno_nome", aluno)
        if status:
            q = q.eq("status", status)
        # ordernar por data_hora desc
        resp = q.order("data_hora", desc=True).execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------- Listas para selects ----------
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
        resp = supabase.table("d_salas").select("id, nome").order("nome").execute()
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

# ---------- Criar nova ocorrência ----------
@app.route("/api/ocorrencias", methods=["POST"])
def api_create_ocorrencia():
    supabase = get_supabase()
    try:
        payload = request.json or {}
        # Campos esperados do frontend:
        # professor_nome, sala_nome, aluno_id (ou aluno_nome), aluno_nome, tutor_nome,
        # atendimento_professor (texto opcional), solicitado_tutor (bool), solicitado_coordenacao, solicitado_gestao
        professor_nome = payload.get("professor_nome")
        sala_nome = payload.get("sala_nome")
        aluno_nome = payload.get("aluno_nome")
        tutor_nome = payload.get("tutor_nome")
        atendimento_professor = payload.get("atendimento_professor", "")
        solicitado_tutor = bool(payload.get("solicitado_tutor", False))
        solicitado_coordenacao = bool(payload.get("solicitado_coordenacao", False))
        solicitado_gestao = bool(payload.get("solicitado_gestao", False))
        status = payload.get("status", "aberta")  # default se desejar

        # data_hora agora
        data_hora = now_iso()

        # monta objeto para inserir
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

        # Se sua coluna numero é serial/identity no DB, o banco vai preencher automaticamente.
        # Caso NÃO seja, você pode gerar numero aqui (ver observação abaixo).
        resp = supabase.table("ocorrencias").insert(record).execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ---------- Atualizar atendimentos (edits) ----------
@app.route("/api/ocorrencias/<int:oc_id>/atendimento", methods=["PUT"])
def api_update_atendimento(oc_id):
    """
    Espera JSON:
    {
      "tipo": "tutor" | "coordenacao" | "gestao",
      "texto": "texto do atendimento"
    }
    Ao salvar, também grava dt_atendimento_<tipo> com timestamp atual.
    """
    supabase = get_supabase()
    try:
        payload = request.json or {}
        tipo = payload.get("tipo")
        texto = payload.get("texto", "")
        if tipo not in ("tutor", "coordenacao", "gestao"):
            return jsonify({"ok": False, "error": "tipo inválido"}), 400

        field_text = f"atendimento_{tipo}"
        field_dt = f"dt_atendimento_{tipo}"

        updates = {
            field_text: texto,
            field_dt: now_iso()
        }

        resp = supabase.table("ocorrencias").update(updates).eq("id", oc_id).execute()
        data = handle_supabase_response(resp)
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# ========== ROTAS DE FREQUÊNCIA ==========

@app.route('/api/d_salas', methods=['GET'])
def get_salas():
    """Buscar todas as salas"""
    try:
        response = supabase.table('d_salas').select('*').eq('ativa', True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos_por_sala/<int:sala_id>', methods=['GET'])
def get_alunos_por_sala(sala_id):
    """Buscar alunos por sala"""
    try:
        response = supabase.table('d_alunos').select('*').eq('sala_id', sala_id).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia/status', methods=['GET'])
def get_status_frequencia():
    """Verificar se frequência já foi registrada para uma sala e data"""
    try:
        sala_id = request.args.get('sala_id')
        data = request.args.get('data')
        
        if not sala_id or not data:
            return jsonify({'error': 'sala_id e data são obrigatórios'}), 400
        
        # Buscar nome da sala
        sala_response = supabase.table('d_salas').select('nome').eq('id', sala_id).execute()
        if not sala_response.data:
            return jsonify({'error': 'Sala não encontrada'}), 404
        
        sala_nome = sala_response.data[0]['nome']
        
        # Verificar se existe frequência para esta sala e data
        response = supabase.table('f_frequencia').select('id').eq('sala_nome', sala_nome).eq('data', data).execute()
        
        return jsonify({'registrada': len(response.data) > 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_frequencia_unificada', methods=['POST'])
def salvar_frequencia_unificada():
    """Salvar frequência, atrasos e saídas antecipadas"""
    try:
        dados = request.get_json()
        
        if not isinstance(dados, list):
            return jsonify({'error': 'Dados devem ser uma lista'}), 400
        
        resultados = []
        
        for registro in dados:
            # Buscar nome da sala se só tiver sala_id
            sala_nome = registro.get('sala_nome')
            if not sala_nome and 'sala_id' in registro:
                sala_response = supabase.table('d_salas').select('nome').eq('id', registro['sala_id']).execute()
                if sala_response.data:
                    sala_nome = sala_response.data[0]['nome']
                else:
                    resultados.append({'error': f'Sala com id {registro["sala_id"]} não encontrada'})
                    continue
            
            # Buscar nome do aluno se só tiver aluno_id
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
            
            # Verificar se já existe registro para este aluno na data
            existing = supabase.table('f_frequencia')\
                .select('*')\
                .eq('aluno_nome', aluno_nome)\
                .eq('data', registro['data'])\
                .execute()
            
            # Determinar status baseado nos dados
            status = determinar_status(registro, existing.data[0] if existing.data else None)
            
            # Preparar dados para inserção/atualização
            dados_frequencia = {
                'aluno_nome': aluno_nome,
                'sala_nome': sala_nome,
                'data': registro['data'],
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            # Adicionar campos opcionais se existirem
            campos_opcionais = [
                'hora_entrada', 'motivo_atraso', 'hora_saida', 
                'motivo_saida', 'responsavel_nome', 'responsavel_telefone'
            ]
            
            for campo in campos_opcionais:
                if campo in registro:
                    dados_frequencia[campo] = registro[campo]
            
            if existing.data:
                # Atualizar registro existente
                result = supabase.table('f_frequencia')\
                    .update(dados_frequencia)\
                    .eq('id', existing.data[0]['id'])\
                    .execute()
            else:
                # Inserir novo registro
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
    """Determinar o status final baseado no registro existente e novo"""
    if registro_existente:
        status_atual = registro_existente.get('status', 'P')
    else:
        status_atual = novo_registro.get('status', 'P')  # Default para Presença
    
    # Se veio com status explícito, usar esse
    if 'status' in novo_registro and novo_registro['status'] in ['P', 'F']:
        return novo_registro['status']
    
    # Lógica para combinar status
    tem_atraso = 'hora_entrada' in novo_registro and novo_registro['hora_entrada']
    tem_saida = 'hora_saida' in novo_registro and novo_registro['hora_saida']
    
    # Se é um registro de frequência normal (sem atraso/saída)
    if not tem_atraso and not tem_saida and 'status' in novo_registro:
        return novo_registro['status']
    
    # Lógica para status especiais
    if tem_atraso and tem_saida:
        return 'PSA'  # Presença com Atraso e Saída Antecipada
    elif tem_atraso:
        # Se já tinha saída, vira PSA, senão PA
        if registro_existente and registro_existente.get('hora_saida'):
            return 'PSA'
        return 'PA'   # Presença com Atraso
    elif tem_saida:
        # Se já tinha atraso, vira PSA, senão PS
        if registro_existente and registro_existente.get('hora_entrada'):
            return 'PSA'
        return 'PS'   # Presença com Saída Antecipada
    
    return status_atual

@app.route('/api/frequencia', methods=['GET'])
def get_frequencia_relatorio():
    """Buscar dados de frequência para relatório"""
    try:
        sala_id = request.args.get('sala')
        mes = request.args.get('mes')
        ano = datetime.now().year
        
        if not sala_id or not mes:
            return jsonify({'error': 'sala e mes são obrigatórios'}), 400
        
        # Buscar nome da sala
        sala_response = supabase.table('d_salas').select('nome').eq('id', sala_id).execute()
        if not sala_response.data:
            return jsonify({'error': 'Sala não encontrada'}), 404
        
        sala_nome = sala_response.data[0]['nome']
        
        # Buscar alunos da sala
        alunos_response = supabase.table('d_alunos')\
            .select('id, nome')\
            .eq('sala_id', sala_id)\
            .execute()
        
        if not alunos_response.data:
            return jsonify([])
        
        # Buscar frequência dos alunos no mês
        data_inicio = f"{ano}-{mes.zfill(2)}-01"
        data_fim = f"{ano}-{mes.zfill(2)}-31"
        
        frequencia_response = supabase.table('f_frequencia')\
            .select('*')\
            .in_('aluno_nome', [aluno['nome'] for aluno in alunos_response.data])\
            .eq('sala_nome', sala_nome)\
            .gte('data', data_inicio)\
            .lte('data', data_fim)\
            .execute()
        
        # Organizar dados
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
        # Busca o registro de frequência do aluno para a data informada
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
        print("Erro ao buscar detalhes de frequência:", e)
        return jsonify({"error": str(e)}), 500

# ========== ROTAS ADICIONAIS PARA COMPATIBILIDADE ==========

@app.route('/api/frequencia_diaria', methods=['GET'])
def get_frequencia_diaria():
    """Buscar frequência de uma sala em uma data específica"""
    try:
        sala_id = request.args.get('sala_id')
        data = request.args.get('data')
        
        if not sala_id or not data:
            return jsonify({'error': 'sala_id e data são obrigatórios'}), 400
        
        # Buscar nome da sala
        sala_response = supabase.table('d_salas').select('nome').eq('id', sala_id).execute()
        if not sala_response.data:
            return jsonify({'error': 'Sala não encontrada'}), 404
        
        sala_nome = sala_response.data[0]['nome']
        
        # Buscar alunos da sala
        alunos_response = supabase.table('d_alunos')\
            .select('id, nome')\
            .eq('sala_id', sala_id)\
            .execute()
        
        # Buscar frequência dos alunos na data
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
# ROTAS HTML (mantidas)
# =============================================================

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    return render_template('index.html')

# ocorrencias
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

# frequencia
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

# tutoria
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

# cadastro
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

# aulas
@main_bp.route('/gestao_aulas')
def gestao_aulas():
    return render_template('gestao_aulas.html')

@main_bp.route('/gestao_aulas_plano')
def gestao_aulas_plano():
    return render_template('gestao_aulas_plano.html')

@main_bp.route('/gestao_aulas_guia')
def gestao_aulas_guia():
    return render_template('gestao_aulas_guia.html')

# correções / tec
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

# Registrar blueprint principal
app.register_blueprint(main_bp, url_prefix='/')


# =============================================================
# Execução
# =============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

















