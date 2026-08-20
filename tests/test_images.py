"""
Tests para edupack/images.py — es_licencia_valida() es la función que
decide qué imágenes se quedan y cuáles se descartan. Vale la pena
protegerla con tests porque ahí vivió el bug de licencias no detectadas
(cuando solo se miraba 'LicenseShortName').
"""
from edupack import images


class TestEsLicenciaValida:
    def test_licencia_vacia_es_invalida(self):
        assert images.es_licencia_valida("") is False

    def test_licencia_none_es_invalida(self):
        assert images.es_licencia_valida(None) is False

    def test_cc_by_es_valida(self):
        assert images.es_licencia_valida("CC-BY 4.0") is True

    def test_cc0_es_valida(self):
        assert images.es_licencia_valida("CC0") is True

    def test_dominio_publico_es_valida(self):
        assert images.es_licencia_valida("Public Domain") is True

    def test_licencia_no_libre_es_invalida(self):
        assert images.es_licencia_valida("All rights reserved") is False

    def test_mayusculas_no_afectan_la_deteccion(self):
        assert images.es_licencia_valida("CC-BY-SA-4.0") is True
        assert images.es_licencia_valida("cc-by-sa-4.0") is True


class TestExtraerLicenciaCommons:
    def test_usa_licenseshortname_si_existe(self):
        meta = {"LicenseShortName": {"value": "CC BY 4.0"}}
        assert images._extraer_licencia_commons(meta) == "CC BY 4.0"

    def test_recurre_a_usageterms_si_falta_licenseshortname(self):
        # Este es el caso del bug original: LicenseShortName vacío pero
        # el archivo sí es libre según otro campo.
        meta = {"UsageTerms": {"value": "Creative Commons"}}
        assert images._extraer_licencia_commons(meta) == "Creative Commons"

    def test_devuelve_vacio_si_ningun_campo_tiene_valor(self):
        meta = {}
        assert images._extraer_licencia_commons(meta) == ""
