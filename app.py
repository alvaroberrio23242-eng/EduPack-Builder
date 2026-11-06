import os
import secrets
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, abort, session

from edupack import jobs, seleccion


def resolver_secret_key(config):
    """Decide la SECRET_KEY de la app.

    Reglas:
    - Si SECRET_KEY está en el entorno, se usa tal cual (producción).
    - Si no, solo se permite continuar con un opt-in explícito:
      EDUPACK_DEV=1 (desarrollo local) o app.config["TESTING"] (tests).
      En ese caso se genera una clave aleatoria efímera, nunca una constante.
    - En cualquier otro caso la app falla aquí, con un error claro, en lugar
      de arrancar con una clave predecible.

    No depende de FLASK_ENV (deprecada desde Flask 2.3) ni de que la
    plataforma defina alguna variable. La clave nunca se imprime ni se
    registra en ningún log.
    """
    clave = os.environ.get("SECRET_KEY")
    if clave:
        return clave
    if config.get("TESTING") or os.environ.get("EDUPACK_DEV") == "1":
        return secrets.token_hex(32)
    raise RuntimeError(
        "Falta SECRET_KEY: define la variable de entorno SECRET_KEY "
        "(obligatoria en producción) o activa explícitamente el modo "
        "desarrollo con EDUPACK_DEV=1."
    )


app = Flask(__name__)
app.secret_key = resolver_secret_key(app.config)

LIMITE_MIS_JOBS = 200


def registrar_job_propio(job_id):
    """Anota en la sesión del navegador que este job lo creó él.

    Se reasigna la lista entera (no se muta in place) para que Flask marque
    la sesión como modificada y la guarde en la cookie.
    """
    lista = list(session.get("mis_jobs", []))
    if job_id not in lista:
        lista.append(job_id)
        del lista[:-LIMITE_MIS_JOBS]
    session["mis_jobs"] = lista


def es_job_propio(job_id):
    return job_id in session.get("mis_jobs", [])


def proteger_job(job_id, job):
    """404 si no existe; 403 si existe pero pertenece a otra sesión."""
    if not job:
        abort(404)
    if not es_job_propio(job_id):
        abort(403)


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
    registrar_job_propio(job_id)
    return redirect(url_for("progreso", job_id=job_id))


@app.route("/progreso/<job_id>")
def progreso(job_id):
    job = jobs.obtener_job(job_id)
    proteger_job(job_id, job)
    return render_template("progreso.html", job=job)


@app.route("/api/estado/<job_id>")
def api_estado(job_id):
    job = jobs.obtener_job(job_id)
    if not job:
        return jsonify({"error": "no encontrado"}), 404
    if not es_job_propio(job_id):
        return jsonify({"error": "no autorizado"}), 403
    return jsonify(job)


@app.route("/vista-previa/<job_id>")
def vista_previa(job_id):
    job = jobs.obtener_job(job_id)
    if not job or job["estado"] != "listo":
        abort(404)
    if not es_job_propio(job_id):
        abort(403)
    return render_template("vista_previa.html", job=job, seleccion=seleccion.seleccion_de_job(job))


@app.route("/descargar/<job_id>")
def descargar(job_id):
    if not es_job_propio(job_id):
        abort(404 if jobs.obtener_job(job_id) is None else 403)
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
    propios = set(session.get("mis_jobs", []))
    items = [i for i in jobs.obtener_historial() if i.get("id") in propios]
    return render_template("historial.html", items=items)



@app.route("/api/seleccion/<job_id>", methods=["POST"])
def api_guardar_seleccion(job_id):
    if not request.is_json:
        return jsonify({"error": "Se requiere JSON."}), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({"error": "JSON inválido."}), 400

    job = jobs.obtener_job(job_id)
    if job is None:
        return jsonify({"error": "Trabajo no encontrado."}), 404

    proteger_job(job_id, job)

    try:
        resultado = seleccion.guardar_seleccion(
            job_id,
            datos.get("excluidos"),
            datos.get("version"),
        )
        return jsonify(resultado), 200

    except seleccion.VersionConflicto as exc:
        return jsonify({
            "error": str(exc),
            "version_actual": exc.version_actual,
        }), 409

    except seleccion.SeleccionInvalida as exc:
        return jsonify({"error": str(exc)}), 400

    except seleccion.JobNoDisponible as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/reempaquetar/<job_id>", methods=["POST"])
def api_reempaquetar(job_id):
    if not request.is_json:
        return jsonify({"error": "Se requiere JSON."}), 400

    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({"error": "JSON inválido."}), 400

    job = jobs.obtener_job(job_id)
    if job is None:
        return jsonify({"error": "Trabajo no encontrado."}), 404

    proteger_job(job_id, job)

    try:
        resultado = seleccion.reempaquetar(job_id)
        return jsonify(resultado), 200

    except seleccion.JobNoDisponible as exc:
        return jsonify({"error": str(exc)}), 404

    except seleccion.SeleccionInvalida as exc:
        return jsonify({"error": str(exc)}), 400

    except (
        seleccion.ReempaquetadoEnCurso,
        seleccion.ZipOcupado,
        seleccion.VersionConflicto,
    ) as exc:
        respuesta = {"error": str(exc)}
        if isinstance(exc, seleccion.VersionConflicto):
            respuesta["version_actual"] = exc.version_actual
        return jsonify(respuesta), 409

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
