from flask import Flask, render_template, redirect
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK"

# Dashboard
@app.route("/dashboard_ocorrencias")
def dashboard_ocorrencias():
    return render_template("dashboard_ocorrencias.html")

# Ocorrências
@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    return render_template("gestao_ocorrencia.html")

@app.route("/gestao_ocorrencia_nova")
def gestao_ocorrencia_nova():
    return render_template("gestao_ocorrencia_nova.html")

@app.route("/gestao_ocorrencia_editar")
def gestao_ocorrencia_editar():
    return render_template("gestao_ocorrencia_editar.html")

@app.route("/gestao_relatorio_impressao")
def gestao_relatorio_impressao():
    return redirect("/gestao_ocorrencia")

# aliases antigos -> tela única de ocorrências
@app.route("/gestao_ocorrencia_aberta")
@app.route("/gestao_ocorrencia_abertas")
@app.route("/gestao_ocorrencia_finalizada")
@app.route("/gestao_ocorrencia_finalizadas")
def aliases_ocorrencias():
    return redirect("/gestao_ocorrencia")

# Frequência
@app.route("/gestao_frequencia")
def gestao_frequencia():
    return render_template("gestao_frequencia.html")

@app.route("/gestao_frequencia_registro")
def gestao_frequencia_registro():
    return render_template("gestao_frequencia_registro.html")

@app.route("/gestao_frequencia_atraso")
def gestao_frequencia_atraso():
    return render_template("gestao_frequencia_atraso.html")

@app.route("/gestao_frequencia_saida")
def gestao_frequencia_saida():
    return render_template("gestao_frequencia_saida.html")

@app.route("/gestao_relatorio_frequencia")
def gestao_relatorio_frequencia():
    return render_template("gestao_relatorio_frequencia.html")

# Tecnologia
@app.route("/gestao_tecnologia")
def gestao_tecnologia():
    return render_template("gestao_tecnologia.html")

# Tutoria
@app.route("/gestao_tutoria")
def gestao_tutoria():
    return render_template("gestao_tutoria.html")

# Cadastro
@app.route("/gestao_cadastro")
def gestao_cadastro():
    return render_template("gestao_cadastro.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
