# =============================================================
# APP UNIFICADO - GESTÃO ESCOLAR
# Conteúdo: merge completo de app.py + db_utils.py + routes_frequencia.py
# Ajustes: utiliza apenas d_alunos; f_frequencia; ocorrencias identificadas por numero
# CORRIGIDO: coluna tutor_nome em vez de tutor
# =============================================================

from flask import Flask, render_template, Blueprint, request, jsonify
import os
import logging
import time
from datetime import datetime, date
from calendar import monthrange
from supabase import create_client
from dotenv import load_dotenv
import psycopg2

# -----------------------------
# Carregar .env
# -----------------------------
load_dotenv()

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Supabase
# -----------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

_supabase_client = None

def _init_supabase_client(retries=3, backoff=1.0):
    global _supabase_client
    if _supabase_client:
        return _supabase_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL ou SUPABASE_KEY ausentes.")
        return None
    for attempt in range(1, retries + 1):
        try:
            _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
            try:
                _supabase_client.table('d_funcionarios').select('*').limit(1).execute()
            except:
                pass
            return _supabase_client
        except Exception as e:
            logger.error(f"Falha ao criar client Supabase (tentativa {attempt}): {e}")
            if attempt < retries:
                time.sleep(backoff * attempt)
            else:
                return None

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = _init_supabase_client()
    return _supabase_client

def handle_supabase_response(response):
    try:
        if response is None:
            raise Exception("Resposta Supabase é None.")
        if hasattr(response, "error") and response.error:
            raise Exception(f"Erro Postgrest: {response.error}")
        if hasattr(response, "data"):
            return response.data
        if isinstance(response, dict):
            if response.get("error"):
                raise Exception(f"Erro Postgrest: {response['error']}")
            return response.get("data", response)
        return response
    except Exception:
        logger.exception("Erro ao tratar resposta Supabase.")
        raise

# -----------------------------
# Helpers
# -----------------------------
def _to_bool(value):
    if isinstance(value, bool): return value
    if isinstance(value, (int, float)): return bool(value)
    if isinstance(value, str): return value.lower() in ('true', '1', 'yes', 'sim', 's', 'y')
    return False

def formatar_data_hora(data_hora_str):
    if not data_hora_str: return ""
    try:
        dt = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return data_hora_str

def safe_pdf_text(texto):
    if not texto: return ""
    return str(texto).replace('°', 'º').replace('ª', 'a').replace('º', 'o')

def get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT", 5432)
    )

# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
supabase = get_supabase()
main_bp = Blueprint('main', __name__)

# -----------------------------
# Funções de consulta
# -----------------------------
def get_salas():
    try:
        if supabase:
            return handle_supabase_response(supabase.table('salas').select('*').execute())
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar salas: {e}")
        return []

def get_d_alunos():
    try:
        if supabase:
            return handle_supabase_response(supabase.table('d_alunos').select('*').execute())
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar d_alunos: {e}")
        return []

def get_ocorrencias():
    try:
        if supabase:
            return handle_supabase_response(supabase.table('ocorrencias').select('*').order('numero', desc=True).execute())
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar ocorrências: {e}")
        return []

def get_ocorrencia_por_numero(numero):
    try:
        if supabase:
            # CORREÇÃO: Buscar ocorrência com dados do aluno incluindo tutor_nome
            data = handle_supabase_response(
                supabase.table('ocorrencias')
                .select('*, d_alunos(nome, sala_id, tutor_nome)')
                .eq('numero', numero)
                .execute()
            )
            return data[0] if data else None
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar ocorrência: {e}")
        return None

def get_ocorrencias_completas():
    try:
        if supabase:
            # CORREÇÃO: Buscar ocorrências com dados relacionados incluindo tutor_nome
            response = supabase.table('ocorrencias').select('*, d_alunos(nome, sala_id, tutor_nome)').order('numero', desc=True).execute()
            return handle_supabase_response(response)
        return []
    except Exception as e:
        logger.error(f"Erro ao buscar ocorrências completas: {e}")
        return []

# -----------------------------
# Frequência unificada
# -----------------------------
def salvar_frequencia_unificada(registros):
    try:
        if not supabase: return False
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
                supabase.table('f_frequencia').insert({**registro,'created_at':datetime.now().isoformat(),'updated_at':datetime.now().isoformat()}).execute()
        return True
    except Exception as e:
        logger.exception("Erro ao salvar frequência unificada")
        return False

