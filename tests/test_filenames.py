"""
Tests de P1.2 — edupack/filenames.py: todo nombre que llegue al disco
(zip del paquete y .txt de ensayos) pasa por sanitizar_nombre().
"""
from edupack.filenames import sanitizar_nombre


class TestCaracteresInvalidos:
    def test_caracteres_invalidos_de_windows_se_reemplazan(self):
        nombre = sanitizar_nombre('a<b>c:d"e/f\\g|h?i*j')
        assert not any(c in nombre for c in '<>:"/\\|?*')

    def test_barra_incluida_no_forma_rutas(self):
        assert "/" not in sanitizar_nombre("sub/carpeta/archivo")

    def test_barra_invertida_no_forma_rutas(self):
        assert "\\" not in sanitizar_nombre("sub\\carpeta\\archivo")

    def test_caracteres_de_control_se_quitan(self):
        nombre = sanitizar_nombre("hola\x00\x1f\x7f mundo")
        assert "\x00" not in nombre
        assert "\x1f" not in nombre
        assert "\x7f" not in nombre

    def test_salto_de_linea_no_se_conserva(self):
        assert "\n" not in sanitizar_nombre("linea1\nlinea2")


class TestUnicode:
    def test_tildes_y_enye_se_conservan(self):
        assert sanitizar_nombre("fotosíntesis") == "fotosíntesis"
        assert "ñ" in sanitizar_nombre("español")

    def test_caracteres_de_formato_zero_width_se_quitan(self):
        assert sanitizar_nombre("a\u200bb\u200cc") == "abc"

    def test_marcas_bidi_se_quitan(self):
        assert sanitizar_nombre("a\u202eb") == "ab"

    def test_no_se_rompe_con_emoji(self):
        assert sanitizar_nombre("tema 🌱 verde").startswith("tema")


class TestPathTraversal:
    def test_dos_puntos_con_barra_no_escapa(self):
        nombre = sanitizar_nombre("../../etc/passwd")
        assert "/" not in nombre
        assert not nombre.startswith("..")

    def test_dos_puntos_con_barra_invertida_no_escapa(self):
        nombre = sanitizar_nombre("..\\..\\windows\\system32")
        assert "\\" not in nombre

    def test_nombre_que_es_solo_dos_puntos_usa_el_fallback(self):
        assert sanitizar_nombre("..") == "archivo"

    def test_ruta_absoluta_no_se_conserva(self):
        assert "/" not in sanitizar_nombre("/etc/shadow")

    def test_no_quedan_puntos_iniciales(self):
        assert not sanitizar_nombre(".oculto").startswith(".")


class TestNombresReservados:
    def test_con_mayusculas(self):
        assert sanitizar_nombre("CON") == "_CON"

    def test_con_minusculas(self):
        assert sanitizar_nombre("con") == "_con"

    def test_con_extension(self):
        assert sanitizar_nombre("con.txt") == "_con.txt"

    def test_todas_las_reservadas(self):
        reservadas = ["PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"]
        for r in reservadas:
            assert sanitizar_nombre(r) == "_" + r, r

    def test_reservada_como_tema_de_zip(self):
        assert sanitizar_nombre("NUL", extension=".zip") == "_NUL.zip"

    def test_no_reservada_no_se_toca(self):
        assert sanitizar_nombre("contenido") == "contenido"


class TestVaciosYFallback:
    def test_cadena_vacia_usa_fallback(self):
        assert sanitizar_nombre("") == "archivo"

    def test_solo_espacios_usa_fallback(self):
        assert sanitizar_nombre("     ") == "archivo"

    def test_none_usa_fallback(self):
        assert sanitizar_nombre(None) == "archivo"

    def test_numero_usa_fallback(self):
        assert sanitizar_nombre(12345) == "archivo"

    def test_fallback_personalizado(self):
        assert sanitizar_nombre("", fallback="EduPack") == "EduPack"

    def test_fallback_con_extension(self):
        assert sanitizar_nombre("", extension=".zip", fallback="EduPack") == "EduPack.zip"

    def test_solo_puntos_usa_fallback(self):
        assert sanitizar_nombre("....") == "archivo"


class TestExtensiones:
    def test_agrega_la_extension_pedida(self):
        assert sanitizar_nombre("tema", extension=".zip") == "tema.zip"

    def test_no_duplica_si_ya_la_trae(self):
        assert sanitizar_nombre("tema.zip", extension=".zip") == "tema.zip"

    def test_extension_sin_punto_inicial(self):
        assert sanitizar_nombre("tema", extension="zip") == "tema.zip"

    def test_conserva_la_extension_propia_del_nombre(self):
        assert sanitizar_nombre("informe.final") == "informe.final"

    def test_extension_tambien_se_limpia(self):
        assert "/" not in sanitizar_nombre("tema", extension=".z/p")


class TestLongitud:
    def test_nombre_largo_se_trunca(self):
        nombre = sanitizar_nombre("x" * 500)
        assert len(nombre) <= 100

    def test_al_truncar_conserva_la_extension(self):
        nombre = sanitizar_nombre("x" * 500, extension=".zip")
        assert nombre.endswith(".zip")
        assert len(nombre) <= 100

    def test_al_truncar_conserva_la_extension_propia(self):
        nombre = sanitizar_nombre("y" * 500 + ".pdf")
        assert nombre.endswith(".pdf")
        assert len(nombre) <= 100

    def test_max_largo_personalizado(self):
        assert len(sanitizar_nombre("z" * 300, max_largo=20)) <= 20

    def test_no_trunca_si_cabe(self):
        assert sanitizar_nombre("tema corto") == "tema corto"

    def test_reservada_con_varios_puntos(self):
        assert sanitizar_nombre("CON.tar.gz") == "_CON.tar.gz"

    def test_no_reservada_solo_por_empezar_igual(self):
        # Windows no reserva "CONtexto", solo el componente inicial exacto.
        assert sanitizar_nombre("CONtexto") == "CONtexto"

    def test_largo_maximo_con_extension_y_reservada(self):
        nombre = sanitizar_nombre("NUL", extension=".zip", max_largo=50)
        assert nombre.startswith("_NUL")
        assert nombre.endswith(".zip")
        assert len(nombre) <= 50


class TestCombinados:
    def test_tema_hostil_completo(self):
        nombre = sanitizar_nombre('../CON:"*?|<> \x00.txt', extension=".zip")
        assert "/" not in nombre and "\\" not in nombre
        assert not any(c in nombre for c in '<>:"|?*')
        assert nombre.endswith(".zip")
        assert len(nombre) <= 100

    def test_nombre_normal_de_tema_se_mantiene_legible(self):
        assert sanitizar_nombre("La Revolución Industrial", extension=".zip") == \
            "La Revolución Industrial.zip"
