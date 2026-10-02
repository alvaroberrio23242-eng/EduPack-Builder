"""
Tests de P2.3 — accesibilidad básica y contraste (WCAG AA).

Nada de librerías externas: se comprueba el HTML servido y el CSS real,
para que una regresión futura (quitar aria-hidden, bajar la opacidad de
la tinta) haga fallar la suite.
"""
from conftest import esperar_estado_final

CSS_PATH = "css/style.css"


def _css(app_modulo):
    ruta = app_modulo.app.static_folder + "/" + CSS_PATH
    with open(ruta, encoding="utf-8") as f:
        return f.read()


class TestAtributosAria:
    def test_video_de_fondo_oculto_para_lectores(self, cliente, app_modulo):
        html = cliente.get("/").get_data(as_text=True)
        assert 'aria-hidden="true"' in html
        assert "<video" in html
        video = html.split("<video", 1)[1].split(">", 1)[0]
        assert 'aria-hidden="true"' in video

    def test_svg_de_progreso_ocultos(self, cliente, app_modulo, jobs_en_tmp):
        resp = cliente.post("/generar", data={
            "tema": "Tema aria", "objetivo_general": "og",
            "terminos_imagenes": "agua",
        }, follow_redirects=False)
        job_id = resp.headers["Location"].rsplit("/", 1)[-1]
        esperar_estado_final(job_id)
        html = cliente.get(f"/progreso/{job_id}").get_data(as_text=True)
        assert "<svg aria-hidden=" in html
        # ningún SVG decorativo puede quedar sin aria-hidden
        assert html.count("<svg") == html.count('<svg aria-hidden="true"')

    def test_fase_actual_lleva_aria_current(self, cliente, jobs_en_tmp):
        resp = cliente.post("/generar", data={
            "tema": "Tema aria", "objetivo_general": "og",
            "terminos_imagenes": "agua",
        }, follow_redirects=False)
        job_id = resp.headers["Location"].rsplit("/", 1)[-1]
        esperar_estado_final(job_id)
        html = cliente.get(f"/progreso/{job_id}").get_data(as_text=True)
        assert 'setAttribute("aria-current", "step")' in html
        assert 'removeAttribute("aria-current")' in html


class TestContraste:
    def test_tinta_suave_alcanza_contraste_aa(self, app_modulo):
        css = _css(app_modulo)
        assert "--ink-soft: rgba(43,33,25,.70)" in css
        # 0.62 quedaba en ~4.36:1 sobre #FAF3E7 (bajo AA para texto pequeño)
        assert "--ink-soft: rgba(43,33,25,.62)" not in css

    def test_tinta_tenue_alcanza_contraste_aa(self, app_modulo):
        css = _css(app_modulo)
        assert "--ink-faint: rgba(43,33,25,.64)" in css
        # 0.38 quedaba en ~2.25:1 sobre #FAF3E7
        assert "--ink-faint: rgba(43,33,25,.38)" not in css


class TestMovimiento:
    def test_respeta_prefers_reduced_motion(self, app_modulo):
        assert "prefers-reduced-motion" in _css(app_modulo)
