# =============================================================
# APP UNIFICADO - GESTÃO ESCOLAR (AJUSTADO)
# Conteúdo: merge de app (6).py + db_utils.py + routes_frequencia.py
# Ajustes: utiliza apenas d_alunos; compatível com f_frequencia
# Autor: gerado automaticamente (ajustes)
# =============================================================

from flask import Flask, render_template, Blueprint, request, jsonify
import os
import logging
import time
from datetime import datetime, date
from calendar import monthrange
from supabase import create_client, Client
from dotenv import load_dotenv
from io import BytesIO

# -----------------------------
# Carregar .env
# -----------------------------
load_dotenv()

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================
# DB_UTILS (integrado)
# Conteúdo adaptado de db_utils.py
# =============================================================

# Variáveis de ambiente
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL:
    logger.warning("SUPABASE_URL não encontrada nas variáveis de ambiente.")
if not SUPABASE_KEY:
    logger.warning("SUPABASE_KEY não encontrada nas variáveis de ambiente.")

_supabase_client = None

def _init_supabase_client(retries: int = 3, backoff: float = 1.0):
    global _supabase_client
    if _supabase_client:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("Não é possível inicializar Supabase: SUPABASE_URL ou SUPABASE_KEY ausentes.")
        return None

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Tentando inicializar Supabase (tentativa {attempt}/{retries})...")
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Teste simples (não falha o init caso tabela não exista)
            try:
                _supabase_client.table('d_funcionarios').select('*').limit(1).execute()
                logger.info("Conexão Supabase inicializada e testada com sucesso.")
            except Exception as test_error:
                logger.warning(f"Conexão estabelecida, mas teste falhou: {test_error}")

            return _supabase_client
        except Exception as e:
            logger.error(f"Falha ao criar client Supabase (tentativa {attempt}): {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                logger.error("Não foi possível inicializar Supabase após várias tentativas.")
                return None

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = _init_supabase_client()
    return _supabase_client

# handle response
def handle_supabase_response(response):
    """
    Normaliza respostas do supabase-py:
    - aceita objetos que têm .data e .error
    - aceita dicts {'data': ..., 'error': ...}
    - retorna a lista / objeto de dados
    """
    try:
        if response is None:
            raise Exception("Resposta Supabase é None.")
        # supabase-py v1: response is an object with .data / .error
        if hasattr(response, "error") and response.error:
            raise Exception(f"Erro Postgrest: {response.error}")
        if hasattr(response, "data"):
            return response.data
        # fallback: dict-like
        if isinstance(response, dict):
            if response.get("error"):
                raise Exception(f"Erro Postgrest: {response['error']}")
            return response.get("data", response)
        return response
    except Exception:
        logger.exception("Erro ao tratar resposta Supabase.")
        raise

# utilitários úteis (copiados de db_utils.py)
DEFAULT_AUTOTEXT = "Não solicitado"

def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes', 'sim', 's', 'y')
    return False

def formatar_data_hora(data_hora_str):
    if not data_hora_str:
        return ""
    try:
        dt = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return data_hora_str

def calcular_dias_resposta(data_abertura, data_atendimento):
    if not data_abertura or not data_atendimento:
        return None
    try:
        dt_abertura = datetime.fromisoformat(data_abertura.replace('Z', '+00:00'))
        dt_atendimento = datetime.fromisoformat(data_atendimento.replace('Z', '+00:00'))
        return (dt_atendimento - dt_abertura).days
    except:
        return None

def safe_pdf_text(texto):
    if not texto:
        return ""
    return str(texto).replace('°', 'º').replace('ª', 'a').replace('º', 'o')

# Exemplos de helpers para consultas (do db_utils)
def get_alunos_por_sala_data(sala_id):
    """
    Retorna lista de alunos (d_alunos) da sala com dados do tutor (d_funcionarios).
    Ajustado para d_alunos.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            return []
        # tenta incluir join para pegar nome do tutor se existir tutor_id
        response = supabase.table('d_alunos').select('id, nome, tutor_nome').eq('sala_id', sala_id).execute()
        alunos = handle_supabase_response(response)
        return alunos
    except Exception as e:
        logger.error(f"Erro ao buscar alunos da sala {sala_id}: {e}")
        return []

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
            response = supabase.table('salas').select('*').execute()
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

@app.route("/api/gerar_pdf_ocorrencias", methods=["POST"])
def api_gerar_pdf_ocorrencias():
    """
    Gerar PDF para as ocorrências selecionadas
    """
    supabase = get_supabase()
    try:
        payload = request.json or {}
        numeros_ocorrencias = payload.get("numeros", [])
        
        if not numeros_ocorrencias:
            return jsonify({"success": False, "error": "Nenhuma ocorrência selecionada"}), 400

        # Buscar as ocorrências selecionadas
        resp = supabase.table("ocorrencias").select("*").in_("numero", numeros_ocorrencias).execute()
        ocorrencias = handle_supabase_response(resp)
        
        if not ocorrencias:
            return jsonify({"success": False, "error": "Nenhuma ocorrência encontrada"}), 404

        # Gerar o PDF
        pdf_buffer = gerar_pdf_ocorrencias(ocorrencias)  # Chamando a função auxiliar
        
        # Marcar como impresso no banco
        for numero in numeros_ocorrencias:
            supabase.table("ocorrencias").update({"impressao_pdf": True}).eq("numero", numero).execute()

        # Retornar o arquivo PDF para download
        from io import BytesIO
        pdf_buffer.seek(0)
        
        nome_arquivo = f"ocorrencias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/pdf'
        )
            
    except Exception as e:
        print(f"Erro ao gerar PDF: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def gerar_pdf_ocorrencias(ocorrencias):
    """
    Gerar PDF com as ocorrências selecionadas no formato específico
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                          topMargin=0.5*inch, 
                          bottomMargin=0.5*inch,
                          leftMargin=0.5*inch,
                          rightMargin=0.5*inch)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Título principal
    title = Paragraph("RELATÓRIO DE OCORRÊNCIAS - ASSINATURA", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2 * inch))
    
    # Cabeçalho da escola
    escola = Paragraph("<b>E.E. PEI PROFESSOR IRENE DIAS RIBEIRO</b>", styles['Heading2'])
    elements.append(escola)
    elements.append(Spacer(1, 0.1 * inch))
    
    # Data do relatório
    data_relatorio = Paragraph(f"<b>Data do Relatório:</b> {datetime.now().strftime('%d/%m/%Y')}", styles['Normal'])
    elements.append(data_relatorio)
    elements.append(Spacer(1, 0.3 * inch))
    
    # Dados das ocorrências
    for i, ocorrencia in enumerate(ocorrencias):
        # Número da ocorrência
        elements.append(Paragraph(f"<b>OCORRÊNCIA Nº: {ocorrencia.get('numero', 'N/A')}</b>", styles['Heading2']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Dados do aluno
        aluno_text = f"<b>Aluno:</b> {ocorrencia.get('aluno_nome', 'N/A')}"
        elements.append(Paragraph(aluno_text, styles['Normal']))
        
        # Data e hora
        data_hora = ocorrencia.get('data_hora', '')
        if data_hora:
            try:
                data_obj = datetime.fromisoformat(data_hora.replace('Z', '+00:00'))
                data_formatada = data_obj.strftime('%d/%m/%Y')
                hora_formatada = data_obj.strftime('%H:%M:%S')
                data_hora_text = f"<b>Data:</b> {data_formatada}    <b>Hora:</b> {hora_formatada}"
            except:
                data_hora_text = f"<b>Data/Hora:</b> {data_hora}"
        else:
            data_hora_text = "<b>Data/Hora:</b> N/A"
        
        elements.append(Paragraph(data_hora_text, styles['Normal']))
        
        # Professor
        professor_text = f"<b>Professor:</b> {ocorrencia.get('professor_nome', 'N/A')}"
        elements.append(Paragraph(professor_text, styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Descrição da ocorrência
        elements.append(Paragraph("<b>Descrição da Ocorrência:</b>", styles['Heading3']))
        descricao = ocorrencia.get('descricao', 'Nenhuma descrição fornecida')
        elements.append(Paragraph(descricao, styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Atendimento Professor
        elements.append(Paragraph("<b>Atendimento Professor:</b>", styles['Heading3']))
        atendimento_prof = ocorrencia.get('atendimento_professor', 'Nenhum atendimento registrado')
        elements.append(Paragraph(atendimento_prof, styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Atendimento Tutor
        elements.append(Paragraph("<b>Atendimento Tutor:</b>", styles['Heading3']))
        if ocorrencia.get('solicitado_tutor'):
            atendimento_tutor = ocorrencia.get('atendimento_tutor', 'Pendente')
            if not atendimento_tutor or atendimento_tutor.strip() == '':
                atendimento_tutor = 'Pendente'
        else:
            atendimento_tutor = 'Atendimento Não Solicitado pelo Professor Responsável da Ocorrência'
        elements.append(Paragraph(atendimento_tutor, styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Atendimento Coordenação
        elements.append(Paragraph("<b>Atendimento Coordenação:</b>", styles['Heading3']))
        if ocorrencia.get('solicitado_coordenacao'):
            atendimento_coord = ocorrencia.get('atendimento_coordenacao', 'Pendente')
            if not atendimento_coord or atendimento_coord.strip() == '':
                atendimento_coord = 'Pendente'
        else:
            atendimento_coord = 'Atendimento Não Solicitado pelo Professor Responsável da Ocorrência'
        elements.append(Paragraph(atendimento_coord, styles['Normal']))
        elements.append(Spacer(1, 0.1 * inch))
        
        # Atendimento Gestão
        elements.append(Paragraph("<b>Atendimento Gestão:</b>", styles['Heading3']))
        if ocorrencia.get('solicitado_gestao'):
            atendimento_gestao = ocorrencia.get('atendimento_gestao', 'Pendente')
            if not atendimento_gestao or atendimento_gestao.strip() == '':
                atendimento_gestao = 'Pendente'
        else:
            atendimento_gestao = 'Atendimento Não Solicitado pelo Professor Responsável da Ocorrência'
        elements.append(Paragraph(atendimento_gestao, styles['Normal']))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Sala e Tutor (informações adicionais)
        sala_tutor_text = f"<b>Sala:</b> {ocorrencia.get('sala_nome', 'N/A')}    <b>Tutor:</b> {ocorrencia.get('tutor_nome', 'N/A')}"
        elements.append(Paragraph(sala_tutor_text, styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))
        
        # Assinatura apenas para a última ocorrência
        if i == len(ocorrencias) - 1:
            elements.append(Paragraph("<b>Assinatura do Responsável: _____</b>", styles['Heading3']))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("<b>Data: _____ /_____/_____</b>", styles['Heading3']))
        else:
            elements.append(Spacer(1, 0.2 * inch))
    
    # Construir o PDF
    doc.build(elements)
    return buffer
    
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

# =============================================================
# FUNÇÕES DE FREQUÊNCIA UNIFICADA (mantidas)
# =============================================================

def salvar_frequencia_unificada(registros):
    """
    Espera lista de registros com chaves compatíveis com f_frequencia.
    """
    try:
        if not supabase:
            return False
        for registro in registros:
            resp = supabase.table('f_frequencia').select('*').eq('aluno_id', registro['aluno_id']).eq('data', registro['data']).execute()
            existing = handle_supabase_response(resp)
            if existing:
                supabase.table('f_frequencia').update({
                    'status': registro.get('status'),
                    'hora_entrada': registro.get('hora_entrada'),
                    'hora_saida': registro.get('hora_saida'),
                    'motivo_atraso': registro.get('motivo_atraso'),
                    'motivo_saida': registro.get('motivo_saida'),
                    'responsavel_nome': registro.get('responsavel_nome'),
                    'responsavel_telefone': registro.get('responsavel_telefone'),
                    'updated_at': datetime.now().isoformat()
                }).eq('id', existing[0]['id']).execute()
            else:
                insert_payload = {
                    **registro,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                supabase.table('f_frequencia').insert(insert_payload).execute()
        return True
    except Exception as e:
        logger.exception("Erro ao salvar frequência unificada")
        return False

def salvar_atraso_unificado(dados):
    try:
        if not supabase:
            return False
        resp = supabase.table('f_frequencia').select('*').eq('aluno_id', dados['aluno_id']).eq('data', dados['data']).execute()
        existing = handle_supabase_response(resp)
        registro_atualizado = {
            'aluno_id': dados['aluno_id'],
            'sala_id': dados.get('sala_id'),
            'data': dados['data'],
            'hora_entrada': dados.get('hora_entrada'),
            'motivo_atraso': dados.get('motivo_atraso'),
            'responsavel_nome': dados.get('responsavel_nome'),
            'responsavel_telefone': dados.get('responsavel_telefone'),
            'updated_at': datetime.now().isoformat()
        }
        if existing:
            status_atual = existing[0].get('status')
            if status_atual == 'PS':
                novo_status = 'PSA'
            else:
                novo_status = 'PA'
            registro_atualizado['status'] = novo_status
            supabase.table('f_frequencia').update(registro_atualizado).eq('id', existing[0]['id']).execute()
        else:
            registro_atualizado['status'] = 'PA'
            registro_atualizado['created_at'] = datetime.now().isoformat()
            supabase.table('f_frequencia').insert(registro_atualizado).execute()
        return True
    except Exception as e:
        logger.exception("Erro ao salvar atraso unificado")
        return False

def salvar_saida_unificado(dados):
    try:
        if not supabase:
            return False
        resp = supabase.table('f_frequencia').select('*').eq('aluno_id', dados['aluno_id']).eq('data', dados['data']).execute()
        existing = handle_supabase_response(resp)
        registro_atualizado = {
            'aluno_id': dados['aluno_id'],
            'sala_id': dados.get('sala_id'),
            'data': dados['data'],
            'hora_saida': dados.get('hora_saida'),
            'motivo_saida': dados.get('motivo_saida'),
            'responsavel_nome': dados.get('responsavel_nome'),
            'responsavel_telefone': dados.get('responsavel_telefone'),
            'updated_at': datetime.now().isoformat()
        }
        if existing:
            status_atual = existing[0].get('status')
            if status_atual == 'PA':
                novo_status = 'PSA'
            else:
                novo_status = 'PS'
            registro_atualizado['status'] = novo_status
            supabase.table('f_frequencia').update(registro_atualizado).eq('id', existing[0]['id']).execute()
        else:
            registro_atualizado['status'] = 'PS'
            registro_atualizado['created_at'] = datetime.now().isoformat()
            supabase.table('f_frequencia').insert(registro_atualizado).execute()
        return True
    except Exception as e:
        logger.exception("Erro ao salvar saida unificado")
        return False

# =============================================================
# APIS DE FREQUÊNCIA (rotas principais)
# =============================================================

@app.route('/api/salvar_frequencia', methods=['POST'])
def api_salvar_frequencia():
    try:
        dados = request.get_json()
        if not dados or not isinstance(dados, list):
            return jsonify({'error': 'Dados inválidos'}), 400
        success = salvar_frequencia_unificada(dados)
        if success:
            return jsonify({'success': True, 'message': f'Frequência de {len(dados)} alunos salva com sucesso'})
        else:
            return jsonify({'error': 'Erro ao salvar frequência'}), 500
    except Exception as e:
        logger.exception("Erro api_salvar_frequencia")
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_atraso', methods=['POST'])
def api_salvar_atraso():
    try:
        dados = request.get_json()
        campos_obrigatorios = ['aluno_id', 'sala_id', 'data', 'hora_entrada', 'motivo_atraso', 'responsavel_nome', 'responsavel_telefone']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400
        success = salvar_atraso_unificado(dados)
        if success:
            return jsonify({'success': True, 'message': 'Atraso registrado com sucesso'})
        else:
            return jsonify({'error': 'Erro ao salvar atraso'}), 500
    except Exception as e:
        logger.exception("Erro api_salvar_atraso")
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_saida_antecipada', methods=['POST'])
def api_salvar_saida_antecipada():
    try:
        dados = request.get_json()
        campos_obrigatorios = ['aluno_id', 'sala_id', 'data', 'hora_saida', 'motivo_saida', 'responsavel_nome', 'responsavel_telefone']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400
        success = salvar_saida_unificado(dados)
        if success:
            return jsonify({'success': True, 'message': 'Saída antecipada registrada com sucesso'})
        else:
            return jsonify({'error': 'Erro ao salvar saída antecipada'}), 500
    except Exception as e:
        logger.exception("Erro api_salvar_saida_antecipada")
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia_detalhes/<int:aluno_id>/<data>')
def api_frequencia_detalhes(aluno_id, data):
    try:
        if supabase:
            response = supabase.table('f_frequencia').select('*').eq('aluno_id', aluno_id).eq('data', data).execute()
            data_resp = handle_supabase_response(response)
            if data_resp:
                return jsonify(data_resp[0])
            else:
                return jsonify({'error': 'Registro não encontrado'}), 404
        return jsonify({'error': 'Supabase não configurado'}), 500
    except Exception as e:
        logger.exception("Erro api_frequencia_detalhes")
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia')
def api_frequencia():
    """
    Retorna frequência por sala e mês.
    Parâmetros:
    - sala (id)
    - mes (1-12 ou '01'..'12')
    """
    try:
        sala_id = request.args.get('sala')
        mes = request.args.get('mes')
        if not sala_id or not mes:
            return jsonify({'error': 'Sala e mês são obrigatórios'}), 400
        if supabase:
            alunos_response = supabase.table('d_alunos').select('*').eq('sala_id', sala_id).execute()
            alunos = handle_supabase_response(alunos_response)
            ano = datetime.now().year
            mes_str = str(mes).zfill(2)
            try:
                last_day = monthrange(ano, int(mes_str))[1]
            except Exception:
                last_day = 31
            data_inicio = f"{ano}-{mes_str}-01"
            data_fim = f"{ano}-{mes_str}-{last_day:02d}"
            frequencia_response = supabase.table('f_frequencia').select('*').eq('sala_id', sala_id).gte('data', data_inicio).lte('data', data_fim).execute()
            freq_list = handle_supabase_response(frequencia_response)
            dados = []
            for aluno in (alunos or []):
                aluno_data = {'id': aluno.get('id'), 'nome': aluno.get('nome'), 'frequencia': {}}
                freq_aluno = [f for f in (freq_list or []) if f.get('aluno_id') == aluno.get('id')]
                for freq in freq_aluno:
                    aluno_data['frequencia'][freq.get('data')] = {
                        'status': freq.get('status'),
                        'hora_entrada': freq.get('hora_entrada'),
                        'hora_saida': freq.get('hora_saida'),
                        'motivo_atraso': freq.get('motivo_atraso'),
                        'motivo_saida': freq.get('motivo_saida'),
                        'responsavel_nome': freq.get('responsavel_nome'),
                        'responsavel_telefone': freq.get('responsavel_telefone')
                    }
                dados.append(aluno_data)
            return jsonify(dados)
        return jsonify([])
    except Exception as e:
        logger.exception("Erro api_frequencia")
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia/status')
def api_frequencia_status_route():
    try:
        sala_id = request.args.get('sala_id')
        data = request.args.get('data')
        if supabase:
            response = supabase.table('f_frequencia').select('*').eq('sala_id', sala_id).eq('data', data).execute()
            resp_data = handle_supabase_response(response)
            frequencia_registrada = len(resp_data) > 0
        else:
            frequencia_registrada = False
        return jsonify({'registrada': frequencia_registrada, 'sala_id': sala_id, 'data': data})
    except Exception as e:
        logger.exception("Erro api_frequencia_status_route")
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










