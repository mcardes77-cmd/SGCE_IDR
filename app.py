# =============================================================
# APP UNIFICADO - GESTÃO ESCOLAR
# =============================================================

from flask import Flask, request, jsonify, render_template, Blueprint
from datetime import datetime
from calendar import monthrange
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import os
import time

# =============================================================
# CONFIGURAÇÃO E SUPABASE
# =============================================================

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL:
    logger.warning("SUPABASE_URL não encontrada nas variáveis de ambiente.")
if not SUPABASE_KEY:
    logger.warning("SUPABASE_KEY não encontrada nas variáveis de ambiente.")

_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL ou SUPABASE_KEY não configuradas.")
        return None

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Cliente Supabase inicializado com sucesso.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Erro ao inicializar Supabase: {e}")
        return None

def handle_supabase_response(response):
    if not response:
        return []
    if hasattr(response, 'data'):
        return response.data
    if isinstance(response, dict):
        return response.get('data', [])
    return []

supabase = get_supabase()

# =============================================================
# INICIALIZAÇÃO DO FLASK
# =============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')

# =============================================================
# ROTAS DE FREQUÊNCIA (UNIFICADAS)
# =============================================================

@app.route('/api/frequencia/status', methods=['GET'])
def api_frequencia_status():
    sala_id = request.args.get('sala_id')
    data = request.args.get('data')

    if not sala_id or not data:
        return jsonify({"error": "Parâmetros sala_id e data são obrigatórios."}), 400

    try:
        supabase = get_supabase()
        resp = supabase.table('f_frequencia').select('id').eq('sala_id', int(sala_id)).eq('data', data).execute()
        registrada = len(resp.data) > 0
        return jsonify({"registrada": registrada}), 200
    except Exception as e:
        logger.exception("Erro /api/frequencia/status")
        return jsonify({"error": str(e)}), 500

@app.route('/api/salvar_frequencia', methods=['POST'])
def api_salvar_frequencia():
    registros = request.json
    if not isinstance(registros, list) or not registros:
        return jsonify({"error": "O corpo da requisição deve ser uma lista não vazia de registros."}), 400

    try:
        supabase = get_supabase()
        primeiro = registros[0]
        sala_id = primeiro.get('sala_id')
        data = primeiro.get('data')

        if not sala_id or not data:
            return jsonify({"error": "Dados de sala e data obrigatórios."}), 400

        resp_status = supabase.table('f_frequencia').select('id').eq('sala_id', sala_id).eq('data', data).limit(1).execute()
        if len(resp_status.data) > 0:
            return jsonify({"error": "Frequência para esta sala e data já registrada."}), 409

        dados = []
        for reg in registros:
            if reg.get('status') in ['P', 'F']:
                dados.append({
                    'aluno_id': int(reg.get('aluno_id')),
                    'sala_id': int(reg.get('sala_id')),
                    'data': reg.get('data'),
                    'status': reg.get('status'),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                })

        if not dados:
            return jsonify({"error": "Nenhum registro P/F válido."}), 400

        response = supabase.table('f_frequencia').insert(dados).execute()
        handle_supabase_response(response)
        return jsonify({"message": f"Frequência de {len(dados)} alunos registrada."}), 201

    except Exception as e:
        logger.exception("Erro /api/salvar_frequencia")
        return jsonify({"error": str(e)}), 500

