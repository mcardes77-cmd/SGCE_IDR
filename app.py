# app.py
from flask import Flask, render_template, Blueprint
import os
import logging
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from flask import Flask, render_template, Blueprint, request, jsonify

# --- Importa Blueprints de API ---
from routes_frequencia import frequencia_bp
from routes_tutoria import tutoria_bp
from routes_cadastro import cadastro_bp
from routes_aulas import aulas_bp
from routes_ocorrencias import ocorrencias_bp
from routes_tecnologia import tecnologia_bp 

# Carregar variáveis de ambiente
load_dotenv()

# Configuração
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
logging.basicConfig(level=logging.INFO)

# Configuração do Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

# Inicializar cliente Supabase
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("⚠️  AVISO: SUPABASE_URL ou SUPABASE_KEY não configurados")

# Funções para interagir com Supabase
def get_salas():
    try:
        if supabase:
            response = supabase.table('salas').select('*').execute()
            return response.data
        return []
    except Exception as e:
        print(f"Erro ao buscar salas: {e}")
        return []

def get_alunos():
    try:
        if supabase:
            response = supabase.table('alunos').select('*').execute()
            return response.data
        return []
    except Exception as e:
        print(f"Erro ao buscar alunos: {e}")
        return []

def get_alunos_por_sala(sala_id):
    try:
        if supabase:
            response = supabase.table('alunos').select('*').eq('sala_id', sala_id).execute()
            return response.data
        return []
    except Exception as e:
        print(f"Erro ao buscar alunos: {e}")
        return []

def get_professores():
    try:
        if supabase:
            response = supabase.table('professores').select('*').execute()
            return response.data
        return []
    except Exception as e:
        print(f"Erro ao buscar professores: {e}")
        return []

# =============================================
# FUNÇÕES DE FREQUÊNCIA UNIFICADA
# =============================================

