"""
Tests de P0.2 — concurrencia en edupack/jobs.py.

_log(), _set_estado() y _actualizar_progreso() hacen read-modify-write
sobre estado.json. Si dos hilos leen a la vez, modifican cada uno su copia
y escriben, el último pisa al primero (logs perdidos, progreso/total
incoherentes). La corrección es serializar esa lectura-modificación-escritura
con el _LOCK existente.

Los tests lanzan ~10 hilos que sincronizan con threading.Barrier (sin
sleeps arbitrarios) y luego releen el estado desde disco.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from edupack import jobs

HILOS = 10
# Motivo del cambio (auditoría §6): obtener_job() solo acepta ahora ids con
# el formato real que genera crear_job() (uuid4().hex[:10], hex puro) para
# impedir path traversal. El id anterior, "concurrenc", no es hex y ya no
# se puede leer desde disco; se sustituye por uno con el mismo formato real.
JOB_ID = "abcdef1234"


@pytest.fixture
def job_en_carpeta_temporal(tmp_path, monkeypatch):
    """Un job con estado inicial escrito, en una carpeta temporal."""
    monkeypatch.setattr(jobs, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(jobs, "HISTORIAL_PATH", str(tmp_path / "historial.json"))
    jobs._escribir_estado(JOB_ID, {
        "id": JOB_ID, "tema": "Tema", "estado": "en_cola",
        "progreso": 0, "total": 1, "log": [], "error": None, "resultado": None,
    })
    return JOB_ID


def _lanzar(cantidad, funcion):
    """Arranca `cantidad` hilos sincronizados con una misma Barrier."""
    barrera = threading.Barrier(cantidad)

    def worker(indice):
        barrera.wait()
        funcion(indice)

    with ThreadPoolExecutor(max_workers=cantidad) as executor:
        futuros = [executor.submit(worker, i) for i in range(cantidad)]
        for f in futuros:
            f.result()  # propaga cualquier excepción del hilo


def test_log_concurrente_no_pierde_mensajes(job_en_carpeta_temporal):
    def accion(i):
        jobs._log(job_en_carpeta_temporal, f"mensaje-{i}")

    _lanzar(HILOS, accion)

    estado = jobs.obtener_job(job_en_carpeta_temporal)
    assert sorted(estado["log"]) == sorted(f"mensaje-{i}" for i in range(HILOS))


def test_log_concurrente_no_duplica_ni_descarta(job_en_carpeta_temporal):
    def accion(i):
        jobs._log(job_en_carpeta_temporal, f"linea-{i % 3}")

    _lanzar(HILOS, accion)

    estado = jobs.obtener_job(job_en_carpeta_temporal)
    assert len(estado["log"]) == HILOS  # ni más (escrituras pisadas) ni menos


def test_actualizar_progreso_conserva_el_par_coherente(job_en_carpeta_temporal):
    """progreso y total se escriben juntos: el par final debe ser el de un
    mismo hilo, nunca progreso de uno y total de otro."""
    def accion(i):
        jobs._actualizar_progreso(job_en_carpeta_temporal, progreso=i, total=i + 100)

    _lanzar(HILOS, accion)

    estado = jobs.obtener_job(job_en_carpeta_temporal)
    assert estado["total"] - estado["progreso"] == 100
    assert 0 <= estado["progreso"] < HILOS


def test_set_estado_concurrente_termina_en_un_estado_valido(job_en_carpeta_temporal):
    estados = ["generando_contenido", "buscando_imagenes", "buscando_videos",
               "buscando_repositorios", "buscando_ensayos"]

    def accion(i):
        jobs._set_estado(job_en_carpeta_temporal, estados[i % len(estados)])

    _lanzar(HILOS, accion)

    estado = jobs.obtener_job(job_en_carpeta_temporal)
    assert estado["estado"] in estados


def test_logs_y_progreso_mixtos_no_corrompen_el_archivo(job_en_carpeta_temporal):
    """Mitad hilos escriben log, mitad progreso: el JSON debe seguir
    legible y las dos escrituras deben convivir (no pisarse)."""
    def accion(i):
        if i % 2 == 0:
            jobs._log(job_en_carpeta_temporal, f"mixto-{i}")
        else:
            jobs._actualizar_progreso(job_en_carpeta_temporal, progreso=i, total=i + 100)

    _lanzar(HILOS, accion)

    estado = jobs.obtener_job(job_en_carpeta_temporal)
    assert estado is not None
    assert len(estado["log"]) == HILOS // 2
    assert estado["total"] - estado["progreso"] == 100


def test_estado_sigue_siendo_json_valido_tras_escrituras_concurrentes(job_en_carpeta_temporal):
    def accion(i):
        jobs._log(job_en_carpeta_temporal, f"json-{i}")

    _lanzar(HILOS, accion)

    import json
    with open(jobs._ruta_estado(job_en_carpeta_temporal), "r", encoding="utf-8") as f:
        datos = json.load(f)  # lanza si quedó a medio escribir
    assert len(datos["log"]) == HILOS
