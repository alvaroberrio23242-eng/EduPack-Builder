"""
Tests de cierre — validación de job_id (auditoría §6).

Los ids legítimos son uuid4().hex[:10] (hex puro, 10 caracteres).
Todo lo demás debe morir en 404 ANTES de construir rutas en disco: sin
esto, un id manipulado desde la URL ("..", "..\\..\\x") permitía leer
estado.json fuera de data/jobs/ (path traversal en lectura).
"""
from edupack import jobs


def _estado_falso(ruta_base):
    """Crea un estado.json FUERA de data/jobs (a un nivel de distancia)."""
    import json
    import os
    nivel_arriba = os.path.dirname(ruta_base)
    ruta = os.path.join(nivel_arriba, "estado.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"id": "fuera", "estado": "listo", "log": [], "tema": "SECRETO"}, f)
    return ruta


class TestFormatoDeId:
    def test_ids_validos_de_un_job_real(self, jobs_en_tmp):
        job_id = jobs.crear_job("Tema", "og", [], "ctx", [], [], 6)
        assert jobs.es_id_valido(job_id)
        assert jobs.obtener_job(job_id) is not None

    def test_id_con_dos_puntos_devuelve_none(self, jobs_en_tmp):
        assert jobs.obtener_job("..") is None

    def test_id_con_backslash_devuelve_none(self, jobs_en_tmp):
        assert jobs.obtener_job("..\\..\\etc") is None

    def test_id_con_barra_devuelve_none(self, jobs_en_tmp):
        assert jobs.obtener_job("../../etc") is None

    def test_id_largo_devuelve_none(self, jobs_en_tmp):
        assert jobs.obtener_job("a" * 200) is None

    def test_id_hex_de_otra_longitud_devuelve_none(self, jobs_en_tmp):
        assert jobs.obtener_job("abc123") is None  # 6 chars: no es un id legítimo
        assert jobs.obtener_job("abcdef123456") is None  # 12 chars

    def test_id_con_caracteres_no_hex_devuelve_none(self, jobs_en_tmp):
        assert jobs.obtener_job("zzzzzzzzzz") is None

    def test_id_none_o_no_texto_devuelve_none(self, jobs_en_tmp):
        assert jobs.obtener_job(None) is None
        assert jobs.obtener_job(1234567890) is None


class TestNoLecturaFueraDeDataJobs:
    def test_traversal_no_lee_estado_fuera_del_alcance(self, jobs_en_tmp, monkeypatch):
        """Crea data/jobs/../estado.json (fuera del alcance) y comprueba
        que obtener_job("..") no lo devuelve."""
        import os
        _estado_falso(jobs.DATA_DIR)
        assert os.path.exists(os.path.join(os.path.dirname(jobs.DATA_DIR), "estado.json"))
        assert jobs.obtener_job("..") is None

    def test_traversal_tampoco_resuelve_zip_historial(self, jobs_en_tmp):
        assert jobs.ruta_zip_historial("..") is None
        assert jobs.ruta_zip_historial("..\\..\\x") is None


class TestRespuestasHttp:
    def _post(self, cliente, tema="Tema"):
        return cliente.post("/generar", data={
            "tema": tema, "objetivo_general": "og", "terminos_imagenes": "agua",
        }, follow_redirects=False)

    def _id_real(self, cliente):
        return self._post(cliente).headers["Location"].rsplit("/", 1)[-1]

    def test_ids_hostiles_en_las_cuatro_rutas_devuelven_404(self, cliente, jobs_en_tmp):
        hostiles = ["..", "..%5C..%5Cx", "%2e%2e", "zzzzzzzzzz", "abc123"]
        rutas = ["/progreso/{}", "/api/estado/{}", "/vista-previa/{}", "/descargar/{}"]
        for hostil in hostiles:
            for plantilla in rutas:
                resp = cliente.get(plantilla.format(hostil))
                assert resp.status_code == 404, (plantilla, hostil, resp.status_code)

    def test_un_id_legitimo_sigue_funcionando(self, cliente, jobs_en_tmp):
        job_id = self._id_real(cliente)
        assert cliente.get(f"/progreso/{job_id}").status_code == 200
