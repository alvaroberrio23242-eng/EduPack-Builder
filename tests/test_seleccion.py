"""Tests de la selección de resultados y el reempaquetado (edupack/seleccion.py)."""
import io
import os
import re
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest

from edupack import jobs, packager, seleccion

JOB_ID = "abcdef1234"
N = 10


def _escritor(carpeta, campo):
    """Escritor simulado: un archivo por elemento recibido."""
    def escribir(raiz, items):
        destino = os.path.join(raiz, carpeta)
        os.makedirs(destino, exist_ok=True)
        for i, item in enumerate(items, start=1):
            with open(os.path.join(destino, f"{i:02d}.txt"), "w", encoding="utf-8") as f:
                f.write(item[campo])
    return escribir


@pytest.fixture
def job_listo(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(jobs, "HISTORIAL_PATH", str(tmp_path / "historial.json"))
    monkeypatch.setattr(seleccion.videos, "escribir_videos", _escritor("3b_Videos", "titulo"))
    monkeypatch.setattr(seleccion.repos, "escribir_repositorios", _escritor("4_Repositorios", "nombre"))

    raiz = tmp_path / JOB_ID / "paquete"
    (raiz / "1_Contexto").mkdir(parents=True)
    (raiz / "1_Contexto" / "Guia_Docente.txt").write_text("guia", encoding="utf-8")
    (raiz / "2_Trivia_y_Evaluacion").mkdir()
    (raiz / "2_Trivia_y_Evaluacion" / "Trivia.json").write_text("{}", encoding="utf-8")

    videos_ = [{"termino": "t", "titulo": f"Video {i}", "url": f"https://archive.org/details/v{i}",
                "fuente": "Internet Archive", "licencia": "CC BY"} for i in range(N)]
    repos_ = [{"nombre": f"Repo {i}", "url": f"https://github.com/x/r{i}", "licencia": "MIT",
               "estrellas": i, "descripcion": "d", "es_plantilla": False} for i in range(3)]
    ensayos_ = [{"termino": "t", "titulo": f"Ensayo {i}", "texto": f"Texto {i}",
                 "url": f"https://es.wikipedia.org/wiki/Ensayo_{i}", "licencia": "CC BY-SA 4.0"}
                for i in range(N)]

    # ZIP original: lo que produciría el job sin selección.
    seleccion.videos.escribir_videos(str(raiz), videos_)
    seleccion.repos.escribir_repositorios(str(raiz), repos_)
    seleccion.essays.escribir_ensayos(str(raiz), ensayos_)
    zip_destino = str(tmp_path / JOB_ID / "Tema.zip")
    packager.empaquetar(str(raiz), zip_destino)

    jobs._escribir_estado(JOB_ID, {
        "id": JOB_ID, "tema": "Tema", "estado": "listo", "progreso": 1, "total": 1,
        "log": [], "error": None,
        "resultado": {
            "tema": "Tema", "objetivo_general": "o", "objetivos_especificos": [],
            "num_preguntas": 0, "num_imagenes": 0, "descartadas_por_licencia": 0,
            "imagenes": [], "videos": videos_, "repositorios": repos_, "ensayos": ensayos_,
            "guia_texto": "g", "bibliografia_texto": "b", "preguntas": [],
            "zip_path": zip_destino, "zip_nombre": "Tema.zip", "fecha": "2026-11-04 10:00",
        },
    })
    return JOB_ID


def _zip(job_id):
    return os.path.join(jobs._carpeta_job(job_id), "Tema.zip")


def _nombres(job_id):
    with zipfile.ZipFile(_zip(job_id)) as z:
        return z.namelist()


def _leer_en_zip(job_id, sufijo):
    with zipfile.ZipFile(_zip(job_id)) as z:
        nombre = next(n for n in z.namelist() if n.endswith(sufijo))
        return z.read(nombre).decode("utf-8")


def _contar(nombres, carpeta):
    return len([n for n in nombres if f"/{carpeta}/" in n])


# ---------- guardar_seleccion ----------

def test_sin_seleccion_previa_los_valores_por_defecto(job_listo):
    sel = seleccion.seleccion_de_job(jobs.obtener_job(job_listo))
    assert sel == {"version": 0, "zip_version": 0, "excluidos": []}


def test_guardar_persiste_y_sube_la_version(job_listo):
    sel = seleccion.guardar_seleccion(job_listo, ["ensayos:3", "videos:1"], 0)
    assert sel["version"] == 1
    assert sel["excluidos"] == ["ensayos:3", "videos:1"]
    again = seleccion.seleccion_de_job(jobs.obtener_job(job_listo))
    assert again["excluidos"] == ["ensayos:3", "videos:1"]


def test_guardar_la_misma_seleccion_no_sube_la_version(job_listo):
    seleccion.guardar_seleccion(job_listo, ["ensayos:3"], 0)
    sel = seleccion.guardar_seleccion(job_listo, ["ensayos:3"], 1)
    assert sel["version"] == 1


def test_version_obsoleta_es_un_conflicto(job_listo):
    seleccion.guardar_seleccion(job_listo, ["ensayos:3"], 0)
    with pytest.raises(seleccion.VersionConflicto) as exc:
        seleccion.guardar_seleccion(job_listo, [], 0)
    assert exc.value.version_actual == 1


@pytest.mark.parametrize("malo", [["imagenes:0"], ["videos:99"], ["ensayos:-1"], ["basura"], ["videos:abc"]])
def test_claves_desconocidas_se_rechazan(job_listo, malo):
    with pytest.raises(seleccion.SeleccionInvalida):
        seleccion.guardar_seleccion(job_listo, malo, 0)
    assert seleccion.seleccion_de_job(jobs.obtener_job(job_listo))["version"] == 0


@pytest.mark.parametrize("excluidos,version", [("x", 0), ([1], 0), (None, 0), ([], "0"), ([], True), ([], None)])
def test_formato_invalido_se_rechaza(job_listo, excluidos, version):
    with pytest.raises(seleccion.SeleccionInvalida):
        seleccion.guardar_seleccion(job_listo, excluidos, version)


def test_job_inexistente_o_con_id_manipulado(job_listo):
    for job_id in ("0000000000", "../x", "..\\..\\x"):
        with pytest.raises(seleccion.JobNoDisponible):
            seleccion.guardar_seleccion(job_id, [], 0)


def test_job_que_no_esta_listo(job_listo):
    estado = jobs.obtener_job(job_listo)
    estado["estado"] = "buscando_videos"
    jobs._escribir_estado(job_listo, estado)
    with pytest.raises(seleccion.JobNoDisponible):
        seleccion.guardar_seleccion(job_listo, [], 0)


def test_guardar_concurrente_solo_una_gana(job_listo):
    barrera = threading.Barrier(N)

    def worker(i):
        barrera.wait()
        try:
            seleccion.guardar_seleccion(job_listo, [f"videos:{i}"], 0)
            return "ok"
        except seleccion.VersionConflicto:
            return "conflicto"

    with ThreadPoolExecutor(max_workers=N) as ex:
        resultados = list(ex.map(worker, range(N)))

    assert resultados.count("ok") == 1
    assert resultados.count("conflicto") == N - 1
    sel = seleccion.seleccion_de_job(jobs.obtener_job(job_listo))
    assert sel["version"] == 1 and len(sel["excluidos"]) == 1


# ---------- reempaquetar ----------

def test_reempaquetar_deja_fuera_lo_excluido(job_listo):
    antes = _nombres(job_listo)
    assert _contar(antes, "5_Ensayos_y_Articulos") == N

    seleccion.guardar_seleccion(job_listo, ["ensayos:3", "ensayos:4", "videos:0", "repositorios:2"], 0)
    sel = seleccion.reempaquetar(job_listo)

    assert sel["zip_version"] == sel["version"] == 1
    despues = _nombres(job_listo)
    assert all(n.startswith("paquete/") for n in despues)
    assert _contar(despues, "5_Ensayos_y_Articulos") == N - 2
    assert _contar(despues, "3b_Videos") == N - 1
    assert _contar(despues, "4_Repositorios") == 2
    biblio = _leer_en_zip(job_listo, "Bibliografia.txt")
    assert "Ensayo 3" not in biblio and "Ensayo 4" not in biblio
    assert "Ensayo 5" in biblio
    assert "Video 0" not in biblio and "Video 1" in biblio
    assert "Repo 2" not in biblio and "Repo 1" in biblio
    assert any(n.endswith("Guia_Docente.txt") for n in despues)
    assert any(n.endswith("Trivia.json") for n in despues)


def test_reempaquetar_no_toca_los_originales(job_listo):
    antes = jobs.obtener_job(job_listo)["resultado"]
    carpeta_ensayos = os.path.join(jobs._carpeta_job(job_listo), "paquete", "5_Ensayos_y_Articulos")
    archivos_antes = sorted(os.listdir(carpeta_ensayos))

    seleccion.guardar_seleccion(job_listo, ["ensayos:3"], 0)
    seleccion.reempaquetar(job_listo)

    assert jobs.obtener_job(job_listo)["resultado"] == antes
    assert sorted(os.listdir(carpeta_ensayos)) == archivos_antes


def test_reempaquetar_sin_exclusiones_conserva_todo(job_listo):
    antes = sorted(_nombres(job_listo))
    seleccion.reempaquetar(job_listo)
    assert sorted(_nombres(job_listo)) == antes


def test_restaurar_todo_recupera_lo_excluido(job_listo):
    seleccion.guardar_seleccion(job_listo, ["ensayos:3"], 0)
    seleccion.reempaquetar(job_listo)
    seleccion.guardar_seleccion(job_listo, [], 1)
    seleccion.reempaquetar(job_listo)
    assert _contar(_nombres(job_listo), "5_Ensayos_y_Articulos") == N


def test_zip_desactualizado_se_detecta(job_listo):
    seleccion.guardar_seleccion(job_listo, ["ensayos:3"], 0)
    sel = seleccion.seleccion_de_job(jobs.obtener_job(job_listo))
    assert sel["version"] != sel["zip_version"]


def test_reempaquetado_en_curso_se_rechaza(job_listo):
    seleccion._EN_PROCESO.add(job_listo)
    try:
        with pytest.raises(seleccion.ReempaquetadoEnCurso):
            seleccion.reempaquetar(job_listo)
    finally:
        seleccion._EN_PROCESO.discard(job_listo)


def test_zip_ocupado_no_deja_basura_ni_rompe_el_original(job_listo, monkeypatch):
    real = os.replace

    def falso(origen, destino):
        if str(destino).endswith(".zip"):
            raise PermissionError("en uso")
        return real(origen, destino)

    monkeypatch.setattr(seleccion.os, "replace", falso)
    monkeypatch.setattr(seleccion.time, "sleep", lambda s: None)
    antes = sorted(_nombres(job_listo))

    seleccion.guardar_seleccion(job_listo, ["ensayos:3"], 0)
    with pytest.raises(seleccion.ZipOcupado):
        seleccion.reempaquetar(job_listo)

    assert not os.path.exists(_zip(job_listo) + ".tmp")
    assert job_listo not in seleccion._EN_PROCESO
    assert sorted(_nombres(job_listo)) == antes
    assert not [d for d in os.listdir(jobs._carpeta_job(job_listo)) if d.startswith("_sel_")]


# ---------- rutas HTTP ----------

@pytest.fixture
def cliente_dueno(cliente, job_listo):
    with cliente.session_transaction() as s:
        s["mis_jobs"] = [job_listo]
    return cliente


def test_api_guardar_seleccion_ok(cliente_dueno, job_listo):
    r = cliente_dueno.post(f"/api/seleccion/{job_listo}", json={"excluidos": ["ensayos:2"], "version": 0})
    assert r.status_code == 200
    assert r.get_json() == {"version": 1, "zip_version": 0, "excluidos": ["ensayos:2"]}


def test_api_seleccion_errores(cliente_dueno, job_listo):
    url = f"/api/seleccion/{job_listo}"
    assert cliente_dueno.post(url, data="no es json").status_code == 400
    assert cliente_dueno.post(url, json={"excluidos": ["imagenes:0"], "version": 0}).status_code == 400
    r = cliente_dueno.post(url, json={"excluidos": [], "version": 5})
    assert r.status_code == 409 and r.get_json()["version_actual"] == 0
    assert cliente_dueno.post("/api/seleccion/0000000000", json={"excluidos": [], "version": 0}).status_code == 404
    assert cliente_dueno.post("/api/seleccion/zzz", json={"excluidos": [], "version": 0}).status_code == 404


def test_api_otra_sesion_recibe_403(cliente_dueno, app_modulo, job_listo):
    ajeno = app_modulo.app.test_client()
    r = ajeno.post(f"/api/seleccion/{job_listo}", json={"excluidos": ["ensayos:1"], "version": 0})
    assert r.status_code == 403
    r = ajeno.post(f"/api/reempaquetar/{job_listo}", json={})
    assert r.status_code == 403
    assert seleccion.seleccion_de_job(jobs.obtener_job(job_listo))["excluidos"] == []


def test_api_reempaquetar_exige_json(cliente_dueno, job_listo):
    assert cliente_dueno.post(f"/api/reempaquetar/{job_listo}").status_code == 400
    assert cliente_dueno.post(f"/api/reempaquetar/{job_listo}", data="x=1").status_code == 400


def test_flujo_completo_por_http_y_descarga(cliente_dueno, job_listo):
    cliente_dueno.post(f"/api/seleccion/{job_listo}", json={"excluidos": ["ensayos:3"], "version": 0})
    r = cliente_dueno.post(f"/api/reempaquetar/{job_listo}", json={})
    assert r.status_code == 200 and r.get_json()["zip_version"] == 1

    r = cliente_dueno.get(f"/descargar/{job_listo}")
    assert r.status_code == 200
    datos = r.data
    r.close()
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        assert _contar(z.namelist(), "5_Ensayos_y_Articulos") == N - 1


def test_vista_previa_muestra_casillas_y_respeta_lo_excluido(cliente_dueno, job_listo):
    html = cliente_dueno.get(f"/vista-previa/{job_listo}").get_data(as_text=True)
    caja = re.search(r'<input[^>]*data-clave="videos:0"[^>]*>', html)
    assert caja and " checked" in caja.group(0)
    assert 'id="seleccion-panel"' in html

    cliente_dueno.post(f"/api/seleccion/{job_listo}", json={"excluidos": ["videos:0"], "version": 0})
    html = cliente_dueno.get(f"/vista-previa/{job_listo}").get_data(as_text=True)
    caja = re.search(r'<input[^>]*data-clave="videos:0"[^>]*>', html)
    assert caja and " checked" not in caja.group(0)
    assert "todavía no está en el ZIP" in html

