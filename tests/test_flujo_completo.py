"""
Tests de P2.1 — flujo completo del usuario, de punta a punta y sin red:

  GET /  ->  POST /generar  ->  /progreso  ->  /api/estado  ->
  /vista-previa  ->  /descargar (ZIP real)  ->  /historial

Además cubre las validaciones del formulario (sin red, sin servidores:
el cliente de test de Flask recorre las mismas rutas que un navegador).
"""
import io
import os
import zipfile

from conftest import esperar_estado_final
from edupack import jobs


def _datos(tema="La fotosíntesis", objetivo="comprender el proceso", terminos="agua, luz"):
    return {
        "tema": tema,
        "objetivo_general": objetivo,
        "objetivo_especifico[]": ["identificar las fases", "explicar el papel de la clorofila"],
        "contexto": "clase de biología de 4º",
        "terminos_imagenes": terminos,
        "max_por_termino": "2",
        "pregunta_texto[]": ["¿Qué gas se libera?"],
        "pregunta_correcta[]": ["Oxígeno"],
        "pregunta_explicacion[]": ["Oxígeno, producto de la fotosíntesis"],
        "pregunta_opciones[]": ["Dióxido de carbono|Agua|Oxígeno"],
    }


def test_flujo_completo_de_principio_a_fin(cliente, jobs_en_tmp):
    # 1. el formulario carga
    inicio = cliente.get("/")
    assert inicio.status_code == 200

    # 2. se envía y redirige al progreso
    resp = cliente.post("/generar", data=_datos(), follow_redirects=False)
    assert resp.status_code == 302
    job_id = resp.headers["Location"].rsplit("/", 1)[-1]
    assert len(job_id) == 10

    # 3. la página de progreso responde mientras corre
    assert cliente.get(f"/progreso/{job_id}").status_code == 200

    # 4. el job termina y la API lo refleja
    job = esperar_estado_final(job_id)
    assert job["estado"] == "listo"
    api = cliente.get(f"/api/estado/{job_id}").get_json()
    assert api["estado"] == "listo"
    assert api["resultado"]["tema"] == "La fotosíntesis"
    assert api["resultado"]["objetivos_especificos"] == [
        "identificar las fases", "explicar el papel de la clorofila"]
    assert api["resultado"]["num_preguntas"] == 1

    # 5. vista previa con el contenido
    vista = cliente.get(f"/vista-previa/{job_id}")
    assert vista.status_code == 200
    html = vista.get_data(as_text=True)
    assert "La fotosíntesis" in html

    # 6. descarga: un ZIP real y legible, con el quiz dentro
    descarga = cliente.get(f"/descargar/{job_id}")
    assert descarga.status_code == 200
    assert descarga.data[:2] == b"PK"
    quiz_en_zip = False
    with zipfile.ZipFile(io.BytesIO(descarga.data)) as zf:
        nombres = zf.namelist()
        assert nombres, "el ZIP no puede venir vacío"
        assert zf.testzip() is None, "el ZIP está corrupto"
        for nombre in nombres:
            if nombre.endswith((".md", ".html", ".txt", ".json")):
                if "Oxígeno".encode("utf-8") in zf.read(nombre):
                    quiz_en_zip = True
    assert quiz_en_zip, "la pregunta del formulario debe viajar dentro del paquete"

    # 7. aparece en el historial con enlace de descarga
    historial = cliente.get("/historial").get_data(as_text=True)
    assert job_id in historial
    assert "La fotosíntesis" in historial


def test_tema_con_caracteres_hostiles_sigue_funcionando(cliente, jobs_en_tmp):
    """El nombre del tema no puede romper el ZIP ni escapar de su carpeta."""
    resp = cliente.post("/generar", data=_datos(tema="../../CON:¿qué*?"), follow_redirects=False)
    job_id = resp.headers["Location"].rsplit("/", 1)[-1]
    job = esperar_estado_final(job_id)
    assert job["estado"] == "listo"
    zip_path = job["resultado"]["zip_path"]
    # el ZIP queda dentro de la carpeta del job, con un nombre sin rutas
    assert os.path.dirname(zip_path) == os.path.join(jobs.DATA_DIR, job_id)
    nombre_zip = os.path.basename(zip_path)
    assert "/" not in nombre_zip
    assert not nombre_zip.startswith("..")
    assert nombre_zip.lower().endswith(".zip")
    descarga = cliente.get(f"/descargar/{job_id}")
    assert descarga.status_code == 200
    assert descarga.data[:2] == b"PK"


def test_varios_jobs_en_paralelo_no_se_pisan(cliente, jobs_en_tmp):
    ids = []
    for i in range(3):
        resp = cliente.post("/generar", data=_datos(tema=f"Tema {i}"), follow_redirects=False)
        ids.append(resp.headers["Location"].rsplit("/", 1)[-1])
    assert len(set(ids)) == 3
    for job_id, n in zip(ids, range(3)):
        job = esperar_estado_final(job_id)
        assert job["estado"] == "listo"
        assert job["resultado"]["tema"] == f"Tema {n}"


def test_valida_tema_vacio(cliente, jobs_en_tmp):
    datos = _datos(tema="   ")
    resp = cliente.post("/generar", data=datos)
    assert resp.status_code == 200
    assert "Escribe un tema" in resp.get_data(as_text=True)


def test_valida_objetivo_general_vacio(cliente, jobs_en_tmp):
    datos = _datos()
    datos["objetivo_general"] = ""
    resp = cliente.post("/generar", data=datos)
    assert resp.status_code == 200
    assert "objetivo general" in resp.get_data(as_text=True).lower()


def test_valida_sin_terminos_de_busqueda(cliente, jobs_en_tmp):
    datos = _datos(terminos="  ,  ")
    resp = cliente.post("/generar", data=datos)
    assert resp.status_code == 200
    assert "término" in resp.get_data(as_text=True)


def test_max_por_termino_invalido_usa_el_valor_por_defecto(cliente, jobs_en_tmp):
    datos = _datos()
    datos["max_por_termino"] = "no-es-un-numero"
    resp = cliente.post("/generar", data=datos, follow_redirects=False)
    assert resp.status_code == 302
    job_id = resp.headers["Location"].rsplit("/", 1)[-1]
    job = esperar_estado_final(job_id)
    assert job["estado"] == "listo"
