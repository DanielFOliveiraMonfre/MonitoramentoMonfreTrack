# -*- coding: utf-8 -*-

from functools import wraps
import os

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for

import database
from forms_parser import parse_forms_payload


app = Flask(__name__)
app.secret_key = os.environ.get("MONFRETRACK_SECRET", "monfretrack-painel-local-2026")

LOGO_PATH = (
    r"C:\Users\DANIEL.OLIVEIRA\OneDrive - MONFREDINI TRANSPORTES LTDA"
    r"\Área de Trabalho\MonfreTrack\logo.png"
)


@app.template_filter("title_status")
def title_status(valor):
    return str(valor or "-").replace("_", " ").title()


@app.context_processor
def injetar_usuario():
    return {"usuario_atual": session.get("usuario")}


def usuario_logado():
    return session.get("usuario")


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not usuario_logado():
            return redirect(url_for("login", next=request.path))
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        usuario = usuario_logado()
        if not usuario:
            return redirect(url_for("login", next=request.path))
        if not usuario.get("admin"):
            return redirect(url_for("minha_operacao"))
        return func(*args, **kwargs)

    return wrapper


def obter_history_hours():
    return database.normalizar_horas_historico(request.args.get("history_hours"))


@app.get("/logo.png")
def logo():
    if os.path.exists(LOGO_PATH):
        return send_file(LOGO_PATH, mimetype="image/png")
    return ("", 404)


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None

    if request.method == "POST":
        nome = (request.form.get("usuario") or "").strip().lower()
        senha = request.form.get("senha") or ""
        usuario = database.validar_login(nome, senha)

        if usuario:
            session["usuario"] = usuario
            destino = request.args.get("next")
            if destino and destino.startswith("/"):
                return redirect(destino)
            return redirect(url_for("dashboard"))

        erro = "Usuario ou senha invalidos."

    return render_template("login.html", erro=erro)


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", pagina="dashboard")


@app.route("/operacao")
@login_required
def operacao():
    return render_template("operacao.html", pagina="operacao")


@app.route("/minha-operacao")
@login_required
def minha_operacao():
    return redirect(url_for("dashboard"))


@app.route("/troca-turno")
@login_required
def troca_turno():
    return render_template("troca_turno.html", pagina="troca_turno")


@app.get("/api/dashboard")
def api_dashboard():
    return jsonify(database.resumo_dashboard(history_hours=obter_history_hours()))


@app.get("/api/operadores")
def api_operadores():
    return jsonify({"operadores": database.listar_operadores()})


@app.post("/api/heartbeat")
def api_heartbeat():
    payload = request.get_json(silent=True) or {}
    operador_id = database.upsert_operador(
        payload.get("operador"),
        payload.get("maquina"),
        payload.get("status") or "ABERTO",
        payload.get("versao"),
    )
    return jsonify({"ok": True, "operador_id": operador_id})


@app.post("/api/alerta-tratado")
def api_alerta_tratado():
    payload = request.get_json(silent=True) or {}
    registro_id = database.registrar_alerta_tratado(
        payload.get("operador"),
        payload.get("maquina"),
        payload.get("tipo"),
        payload.get("placa"),
        payload.get("motorista"),
    )
    return jsonify({"ok": True, "registro_id": registro_id})


@app.get("/api/ocorrencias")
def api_listar_ocorrencias():
    abertas = request.args.get("abertas") == "1"
    finalizadas = request.args.get("finalizadas") == "1"
    return jsonify({
        "ocorrencias": database.listar_ocorrencias(
            apenas_abertas=abertas,
            apenas_finalizadas=finalizadas,
            history_hours=obter_history_hours(),
        )
    })


@app.post("/api/ocorrencias")
def api_criar_ocorrencia():
    payload = request.get_json(silent=True) or {}
    if usuario_logado() and not payload.get("operador"):
        payload["operador"] = usuario_logado()["nome"]
    ocorrencia_id = database.criar_ocorrencia(payload)
    return jsonify({"ok": True, "ocorrencia_id": ocorrencia_id})


