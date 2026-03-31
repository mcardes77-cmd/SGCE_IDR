PACOTE FINAL PARA SUBIR HOJE - SGCE

Conteúdo principal:
- app.py unificado
- 01_sql_supabase_completo.sql
- templates com login por usuário, primeiro acesso, dashboard, relatórios, cadastro, frequência e tutoria
- relatorio_ocorrencias_pdf.html em retrato e sem quebrar ocorrência no meio

IMPORTANTE:
1. Execute 01_sql_supabase_completo.sql no Supabase
2. Faça backup do seu projeto atual
3. Substitua o app.py
4. Copie os arquivos da pasta templates
5. Reinicie a aplicação

Fluxo de login:
- Primeiro acesso: /primeiro_acesso
- O funcionário escolhe o nome na lista, cria usuário e senha
- Depois que ativa, o nome sai da lista
- Próximos acessos: /login com usuário + senha

Decisões ativas neste pacote:
- Página inicial continua: /dashboard_ocorrencias
- /dashboard_geral fica ativo para testes
- Dashboard de ocorrências com gráfico semanal corrigido para bater com o ranking da semana
- PDF de impressão em retrato e sem quebrar a ocorrência no meio

Atenção:
- Como o template original de gestao_ocorrencia.html não estava disponível neste pacote, o ajuste do filtro de tutor foi entregue no arquivo:
  PATCH_filtro_tutor_gestao_ocorrencia.txt
