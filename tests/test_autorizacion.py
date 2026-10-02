"""
Tests de P1.3 — autorización de rutas de job.

Nadie puede leer ni descargar el trabajo de otra persona con solo conocer
el id: cada job queda ligado a la sesión que lo creó (token en la cookie,
no hace falta cuenta ni base de datos de usuarios).
"""
from conftest import esperar_estado_final


def _crear_job(cliente, tema="Tema autorización"):
    resp = cliente.post("/generar", data={
        "tema": tema,
        "objetivo_general": "comprender el tema",
        "objetivo_especifico[]": ["identificar ideas"],
        "contexto": "prueba",
        "terminos_imagenes": "agua",
        "max_por_termino": "1",
    }, follow_redirects=False)
    assert resp.status_code == 302
    return resp.headers["Location"].rsplit("/", 1)[-1]


def _otra_sesion(app_modulo):
    app_modulo.app.config["TESTING"] = True
    return app_modulo.app.test_client()


class TestDescarga:
    def test_el_creador_puede_descargar_su_zip(self, cliente, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        resp = cliente.get(f"/descargar/{job_id}")
        assert resp.status_code == 200
        cd = resp.headers.get("Content-Disposition", "")
        assert "attachment" in cd
        assert ".zip" in cd

    def test_otra_sesion_no_puede_descargar(self, cliente, app_modulo, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        ajeno = _otra_sesion(app_modulo)
        assert ajeno.get(f"/descargar/{job_id}").status_code == 403

    def test_job_inexistente_devuelve_404(self, cliente, jobs_en_tmp):
        assert cliente.get("/descargar/0000000000").status_code == 404

    def test_sin_sesion_ni_job_devuelve_404(self, cliente, app_modulo, jobs_en_tmp):
        ajeno = _otra_sesion(app_modulo)
        assert ajeno.get("/descargar/0000000000").status_code == 404


class TestOtrasRutasDelJob:
    def test_progreso_del_creador_se_ve(self, cliente, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        assert cliente.get(f"/progreso/{job_id}").status_code == 200

    def test_progreso_ajeno_esta_protegido(self, cliente, app_modulo, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        ajeno = _otra_sesion(app_modulo)
        assert ajeno.get(f"/progreso/{job_id}").status_code == 403

    def test_api_de_estado_ajena_esta_protegida(self, cliente, app_modulo, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        ajeno = _otra_sesion(app_modulo)
        resp = ajeno.get(f"/api/estado/{job_id}")
        assert resp.status_code == 403
        assert resp.get_json()["error"] == "no autorizado"

    def test_api_de_estado_del_creador_responde_con_el_job(self, cliente, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        resp = cliente.get(f"/api/estado/{job_id}")
        assert resp.status_code == 200
        assert resp.get_json()["id"] == job_id

    def test_vista_previa_del_creador_se_ve(self, cliente, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        assert cliente.get(f"/vista-previa/{job_id}").status_code == 200

    def test_vista_previa_ajena_esta_protegida(self, cliente, app_modulo, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        ajeno = _otra_sesion(app_modulo)
        assert ajeno.get(f"/vista-previa/{job_id}").status_code == 403


class TestHistorial:
    def test_historial_solo_muestra_los_mios(self, cliente, jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        html = cliente.get("/historial").get_data(as_text=True)
        assert job_id in html
        assert "Tema autorización" in html

    def test_historial_de_otra_sesion_no_expone_mis_jobs(self, cliente, app_modulo,
                                                         jobs_en_tmp):
        job_id = _crear_job(cliente)
        esperar_estado_final(job_id)
        ajeno = _otra_sesion(app_modulo)
        resp = ajeno.get("/historial")
        assert resp.status_code == 200
        assert job_id not in resp.get_data(as_text=True)
        assert "Tema autorización" not in resp.get_data(as_text=True)


class TestRegistroDePropiedad:
    def test_registrar_no_duplica(self, app_modulo):
        with app_modulo.app.test_request_context():
            app_modulo.registrar_job_propio("abc123")
            app_modulo.registrar_job_propio("abc123")
            assert app_modulo.session["mis_jobs"] == ["abc123"]

    def test_la_lista_de_mis_jobs_tiene_tope(self, app_modulo):
        with app_modulo.app.test_request_context():
            for i in range(app_modulo.LIMITE_MIS_JOBS + 50):
                app_modulo.registrar_job_propio(f"job{i}")
            lista = app_modulo.session["mis_jobs"]
            assert len(lista) == app_modulo.LIMITE_MIS_JOBS
            assert lista[-1] == f"job{app_modulo.LIMITE_MIS_JOBS + 49}"
            assert "job0" not in lista

    def test_sin_sesion_no_se_puede_descargar_nada(self, app_modulo, jobs_en_tmp):
        with app_modulo.app.test_request_context("/descargar/abc"):
            assert app_modulo.es_job_propio("abc") is False
