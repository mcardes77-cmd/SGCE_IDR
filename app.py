import os
from flask import Flask, request, jsonify, render_template, Response, send_file
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from supabase import create_client, Client
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-secret-key-producao')

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

def get_ocorrencias():
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('*').order('id', desc=True).execute()
            return response.data
        return []
    except Exception as e:
        print(f"Erro ao buscar ocorrências: {e}")
        return []

def get_ocorrencia_por_numero(numero):
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('*').eq('numero', numero).execute()
            return response.data[0] if response.data else None
        return None
    except Exception as e:
        print(f"Erro ao buscar ocorrência: {e}")
        return None

def salvar_ocorrencia(ocorrencia):
    try:
        if supabase:
            response = supabase.table('ocorrencias').insert(ocorrencia).execute()
            return response.data[0] if response.data else None
        return None
    except Exception as e:
        print(f"Erro ao salvar ocorrência: {e}")
        return None

def atualizar_ocorrencia(numero, dados):
    try:
        if supabase:
            response = supabase.table('ocorrencias').update(dados).eq('numero', numero).execute()
            return response.data[0] if response.data else None
        return None
    except Exception as e:
        print(f"Erro ao atualizar ocorrência: {e}")
        return None

def salvar_frequencia(registros):
    try:
        if not supabase:
            return False
            
        for registro in registros:
            # Verificar se já existe registro
            existing = supabase.table('frequencia')\
                .select('*')\
                .eq('aluno_id', registro['aluno_id'])\
                .eq('data', registro['data'])\
                .execute()
            
            if existing.data:
                supabase.table('frequencia')\
                    .update({'status': registro['status']})\
                    .eq('id', existing.data[0]['id'])\
                    .execute()
            else:
                supabase.table('frequencia').insert(registro).execute()
        
        return True
    except Exception as e:
        print(f"Erro ao salvar frequência: {e}")
        return False

def get_professores():
    try:
        if supabase:
            response = supabase.table('professores').select('*').execute()
            return response.data
        return []
    except Exception as e:
        print(f"Erro ao buscar professores: {e}")
        return []

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gestao_ocorrencia')
def gestao_ocorrencia():
    return render_template('gestao_ocorrencia.html')

@app.route('/gestao_ocorrencia_editar')
def gestao_ocorrencia_editar():
    ocorrencia_id = request.args.get('id', type=int)
    nivel = request.args.get('nivel', '')
    
    ocorrencia = get_ocorrencia_por_numero(str(ocorrencia_id))
    if not ocorrencia:
        return "Ocorrência não encontrada", 404
    
    return render_template('gestao_ocorrencia_editar.html', 
                         ocorrencia=ocorrencia, 
                         nivel=nivel)

@app.route('/gestao_ocorrencia_nova')
def gestao_ocorrencia_nova():
    return render_template('gestao_ocorrencia_nova.html')

@app.route('/gestao_ocorrencia_aberta')
def gestao_ocorrencia_aberta():
    return render_template('gestao_ocorrencia_aberta.html')

@app.route('/gestao_ocorrencia_finalizada')
def gestao_ocorrencia_finalizada():
    return render_template('gestao_ocorrencia_finalizada.html')

@app.route('/gestao_relatorio_impressao')
def gestao_relatorio_impressao():
    return render_template('gestao_relatorio_impressao.html')

# ========== ROTAS DE FREQUÊNCIA ==========

@app.route('/gestao_frequencia')
def gestao_frequencia():
    return render_template('gestao_frequencia.html')

@app.route('/gestao_frequencia_registro')
def gestao_frequencia_registro():
    return render_template('gestao_frequencia_registro.html')

@app.route('/gestao_frequencia_atraso')
def gestao_frequencia_atraso():
    return render_template('gestao_frequencia_atraso.html')

@app.route('/gestao_frequencia_saida')
def gestao_frequencia_saida():
    return render_template('gestao_frequencia_saida.html')

@app.route('/gestao_relatorio_frequencia')
def gestao_relatorio_frequencia():
    return render_template('gestao_relatorio_frequencia.html')

# ========== APIs PRINCIPAIS ==========

@app.route('/api/professores')
def api_professores():
    professores = get_professores()
    return jsonify(professores)

@app.route('/api/salas')
def api_salas():
    salas = get_salas()
    return jsonify(salas)

@app.route('/api/salas_com_ocorrencias')
def salas_com_ocorrencias():
    salas = get_salas()
    return jsonify(salas)

@app.route('/api/salas_por_professor/<int:professor_id>')
def salas_por_professor(professor_id):
    salas = get_salas()
    return jsonify(salas)

@app.route('/api/alunos_por_sala/<int:sala_id>')
def alunos_por_sala(sala_id):
    alunos = get_alunos_por_sala(sala_id)
    return jsonify(alunos)

@app.route('/api/tutor_por_aluno/<int:aluno_id>')
def tutor_por_aluno(aluno_id):
    alunos = get_alunos()
    aluno = next((a for a in alunos if a['id'] == aluno_id), None)
    if aluno:
        return jsonify({'tutor': aluno['tutor']})
    return jsonify({'tutor': ''})

