"""
Tests para edupack/content.py — construir_guia() y validar_preguntas()
son funciones puras (no tocan red ni disco salvo escribir_contenido),
así que son las más fáciles y rentables de testear primero.
"""
from edupack import content


class TestConstruirGuia:
    def test_incluye_el_tema_en_mayusculas(self):
        guia = content.construir_guia("historia del jazz", "aprender ritmos", ["ritmo 1"], "clase de 10mo")
        assert "HISTORIA DEL JAZZ" in guia

    def test_usa_placeholder_si_objetivo_general_esta_vacio(self):
        guia = content.construir_guia("tema", "", [], "contexto")
        assert "(sin definir)" in guia

    def test_usa_placeholder_si_no_hay_objetivos_especificos(self):
        guia = content.construir_guia("tema", "Objetivo general", [], "contexto")
        assert "(sin definir)" in guia

    def test_usa_placeholder_si_contexto_esta_vacio(self):
        guia = content.construir_guia("tema", "objetivo general", ["específico 1"], "   ")
        assert "(sin definir)" in guia

    def test_incluye_objetivo_general_y_contexto_cuando_existen(self):
        guia = content.construir_guia("tema", "Objetivo A", [], "Contexto B")
        assert "Objetivo A" in guia
        assert "Contexto B" in guia

    def test_incluye_objetivos_especificos_numerados(self):
        guia = content.construir_guia("tema", "General", ["Primero", "Segundo"], "Contexto")
        assert "1. Primero" in guia
        assert "2. Segundo" in guia

    def test_ignora_objetivos_especificos_vacios(self):
        guia = content.construir_guia("tema", "General", ["", "  ", "Válido"], "Contexto")
        assert "1. Válido" in guia
        assert "2." not in guia


class TestConstruirBibliografia:
    def test_bibliografia_vacia_si_no_hay_fuentes(self):
        bib = content.construir_bibliografia([], [], [], [])
        assert "No se encontraron fuentes" in bib

    def test_incluye_seccion_de_ensayos(self):
        ensayos = [{"titulo": "Fotosíntesis", "url": "https://es.wikipedia.org/wiki/Fotosíntesis", "licencia": "CC BY-SA 4.0"}]
        bib = content.construir_bibliografia([], [], ensayos, [])
        assert "ARTÍCULOS Y ENSAYOS" in bib
        assert "Fotosíntesis" in bib

    def test_incluye_seccion_de_imagenes_con_autor_y_licencia(self):
        imagenes = [{"descripcion": "Célula vegetal", "autor": "Juan Pérez", "url_fuente": "https://commons.wikimedia.org/x",
                     "licencia": "CC-BY-SA-4.0", "fuente": "Wikimedia Commons"}]
        bib = content.construir_bibliografia(imagenes, [], [], [])
        assert "IMÁGENES" in bib
        assert "Juan Pérez" in bib

    def test_incluye_las_cuatro_secciones_cuando_hay_de_todo(self):
        imagenes = [{"descripcion": "img", "autor": "a", "url_fuente": "u", "licencia": "cc0", "fuente": "Openverse"}]
        videos = [{"titulo": "vid", "url": "u", "licencia": "cc0", "fuente": "Internet Archive"}]
        ensayos = [{"titulo": "art", "url": "u", "licencia": "CC BY-SA"}]
        repos = [{"nombre": "repo", "url": "u", "licencia": "MIT", "estrellas": 5}]
        bib = content.construir_bibliografia(imagenes, videos, ensayos, repos)
        for seccion in ("ARTÍCULOS Y ENSAYOS", "IMÁGENES", "VIDEOS", "REPOSITORIOS Y PROYECTOS"):
            assert seccion in bib


class TestValidarPreguntas:
    def test_pregunta_completa_pasa(self):
        preguntas = [{
            "pregunta": "¿Capital de Colombia?",
            "opciones": ["Bogotá", "Medellín", "Cali"],
            "respuesta_correcta": "Bogotá",
            "explicacion": "Es la capital.",
        }]
        validas = content.validar_preguntas(preguntas)
        assert len(validas) == 1
        assert validas[0]["pregunta"] == "¿Capital de Colombia?"

    def test_pregunta_sin_texto_se_descarta(self):
        preguntas = [{
            "pregunta": "   ",
            "opciones": ["A", "B"],
            "respuesta_correcta": "A",
        }]
        assert content.validar_preguntas(preguntas) == []

    def test_pregunta_con_menos_de_dos_opciones_se_descarta(self):
        preguntas = [{
            "pregunta": "¿Pregunta?",
            "opciones": ["Única opción"],
            "respuesta_correcta": "Única opción",
        }]
        assert content.validar_preguntas(preguntas) == []

    def test_respuesta_correcta_que_no_esta_en_opciones_se_descarta(self):
        preguntas = [{
            "pregunta": "¿Pregunta?",
            "opciones": ["A", "B"],
            "respuesta_correcta": "C",
        }]
        assert content.validar_preguntas(preguntas) == []

    def test_opciones_con_espacios_en_blanco_se_ignoran(self):
        preguntas = [{
            "pregunta": "¿Pregunta?",
            "opciones": ["A", "  ", "B"],
            "respuesta_correcta": "A",
        }]
        validas = content.validar_preguntas(preguntas)
        assert validas[0]["opciones"] == ["A", "B"]

    def test_mezcla_de_preguntas_validas_e_invalidas(self):
        preguntas = [
            {"pregunta": "", "opciones": ["A", "B"], "respuesta_correcta": "A"},
            {"pregunta": "¿Buena?", "opciones": ["X", "Y"], "respuesta_correcta": "X"},
        ]
        validas = content.validar_preguntas(preguntas)
        assert len(validas) == 1
        assert validas[0]["pregunta"] == "¿Buena?"