def salvar_atraso_unificado(dados):
    try:
        if not supabase: return False
        resp = supabase.table('f_frequencia').select('*').eq('aluno_id', dados['aluno_id']).eq('data', dados['data']).execute()
        existing = handle_supabase_response(resp)
        registro = {**dados,'updated_at': datetime.now().isoformat()}
        if existing:
            status_atual = existing[0].get('status')
            registro['status'] = 'PSA' if status_atual=='PS' else 'PA'
            supabase.table('f_frequencia').update(registro).eq('id', existing[0]['id']).execute()
        else:
            registro['status'] = 'PA'
            registro['created_at'] = datetime.now().isoformat()
            supabase.table('f_frequencia').insert(registro).execute()
        return True
    except Exception as e:
        logger.exception("Erro ao salvar atraso")
        return False

def salvar_saida_unificado(dados):
    try:
        if not supabase: return False
        resp = supabase.table('f_frequencia').select('*').eq('aluno_id', dados['aluno_id']).eq('data', dados['data']).execute()
        existing = handle_supabase_response(resp)
        registro = {**dados,'updated_at': datetime.now().isoformat()}
        if existing:
            status_atual = existing[0].get('status')
            registro['status'] = 'PSA' if status_atual=='PA' else 'PS'
            supabase.table('f_frequencia').update(registro).eq('id', existing[0]['id']).execute()
        else:
            registro['status'] = 'PS'
            registro['created_at'] = datetime.now().isoformat()
            supabase.table('f_frequencia').insert(registro).execute()
        return True
    except Exception as e:
        logger.exception("Erro ao salvar saída")
        return False

# -----------------------------
# APIs Frequência
# -----------------------------
@app.route('/api/salvar_frequencia', methods=['POST'])
def api_salvar_frequencia():
    try:
        dados = request.get_json()
        if not dados or not isinstance(dados,list): return jsonify({'error':'Dados inválidos'}),400
        success = salvar_frequencia_unificada(dados)
        return jsonify({'success': success})
    except Exception as e:
        logger.exception("Erro api_salvar_frequencia")
        return jsonify({'error': str(e)}),500

@app.route('/api/salvar_atraso', methods=['POST'])
def api_salvar_atraso():
    try:
        dados = request.get_json()
        success = salvar_atraso_unificado(dados)
        return jsonify({'success': success})
    except Exception as e:
        logger.exception("Erro api_salvar_atraso")
        return jsonify({'error': str(e)}),500

@app.route('/api/salvar_saida_antecipada', methods=['POST'])
def api_salvar_saida_antecipada():
    try:
        dados = request.get_json()
        success = salvar_saida_unificado(dados)
        return jsonify({'success': success})
    except Exception as e:
        logger.exception("Erro api_salvar_saida_antecipada")
        return jsonify({'error': str(e)}),500

