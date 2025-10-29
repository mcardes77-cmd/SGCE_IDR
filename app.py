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
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime, timedelta

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
        
# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route('/gestao_frequencia')
def gestao_frequencia():
    """Página de gestão de frequência"""
    return render_template('gestao_frequencia.html')

@app.route('/gestao_ocorrencia')
def gestao_ocorrencia():
    """Página de gestão de ocorrência"""
    return render_template('gestao_ocorrencia.html')

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
            return jsonify({
                "success": False, 
                "error": "Dados obrigatórios faltando",
                "redirect": False
            }), 400

        # VERIFICAÇÃO DE DUPLICAÇÃO - Prevenir múltiplos cliques
        cinco_minutos_atras = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
        verificacao = supabase.table("ocorrencias")\
            .select("numero")\
            .eq("aluno_id", aluno_id)\
            .eq("professor_id", professor_id)\
            .gte("data_hora", cinco_minutos_atras)\
            .execute()
            
        if verificacao.data:
            return jsonify({
                "success": False, 
                "error": "Uma ocorrência similar foi registrada recentemente. Aguarde alguns minutos antes de tentar novamente.",
                "redirect": False
            }), 400

        # Buscar informações do aluno para obter nome e sala
        resp_aluno = supabase.table("d_alunos").select("nome, sala_id, sala_nome, tutor_nome").eq("id", aluno_id).execute()
        if not resp_aluno.data:
            return jsonify({
                "success": False, 
                "error": "Aluno não encontrado",
                "redirect": False
            }), 404
        
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
                "data": data[0],
                "redirect": True,
                "redirect_url": "/gestao_ocorrencia",
                "message": f"Ocorrência #{proximo_numero} registrada com sucesso!"
            })
        else:
            return jsonify({
                "success": False, 
                "error": "Nenhum dado retornado",
                "redirect": False
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e),
            "redirect": False
        }), 500
        
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

@app.route('/api/salas', methods=['GET'])
def get_salas():
    """Busca todas as salas disponíveis"""
    try:
        response = supabase.table('d_alunos')\
            .select('sala_id, sala_nome')\
            .not_('sala_id', 'is', None)\
            .execute()
        
        # Remover duplicatas
        salas_unicas = []
        ids_vistos = set()
        
        for item in response.data:
            if item['sala_id'] and item['sala_id'] not in ids_vistos:
                ids_vistos.add(item['sala_id'])
                salas_unicas.append({
                    'id': item['sala_id'],
                    'nome': item['sala_nome']
                })
        
        return jsonify(salas_unicas)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos/<int:sala_id>', methods=['GET'])
