"""
Búsqueda y descarga de imágenes con licencia libre.
Usa DOS motores en paralelo para no depender de uno solo:
  1) Wikimedia Commons
  2) Openverse (agregador de contenido con licencia abierta: Flickr, Museos, etc.)
Genérico: recibe la lista de términos desde el formulario, no un tema fijo.
"""
import os
import requests

LICENCIAS_PERMITIDAS = [
    "cc-by", "cc-by-sa", "cc0", "pd", "public domain",
    "cc-by-2.0", "cc-by-2.5", "cc-by-3.0", "cc-by-4.0",
    "cc-by-sa-2.0", "cc-by-sa-2.5", "cc-by-sa-3.0", "cc-by-sa-4.0",
    "by", "by-sa", "pdm",
    # Wikimedia Commons a menudo solo rellena 'UsageTerms' con texto humano
    # (no el código corto), así que hay que reconocer también estas formas:
    "creative commons", "atribución", "attribution", "compartir igual",
    "share alike", "dominio público", "dominio publico",
]

HEADERS = {"User-Agent": "EduPackBuilder/1.0 (uso educativo)"}


def es_licencia_valida(licencia_str: str) -> bool:
    if not licencia_str:
        return False
    lic = licencia_str.lower().strip()
    return any(p in lic for p in LICENCIAS_PERMITIDAS)


def _extraer_licencia_commons(meta: dict) -> str:
    """
    Dos bugs corregidos aquí:
    1) Antes solo se miraba 'LicenseShortName', que muchos archivos de Commons
       no traen relleno aunque sí sean libres.
    2) El orden importaba: 'UsageTerms' suele traer texto humano completo
       ("Creative Commons Attribution-Share Alike 4.0") que no calzaba con los
       códigos cortos de LICENCIAS_PERMITIDAS, y como se revisaba ANTES que
       'License' (el campo machine-readable, ej. "cc-by-sa-4.0"), la imagen se
       descartaba aunque 'License' sí tuviera un código válido.
    Ahora se prioriza el campo machine-readable primero; 'UsageTerms' queda de
    último recurso, y LICENCIAS_PERMITIDAS ya reconoce también su forma humana.
    """
    for campo in ("License", "LicenseShortName", "UsageTerms"):
        valor = meta.get(campo, {}).get("value", "")
        if valor:
            return valor
    return ""


def _buscar_commons(termino, max_resultados, log_cb=None):
    resultados = []
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": termino,          # antes: f"File:{termino}", lo que reducía drásticamente los resultados
        "gsrnamespace": "6",
        "gsrlimit": str(max_resultados),
        "prop": "imageinfo", "iiprop": "url|extmetadata",
    }
    try:
        res = requests.get("https://commons.wikimedia.org/w/api.php",
                            params=params, headers=HEADERS, timeout=15)
        res.raise_for_status()
        pages = res.json().get("query", {}).get("pages", {})
    except Exception as e:
        if log_cb:
            log_cb(f"⚠ Wikimedia Commons no respondió para '{termino}': {e}")
        return resultados

    for _, info in pages.items():
        imageinfo = info.get("imageinfo", [{}])[0]
        url = imageinfo.get("url")
        meta = imageinfo.get("extmetadata", {})
        licencia = _extraer_licencia_commons(meta)
        ext = os.path.splitext(url or "")[-1].split("?")[0].lower()
        if not url or ext not in (".jpg", ".jpeg", ".png"):
            continue
        resultados.append({
            "termino": termino, "url_descarga": url,
            "descripcion": meta.get("ObjectName", {}).get("value")
                or meta.get("ImageDescription", {}).get("value", "Sin descripción"),
            "autor": meta.get("Artist", {}).get("value", "No especificado"),
            "licencia": licencia, "url_fuente": url, "fuente": "Wikimedia Commons",
        })
    return resultados


