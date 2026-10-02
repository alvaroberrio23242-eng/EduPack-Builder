"""
Fixtures compartidas de la suite. Solo tests: no levanta servidores ni
hace llamadas de red reales.
"""
import importlib
import time

import pytest

from fakes import instalar_red

CLAVE_DE_PRUEBA = "clave-de-prueba-suficientemente-larga-0123456789"


@pytest.fixture
def red(monkeypatch):
    """Sustituye net.requests.get por un simulador programable.

    Uso dentro de un test:
        registro = red([RespuestaFalsa(json_data={...})])
        registro = red([requests.exceptions.Timeout("t"), ...])
    """
    def instalar(respuestas):
        return instalar_red(monkeypatch, respuestas)

    return instalar


@pytest.fixture
def jobs_en_tmp(tmp_path, monkeypatch):
    """DATA_DIR/HISTORIAL_PATH en carpeta temporal y fuentes externas
    sustitutas: el job termina al instante y sin red."""
    data_dir = tmp_path / "data" / "jobs"
    data_dir.mkdir(parents=True)
    from edupack import jobs
    monkeypatch.setattr(jobs, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(jobs, "HISTORIAL_PATH", str(data_dir / "historial.json"))

    monkeypatch.setattr(jobs.images, "buscar_y_descargar",
                        lambda *a, **k: {"descargadas": [], "descartadas_por_licencia": 0})
    monkeypatch.setattr(jobs.videos, "buscar_videos_multi", lambda *a, **k: [])
    monkeypatch.setattr(jobs.videos, "escribir_videos", lambda *a, **k: None)
    monkeypatch.setattr(jobs.repos, "buscar_repositorios_multi", lambda *a, **k: [])
    monkeypatch.setattr(jobs.repos, "escribir_repositorios", lambda *a, **k: None)
    monkeypatch.setattr(jobs.essays, "buscar_ensayos_multi", lambda *a, **k: [])
    monkeypatch.setattr(jobs.essays, "escribir_ensayos", lambda *a, **k: None)
    yield


@pytest.fixture
def app_modulo(monkeypatch):
    """Recarga el módulo app con una SECRET_KEY de prueba válida."""
    monkeypatch.setenv("SECRET_KEY", CLAVE_DE_PRUEBA)
    monkeypatch.delenv("EDUPACK_DEV", raising=False)
    import app
    return importlib.reload(app)


@pytest.fixture
def cliente(app_modulo):
    """Cliente HTTP con su propia sesión (cookies)."""
    app_modulo.app.config["TESTING"] = True
    return app_modulo.app.test_client()


def esperar_estado_final(job_id, timeout=10):
    """Espera a que un job termine (listo o error); solo para tests."""
    from edupack import jobs
    limite = time.time() + timeout
    while time.time() < limite:
        job = jobs.obtener_job(job_id)
        if job and job["estado"] in ("listo", "error"):
            return job
        time.sleep(0.05)
    raise TimeoutError(f"El job {job_id} no terminó en {timeout}s")
