"""
Utilidad centralizada para golpear las APIs externas (Wikimedia, Openverse,
GitHub, Internet Archive, Wikipedia). Antes cada módulo repetía su propio
try/except con timeout=15 y sin reintento; ahora todos comparten esta función,
así un fallo de red puntual (timeout, 503, DNS) no tumba el job completo.
"""
import time
import requests

TIMEOUT = 15
REINTENTOS = 1  # 1 reintento extra tras el primer intento fallido
ESPERA_ENTRE_REINTENTOS = 1.5  # segundos

HEADERS = {"User-Agent": "EduPackBuilder/1.0 (uso educativo)"}


def get_json(url, params=None, headers=None, log_cb=None, contexto=""):
    """
    GET que devuelve el JSON parseado, o None si falla tras los reintentos.
    contexto: texto descriptivo para los mensajes de log (ej. "GitHub para 'agua'").
    """
    headers = headers or HEADERS
    intentos_totales = 1 + REINTENTOS
    for intento in range(1, intentos_totales + 1):
        try:
            res = requests.get(url, params=params, headers=headers, timeout=TIMEOUT)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            es_ultimo = intento == intentos_totales
            if log_cb:
                if es_ultimo:
                    log_cb(f"⚠ {contexto or url} no respondió tras {intentos_totales} intentos: {e}")
                else:
                    log_cb(f"  … reintentando {contexto or url} ({intento}/{intentos_totales})")
            if not es_ultimo:
                time.sleep(ESPERA_ENTRE_REINTENTOS)
    return None


def get_bytes(url, headers=None, log_cb=None, contexto=""):
    """GET binario (para descargar imágenes) con el mismo esquema de reintento."""
    headers = headers or HEADERS
    intentos_totales = 1 + REINTENTOS
    for intento in range(1, intentos_totales + 1):
        try:
            res = requests.get(url, headers=headers, timeout=TIMEOUT)
            res.raise_for_status()
            return res.content
        except Exception as e:
            es_ultimo = intento == intentos_totales
            if log_cb and es_ultimo:
                log_cb(f"⚠ Error descargando {contexto or url}: {e}")
            if not es_ultimo:
                time.sleep(ESPERA_ENTRE_REINTENTOS)
    return None
