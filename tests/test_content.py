"""
Tests para edupack/content.py — construir_guia() y validar_preguntas()
son funciones puras (no tocan red ni disco salvo escribir_contenido),
así que son las más fáciles y rentables de testear primero.
"""
from edupack import content


class TestConstruirGuia:
    def test_incluye_el_tema_en_mayusculas(self):
        guia = content.construir_guia("historia del jazz", "aprender ritmos", "clase de 10mo")
        assert "HISTORIA DEL JAZZ" in guia

    def test_usa_placeholder_si_objetivos_esta_vacio(self):
        guia = content.construir_guia("tema", "", "contexto")
        assert "(sin definir)" in guia

    def test_usa_placeholder_si_contexto_esta_vacio(self):
        guia = content.construir_guia("tema", "objetivos", "   ")
        assert "(sin definir)" in guia

    def test_incluye_objetivos_y_contexto_cuando_existen(self):
        guia = content.construir_guia("tema", "Objetivo A", "Contexto B")
        assert "Objetivo A" in guia
        assert "Contexto B" in guia


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
