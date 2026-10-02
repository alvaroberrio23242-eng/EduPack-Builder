"""
Utilidad centralizada para golpear las APIs externas (Wikimedia, Openverse,
GitHub, Internet Archive, Wikipedia). Antes cada módulo repetía su propio
try/except con timeout=15 y sin reintento; ahora todos comparten estas
funciones, así un fallo de red puntual (timeout, 503, DNS) no tumba el
job completo.

Ninguna función lanza: devuelven None y avisan por log_cb, para que cada
fuente pueda seguir con la siguiente.
"""
import time
import requests

TIMEOUT = 15
REINTENTOS = 1  # 1 reintento extra tras el primer intento fallido
ESPERA_ENTRE_REINTENTOS = 1.5  # segundos

HEADERS = {"User-Agent": "EduPackBuilder/1.0 (uso educativo)"}


def _pedir(url, params=None, headers=None, log_cb=None, contexto="",
           parsear_json=False, mensaje_error=None):
    """GET con reintento. Devuelve la respuesta (o su JSON, si parsear_json)
    o None tras agotar los intentos.

    contexto: texto descriptivo para los mensajes de log (ej. "GitHub para 'agua'").
    mensaje_error: fn(e) -> str para personalizar el mensaje del último intento.
    """
    headers = headers or HEADERS
    intentos_totales = 1 + REINTENTOS
    for intento in range(1, intentos_totales + 1):
        try:
            res = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
            res.raise_for_status()
            return res.json() if parsear_json else res
        except Exception as e:
            es_ultimo = intento == intentos_totales
            if log_cb:
                if es_ultimo:
                    if mensaje_error:
                        log_cb(mensaje_error(e))
                    else:
                        log_cb(f"⚠ {contexto or url} no respondió tras {intentos_totales} intentos: {e}")
                else:
                    log_cb(f"  … reintentando {contexto or url} ({intento}/{intentos_totales})")
            if not es_ultimo:
                time.sleep(ESPERA_ENTRE_REINTENTOS)
    return None


def get_json(url, params=None, headers=None, log_cb=None, contexto=""):
    """
    GET que devuelve el JSON parseado, o None si falla tras los reintentos
    (incluye respuestas con JSON inválido, que también se reintentan).
    """
    return _pedir(url, params=params, headers=headers, log_cb=log_cb,
                  contexto=contexto, parsear_json=True)


def get_respuesta(url, params=None, headers=None, log_cb=None, contexto=""):
    """GET que devuelve la respuesta completa (con headers), o None si falla.
    Se usa cuando hace falta inspeccionar Content-Type, p.ej. descargas."""
    return _pedir(url, params=params, headers=headers, log_cb=log_cb, contexto=contexto)


def get_bytes(url, headers=None, log_cb=None, contexto=""):
    """GET binario (para descargar imágenes) con el mismo esquema de reintento."""
    res = _pedir(
        url, headers=headers, log_cb=log_cb, contexto=contexto,
        mensaje_error=lambda e: f"⚠ Error descargando {contexto or url}: {e}",
    )
    return res.content if res is not None else None