# -----------------------------
# APIs Ocorrências
# -----------------------------
@app.route('/api/registrar_ocorrencia', methods=['POST'])
def api_registrar_ocorrencia():
    try:
        data = request.get_json()
        aluno_id = data.get('aluno_id')
        
        # CORREÇÃO: Buscar dados do aluno com a coluna correta tutor_nome
        response_aluno = supabase.table('d_alunos').select('nome, sala_id, tutor_nome').eq('id', aluno_id).execute()
        
        if not response_aluno.data:
            return jsonify({'error': 'Aluno não encontrado'}), 404
            
        aluno_data = response_aluno.data[0]
        
        # Preparar dados da ocorrência
        ocorrencia_data = {
            'aluno_id': aluno_id,
            'aluno_nome': aluno_data['nome'],
            'sala_id': aluno_data['sala_id'],
            'tutor_nome': aluno_data.get('tutor_nome'),  # CORREÇÃO: usar tutor_nome
            'data_ocorrencia': data.get('data_ocorrencia', datetime.now().isoformat()),
            'tipo': data.get('tipo'),
            'descricao': data.get('descricao'),
            'gravidade': data.get('gravidade'),
            'status': 'aberta',
            'registrado_por': data.get('registrado_por'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Inserir ocorrência
        response = supabase.table('ocorrencias').insert(ocorrencia_data).execute()
        
        if hasattr(response, 'error') and response.error:
            return jsonify({'error': f'Erro ao salvar ocorrência: {response.error}'}), 500
            
        return jsonify({'success': True, 'message': 'Ocorrência registrada com sucesso'})
        
    except Exception as e:
        logger.error(f'Erro ao registrar ocorrência: {str(e)}')
        return jsonify({'error': 'Erro interno do servidor'}), 500

@app.route('/api/ocorrencia/<int:numero>', methods=['GET'])
def api_buscar_ocorrencia(numero):
    try:
        ocorrencia = get_ocorrencia_por_numero(numero)
        if not ocorrencia: return jsonify({'error': f'Ocorrência #{numero} não encontrada'}),404
        return jsonify(ocorrencia)
    except Exception as e:
        logger.exception("Erro ao buscar ocorrência")
        return jsonify({'error': str(e)}),500

@app.route('/api/ocorrencias_todas', methods=['GET'])
def api_ocorrencias_todas():
    try:
        # Usar a função corrigida que inclui tutor_nome
        ocorrencias = get_ocorrencias_completas()
        return jsonify(ocorrencias)
    except Exception as e:
        logger.error(f"Erro ao buscar todas ocorrências: {e}")
        return jsonify({'error': str(e)}),500

@app.route('/api/salas_com_ocorrencias', methods=['GET'])
def api_salas_com_ocorrencias():
    try:
        if supabase:
            # Buscar salas que têm ocorrências
            response = supabase.table('ocorrencias').select('sala_id').execute()
            salas_ids = list(set([oc['sala_id'] for oc in response.data]))
            return jsonify(salas_ids)
        return jsonify([])
    except Exception as e:
        logger.error(f"Erro ao buscar salas com ocorrências: {e}")
        return jsonify({'error': str(e)}),500

@app.route('/api/tutores_com_ocorrencias', methods=['GET'])
def api_tutores_com_ocorrencias():
    try:
        if supabase:
            # CORREÇÃO: Buscar tutor_nome das ocorrências
            response = supabase.table('ocorrencias').select('tutor_nome').execute()
            tutores = list(set([oc['tutor_nome'] for oc in response.data if oc.get('tutor_nome')]))
            return jsonify(tutores)
        return jsonify([])
    except Exception as e:
        logger.error(f"Erro ao buscar tutores com ocorrências: {e}")
        return jsonify({'error': str(e)}),500

@app.route('/api/aluno/<int:aluno_id>', methods=['GET'])
def api_buscar_aluno(aluno_id):
    try:
        # CORREÇÃO: Incluir tutor_nome na busca
        response = supabase.table('d_alunos').select('id, nome, sala_id, tutor_nome').eq('id', aluno_id).execute()
        
        if not response.data:
            return jsonify({'error': 'Aluno não encontrado'}), 404
            
        aluno_data = response.data[0]
        return jsonify(aluno_data)
        
    except Exception as e:
        logger.error(f"Erro ao buscar aluno: {e}")
        return jsonify({'error': str(e)}),500

@app.route('/api/alunos', methods=['GET'])
def api_listar_alunos():
    try:
        # CORREÇÃO: Incluir tutor_nome na listagem
        response = supabase.table('d_alunos').select('id, nome, sala_id, tutor_nome').order('nome').execute()
        return jsonify(response.data if response.data else [])
    except Exception as e:
        logger.error(f"Erro ao listar alunos: {e}")
        return jsonify({'error': str(e)}),500

MAPA_ATENDIMENTO = {
    "tutor": ("atendimento_tutor","dt_atendimento_tutor"),
    "coordenacao": ("atendimento_coordenacao","dt_atendimento_coordenacao"),
    "gestao": ("atendimento_gestao","dt_atendimento_gestao")
}

@app.route("/api/salvar_atendimento", methods=["POST"])
def salvar_atendimento():
    data = request.json
    numero = data.get("numero")
    nivel = data.get("nivel")
    texto = data.get("texto")
    if not (numero and nivel and texto): return jsonify({"success":False,"error":"Parâmetros incompletos"}),400
    if nivel not in MAPA_ATENDIMENTO: return jsonify({"success":False,"error":"Nível inválido"}),400
    campo_texto, campo_data = MAPA_ATENDIMENTO[nivel]
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"UPDATE ocorrencias SET {campo_texto}=%s, {campo_data}=%s WHERE numero=%s",(texto,date.today(),numero))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success":True})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}),500

# -----------------------------
# Blueprint HTML
# -----------------------------
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

# Registrar Blueprint
app.register_blueprint(main_bp)

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
