"""
Tests del ciclo de vida de un job. crear_job() corre en un hilo aparte,
así que estos tests hacen polling con timeout hasta ver el estado final.

Los recursos (imagenes/videos/repositorios/ensayos) se dejan en False
para que el job no dependa de internet: así el test es rápido y estable
en CI. Las funciones que sí llaman APIs externas (images.py, videos.py,
repos.py, essays.py) se prueban por separado con mocks si hace falta,
no aquí.

Desde la migración a data/jobs/<id>/estado.json, cada test usa su propia
carpeta temporal (tmp_path), así que no hace falta limpiar nada entre
tests: no hay estado compartido en memoria.
"""
import time
import pytest

from edupack import jobs


@pytest.fixture
def jobs_en_carpeta_temporal(tmp_path, monkeypatch):
    """Redirige DATA_DIR/HISTORIAL_PATH a una carpeta temporal por test,
    para no ensuciar ni depender de data/jobs/ real."""
    data_dir = tmp_path / "data" / "jobs"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr(jobs, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(jobs, "HISTORIAL_PATH", str(data_dir / "historial.json"))
    yield


def _esperar_estado_final(job_id, timeout=10):
    """Espera a que el job termine (listo o error) o lanza si se agota el tiempo."""
    limite = time.time() + timeout
    while time.time() < limite:
        job = jobs.obtener_job(job_id)
        if job and job["estado"] in ("listo", "error"):
            return job
        time.sleep(0.05)
    raise TimeoutError(f"El job {job_id} no terminó en {timeout}s")


RECURSOS_SIN_RED = {"imagenes": False, "videos": False, "repositorios": False, "ensayos": False}


def test_crear_job_devuelve_un_id_unico(jobs_en_carpeta_temporal):
    id_a = jobs.crear_job("Tema A", "obj", "ctx", [], [], 6, RECURSOS_SIN_RED)
    id_b = jobs.crear_job("Tema B", "obj", "ctx", [], [], 6, RECURSOS_SIN_RED)
    assert id_a != id_b
    assert len(id_a) == 10  # uuid4().hex[:10]
    # Espera a que ambos hilos terminen para no dejarlos corriendo después
    # de que el test acabe (evita interferencia entre tests).
    _esperar_estado_final(id_a)
    _esperar_estado_final(id_b)


def test_job_recien_creado_empieza_en_cola(jobs_en_carpeta_temporal):
    job_id = jobs.crear_job("Tema", "obj", "ctx", [], [], 6, RECURSOS_SIN_RED)
    job = jobs.obtener_job(job_id)
    assert job is not None
    assert job["estado"] in ("en_cola", "generando_contenido", "empaquetando", "listo")
    # Espera a que termine antes de salir del test, para no dejar el hilo
    # corriendo (evita interferencia entre tests).
    _esperar_estado_final(job_id)


def test_obtener_job_con_id_inexistente_devuelve_none(jobs_en_carpeta_temporal):
    assert jobs.obtener_job("id-que-no-existe") is None


def test_job_sin_recursos_de_red_termina_listo(jobs_en_carpeta_temporal):
    job_id = jobs.crear_job("Fotosíntesis", "entender el proceso", "clase de biología",
                             [], ["fotosíntesis"], 6, RECURSOS_SIN_RED)
    job = _esperar_estado_final(job_id)
    assert job["estado"] == "listo"
    assert job["resultado"] is not None
    assert job["resultado"]["zip_path"].endswith(".zip")


def test_job_queda_en_historial_despues_de_terminar(jobs_en_carpeta_temporal):
    job_id = jobs.crear_job("Tema histórico", "obj", "ctx", [], [], 6, RECURSOS_SIN_RED)
    _esperar_estado_final(job_id)
    historial = jobs.obtener_historial()
    ids_en_historial = [h["id"] for h in historial]
    assert job_id in ids_en_historial


def test_preguntas_invalidas_no_rompen_el_job(jobs_en_carpeta_temporal):
    preguntas_incompletas = [{"pregunta": "", "opciones": [], "respuesta_correcta": ""}]
    job_id = jobs.crear_job("Tema", "obj", "ctx", preguntas_incompletas, [], 6, RECURSOS_SIN_RED)
    job = _esperar_estado_final(job_id)
    assert job["estado"] == "listo"
    assert job["resultado"]["num_preguntas"] == 0


def test_estado_sobrevive_a_una_lectura_fresca_del_archivo(jobs_en_carpeta_temporal):
    """Este es el test clave de la migración: simula que otro proceso
    (otro worker de gunicorn) lee el job sin haber estado presente
    cuando se creó — algo que con _JOBS en RAM era imposible."""
    job_id = jobs.crear_job("Tema persistente", "obj", "ctx", [], [], 6, RECURSOS_SIN_RED)
    job = _esperar_estado_final(job_id)
    assert job["estado"] == "listo"

    # Lectura "fresca": llama a obtener_job() de nuevo como si fuera
    # una petición HTTP completamente nueva.
    job_releido = jobs.obtener_job(job_id)
    assert job_releido["estado"] == "listo"
    assert job_releido["resultado"]["tema"] == "Tema persistente"
