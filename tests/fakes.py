"""
Dobles de red compartidos por los tests: ninguna prueba hace llamadas reales.
El fixture `red` vive en conftest.py y usa estas utilidades.
"""
import requests

from edupack import net


class RespuestaFalsa:
    """Mini requests.Response para tests."""

    def __init__(self, json_data=None, content=b"", headers=None, status=200, json_invalido=False):
        self._json_data = json_data
        self.content = content
        self.headers = headers or {"Content-Type": "application/json"}
        self.status_code = status
        self._json_invalido = json_invalido

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Error del servidor")

    def json(self):
        if self._json_invalido:
            raise ValueError("No se pudo decodificar el JSON")
        return self._json_data


def instalar_red(monkeypatch, respuestas):
    """Sustituye net.requests.get por un simulador programable.

    respuestas: lista de RespuestaFalsa o de Excepciones a lanzar.
    Si se acaban, repite la última. Devuelve el registro de llamadas
    (url/params/headers/timeout), que el test puede inspeccionar.
    """
    registro = []
    iterador = iter(respuestas)

    def fake_get(url, params=None, headers=None, timeout=None):
        registro.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        try:
            elemento = next(iterador)
        except StopIteration:
            elemento = respuestas[-1]
        if isinstance(elemento, Exception):
            raise elemento
        return elemento

    monkeypatch.setattr(net.requests, "get", fake_get)
    monkeypatch.setattr(net, "ESPERA_ENTRE_REINTENTOS", 0)
    return registro
