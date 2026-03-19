from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return "OK"

@app.route("/teste")
def teste():
    return "TESTE OK"

@app.route("/gestao_ocorrencia")
def gestao_ocorrencia():
    return render_template("gestao_ocorrencia.html")

@app.route("/gestao_ocorrencia_nova")
def gestao_ocorrencia_nova():
    return render_template("gestao_ocorrencia_nova.html")

@app.route("/api/debug")
def api_debug():
    return jsonify({"ok": True})
