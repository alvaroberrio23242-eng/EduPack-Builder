"""
Busca textos ya existentes con licencia libre (Wikipedia, CC BY-SA) sobre el tema.
No redacta contenido nuevo: trae el resumen introductorio de artículos existentes,
con su fuente y licencia, para que la persona los use o los edite.
"""
import os
import requests

HEADERS = {"User-Agent": "EduPackBuilder/1.0 (uso educativo)"}


def buscar_ensayos(termino, max_resultados, log_cb=None):
    resultados = []
    try:
        res = requests.get(
            "https://es.wikipedia.org/w/api.php",
            params={
                "action": "query", "format": "json", "generator": "search",
                "gsrsearch": termino, "gsrlimit": max_resultados,
                "prop": "extracts", "exintro": "1", "explaintext": "1",
            },
            headers=HEADERS, timeout=15,
        )
        res.raise_for_status()
        pages = res.json().get("query", {}).get("pages", {})
    except Exception as e:
        if log_cb:
            log_cb(f"⚠ Wikipedia no respondió para '{termino}': {e}")
        return resultados

    for _, page in pages.items():
        titulo = page.get("title", "Sin título")
        texto = (page.get("extract") or "").strip()
        if not texto:
            continue
        resultados.append({
            "termino": termino,
            "titulo": titulo,
            "texto": texto,
            "url": f"https://es.wikipedia.org/wiki/{titulo.replace(' ', '_')}",
            "licencia": "CC BY-SA 4.0",
        })
    return resultados


def buscar_ensayos_multi(terminos, max_por_termino, progress_cb=None, log_cb=None):
    todos = []
    total = len(terminos)
    for idx, termino in enumerate(terminos, start=1):
        if log_cb:
            log_cb(f"Buscando artículos: {termino}")
        encontrados = buscar_ensayos(termino, max_por_termino, log_cb)
        if not encontrados and log_cb:
            log_cb(f"  ✗ Sin artículos para '{termino}'.")
        else:
            for e in encontrados:
                if log_cb:
                    log_cb(f"  ✓ {e['titulo']}")
        todos.extend(encontrados)
        if progress_cb:
            progress_cb(idx, total)
    return todos


def escribir_ensayos(carpeta_raiz, resultados):
    carpeta = os.path.join(carpeta_raiz, "5_Ensayos_y_Articulos")
    os.makedirs(carpeta, exist_ok=True)
    if not resultados:
        with open(os.path.join(carpeta, "Articulos.txt"), "w", encoding="utf-8") as f:
            f.write("No se encontraron artículos para los términos buscados.\n")
        return
    for i, e in enumerate(resultados, start=1):
        nombre = f"{i:02d}_{e['titulo'][:40].replace('/', '-')}.txt"
        with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
            f.write(f"{e['titulo']}\n")
            f.write("=" * len(e['titulo']) + "\n\n")
            f.write(e["texto"] + "\n\n")
            f.write(f"Fuente: {e['url']}\n")
            f.write(f"Licencia: {e['licencia']}\n")
