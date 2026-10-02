import os
import json
import re
import threading
import time
import uuid
from datetime import datetime

from . import content, filenames, images, videos, repos, essays, packager

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "jobs")
HISTORIAL_PATH = os.path.join(DATA_DIR, "historial.json")
os.makedirs(DATA_DIR, exist_ok=True)

# Protege las operaciones read-modify-write compartidas entre hilos:
# el historial.json global y el estado.json de cada job (que puede ser
# leído/escrito por el hilo del job y, a la vez, consultado por las
# peticiones HTTP de Flask). Secciones críticas pequeñas: solo leer,
# modificar en memoria y escribir. Nunca se anida un lock dentro de otro,
# así que no hay riesgo de deadlock.
_LOCK = threading.Lock()


def _carpeta_job(job_id):
    return os.path.join(DATA_DIR, job_id)


# Los ids legítimos los genera crear_job() con uuid4().hex[:10] (hex puro,
# 10 caracteres). Cualquier otra cosa no debe usarse para construir rutas:
# sin esta comprobación, un job_id manipulado desde la URL ("..", "..\\..\\x")
# haría que _leer_estado leyera estado.json fuera de data/jobs/.
_ID_VALIDO = re.compile(r"[0-9a-f]{10}")


def es_id_valido(job_id):
    return isinstance(job_id, str) and _ID_VALIDO.fullmatch(job_id) is not None


def _ruta_estado(job_id):
    return os.path.join(_carpeta_job(job_id), "estado.json")


def _leer_estado(job_id):
    ruta = _ruta_estado(job_id)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Si el archivo quedó a medio escribir por algún corte (ej. el
        # proceso murió justo al escribir), no se rompe: se trata como
        # si el job no existiera en vez de lanzar una excepción.
        return None


def _escribir_estado(job_id, estado_dict):
    """Escritura atómica: escribe en un .tmp y luego renombra, para que
    ningún lector vea nunca un estado.json a medio escribir.

    Dos detalles de robustez:
    - DATA_DIR se resuelve UNA sola vez por llamada, para que la carpeta de
      creación y la del renombre sean siempre la misma.
    - En Windows, os.replace falla con PermissionError si otro hilo está
      leyendo estado.json justo en ese instante (el lector mantiene el
      archivo abierto); se reintenta brevemente antes de rendirse.
    """
    carpeta = _carpeta_job(job_id)
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "estado.json")
    ruta_tmp = ruta + ".tmp"
    with open(ruta_tmp, "w", encoding="utf-8") as f:
        json.dump(estado_dict, f, ensure_ascii=False, indent=2)
    for intento in range(5):
        try:
            os.replace(ruta_tmp, ruta)
            return
        except PermissionError:
            if intento == 4:
                raise
            time.sleep(0.01)


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
    if not es_id_valido(job_id):
        return None
    return _leer_estado(job_id)


def crear_job(tema, objetivo_general, objetivos_especificos, contexto, preguntas, terminos, max_por_termino):
    """
    Los 4 tipos de recurso (imágenes, videos, repositorios, ensayos) ya no son
    opcionales: todo paquete los busca todos, para que el resultado sea
    siempre completo.
    """
    job_id = uuid.uuid4().hex[:10]
    estado_inicial = {
        "id": job_id, "tema": tema, "estado": "en_cola",
        "progreso": 0, "total": max(len(terminos), 1),
        "log": [], "error": None, "resultado": None,
    }
    _escribir_estado(job_id, estado_inicial)

    hilo = threading.Thread(
        target=_ejecutar_job,
        args=(job_id, tema, objetivo_general, objetivos_especificos, contexto, preguntas, terminos, max_por_termino),
        daemon=True,
    )
    hilo.start()
    return job_id


def _log(job_id, mensaje):
    with _LOCK:
        estado = _leer_estado(job_id)
        if estado is None:
            return
        estado["log"].append(mensaje)
        _escribir_estado(job_id, estado)


def _set_estado(job_id, nuevo_estado):
    with _LOCK:
        estado = _leer_estado(job_id)
        if estado is None:
            return
        estado["estado"] = nuevo_estado
        _escribir_estado(job_id, estado)


def _actualizar_progreso(job_id, progreso, total):
    with _LOCK:
        estado = _leer_estado(job_id)
        if estado is None:
            return
        estado["progreso"] = progreso
        estado["total"] = total
        _escribir_estado(job_id, estado)