@app.route('/api/tutores_com_ocorrencias')
def tutores_com_ocorrencias():
    try:
        if supabase:
            response = supabase.table('ocorrencias').select('tutor').execute()
            tutores = list(set([occ['tutor'] for occ in response.data]))
            return jsonify([{'id': i, 'nome': tutor} for i, tutor in enumerate(tutores)])
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocorrencias_todas')
def ocorrencias_todas():
    ocorrencias = get_ocorrencias()
    return jsonify(ocorrencias)

@app.route('/api/ocorrencias_filtrar')
def ocorrencias_filtrar():
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
        return jsonify(response.data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocorrencias_abertas')
def ocorrencias_abertas():
    try:
        if supabase:
            response = supabase.table('ocorrencias')\
                .select('*')\
                .in_('status', ['ATENDIMENTO', 'EM_ANDAMENTO'])\
                .execute()
            return jsonify(response.data)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocorrencias_finalizadas')
def ocorrencias_finalizadas():
    try:
        if supabase:
            response = supabase.table('ocorrencias')\
                .select('*')\
                .in_('status', ['FINALIZADA', 'ASSINADA'])\
                .execute()
            return jsonify(response.data)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ocorrencia_detalhes')
def ocorrencia_detalhes():
    try:
        numero = request.args.get('numero')
        
        if not numero:
            return jsonify({'error': 'Número da ocorrência não fornecido'}), 400
        
        ocorrencia = get_ocorrencia_por_numero(numero)
        if not ocorrencia:
            return jsonify({'error': f'Ocorrência {numero} não encontrada'}), 404
        
        return jsonify(ocorrencia)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alunos_com_ocorrencias_por_sala/<sala_id>')
def alunos_com_ocorrencias_por_sala(sala_id):
    alunos = get_alunos_por_sala(sala_id)
    return jsonify(alunos)

@app.route('/api/ocorrencias_por_aluno/<aluno_id>')
def ocorrencias_por_aluno(aluno_id):
    try:
        if supabase:
            alunos = get_alunos()
            aluno_nome = next((a['nome'] for a in alunos if str(a['id']) == str(aluno_id)), '')
            if aluno_nome:
                response = supabase.table('ocorrencias').select('*').eq('aluno', aluno_nome).execute()
                return jsonify(response.data)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== APIs DE FREQUÊNCIA ==========

@app.route('/api/frequencia/status')
def frequencia_status():
    try:
        sala_id = request.args.get('sala_id')
        data = request.args.get('data')
        
        if supabase:
            response = supabase.table('frequencia')\
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

@app.route('/api/salvar_frequencia', methods=['POST'])
def api_salvar_frequencia():
    try:
        dados = request.get_json()
        
        if not dados or not isinstance(dados, list):
            return jsonify({'error': 'Dados inválidos'}), 400

        success = salvar_frequencia(dados)
        
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
def salvar_atraso():
    try:
        dados = request.get_json()
        
        campos_obrigatorios = ['aluno_id', 'sala_id', 'data', 'hora_atraso', 'motivo_atraso', 'responsavel_atraso', 'telefone_atraso']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400

        if supabase:
            response = supabase.table('frequencia_atraso').insert(dados).execute()
            
            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Atraso registrado com sucesso'
                })
        
        return jsonify({'error': 'Erro ao salvar atraso'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_saida_antecipada', methods=['POST'])
def salvar_saida_antecipada():
    try:
        dados = request.get_json()
        
        campos_obrigatorios = ['aluno_id', 'sala_id', 'data', 'hora_saida', 'motivo_saida', 'responsavel_saida', 'telefone_saida']
        for campo in campos_obrigatorios:
            if not dados.get(campo):
                return jsonify({'error': f'Campo {campo} é obrigatório'}), 400

        if supabase:
            response = supabase.table('frequencia_saida').insert(dados).execute()
            
            if response.data:
                return jsonify({
                    'success': True,
                    'message': 'Saída antecipada registrada com sucesso'
                })
        
        return jsonify({'error': 'Erro ao salvar saída antecipada'}), 500
        
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
            
            frequencia_response = supabase.table('frequencia')\
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
                    aluno_data['frequencia'][freq['data']] = freq['status']
                
                dados.append(aluno_data)
            
            return jsonify(dados)
        
        return jsonify([])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/salvar_atendimento', methods=['POST'])
def salvar_atendimento():
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({'error': 'Dados não fornecidos'}), 400

        nivel = dados.get('nivel')
        numero_ocorrencia = dados.get('id')
        texto = dados.get('texto')

        if not nivel:
            return jsonify({'error': 'Nível de atendimento não especificado'}), 400
        if not numero_ocorrencia:
            return jsonify({'error': 'Número da ocorrência não especificado'}), 400

        nivel = nivel.lower().strip()
        niveis_validos = ['tutor', 'coordenacao', 'gestao']
        if nivel not in niveis_validos:
            return jsonify({'error': f"Nível de atendimento inválido. Use: {niveis_validos}"}), 400

        ocorrencia = get_ocorrencia_por_numero(str(numero_ocorrencia))
        if not ocorrencia:
            return jsonify({'error': f'Ocorrência {numero_ocorrencia} não encontrada'}), 404

        # Salvar o atendimento
        data_atual = datetime.now().strftime('%d/%m/%Y')
        hora_atual = datetime.now().strftime('%H:%M:%S')
        texto_formatado = f"{texto} (Atendido em {data_atual} às {hora_atual})"

        campo_atendimento = f"atendimento_{nivel}"
        dados_atualizacao = {
            campo_atendimento: texto_formatado,
            'data_atualizacao': datetime.now().strftime('%Y-%m-%d'),
            'hora_atualizacao': hora_atual
        }

        # Verificar se pode finalizar
        pendente_tutor = ocorrencia.get('solicitado_tutor') and not ocorrencia.get('atendimento_tutor')
        pendente_coord = ocorrencia.get('solicitado_coordenacao') and not ocorrencia.get('atendimento_coordenacao')
        pendente_gestao = ocorrencia.get('solicitado_gestao') and not ocorrencia.get('atendimento_gestao')

        todos_nao_pendentes = not (pendente_tutor or pendente_coord or pendente_gestao)
        status_anterior = str(ocorrencia.get('status', '')).upper()

        if todos_nao_pendentes and status_anterior in ['ATENDIMENTO', 'EM ATENDIMENTO', 'EM_ATENDIMENTO', 'EM-ATENDIMENTO', '']:
            dados_atualizacao['status'] = 'FINALIZADA'

        # Atualizar no banco
        atualizar_ocorrencia(str(numero_ocorrencia), dados_atualizacao)

        return jsonify({
            'success': True,
            'message': 'Atendimento salvo com sucesso',
            'status_atualizado': dados_atualizacao.get('status', ocorrencia.get('status')),
            'data_salvamento': data_atual,
            'nivel_processado': nivel
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/marcar_impressao', methods=['POST'])
def marcar_impressao():
    try:
        dados = request.get_json()
        numeros = dados.get('numeros', [])
        
        for numero in numeros:
            dados_atualizacao = {
                'impressao_pdf': True,
                'status': 'ASSINADA'
            }
            atualizar_ocorrencia(str(numero), dados_atualizacao)
        
        return jsonify({'success': True, 'message': f'{len(numeros)} ocorrências marcadas como impressas'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/registrar_ocorrencia', methods=['POST'])
def registrar_ocorrencia():
    try:
        dados = request.get_json()
        
        # Buscar último número
        ocorrencias = get_ocorrencias()
        ultimo_numero = max([int(occ['numero']) for occ in ocorrencias]) if ocorrencias else 0
        novo_numero = str(ultimo_numero + 1)
        
        aluno_id = dados.get('aluno_id')
        alunos = get_alunos()
        aluno = next((a for a in alunos if str(a['id']) == str(aluno_id)), None)
        
        if not aluno:
            return jsonify({'error': 'Aluno não encontrado'}), 400
        
        salas = get_salas()
        sala = next((s for s in salas if s['id'] == aluno['sala_id']), {})
        
        nova_ocorrencia = {
            'aluno': aluno['nome'],
            'aluno_nome': aluno['nome'],
            'sala': sala.get('nome', ''),
            'sala_nome': sala.get('nome', ''),
            'tutor': aluno['tutor'],
            'tutor_nome': aluno['tutor'],
            'numero': novo_numero,
            'data': datetime.now().strftime('%Y-%m-%d'),
            'data_hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hora': datetime.now().strftime('%H:%M:%S'),
            'professor': dados.get('professor_nome', ''),
            'professor_nome': dados.get('professor_nome', ''),
            'descricao': dados.get('descricao', ''),
            'atendimento_professor': dados.get('atendimento_professor', ''),
            'atendimento_tutor': '',
            'atendimento_coordenacao': '',
            'atendimento_gestao': '',
            'solicitado_tutor': dados.get('solicitar_tutor', False),
            'solicitado_coordenacao': dados.get('solicitar_coordenacao', False),
            'solicitado_gestao': dados.get('solicitar_gestao', False),
            'status': 'ATENDIMENTO',
            'tipo': 'Geral',
            'impressao_pdf': False
        }
        
        ocorrencia_salva = salvar_ocorrencia(nova_ocorrencia)
        
        if ocorrencia_salva:
            return jsonify({
                'success': True,
                'message': 'Ocorrência registrada com sucesso',
                'numero': novo_numero,
                'id': ocorrencia_salva['id']
            })
        else:
            return jsonify({'error': 'Erro ao salvar ocorrência'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== FUNÇÕES AUXILIARES ==========

def _quebrar_texto(texto, max_chars):
    if not texto:
        return ['']
    
    palavras = texto.split()
    linhas = []
    linha_atual = ""
    
    for palavra in palavras:
        if len(linha_atual + " " + palavra) <= max_chars:
            if linha_atual:
                linha_atual += " " + palavra
            else:
                linha_atual = palavra
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    
    if linha_atual:
        linhas.append(linha_atual)
    
    return linhas

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)