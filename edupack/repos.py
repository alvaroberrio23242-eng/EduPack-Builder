"""
Búsqueda de repositorios de código y plantillas de proyecto en GitHub.
No descarga el código (evita bajar repos completos de tamaño variable);
entrega una lista curada con enlace, licencia y estrellas para que la
persona elija cuál abrir.
"""
from . import net

HEADERS = {"User-Agent": "EduPackBuilder/1.0", "Accept": "application/vnd.github+json"}


def buscar_repositorios(termino, max_resultados, log_cb=None):
    resultados = []

    def _query(q, limite):
        params = {"q": q, "sort": "stars", "order": "desc", "per_page": limite}
        datos = net.get_json("https://api.github.com/search/repositories",
                             params=params, headers=HEADERS, log_cb=log_cb,
                             contexto=f"GitHub para «{q}»")
        if datos is None:    # fallo de red o JSON inválido: net.py ya avisó
            return []
        if not isinstance(datos, dict):
            if log_cb:
                log_cb(f"⚠ GitHub devolvió una respuesta inesperada para «{q}».")
            return []
        items = datos.get("items", [])
        if not isinstance(items, list):
            if log_cb:
                log_cb(f"⚠ GitHub devolvió una respuesta inesperada para «{q}».")
            return []
        return [i for i in items if isinstance(i, dict)]

    items = _query(termino, max_resultados)
    plantillas = _query(f"{termino} is:template", max(1, max_resultados // 2))

    vistos = set()
    for item in items + plantillas:
        full_name = item.get("full_name")
        if not full_name or full_name in vistos:
            continue
        vistos.add(full_name)
        licencia = item.get("license")
        resultados.append({
            "termino": termino,
            "nombre": full_name,
            "descripcion": item.get("description") or "Sin descripción",
            "estrellas": item.get("stargazers_count", 0),
            "licencia": (licencia.get("spdx_id") if isinstance(licencia, dict) else None) or "No especificada",
            "url": item.get("html_url"),
            "es_plantilla": bool(item.get("is_template")),
        })
        if len(resultados) >= max_resultados:
            break
    return resultados


def buscar_repositorios_multi(terminos, max_por_termino, progress_cb=None, log_cb=None):
    todos = []
    total = len(terminos)
    for idx, termino in enumerate(terminos, start=1):
        if log_cb:
            log_cb(f"Buscando repositorios: {termino}")
        encontrados = buscar_repositorios(termino, max_por_termino, log_cb)
        if not encontrados and log_cb:
            log_cb(f"  ✗ Sin repositorios para '{termino}'.")
        else:
            for r in encontrados:
                if log_cb:
                    tag = " [plantilla]" if r["es_plantilla"] else ""
                    log_cb(f"  ✓ {r['nombre']}{tag} ({r['estrellas']}⭐)")
        todos.extend(encontrados)
        if progress_cb:
            progress_cb(idx, total)
    return todos


def escribir_repositorios(carpeta_raiz, resultados):
    import os
    carpeta = os.path.join(carpeta_raiz, "4_Repositorios")
    os.makedirs(carpeta, exist_ok=True)
    lineas = ["# Repositorios encontrados", ""]
    for r in resultados:
        etiqueta = " (plantilla)" if r["es_plantilla"] else ""
        lineas.append(f"## {r['nombre']}{etiqueta}")
        lineas.append(f"- Buscado por: {r['termino']}")
        lineas.append(f"- ⭐ {r['estrellas']}  ·  Licencia: {r['licencia']}")
        lineas.append(f"- {r['descripcion']}")
        lineas.append(f"- {r['url']}")
        lineas.append("")
    with open(os.path.join(carpeta, "Repositorios.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