def get_alunos_por_sala(sala_id):
    """Busca alunos por sala"""
    try:
        response = supabase.table('d_alunos')\
            .select('id, aluno_nome, sala_nome')\
            .eq('sala_id', sala_id)\
            .execute()
        
        return jsonify(response.data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia/verificar', methods=['POST'])
def verificar_frequencia():
    """Verifica se frequência já foi registrada para uma sala e data"""
    try:
        data = request.json
        sala_id = data.get('sala_id')
        data_frequencia = data.get('data')
        
        # Primeiro busca alunos da sala
        alunos_response = supabase.table('d_alunos')\
            .select('aluno_nome')\
            .eq('sala_id', sala_id)\
            .execute()
        
        if not alunos_response.data:
            return jsonify({'registrada': False})
        
        aluno_nomes = [aluno['aluno_nome'] for aluno in alunos_response.data]
        
        # Verifica se existe frequência registrada
        frequencia_response = supabase.table('f_frequencia')\
            .select('id')\
            .in_('aluno_nome', aluno_nomes)\
            .eq('data', data_frequencia)\
            .limit(1)\
            .execute()
        
        registrada = len(frequencia_response.data) > 0
        return jsonify({'registrada': registrada})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia/salvar', methods=['POST'])
def salvar_frequencia():
    """Salva registro de frequência"""
    try:
        data = request.json
        registros = data.get('registros', [])
        
        response = supabase.table('f_frequencia')\
            .upsert(registros)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Frequência salva com sucesso!',
            'data': response.data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/atraso/salvar', methods=['POST'])
def salvar_atraso():
    """Registra atraso de aluno"""
    try:
        dados = request.json
        
        # Busca dados do aluno
        aluno_response = supabase.table('d_alunos')\
            .select('aluno_nome, sala_nome')\
            .eq('id', dados['aluno_id'])\
            .execute()
        
        if not aluno_response.data:
            return jsonify({'success': False, 'error': 'Aluno não encontrado'}), 404
        
        aluno = aluno_response.data[0]
        
        # Salva/atualiza na f_frequencia
        registro_atraso = {
            'aluno_nome': aluno['aluno_nome'],
            'sala_nome': aluno['sala_nome'],
            'data': dados['data'],
            'status': 'PA',  # Presença com Atraso
            'hora_entrada': dados['hora_entrada'],
            'motivo_atraso': dados['motivo_atraso'],
            'responsavel_nome': dados['responsavel_nome'],
            'responsavel_telefone': dados['responsavel_telefone'],
            'updated_at': datetime.now().isoformat()
        }
        
        response = supabase.table('f_frequencia')\
            .upsert(registro_atraso)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Atraso registrado com sucesso!',
            'data': response.data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/saida/salvar', methods=['POST'])
def salvar_saida():
    """Registra saída antecipada"""
    try:
        dados = request.json
        
        # Busca dados do aluno
        aluno_response = supabase.table('d_alunos')\
            .select('aluno_nome, sala_nome')\
            .eq('id', dados['aluno_id'])\
            .execute()
        
        if not aluno_response.data:
            return jsonify({'success': False, 'error': 'Aluno não encontrado'}), 404
        
        aluno = aluno_response.data[0]
        
        # Busca registro existente para determinar status
        frequencia_existente = supabase.table('f_frequencia')\
            .select('status')\
            .eq('aluno_nome', aluno['aluno_nome'])\
            .eq('data', dados['data'])\
            .execute()
        
        status = 'PS'  # Presença com Saída Antecipada
        
        # Se já tiver atraso, atualiza para PSA
        if frequencia_existente.data and frequencia_existente.data[0]['status'] == 'PA':
            status = 'PSA'
        
        # Salva/atualiza na f_frequencia
        registro_saida = {
            'aluno_nome': aluno['aluno_nome'],
            'sala_nome': aluno['sala_nome'],
            'data': dados['data'],
            'status': status,
            'hora_saida': dados['hora_saida'],
            'motivo_saida': dados['motivo_saida'],
            'responsavel_nome': dados['responsavel_nome'],
            'responsavel_telefone': dados['responsavel_telefone'],
            'updated_at': datetime.now().isoformat()
        }
        
        response = supabase.table('f_frequencia')\
            .upsert(registro_saida)\
            .execute()
        
        return jsonify({
            'success': True,
            'message': 'Saída antecipada registrada com sucesso!',
            'data': response.data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorio/mensal', methods=['POST'])
def relatorio_mensal():
    """Gera relatório mensal de frequência"""
    try:
        data = request.json
        sala_id = data.get('sala_id')
        mes = data.get('mes')
        
        ano = datetime.now().year
        data_inicio = f"{ano}-{mes:02d}-01"
        data_fim = f"{ano}-{mes:02d}-{28 if mes == 2 else 30}"  # Aproximação
        
        # Carrega alunos da sala
        alunos_response = supabase.table('d_alunos')\
            .select('id, aluno_nome')\
            .eq('sala_id', sala_id)\
            .execute()
        
        if not alunos_response.data:
            return jsonify([])
        
        aluno_nomes = [aluno['aluno_nome'] for aluno in alunos_response.data]
        
        # Carrega frequência do período
        frequencia_response = supabase.table('f_frequencia')\
            .select('*')\
            .in_('aluno_nome', aluno_nomes)\
            .gte('data', data_inicio)\
            .lte('data', data_fim)\
            .execute()
        
        # Processa os dados para o formato do relatório
        relatorio = []
        for aluno in alunos_response.data:
            frequencia_aluno = {}
            
            # Filtra frequência do aluno
            freq_aluno = [f for f in frequencia_response.data if f['aluno_nome'] == aluno['aluno_nome']]
            
            for freq in freq_aluno:
                frequencia_aluno[freq['data']] = {
                    'status': freq.get('status', ''),
                    'hora_entrada': freq.get('hora_entrada'),
                    'hora_saida': freq.get('hora_saida'),
                    'motivo_atraso': freq.get('motivo_atraso'),
                    'motivo_saida': freq.get('motivo_saida'),
                    'responsavel_nome': freq.get('responsavel_nome'),
                    'responsavel_telefone': freq.get('responsavel_telefone')
                }
            
            relatorio.append({
                'id': aluno['id'],
                'nome': aluno['aluno_nome'],
                'frequencia': frequencia_aluno
            })
        
        return jsonify(relatorio)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia/detalhes', methods=['POST'])
def detalhes_frequencia():
    """Busca detalhes específicos da frequência"""
    try:
        data = request.json
        aluno_id = data.get('aluno_id')
        data_frequencia = data.get('data')
        
        # Busca nome do aluno
        aluno_response = supabase.table('d_alunos')\
            .select('aluno_nome')\
            .eq('id', aluno_id)\
            .execute()
        
        if not aluno_response.data:
            return jsonify({})
        
        aluno_nome = aluno_response.data[0]['aluno_nome']
        
        # Busca detalhes da frequência
        frequencia_response = supabase.table('f_frequencia')\
            .select('*')\
            .eq('aluno_nome', aluno_nome)\
            .eq('data', data_frequencia)\
            .execute()
        
        if frequencia_response.data:
            return jsonify(frequencia_response.data[0])
        else:
            return jsonify({})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================
# Execução
# =============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

