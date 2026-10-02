"""
Busca videos con licencia libre o de dominio público.
No descarga el archivo de video completo (pueden pesar cientos de MB y tardar
minutos); entrega una lista con enlace directo, licencia y fuente para que la
persona decida cuáles bajar.
Fuentes: Wikimedia Commons e Internet Archive (ninguna requiere clave de API).
"""
import os

from . import net
from .images import es_licencia_valida, _extraer_licencia_commons, _meta_valor

HEADERS = {"User-Agent": "EduPackBuilder/1.0 (uso educativo)"}


def _buscar_commons_video(termino, max_resultados, log_cb=None):
    resultados = []
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": termino, "gsrnamespace": "6", "gsrlimit": max_resultados,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime",
    }
    datos = net.get_json("https://commons.wikimedia.org/w/api.php",
                         params=params, headers=HEADERS, log_cb=log_cb,
                         contexto=f"Wikimedia Commons (video) para «{termino}»")
    if datos is None:      # fallo de red o JSON inválido: net.py ya avisó por log
        return resultados
    if not isinstance(datos, dict):
        if log_cb:
            log_cb(f"⚠ Wikimedia Commons (video) devolvió una respuesta inesperada para «{termino}».")
        return resultados
    consulta = datos.get("query")
    pages = consulta.get("pages", {}) if isinstance(consulta, dict) else {}
    if not isinstance(pages, dict):
        if log_cb:
            log_cb(f"⚠ Wikimedia Commons (video) devolvió una respuesta inesperada para «{termino}».")
        return resultados

    for _, info in pages.items():
        if not isinstance(info, dict):
            continue
        imageinfo = {}
        imagenes = info.get("imageinfo")
        if isinstance(imagenes, list) and imagenes and isinstance(imagenes[0], dict):
            imageinfo = imagenes[0]
        mime = imageinfo.get("mime", "")
        if not isinstance(mime, str) or not mime.startswith("video/"):
            continue
        meta = imageinfo.get("extmetadata") if isinstance(imageinfo.get("extmetadata"), dict) else {}
        licencia = _extraer_licencia_commons(meta)
        if not es_licencia_valida(licencia):
            continue
        resultados.append({
            "termino": termino,
            "titulo": _meta_valor(meta, "ObjectName", "Sin título") or "Sin título",
            "url": imageinfo.get("url"),
            "licencia": licencia,
            "fuente": "Wikimedia Commons",
        })
    return resultados


def _buscar_internet_archive(termino, max_resultados, log_cb=None):
    resultados = []
    datos = net.get_json(
        "https://archive.org/advancedsearch.php",
        params={
            "q": f'{termino} AND mediatype:(movies)',
            "fl[]": ["identifier", "title", "licenseurl"],
            "rows": max_resultados, "output": "json",
        },
        headers=HEADERS, log_cb=log_cb,
        contexto=f"Internet Archive para «{termino}»",
    )
    if datos is None:      # fallo de red o JSON inválido: net.py ya avisó por log
        return resultados
    if not isinstance(datos, dict):
        if log_cb:
            log_cb(f"⚠ Internet Archive devolvió una respuesta inesperada para «{termino}».")
        return resultados
    respuesta = datos.get("response")
    docs = respuesta.get("docs", []) if isinstance(respuesta, dict) else []
    if not isinstance(docs, list):
        if log_cb:
            log_cb(f"⚠ Internet Archive devolvió una respuesta inesperada para «{termino}».")
        return resultados

    for d in docs:
        if not isinstance(d, dict):
            continue
        identifier = d.get("identifier")
        if not identifier:
            continue
        resultados.append({
            "termino": termino,
            "titulo": d.get("title", "Sin título"),
            "url": f"https://archive.org/details/{identifier}",
            "licencia": d.get("licenseurl") or "Dominio público / Internet Archive",
            "fuente": "Internet Archive",
        })
    return resultados


def buscar_videos_multi(terminos, max_por_termino, progress_cb=None, log_cb=None):
    todos = []
    total = len(terminos)
    for idx, termino in enumerate(terminos, start=1):
        if log_cb:
            log_cb(f"Buscando videos: {termino} (Wikimedia Commons + Internet Archive)")
        encontrados = _buscar_commons_video(termino, max_por_termino, log_cb)
        encontrados += _buscar_internet_archive(termino, max_por_termino, log_cb)
        if not encontrados and log_cb:
            log_cb(f"  ✗ Sin videos con licencia libre para '{termino}'.")
        else:
            for v in encontrados:
                if log_cb:
                    log_cb(f"  ✓ {v['titulo']} ({v['fuente']})")
        todos.extend(encontrados)
        if progress_cb:
            progress_cb(idx, total)
    return todos


def escribir_videos(carpeta_raiz, resultados):
    carpeta = os.path.join(carpeta_raiz, "3b_Videos")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "Videos_encontrados.txt"), "w", encoding="utf-8") as f:
        if not resultados:
            f.write("No se encontraron videos con licencia libre para los términos buscados.\n")
        for v in resultados:
            f.write(f"[{v['fuente']}] {v['titulo']} (licencia: {v['licencia']})\n  {v['url']}\n\n")