@app.route('/api/salvar_atraso', methods=['POST'])
def api_salvar_atraso():
    data_req = request.json
    aluno_id = data_req.get('aluno_id')
    sala_id = data_req.get('sala_id')
    data_dia = data_req.get('data')
    hora_atraso = data_req.get('hora_entrada')

    if not all([aluno_id, sala_id, data_dia, hora_atraso]):
        return jsonify({"error": "Campos obrigatórios ausentes."}), 400

    try:
        supabase = get_supabase()
        resp = supabase.table('f_frequencia').select('*').eq('aluno_id', aluno_id).eq('data', data_dia).execute()

        novo_status = 'PA'
        if resp.data:
            status_atual = resp.data[0]['status']
            if status_atual == 'PS':
                novo_status = 'PSA'
            supabase.table('f_frequencia').update({
                'status': novo_status,
                'hora_entrada': hora_atraso,
                'motivo_atraso': data_req.get('motivo_atraso'),
                'responsavel_nome': data_req.get('responsavel_nome'),
                'responsavel_telefone': data_req.get('responsavel_telefone'),
                'updated_at': datetime.now().isoformat()
            }).eq('id', resp.data[0]['id']).execute()
        else:
            supabase.table('f_frequencia').insert({
                'aluno_id': aluno_id,
                'sala_id': sala_id,
                'data': data_dia,
                'status': 'PA',
                'hora_entrada': hora_atraso,
                'motivo_atraso': data_req.get('motivo_atraso'),
                'responsavel_nome': data_req.get('responsavel_nome'),
                'responsavel_telefone': data_req.get('responsavel_telefone'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).execute()
        return jsonify({"message": "Atraso salvo com sucesso."}), 200
    except Exception as e:
        logger.exception("Erro /api/salvar_atraso")
        return jsonify({"error": str(e)}), 500

@app.route('/api/salvar_saida_antecipada', methods=['POST'])
def api_salvar_saida_antecipada():
    data_req = request.json
    aluno_id = data_req.get('aluno_id')
    sala_id = data_req.get('sala_id')
    data_dia = data_req.get('data')
    hora_saida = data_req.get('hora_saida')

    if not all([aluno_id, sala_id, data_dia, hora_saida]):
        return jsonify({"error": "Campos obrigatórios ausentes."}), 400

    try:
        supabase = get_supabase()
        resp = supabase.table('f_frequencia').select('*').eq('aluno_id', aluno_id).eq('data', data_dia).execute()

        novo_status = 'PS'
        if resp.data:
            status_atual = resp.data[0]['status']
            if status_atual == 'PA':
                novo_status = 'PSA'
            supabase.table('f_frequencia').update({
                'status': novo_status,
                'hora_saida': hora_saida,
                'motivo_saida': data_req.get('motivo_saida'),
                'responsavel_nome': data_req.get('responsavel_nome'),
                'responsavel_telefone': data_req.get('responsavel_telefone'),
                'updated_at': datetime.now().isoformat()
            }).eq('id', resp.data[0]['id']).execute()
        else:
            supabase.table('f_frequencia').insert({
                'aluno_id': aluno_id,
                'sala_id': sala_id,
                'data': data_dia,
                'status': 'PS',
                'hora_saida': hora_saida,
                'motivo_saida': data_req.get('motivo_saida'),
                'responsavel_nome': data_req.get('responsavel_nome'),
                'responsavel_telefone': data_req.get('responsavel_telefone'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).execute()
        return jsonify({"message": "Saída antecipada salva com sucesso."}), 200
    except Exception as e:
        logger.exception("Erro /api/salvar_saida_antecipada")
        return jsonify({"error": str(e)}), 500

@app.route('/api/frequencia', methods=['GET'])
def api_relatorio_frequencia():
    sala_id = request.args.get('sala')
    mes = request.args.get('mes')
    if not sala_id or not mes:
        return jsonify({"error": "Parâmetros sala e mes são obrigatórios."}), 400

    try:
        supabase = get_supabase()
        ano_atual = datetime.now().year
        _, num_dias = monthrange(ano_atual, int(mes))

        data_inicio = f"{ano_atual}-{str(mes).zfill(2)}-01"
        data_fim = f"{ano_atual}-{str(mes).zfill(2)}-{num_dias:02d}"

        resp_alunos = supabase.table('d_alunos').select('id, nome').eq('sala_id', sala_id).order('nome').execute()
        alunos = handle_supabase_response(resp_alunos)
        aluno_ids = [a['id'] for a in alunos]

        resp_freq = supabase.table('f_frequencia').select('aluno_id, data, status').in_('aluno_id', aluno_ids).gte('data', data_inicio).lte('data', data_fim).execute()
        registros = handle_supabase_response(resp_freq)

        freq_por_aluno = {}
        for r in registros:
            aluno_id = r['aluno_id']
            if aluno_id not in freq_por_aluno:
                freq_por_aluno[aluno_id] = {}
            freq_por_aluno[aluno_id][r['data']] = r['status']

        relatorio = [{"id": a['id'], "nome": a['nome'], "frequencia": freq_por_aluno.get(a['id'], {})} for a in alunos]
        return jsonify(relatorio), 200
    except Exception as e:
        logger.exception("Erro /api/frequencia")
        return jsonify({"error": str(e)}), 500

# =============================================================
# ROTA PRINCIPAL (HOME)
# =============================================================

@app.route('/')
def home():
    return render_template('index.html')

# =============================================================
# EXECUÇÃO
# =============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
