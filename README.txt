Substitua no GitHub:
- app.py
- templates/gestao_ocorrencia.html
- templates/gestao_ocorrencia_editar.html

No Supabase, execute se ainda nao fez:
alter table ocorrencias add column if not exists atendimento_responsavel text;
alter table ocorrencias add column if not exists solicitado_responsavel boolean default false;