def _buscar_openverse(termino, max_resultados, log_cb=None):
    resultados = []
    params = {
        "q": termino,
        "license": "cc0,pdm,by,by-sa",
        "page_size": min(max_resultados, 20),
    }
    try:
        res = requests.get("https://api.openverse.org/v1/images/",
                            params=params, headers=HEADERS, timeout=15)
        res.raise_for_status()
        items = res.json().get("results", [])
    except Exception as e:
        if log_cb:
            log_cb(f"⚠ Openverse no respondió para '{termino}': {e}")
        return resultados

    for item in items:
        url = item.get("url")
        ext = os.path.splitext(url or "")[-1].split("?")[0].lower()
        if not url or ext not in (".jpg", ".jpeg", ".png"):
            continue
        resultados.append({
            "termino": termino, "url_descarga": url,
            "descripcion": item.get("title", "Sin descripción"),
            "autor": item.get("creator", "No especificado"),
            "licencia": item.get("license", ""), "url_fuente": item.get("foreign_landing_url", url),
            "fuente": "Openverse",
        })
    return resultados


def _es_imagen_valida(img_bytes: bytes) -> bool:
    """
    Segunda barrera además del Content-Type: intenta abrir los bytes como
    imagen real con Pillow. Cubre el caso en que el servidor declara mal
    el Content-Type pero igual manda HTML/JSON de error.
    """
    if not img_bytes or len(img_bytes) < 100:
        return False
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(img_bytes)) as im:
            im.verify()
        return True
    except Exception:
        return False


def buscar_y_descargar(terminos, max_por_termino, carpeta_salida, progress_cb=None, log_cb=None):
    """
    terminos: lista de strings a buscar.
    progress_cb(hecho, total): se llama tras procesar cada término.
    log_cb(mensaje): mensajes legibles para mostrar en pantalla.
    Devuelve: dict con resumen y lista de imágenes descargadas (para la vista previa).
    """
    os.makedirs(carpeta_salida, exist_ok=True)
    descargadas = []
    descartadas = 0
    total = len(terminos)

    for idx, termino in enumerate(terminos, start=1):
        if log_cb:
            log_cb(f"Buscando: {termino} (Wikimedia Commons + Openverse)")

        candidatos = _buscar_commons(termino, max_por_termino, log_cb)
        candidatos += _buscar_openverse(termino, max_por_termino, log_cb)

        aprobados_este_termino = 0
        for c in candidatos:
            if aprobados_este_termino >= max_por_termino:
                break
            if not es_licencia_valida(c["licencia"]):
                descartadas += 1
                continue
            ext = os.path.splitext(c["url_descarga"])[-1].split("?")[0].lower() or ".jpg"
            nombre = f"imagen_{len(descargadas) + 1}{ext}"
            ruta = os.path.join(carpeta_salida, nombre)
            try:
                resp = requests.get(c["url_descarga"], headers=HEADERS, timeout=15)
                resp.raise_for_status()

                # Validación de contenido: si el servidor devolvió un error
                # (410, página HTML de "no encontrado", etc.) puede llegar con
                # status 200 igual, o el Content-Type puede no ser imagen.
                # Sin esto, esas respuestas se guardaban como .jpg válidos.
                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    if log_cb:
                        log_cb(f"  ⚠ Descartada: '{c['url_descarga']}' no es una imagen "
                               f"(Content-Type: {content_type or 'desconocido'})")
                    continue

                img_bytes = resp.content
                if not _es_imagen_valida(img_bytes):
                    if log_cb:
                        log_cb(f"  ⚠ Descartada: archivo corrupto o ilegible de '{c['url_descarga']}'")
                    continue

                with open(ruta, "wb") as f:
                    f.write(img_bytes)
                c["archivo"] = nombre
                descargadas.append(c)
                aprobados_este_termino += 1
                if log_cb:
                    log_cb(f"  ✓ {nombre} ({c['licencia']} — {c['fuente']})")
            except Exception as e:
                if log_cb:
                    log_cb(f"  ⚠ Error descargando una imagen de '{termino}': {e}")

        if aprobados_este_termino == 0 and log_cb:
            log_cb(f"  ✗ Ningún resultado con licencia libre para '{termino}'. Prueba un término más general.")

        if progress_cb:
            progress_cb(idx, total)

    return {"descargadas": descargadas, "descartadas_por_licencia": descartadas}
