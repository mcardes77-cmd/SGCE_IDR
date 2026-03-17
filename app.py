
from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/gestao_ocorrencia_nova")
def nova():
    return render_template("gestao_ocorrencia_nova.html")

@app.route("/gestao_ocorrencia_editar")
def editar():
    return render_template("gestao_ocorrencia_editar.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