@app.post("/api/forms/ocorrencia")
@app.post("/api/power-automate/ocorrencia")
def api_forms_ocorrencia():
    if os.environ.get("RENDER") and not database.USING_POSTGRES:
        return jsonify({
            "ok": False,
            "erro": "DATABASE_URL nao configurado. O Render precisa de PostgreSQL persistente para salvar historico.",
        }), 503

    payload = request.get_json(silent=True) or {}
    try:
        dados = parse_forms_payload(payload)
        ocorrencia_id = database.criar_ocorrencia_forms(dados)
    except Exception as exc:
        return jsonify({"ok": False, "erro": str(exc)}), 400

    return jsonify({"ok": True, "ocorrencia_id": ocorrencia_id, "ocorrencia": dados})


@app.patch("/api/ocorrencias/ordem")
def api_reordenar_ocorrencias():
    payload = request.get_json(silent=True) or {}
    total = database.reordenar_ocorrencias(payload.get("ids") or [])
    return jsonify({"ok": True, "total": total})


@app.patch("/api/ocorrencias/<int:ocorrencia_id>")
def api_atualizar_ocorrencia(ocorrencia_id):
    payload = request.get_json(silent=True) or {}
    database.atualizar_ocorrencia(ocorrencia_id, payload)
    return jsonify({"ok": True, "ocorrencia_id": ocorrencia_id})


@app.delete("/api/ocorrencias/<int:ocorrencia_id>")
def api_apagar_ocorrencia(ocorrencia_id):
    usuario = usuario_logado()
    if not usuario or not usuario.get("admin"):
        return jsonify({"ok": False, "erro": "admin_required"}), 403

    apagados = database.apagar_ocorrencia(ocorrencia_id)
    return jsonify({"ok": True, "ocorrencia_id": ocorrencia_id, "apagados": apagados})


@app.post("/api/ocorrencias/<int:ocorrencia_id>/timer")
def api_iniciar_timer(ocorrencia_id):
    payload = request.get_json(silent=True) or {}
    minutos = int(payload.get("minutos") or 10)
    minutos = max(5, min(30, minutos))
    database.iniciar_timer_ocorrencia(ocorrencia_id, minutos)
    return jsonify({"ok": True, "ocorrencia_id": ocorrencia_id})


@app.post("/api/ocorrencias/<int:ocorrencia_id>/notas")
def api_ocorrencia_nota(ocorrencia_id):
    payload = request.get_json(silent=True) or {}
    operador = payload.get("operador")
    if usuario_logado() and not operador:
        operador = usuario_logado()["nome"]

    nota_id = database.adicionar_nota_turno(
        {
            "operador": operador or "sem.operador",
            "referencia_tipo": "OCORRENCIA",
            "referencia_id": ocorrencia_id,
            "mensagem": payload.get("mensagem"),
        }
    )
    return jsonify({"ok": True, "nota_id": nota_id})


@app.get("/api/troca-turno")
def api_troca_turno():
    return jsonify(database.dados_troca_turno())


@app.post("/api/troca-turno/notas")
def api_troca_turno_notas():
    payload = request.get_json(silent=True) or {}
    if usuario_logado() and not payload.get("operador"):
        payload["operador"] = usuario_logado()["nome"]
    nota_id = database.adicionar_nota_turno(payload)
    return jsonify({"ok": True, "nota_id": nota_id})


@app.delete("/api/troca-turno/notas/<int:nota_id>")
def api_apagar_troca_turno_nota(nota_id):
    operador = usuario_logado()["nome"] if usuario_logado() else None
    database.apagar_nota_turno(nota_id, operador)
    return jsonify({"ok": True, "nota_id": nota_id})


def criar_app():
    database.init_db()
    return app


if __name__ == "__main__":
    criar_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
