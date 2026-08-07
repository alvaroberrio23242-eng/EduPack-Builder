import os
import json
import threading
import uuid
from datetime import datetime

from . import content, images, videos, repos, essays, packager

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs")
HISTORIAL_PATH = os.path.join(DATA_DIR, "historial.json")
os.makedirs(DATA_DIR, exist_ok=True)

_JOBS = {}
_LOCK = threading.Lock()


def _leer_historial():
    if not os.path.exists(HISTORIAL_PATH):
        return []
    with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_historial(historial):
    with open(HISTORIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(historial, f, ensure_ascii=False, indent=2)


def obtener_historial():
    return list(reversed(_leer_historial()))


def obtener_job(job_id):
    with _LOCK:
        return _JOBS.get(job_id)


def crear_job(tema, objetivos, contexto, preguntas, terminos, max_por_termino, recursos):
    """
    recursos: dict de booleanos, ej. {"imagenes": True, "videos": False, "repositorios": True, "ensayos": False}
    """
    job_id = uuid.uuid4().hex[:10]
    etapas = [r for r, activo in recursos.items() if activo]
    with _LOCK:
        _JOBS[job_id] = {
            "id": job_id, "tema": tema, "estado": "en_cola",
            "progreso": 0, "total": max(len(terminos), 1),
            "log": [], "error": None, "resultado": None,
        }
    hilo = threading.Thread(
        target=_ejecutar_job,
        args=(job_id, tema, objetivos, contexto, preguntas, terminos, max_por_termino, recursos),
        daemon=True,
    )
    hilo.start()
    return job_id


def _log(job_id, mensaje):
    with _LOCK:
        _JOBS[job_id]["log"].append(mensaje)


def _set_estado(job_id, estado):
    with _LOCK:
        _JOBS[job_id]["estado"] = estado


def _ejecutar_job(job_id, tema, objetivos, contexto, preguntas, terminos, max_por_termino, recursos):
    carpeta_raiz = os.path.join(DATA_DIR, job_id, "paquete")
    try:
        _set_estado(job_id, "generando_contenido")
        _log(job_id, f"Generando guía y trivia para «{tema}»...")
        guia_texto = content.construir_guia(tema, objetivos, contexto)
        preguntas_validas = content.validar_preguntas(preguntas)
        if not preguntas_validas:
            _log(job_id, "⚠ Ninguna pregunta quedó completa; la trivia se guarda vacía.")
        content.escribir_contenido(carpeta_raiz, tema, guia_texto, preguntas_validas)

        def on_progreso(hecho, total):
            with _LOCK:
                _JOBS[job_id]["progreso"] = hecho
                _JOBS[job_id]["total"] = total
        log_cb = lambda m: _log(job_id, m)

        num_imagenes = descartadas_licencia = 0
        lista_imagenes, lista_videos, lista_repos, lista_ensayos = [], [], [], []

        if recursos.get("imagenes"):
            _set_estado(job_id, "buscando_imagenes")
            resumen = images.buscar_y_descargar(
                terminos, max_por_termino, os.path.join(carpeta_raiz, "3_Galeria"),
                progress_cb=on_progreso, log_cb=log_cb,
            )
            lista_imagenes = resumen["descargadas"]
            num_imagenes = len(lista_imagenes)
            descartadas_licencia = resumen["descartadas_por_licencia"]

        if recursos.get("videos"):
            _set_estado(job_id, "buscando_videos")
            lista_videos = videos.buscar_videos_multi(terminos, max_por_termino, on_progreso, log_cb)
            videos.escribir_videos(carpeta_raiz, lista_videos)

        if recursos.get("repositorios"):
            _set_estado(job_id, "buscando_repositorios")
            lista_repos = repos.buscar_repositorios_multi(terminos, max_por_termino, on_progreso, log_cb)
            repos.escribir_repositorios(carpeta_raiz, lista_repos)

        if recursos.get("ensayos"):
            _set_estado(job_id, "buscando_ensayos")
            lista_ensayos = essays.buscar_ensayos_multi(terminos, max_por_termino, on_progreso, log_cb)
            essays.escribir_ensayos(carpeta_raiz, lista_ensayos)

        _set_estado(job_id, "empaquetando")
        _log(job_id, "Empaquetando todo en un ZIP...")
        zip_nombre = f"{tema.strip().replace(' ', '_') or 'EduPack'}.zip"
        zip_destino = os.path.join(DATA_DIR, job_id, zip_nombre)
        packager.empaquetar(carpeta_raiz, zip_destino)

        resultado = {
            "tema": tema,
            "num_preguntas": len(preguntas_validas),
            "num_imagenes": num_imagenes,
            "descartadas_por_licencia": descartadas_licencia,
            "imagenes": lista_imagenes,
            "videos": lista_videos,
            "repositorios": lista_repos,
            "ensayos": lista_ensayos,
            "guia_texto": guia_texto,
            "preguntas": preguntas_validas,
            "zip_path": zip_destino,
            "zip_nombre": zip_nombre,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        with _LOCK:
            _JOBS[job_id]["estado"] = "listo"
            _JOBS[job_id]["resultado"] = resultado

        historial = _leer_historial()
        historial.append({
            "id": job_id, "tema": tema, "fecha": resultado["fecha"],
            "num_imagenes": num_imagenes, "num_preguntas": resultado["num_preguntas"],
            "num_videos": len(lista_videos), "num_repositorios": len(lista_repos),
            "num_ensayos": len(lista_ensayos), "zip_nombre": zip_nombre,
        })
        _guardar_historial(historial)
        _log(job_id, "¡Listo! Paquete generado correctamente.")

    except Exception as e:
        with _LOCK:
            _JOBS[job_id]["estado"] = "error"
            _JOBS[job_id]["error"] = str(e)
        _log(job_id, f"✗ Error: {e}")


def ruta_zip_historial(job_id):
    entry = next((h for h in _leer_historial() if h["id"] == job_id), None)
    if not entry:
        return None
    ruta = os.path.join(DATA_DIR, job_id, entry["zip_nombre"])
    return ruta if os.path.exists(ruta) else None
