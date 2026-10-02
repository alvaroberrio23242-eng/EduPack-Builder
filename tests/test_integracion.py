"""
Tests de integración con las 5 fuentes externas, siempre con mocks:
nunca se hace una llamada real (el fixture `red` sustituye net.requests.get).

Cubre, por fuente:
  - respuesta válida
  - respuesta vacía
  - error HTTP (5xx)
  - timeout
  - JSON inválido
  - respuesta con forma inesperada (p.ej. lista donde debería haber dict)

Y verifica que se conservan las URLs y los headers originales.
"""
import pytest
import requests

from edupack import essays, images, jobs, repos, videos
from fakes import RespuestaFalsa

# ---------------------------------------------------------------- respuestas
PAGINA_IMAGEN = {"query": {"pages": {"1": {"imageinfo": [{
    "url": "https://upload.wikimedia.org/wikipedia/commons/f/foto.jpg",
    "extmetadata": {
        "License": {"value": "cc-by"},
        "ObjectName": {"value": "Foto de prueba"},
        "Artist": {"value": "Autor X"},
    },
}]}}}}

RESULTADO_OPENVERSE = {"results": [{
    "url": "https://openverse.example/foto.png",
    "title": "Foto openverse",
    "creator": "Autor Y",
    "license": "cc0",
    "foreign_landing_url": "https://openverse.example/foto",
}]}

PAGINA_VIDEO = {"query": {"pages": {"2": {"imageinfo": [{
    "url": "https://upload.wikimedia.org/wikipedia/commons/v/video.webm",
    "mime": "video/webm",
    "extmetadata": {"License": {"value": "cc0"}, "ObjectName": {"value": "Video"}},
}]}}}}

ARCHIVE = {"response": {"docs": [
    {"identifier": "mi-video", "title": "Video de prueba", "licenseurl": "cc0"},
]}}

GITHUB = {"items": [{
    "full_name": "ejemplo/repo",
    "description": "Un repo",
    "stargazers_count": 42,
    "license": {"spdx_id": "MIT"},
    "html_url": "https://github.com/ejemplo/repo",
    "is_template": False,
}]}

WIKIPEDIA = {"query": {"pages": {"3": {
    "title": "Fotosíntesis",
    "extract": "La fotosíntesis es el proceso...",
}}}}

VACIA_IMAGENES = {"query": {"pages": {}}}
VACIA_OPENVERSE = {"results": []}
VACIA_ARCHIVE = {"response": {"docs": []}}
VACIA_GITHUB = {"total_count": 0, "items": []}
VACIA_WIKIPEDIA = {"query": {"pages": {}}}

FORMA_RARA = [1, 2, 3]
NULLS = {"query": None, "results": None, "items": None, "response": None}

# (nombre, fn(termino, log_cb) -> lista, válida, vacía, url esperada)
FUENTES = [
    ("wikimedia_imagenes", lambda t, log: images._buscar_commons(t, 3, log),
     PAGINA_IMAGEN, VACIA_IMAGENES, "https://commons.wikimedia.org/w/api.php"),
    ("openverse", lambda t, log: images._buscar_openverse(t, 3, log),
     RESULTADO_OPENVERSE, VACIA_OPENVERSE, "https://api.openverse.org/v1/images/"),
    ("wikimedia_videos", lambda t, log: videos._buscar_commons_video(t, 3, log),
     PAGINA_VIDEO, VACIA_IMAGENES, "https://commons.wikimedia.org/w/api.php"),
    ("internet_archive", lambda t, log: videos._buscar_internet_archive(t, 3, log),
     ARCHIVE, VACIA_ARCHIVE, "https://archive.org/advancedsearch.php"),
    ("github", lambda t, log: repos.buscar_repositorios(t, 3, log),
     GITHUB, VACIA_GITHUB, "https://api.github.com/search/repositories"),
    ("wikipedia", lambda t, log: essays.buscar_ensayos(t, 3, log),
     WIKIPEDIA, VACIA_WIKIPEDIA, "https://es.wikipedia.org/w/api.php"),
]
NOMBRES = [f[0] for f in FUENTES]
ARG_IDS = [(f[0], f[1], f[2], f[3], f[4]) for f in FUENTES]


