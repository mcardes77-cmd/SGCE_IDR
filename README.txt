PACOTE LIMPO DAS TELAS DO SISTEMA

O que este pacote resolve:
- organiza as telas principais na pasta templates
- usa a tela nova de gestao_ocorrencia como tela única
- remove a necessidade de páginas separadas de abertas/finalizadas
- inclui app.py pronto para subir no Railway/Render

Start command:
gunicorn app:app

Observação:
As telas estão prontas para abrir.
As APIs de dados do Supabase precisam continuar sendo integradas no próximo passo.