def salvar_frequencia_unificada(registros):
    try:
        if not supabase:
            return False
            
        for registro in registros:
            # Verificar se já existe registro
            existing = supabase.table('f_frequencia')\
                .select('*')\
                .eq('aluno_id', registro['aluno_id'])\
                .eq('data', registro['data'])\
                .execute()
            
            if existing.data:
                supabase.table('f_frequencia')\
                    .update({
                        'status': registro['status'],
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('id', existing.data[0]['id'])\
                    .execute()
            else:
                supabase.table('f_frequencia').insert({
                    **registro,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }).execute()
        
        return True
    except Exception as e:
        print(f"Erro ao salvar frequência: {e}")
        return False

def salvar_atraso_unificado(dados):
    try:
        if not supabase:
            return False
            
        # Verificar se já existe registro
        existing = supabase.table('f_frequencia')\
            .select('*')\
            .eq('aluno_id', dados['aluno_id'])\
            .eq('data', dados['data'])\
            .execute()
        
        registro_atualizado = {
            'aluno_id': dados['aluno_id'],
            'sala_id': dados['sala_id'],
            'data': dados['data'],
            'hora_entrada': dados['hora_entrada'],
            'motivo_atraso': dados['motivo_atraso'],
            'responsavel_nome': dados['responsavel_nome'],
            'responsavel_telefone': dados['responsavel_telefone'],
            'updated_at': datetime.now().isoformat()
        }
        
        if existing.data:
            # Se já existe, atualizar
            status_atual = existing.data[0]['status']
            if status_atual == 'PS':
                novo_status = 'PSA'
            else:
                novo_status = 'PA'
            
            registro_atualizado['status'] = novo_status
            
            supabase.table('f_frequencia')\
                .update(registro_atualizado)\
                .eq('id', existing.data[0]['id'])\
                .execute()
        else:
            # Se não existe, criar novo
            registro_atualizado['status'] = 'PA'
            registro_atualizado['created_at'] = datetime.now().isoformat()
            
            supabase.table('f_frequencia')\
                .insert(registro_atualizado)\
                .execute()
        
        return True
    except Exception as e:
        print(f"Erro ao salvar atraso: {e}")
        return False

def salvar_saida_unificado(dados):
    try:
        if not supabase:
            return False
            
        # Verificar se já existe registro
        existing = supabase.table('f_frequencia')\
            .select('*')\
            .eq('aluno_id', dados['aluno_id'])\
            .eq('data', dados['data'])\
            .execute()
        
        registro_atualizado = {
            'aluno_id': dados['aluno_id'],
            'sala_id': dados['sala_id'],
            'data': dados['data'],
            'hora_saida': dados['hora_saida'],
            'motivo_saida': dados['motivo_saida'],
            'responsavel_nome': dados['responsavel_nome'],
            'responsavel_telefone': dados['responsavel_telefone'],
            'updated_at': datetime.now().isoformat()
        }
        
        if existing.data:
            # Se já existe, atualizar
            status_atual = existing.data[0]['status']
            if status_atual == 'PA':
                novo_status = 'PSA'
            else:
                novo_status = 'PS'
            
            registro_atualizado['status'] = novo_status
            
            supabase.table('f_frequencia')\
                .update(registro_atualizado)\
                .eq('id', existing.data[0]['id'])\
                .execute()
        else:
            # Se não existe, criar novo
            registro_atualizado['status'] = 'PS'
            registro_atualizado['created_at'] = datetime.now().isoformat()
            
            supabase.table('f_frequencia')\
                .insert(registro_atualizado)\
                .execute()
        
        return True
    except Exception as e:
        print(f"Erro ao salvar saída: {e}")
        return False

# =============================================
# APIs DE FREQUÊNCIA UNIFICADA
# =============================================

@app.route('/api/salvar_frequencia', methods=['POST'])
def api_salvar_frequencia():
    try:
        dados = request.get_json()
        
        if not dados or not isinstance(dados, list):
            return jsonify({'error': 'Dados inválidos'}), 400

        success = salvar_frequencia_unificada(dados)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Frequência de {len(dados)} alunos salva com sucesso'
            })
        else:
            return jsonify({'error': 'Erro ao salvar frequência'}), 500

    except Exception as e:
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
            return jsonify({
                'success': True,
                'message': 'Atraso registrado com sucesso'
            })
        else:
            return jsonify({'error': 'Erro ao salvar atraso'}), 500
        
    except Exception as e:
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
            return jsonify({
                'success': True,
                'message': 'Saída antecipada registrada com sucesso'
            })
        else:
            return jsonify({'error': 'Erro ao salvar saída antecipada'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia_detalhes/<int:aluno_id>/<data>')
def api_frequencia_detalhes(aluno_id, data):
    try:
        if supabase:
            response = supabase.table('f_frequencia')\
                .select('*')\
                .eq('aluno_id', aluno_id)\
                .eq('data', data)\
                .execute()
            
            if response.data:
                return jsonify(response.data[0])
            else:
                return jsonify({'error': 'Registro não encontrado'}), 404
        return jsonify({'error': 'Supabase não configurado'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia')
def api_frequencia():
    try:
        sala_id = request.args.get('sala')
        mes = request.args.get('mes')
        
        if not sala_id or not mes:
            return jsonify({'error': 'Sala e mês são obrigatórios'}), 400

        if supabase:
            # Buscar alunos da sala
            alunos_response = supabase.table('alunos').select('*').eq('sala_id', sala_id).execute()
            alunos = alunos_response.data
            
            # Buscar frequência do mês
            ano = datetime.now().year
            data_inicio = f"{ano}-{mes:0>2}-01"
            data_fim = f"{ano}-{mes:0>2}-31"
            
            frequencia_response = supabase.table('f_frequencia')\
                .select('*')\
                .eq('sala_id', sala_id)\
                .gte('data', data_inicio)\
                .lte('data', data_fim)\
                .execute()
            
            # Organizar dados
            dados = []
            for aluno in alunos:
                aluno_data = {
                    'id': aluno['id'],
                    'nome': aluno['nome'],
                    'frequencia': {}
                }
                
                # Buscar frequência do aluno
                freq_aluno = [f for f in frequencia_response.data if f['aluno_id'] == aluno['id']]
                for freq in freq_aluno:
                    aluno_data['frequencia'][freq['data']] = {
                        'status': freq['status'],
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequencia/status')
def api_frequencia_status():
    try:
        sala_id = request.args.get('sala_id')
        data = request.args.get('data')
        
        if supabase:
            response = supabase.table('f_frequencia')\
                .select('*')\
                .eq('sala_id', sala_id)\
                .eq('data', data)\
                .execute()
            
            frequencia_registrada = len(response.data) > 0
        else:
            frequencia_registrada = False
        
        return jsonify({
            'registrada': frequencia_registrada,
            'sala_id': sala_id,
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================
# OUTRAS APIs
# =============================================

@app.route('/api/professores')
def api_professores():
    professores = get_professores()
    return jsonify(professores)

@app.route('/api/salas')
def api_salas():
    salas = get_salas()
    return jsonify(salas)

@app.route('/api/alunos_por_sala/<int:sala_id>')
def api_alunos_por_sala(sala_id):
    alunos = get_alunos_por_sala(sala_id)
    return jsonify(alunos)

# --- 1. Definição do Blueprint Principal ---
main_bp = Blueprint('main', __name__)

# Rota principal (Menu Inicial)
@main_bp.route('/')
def home():
    return render_template('index.html')

# ===============================================
# ROTAS DO MÓDULO DE OCORRÊNCIAS
# ===============================================

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

# ===============================================
# ROTAS EXISTENTES (MANTIDAS)
# ===============================================

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

# ===============================================
# ROTAS CORRIGIDAS (PARA O index.html)
# ===============================================

@main_bp.route('/gestao_tecnologia')
def gestao_tecnologia():
    return render_template('gestao_tecnologia.html')

@main_bp.route('/gestao_aulas_menu')
def gestao_aulas_menu():
    return render_template('gestao_aulas.html')

# ===============================================
# ROTAS DO MÓDULO DE TECNOLOGIA
# ===============================================

@main_bp.route('/gestao_tecnologia_agendamento')
def gestao_tecnologia_agendamento():
    return render_template('gestao_tecnologia_agendamento.html')

@main_bp.route('/gestao_tecnologia_historico')
def gestao_tecnologia_historico():
    return render_template('gestao_tecnologia_historico.html')

@main_bp.route('/gestao_tecnologia_ocorrencia')
def gestao_tecnologia_ocorrencia():
    return render_template('gestao_tecnologia_ocorrencia.html')

# ===============================================
# 3. REGISTRO DOS BLUEPRINTS
# ===============================================

app.register_blueprint(main_bp, url_prefix='/')
app.register_blueprint(frequencia_bp, url_prefix='/api')
app.register_blueprint(tutoria_bp, url_prefix='/api') 
app.register_blueprint(cadastro_bp, url_prefix='/api')
app.register_blueprint(aulas_bp, url_prefix='/api')
app.register_blueprint(ocorrencias_bp, url_prefix='/api')
app.register_blueprint(tecnologia_bp, url_prefix='/api')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