def _dos(respuesta):
    """GitHub hace 2 peticiones (repos y plantillas): se programa la repetición."""
    return [respuesta, respuesta]


def _fallos(excepcion):
    return [excepcion, excepcion]


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_respuesta_valida_devuelve_resultados(nombre, buscar, valida, vacia, url, red):
    red(_dos(RespuestaFalsa(json_data=valida)))
    assert len(buscar("agua", None)) == 1


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_respuesta_vacia_devuelve_lista_vacia(nombre, buscar, valida, vacia, url, red):
    red(_dos(RespuestaFalsa(json_data=vacia)))
    assert buscar("agua", None) == []


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_error_http_devuelve_lista_vacia(nombre, buscar, valida, vacia, url, red):
    red(_fallos(RespuestaFalsa(status=500)))
    assert buscar("agua", None) == []


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_error_http_registra_el_fallo(nombre, buscar, valida, vacia, url, red):
    logs = []
    red(_fallos(RespuestaFalsa(status=500)))
    buscar("agua", logs.append)
    assert any("no respondió" in m for m in logs)


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_timeout_devuelve_lista_vacia(nombre, buscar, valida, vacia, url, red):
    red(_fallos(requests.exceptions.Timeout("sin respuesta")))
    assert buscar("agua", None) == []


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_json_invalido_devuelve_lista_vacia(nombre, buscar, valida, vacia, url, red):
    red(_fallos(RespuestaFalsa(json_invalido=True)))
    assert buscar("agua", None) == []


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_respuesta_con_forma_inesperada_devuelve_lista_vacia(nombre, buscar, valida, vacia, url, red):
    red(_dos(RespuestaFalsa(json_data=FORMA_RARA)))
    assert buscar("agua", None) == []


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_respuesta_con_campos_null_no_explota(nombre, buscar, valida, vacia, url, red):
    red(_dos(RespuestaFalsa(json_data=NULLS)))
    assert buscar("agua", None) == []


@pytest.mark.parametrize("nombre,buscar,valida,vacia,url", ARG_IDS, ids=NOMBRES)
def test_conserva_la_url_de_la_fuente(nombre, buscar, valida, vacia, url, red):
    registro = red(_dos(RespuestaFalsa(json_data=vacia)))
    buscar("agua", None)
    assert registro[0]["url"] == url


def test_github_conserva_sus_headers_especiales(red):
    registro = red(_dos(RespuestaFalsa(json_data=VACIA_GITHUB)))
    repos.buscar_repositorios("agua", 3)
    assert registro[0]["headers"] == repos.HEADERS
    assert registro[0]["headers"]["Accept"] == "application/vnd.github+json"
    assert registro[0]["headers"]["User-Agent"] == "EduPackBuilder/1.0"


def test_las_demas_fuentes_usan_user_agent_edupack(red):
    registro = red(_dos(RespuestaFalsa(json_data=VACIA_IMAGENES)))
    images._buscar_commons("agua", 3)
    assert registro[0]["headers"]["User-Agent"].startswith("EduPackBuilder/")


def test_github_hace_dos_consultas_repositorios_y_plantillas(red):
    registro = red(_dos(RespuestaFalsa(json_data=VACIA_GITHUB)))
    repos.buscar_repositorios("agua", 3)
    assert len(registro) == 2
    assert registro[1]["params"]["q"] == "agua is:template"


def test_las_busquedas_multi_siguen_aunque_todas_las_fuentes_fallen(red, tmp_path):
    """El flujo completo multi-término no se tumba cuando no hay red."""
    red(_fallos(requests.exceptions.ConnectionError("sin red")))
    logs = []
    resumen = images.buscar_y_descargar(["a", "b"], 3, str(tmp_path / "salida"),
                                        log_cb=logs.append)
    assert resumen["descargadas"] == []
    assert resumen["descartadas_por_licencia"] == 0
    assert any("no respondió" in m for m in logs)


def test_videos_y_ensayos_multi_no_se_tumban_sin_red(red):
    red(_fallos(requests.exceptions.ConnectionError("sin red")))
    logs = []
    assert videos.buscar_videos_multi(["agua"], 3, None, logs.append) == []
    assert essays.buscar_ensayos_multi(["agua"], 3, None, logs.append) == []
