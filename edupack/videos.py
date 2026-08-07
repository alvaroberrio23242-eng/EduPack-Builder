"""
Busca videos con licencia libre o de dominio público.
No descarga el archivo de video completo (pueden pesar cientos de MB y tardar
minutos); entrega una lista con enlace directo, licencia y fuente para que la
persona decida cuáles bajar.
Fuentes: Wikimedia Commons e Internet Archive (ninguna requiere clave de API).
"""
import os
import requests

from .images import es_licencia_valida, _extraer_licencia_commons

HEADERS = {"User-Agent": "EduPackBuilder/1.0 (uso educativo)"}


def _buscar_commons_video(termino, max_resultados, log_cb=None):
    resultados = []
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": termino, "gsrnamespace": "6", "gsrlimit": max_resultados,
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime",
    }
    try:
        res = requests.get("https://commons.wikimedia.org/w/api.php",
                            params=params, headers=HEADERS, timeout=15)
        res.raise_for_status()
        pages = res.json().get("query", {}).get("pages", {})
    except Exception as e:
        if log_cb:
            log_cb(f"⚠ Wikimedia Commons (video) no respondió para '{termino}': {e}")
        return resultados

    for _, info in pages.items():
        imageinfo = info.get("imageinfo", [{}])[0]
        mime = imageinfo.get("mime", "")
        if not mime.startswith("video/"):
            continue
        meta = imageinfo.get("extmetadata", {})
        licencia = _extraer_licencia_commons(meta)
        if not es_licencia_valida(licencia):
            continue
        resultados.append({
            "termino": termino,
            "titulo": meta.get("ObjectName", {}).get("value", "Sin título"),
            "url": imageinfo.get("url"),
            "licencia": licencia,
            "fuente": "Wikimedia Commons",
        })
    return resultados


def _buscar_internet_archive(termino, max_resultados, log_cb=None):
    resultados = []
    try:
        res = requests.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": f'{termino} AND mediatype:(movies)',
                "fl[]": ["identifier", "title", "licenseurl"],
                "rows": max_resultados, "output": "json",
            },
            headers=HEADERS, timeout=15,
        )
        res.raise_for_status()
        docs = res.json().get("response", {}).get("docs", [])
    except Exception as e:
        if log_cb:
            log_cb(f"⚠ Internet Archive no respondió para '{termino}': {e}")
        return resultados

    for d in docs:
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
