from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK"

@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    return render_template("gestao_ocorrencia.html")

@app.route("/gestao_frequencia")
def gestao_frequencia():
    return render_template("gestao_frequencia.html")

@app.route("/gestao_tecnologia")
def gestao_tecnologia():
    return render_template("gestao_tecnologia.html")

@app.route("/gestao_tutoria")
def gestao_tutoria():
    return render_template("gestao_tutoria.html")

@app.route("/gestao_cadastro")
def gestao_cadastro():
    return render_template("gestao_cadastro.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
