"""
Tests de P0.1 — la app no debe arrancar nunca con una SECRET_KEY predefinida.

Cada test controla el entorno (SECRET_KEY / EDUPACK_DEV / FLASK_ENV) con
monkeypatch y (re)carga app.py, para probar los cuatro caminos:

1. clave explícita en el entorno (producción)
2. producción sin clave -> RuntimeError claro
3. opt-in de desarrollo explícito (EDUPACK_DEV=1)
4. opt-in de tests (app.config["TESTING"])

FLASK_ENV solo aparece para demostrar que la app ya NO depende de ella.
"""
import importlib
import os

import pytest


CLAVES_HARDCODEADAS_ANTERIORES = (
    "cambia-esto-en-produccion",
    "dev-only-insecure-key",
    "changeme",
)


def _cargar_app(monkeypatch, secret_key=None, dev=None, flask_env=None):
    """(Re)ejecuta app.py con el entorno ya puesto. Devuelve el módulo."""
    if secret_key is None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", secret_key)

    if dev is None:
        monkeypatch.delenv("EDUPACK_DEV", raising=False)
    else:
        monkeypatch.setenv("EDUPACK_DEV", dev)

    if flask_env is None:
        monkeypatch.delenv("FLASK_ENV", raising=False)
    else:
        monkeypatch.setenv("FLASK_ENV", flask_env)

    import app
    return importlib.reload(app)


class TestProduccion:
    def test_produccion_con_clave_usa_la_del_entorno(self, monkeypatch):
        clave = "una-clave-de-produccion-suficientemente-larga"
        modulo = _cargar_app(monkeypatch, secret_key=clave)
        assert modulo.app.secret_key == clave
        assert modulo.resolver_secret_key({}) == clave

    def test_produccion_sin_clave_falla_con_error_claro(self, monkeypatch):
        with pytest.raises(RuntimeError) as exc:
            _cargar_app(monkeypatch)
        assert "SECRET_KEY" in str(exc.value)

    def test_el_error_indica_como_configurarla(self, monkeypatch):
        with pytest.raises(RuntimeError) as exc:
            _cargar_app(monkeypatch)
        assert "EDUPACK_DEV" in str(exc.value)

    def test_no_depende_de_flask_env_production(self, monkeypatch):
        """FLASK_ENV=production sin SECRET_KEY no puede bastar (var. deprecada)."""
        with pytest.raises(RuntimeError):
            _cargar_app(monkeypatch, flask_env="production")

    def test_no_depende_de_flask_env_development(self, monkeypatch):
        """Tampoco un FLASK_ENV=development habilita una clave por defecto."""
        with pytest.raises(RuntimeError):
            _cargar_app(monkeypatch, flask_env="development")


class TestOptInDesarrollo:
    def test_edupack_dev_genera_clave_efimera(self, monkeypatch):
        modulo = _cargar_app(monkeypatch, dev="1")
        clave = modulo.app.secret_key
        assert clave
        assert len(clave) == 64  # secrets.token_hex(32)
        assert clave not in CLAVES_HARDCODEADAS_ANTERIORES

    def test_clave_de_desarrollo_es_aleatoria_entre_cargas(self, monkeypatch):
        modulo = _cargar_app(monkeypatch, dev="1")
        primera = modulo.resolver_secret_key({})
        segunda = modulo.resolver_secret_key({})
        assert primera != segunda

    def test_edupack_dev_distinto_de_1_no_activa_el_modo(self, monkeypatch):
        with pytest.raises(RuntimeError):
            _cargar_app(monkeypatch, dev="0")

    def test_clave_de_desarrollo_es_hexadecimal(self, monkeypatch):
        modulo = _cargar_app(monkeypatch, dev="1")
        int(modulo.app.secret_key, 16)  # lanza si no es hex
        for hardcodeada in CLAVES_HARDCODEADAS_ANTERIORES:
            assert hardcodeada not in modulo.app.secret_key


class TestModoTests:
    def test_testing_genera_clave_efimera(self, monkeypatch):
        modulo = _cargar_app(monkeypatch, secret_key="clave-temporal-para-cargar-app")
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("EDUPACK_DEV", raising=False)
        clave = modulo.resolver_secret_key({"TESTING": True})
        assert len(clave) == 64
        assert clave not in CLAVES_HARDCODEADAS_ANTERIORES

    def test_sin_testing_ni_optin_sigue_fallando(self, monkeypatch):
        modulo = _cargar_app(monkeypatch, secret_key="clave-temporal-para-cargar-app")
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("EDUPACK_DEV", raising=False)
        with pytest.raises(RuntimeError):
            modulo.resolver_secret_key({"TESTING": False})
        with pytest.raises(RuntimeError):
            modulo.resolver_secret_key({})


class TestSinSecretosHardcodeados:
    def test_no_existe_clave_por_defecto_en_el_codigo(self, monkeypatch):
        """Si falta la variable, la app levanta RuntimeError: nunca arranca
        con una de las claves que había antes en app.py."""
        with pytest.raises(RuntimeError):
            _cargar_app(monkeypatch)

    def test_este_archivo_no_escribe_secret_key_real(self, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        assert not os.environ.get("SECRET_KEY")