def _ejecutar_job(job_id, tema, objetivo_general, objetivos_especificos, contexto, preguntas, terminos, max_por_termino):
    carpeta_raiz = os.path.join(DATA_DIR, job_id, "paquete")
    try:
        _set_estado(job_id, "generando_contenido")
        _log(job_id, f"Generando guía para «{tema}»...")
        guia_texto = content.construir_guia(tema, objetivo_general, objetivos_especificos, contexto)
        preguntas_validas = content.validar_preguntas(preguntas)
        content.escribir_contenido(carpeta_raiz, tema, guia_texto, preguntas_validas)

        def on_progreso(hecho, total):
            _actualizar_progreso(job_id, hecho, total)
        log_cb = lambda m: _log(job_id, m)

        # Los 4 tipos de recurso ya no son opcionales: se buscan siempre,
        # para que todo paquete generado sea completo.
        _set_estado(job_id, "buscando_imagenes")
        resumen = images.buscar_y_descargar(
            terminos, max_por_termino, os.path.join(carpeta_raiz, "3_Galeria"),
            progress_cb=on_progreso, log_cb=log_cb,
        )
        lista_imagenes = resumen["descargadas"]
        num_imagenes = len(lista_imagenes)
        descartadas_licencia = resumen["descartadas_por_licencia"]

        _set_estado(job_id, "buscando_videos")
        lista_videos = videos.buscar_videos_multi(terminos, max_por_termino, on_progreso, log_cb)
        videos.escribir_videos(carpeta_raiz, lista_videos)

        _set_estado(job_id, "buscando_repositorios")
        lista_repos = repos.buscar_repositorios_multi(terminos, max_por_termino, on_progreso, log_cb)
        repos.escribir_repositorios(carpeta_raiz, lista_repos)

        _set_estado(job_id, "buscando_ensayos")
        lista_ensayos = essays.buscar_ensayos_multi(terminos, max_por_termino, on_progreso, log_cb)
        essays.escribir_ensayos(carpeta_raiz, lista_ensayos)

        _set_estado(job_id, "generando_bibliografia")
        _log(job_id, "Compilando bibliografía a partir de las fuentes encontradas...")
        bibliografia_texto = content.construir_bibliografia(lista_imagenes, lista_videos, lista_ensayos, lista_repos)
        content.escribir_bibliografia(carpeta_raiz, bibliografia_texto)

        _set_estado(job_id, "empaquetando")
        _log(job_id, "Empaquetando todo en un ZIP...")
        zip_nombre = filenames.sanitizar_nombre(
            tema.strip().replace(" ", "_"), extension=".zip",
            max_largo=120, fallback="EduPack",
        )
        zip_destino = os.path.join(DATA_DIR, job_id, zip_nombre)
        packager.empaquetar(carpeta_raiz, zip_destino)

        resultado = {
            "tema": tema,
            "objetivo_general": objetivo_general,
            "objetivos_especificos": [o for o in objetivos_especificos if o.strip()],
            "num_preguntas": len(preguntas_validas),
            "num_imagenes": num_imagenes,
            "descartadas_por_licencia": descartadas_licencia,
            "imagenes": lista_imagenes,
            "videos": lista_videos,
            "repositorios": lista_repos,
            "ensayos": lista_ensayos,
            "guia_texto": guia_texto,
            "bibliografia_texto": bibliografia_texto,
            "preguntas": preguntas_validas,
            "zip_path": zip_destino,
            "zip_nombre": zip_nombre,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        with _LOCK:
            estado = _leer_estado(job_id) or {"log": []}
            estado["estado"] = "listo"
            estado["resultado"] = resultado
            _escribir_estado(job_id, estado)

        with _LOCK:
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
            estado = _leer_estado(job_id) or {"log": []}
            estado["estado"] = "error"
            estado["error"] = str(e)
            _escribir_estado(job_id, estado)
        _log(job_id, f"✗ Error: {e}")


def ruta_zip_historial(job_id):
    if not es_id_valido(job_id):
        return None
    entry = next((h for h in _leer_historial() if h["id"] == job_id), None)
    if not entry:
        return None
    ruta = os.path.join(DATA_DIR, job_id, entry["zip_nombre"])
    return ruta if os.path.exists(ruta) else None
