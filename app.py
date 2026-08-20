import os
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, abort

from edupack import jobs

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esto-en-produccion")


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/generar", methods=["POST"])
def generar():
    tema = request.form.get("tema", "").strip()
    objetivo_general = request.form.get("objetivo_general", "")
    objetivos_especificos = [o for o in request.form.getlist("objetivo_especifico[]") if o.strip()]
    contexto = request.form.get("contexto", "")

    terminos_raw = request.form.get("terminos_imagenes", "")
    terminos = [t.strip() for t in terminos_raw.split(",") if t.strip()]

    try:
        max_por_termino = max(1, min(int(request.form.get("max_por_termino", 6)), 100))
    except ValueError:
        max_por_termino = 6

    preguntas = []
    textos = request.form.getlist("pregunta_texto[]")
    correctas = request.form.getlist("pregunta_correcta[]")
    explicaciones = request.form.getlist("pregunta_explicacion[]")
    opciones_todas = request.form.getlist("pregunta_opciones[]")  # una string separada por "|" por pregunta

    for i, texto in enumerate(textos):
        opciones = opciones_todas[i].split("|") if i < len(opciones_todas) else []
        preguntas.append({
            "pregunta": texto,
            "opciones": opciones,
            "respuesta_correcta": correctas[i] if i < len(correctas) else "",
            "explicacion": explicaciones[i] if i < len(explicaciones) else "",
        })

    if not tema:
        return render_template("index.html", error="Escribe un tema antes de generar el paquete.")
    if not objetivo_general.strip():
        return render_template("index.html", error="Escribe el objetivo general de la unidad.")
    if not terminos:
        return render_template("index.html", error="Agrega al menos un término de búsqueda.")

    job_id = jobs.crear_job(tema, objetivo_general, objetivos_especificos, contexto, preguntas, terminos, max_por_termino)
    return redirect(url_for("progreso", job_id=job_id))


@app.route("/progreso/<job_id>")
def progreso(job_id):
    job = jobs.obtener_job(job_id)
    if not job:
        abort(404)
    return render_template("progreso.html", job=job)


@app.route("/api/estado/<job_id>")
def api_estado(job_id):
    job = jobs.obtener_job(job_id)
    if not job:
        return jsonify({"error": "no encontrado"}), 404
    return jsonify(job)


@app.route("/vista-previa/<job_id>")
def vista_previa(job_id):
    job = jobs.obtener_job(job_id)
    if not job or job["estado"] != "listo":
        abort(404)
    return render_template("vista_previa.html", job=job)


@app.route("/descargar/<job_id>")
def descargar(job_id):
    job = jobs.obtener_job(job_id)
    ruta = None
    if job and job.get("resultado"):
        ruta = job["resultado"]["zip_path"]
    else:
        ruta = jobs.ruta_zip_historial(job_id)
    if not ruta:
        abort(404)
    return send_file(ruta, as_attachment=True)


@app.route("/historial")
def historial():
    return render_template("historial.html", items=jobs.obtener_historial())


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
