"""
Sanitización de nombres de archivo, reutilizable por todo el proyecto
(hoy: el ZIP del paquete en jobs.py y los .txt de ensayos en essays.py).

Cubre:
- caracteres inválidos en Windows (< > : " / \\ | ? * y control 0-31 / 127)
- '/' y '\\' de Linux (nunca pueden formar rutas)
- caracteres Unicode invisibles de formato/combina (Cf: zero-width, bidi)
- path traversal ("../../etc/passwd", "..\\..\\windows")
- nombres reservados de Windows (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
- nombres vacíos o solo de relleno -> fallback
- nombres demasiado largos -> truncado conservando la extensión
"""
import unicodedata

MAX_LARGO_DEFECTO = 100

# Caracteres prohibidos en nombres de archivo en Windows + / y \ en Linux.
_CARACTERES_INVALIDOS = '<>:"/\\|?*'

# Categorías Unicode que no deben viajar en un nombre de archivo:
# Cc = control, Cf = formato (zero-width, bidi), Cs = surrogates.
_CATEGORIAS_MALAS = ("Cc", "Cf", "Cs")

_RESERVADAS_WINDOWS = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def _limpiar(valor):
    """Devuelve una cadena sin caracteres peligrosos (o '' si no era texto)."""
    if not isinstance(valor, str):
        return ""
    texto = unicodedata.normalize("NFC", valor)
    texto = "".join(c for c in texto if unicodedata.category(c) not in _CATEGORIAS_MALAS)
    texto = "".join(
        c if (c not in _CARACTERES_INVALIDOS and ord(c) >= 32 and ord(c) != 127) else "_"
        for c in texto
    )
    texto = texto.strip(" ")      # espacios a los lados
    texto = texto.lstrip(".")     # evita archivos ocultos y ".."
    texto = texto.rstrip(". ")    # Windows rechaza puntos/espacios al final
    return texto


def _truncar(texto, max_largo, extension=""):
    """Corta a max_largo caracteres sin perder la extensión."""
    if len(texto) <= max_largo:
        return texto
    if extension and len(extension) < max_largo:
        raiz = texto[: max_largo - len(extension)].rstrip(". ")
        return raiz + extension
    raiz, punto, ext = texto.rpartition(".")
    if punto and ext and len(ext) + 1 <= max_largo // 2:
        return raiz[: max_largo - len(ext) - 1].rstrip(". ") + "." + ext
    return texto[:max_largo].rstrip(". ")


def sanitizar_nombre(nombre, extension="", max_largo=MAX_LARGO_DEFECTO, fallback="archivo"):
    """Devuelve un nombre de archivo seguro.

    - nombre: texto de entrada (tema, título...). Si no es str, se usa fallback.
    - extension: extensión que debe cerrar el nombre (".zip"). Si el nombre ya
      termina en ella no se duplica; si trae otra extensión propia se conserva
      y se añade la pedida al final.
    - max_largo: longitud máxima total (raíz + extensión).
    - fallback: nombre a usar cuando no queda nada válido.
    """
    ext_pedida = _limpiar(extension)
    if ext_pedida and not ext_pedida.startswith("."):
        ext_pedida = "." + ext_pedida

    texto = _limpiar(nombre)

    # Windows reserva el nombre hasta el PRIMER punto (NUL.txt, CON.tar.gz).
    if texto.split(".", 1)[0].upper() in _RESERVADAS_WINDOWS:
        texto = "_" + texto

    raiz, punto, ext_propia = texto.rpartition(".")
    if not punto:
        raiz, ext_propia = texto, ""
    if not raiz:
        raiz = fallback
    texto = raiz + (f".{ext_propia}" if ext_propia else "")

    if ext_pedida and not texto.lower().endswith(ext_pedida.lower()):
        texto += ext_pedida

    texto = _truncar(texto, max_largo, ext_pedida)

    if not texto.strip(" ."):
        texto = fallback + ext_pedida
    return texto
