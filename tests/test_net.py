"""
Tests de P1.1 — edupack/net.py es el único punto de salida a la red.

Se mockea net.requests.get (nunca se hace una llamada real) y se pone
ESPERA_ENTRE_REINTENTOS a 0 para que los tests de fallo sean instantáneos.
El fixture `red` y RespuestaFalsa vienen de conftest.py / fakes.py.
"""
import requests

from edupack import net
from fakes import RespuestaFalsa


class TestGetJson:
    def test_respuesta_valida_devuelve_el_json(self, red):
        red([RespuestaFalsa(json_data={"query": {"pages": {}}})])
        logs = []
        assert net.get_json("https://ejemplo.com/api", log_cb=logs.append) == {"query": {"pages": {}}}
        assert logs == []

    def test_error_http_devuelve_none_y_registra(self, red):
        red([RespuestaFalsa(status=500), RespuestaFalsa(status=500)])
        logs = []
        assert net.get_json("https://ejemplo.com/api", log_cb=logs.append, contexto="Ejemplo") is None
        assert any("no respondió" in m for m in logs)
        assert any("Ejemplo" in m for m in logs)

    def test_timeout_devuelve_none(self, red):
        red([requests.exceptions.Timeout("timeout"), requests.exceptions.Timeout("timeout")])
        logs = []
        assert net.get_json("https://ejemplo.com/api", log_cb=logs.append) is None

    def test_json_invalido_devuelve_none(self, red):
        red([RespuestaFalsa(json_invalido=True), RespuestaFalsa(json_invalido=True)])
        logs = []
        assert net.get_json("https://ejemplo.com/api", log_cb=logs.append) is None
        assert logs  # avisa del fallo

    def test_reintenta_una_vez_y_triunfa(self, red):
        registro = red([
            requests.exceptions.ConnectionError("cortado"),
            RespuestaFalsa(json_data={"ok": True}),
        ])
        logs = []
        assert net.get_json("https://ejemplo.com/api", log_cb=logs.append) == {"ok": True}
        assert len(registro) == 2

    def test_no_reintenta_si_no_hay_log_cb(self, red):
        registro = red([requests.exceptions.ConnectionError("cortado"),
                        RespuestaFalsa(json_data={"ok": True})])
        assert net.get_json("https://ejemplo.com/api") == {"ok": True}
        assert len(registro) == 2

    def test_acepta_json_de_forma_inesperada(self, red):
        """net solo parsea; el filtrado por forma le toca a cada módulo."""
        red([RespuestaFalsa(json_data=[1, 2, 3])])
        assert net.get_json("https://ejemplo.com/api") == [1, 2, 3]

    def test_envia_headers_personalesizados(self, red):
        registro = red([RespuestaFalsa(json_data={})])
        headers_github = {"User-Agent": "EduPackBuilder/1.0", "Accept": "application/vnd.github+json"}
        net.get_json("https://api.github.com/search/repositories", headers=headers_github)
        assert registro[0]["headers"] == headers_github

    def test_usa_headers_por_defecto_si_no_se_pasan(self, red):
        registro = red([RespuestaFalsa(json_data={})])
        net.get_json("https://ejemplo.com/api")
        assert registro[0]["headers"] == net.HEADERS

    def test_usa_el_timeout_centralizado(self, red):
        registro = red([RespuestaFalsa(json_data={})])
        net.get_json("https://ejemplo.com/api")
        assert registro[0]["timeout"] == net.TIMEOUT

    def test_registra_el_reintento_antes_del_fallo_final(self, red):
        red([requests.exceptions.ConnectionError("cortado"),
             requests.exceptions.ConnectionError("cortado")])
        logs = []
        net.get_json("https://ejemplo.com/api", log_cb=logs.append, contexto="Fuente X")
        assert any("reintentando Fuente X" in m for m in logs)

    def test_sin_log_cb_no_explota(self, red):
        red([RespuestaFalsa(status=503), RespuestaFalsa(status=503)])
        assert net.get_json("https://ejemplo.com/api") is None


class TestGetRespuesta:
    def test_devuelve_la_respuesta_completa(self, red):
        respuesta = RespuestaFalsa(json_data={"a": 1}, headers={"Content-Type": "image/jpeg"})
        red([respuesta])
        assert net.get_respuesta("https://ejemplo.com/img.jpg") is respuesta

    def test_error_http_devuelve_none(self, red):
        red([RespuestaFalsa(status=404), RespuestaFalsa(status=404)])
        assert net.get_respuesta("https://ejemplo.com/img.jpg") is None


class TestGetBytes:
    def test_devuelve_el_contenido_binario(self, red):
        red([RespuestaFalsa(content=b"imagedata")])
        assert net.get_bytes("https://ejemplo.com/img.jpg") == b"imagedata"

    def test_error_devuelve_none_y_registra(self, red):
        red([requests.exceptions.Timeout("t"), requests.exceptions.Timeout("t")])
        logs = []
        assert net.get_bytes("https://ejemplo.com/img.jpg", log_cb=logs.append, contexto="una imagen") is None
        assert any("Error descargando una imagen" in m for m in logs)

    def test_reintenta_y_triunfa(self, red):
        registro = red([requests.exceptions.ConnectionError("x"),
                        RespuestaFalsa(content=b"ok")])
        assert net.get_bytes("https://ejemplo.com/img.jpg") == b"ok"
        assert len(registro) == 2
