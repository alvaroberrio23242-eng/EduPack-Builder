"""
Generación de contenido pedagógico.
Nada aquí está atado a un tema fijo: el tema, los objetivos y las preguntas
de trivia los define quien usa la herramienta a través del formulario.
"""
import os
import json


def construir_guia(tema: str, objetivo_general: str, objetivos_especificos: list, contexto: str) -> str:
    """
    Arma el texto de la guía docente. Antes había un solo campo "objetivos"
    en texto libre; ahora se distingue el objetivo general (una sola meta de
    la unidad) de los objetivos específicos (una lista de metas puntuales),
    que es como se estructura una guía docente real.
    """
    lineas = [
        "=" * 60,
        f" GUÍA DOCENTE: {tema.upper()}",
        "=" * 60,
        "",
        " OBJETIVO GENERAL:",
        objetivo_general.strip() or "(sin definir)",
        "",
        " OBJETIVOS ESPECÍFICOS:",
    ]
    especificos_validos = [o.strip() for o in objetivos_especificos if o.strip()]
    if especificos_validos:
        lineas.extend(f"  {i}. {o}" for i, o in enumerate(especificos_validos, start=1))
    else:
        lineas.append("  (sin definir)")
    lineas += [
        "",
        " CONTEXTO:",
        contexto.strip() or "(sin definir)",
        "",
    ]
    return "\n".join(lineas)


def validar_preguntas(preguntas: list) -> list:
    """Filtra preguntas incompletas para no romper el paquete final."""
    validas = []
    for i, p in enumerate(preguntas, start=1):
        texto = (p.get("pregunta") or "").strip()
        opciones = [o.strip() for o in p.get("opciones", []) if o.strip()]
        correcta = (p.get("respuesta_correcta") or "").strip()
        if not texto or len(opciones) < 2 or correcta not in opciones:
            continue
        validas.append({
            "id": i,
            "pregunta": texto,
            "opciones": opciones,
            "respuesta_correcta": correcta,
            "explicacion": (p.get("explicacion") or "").strip(),
        })
    return validas


def construir_bibliografia(imagenes: list, videos: list, ensayos: list, repositorios: list) -> str:
    """
    Compila automáticamente una bibliografía a partir de TODO lo que
    realmente se encontró y se incluyó en el paquete (no algo que el usuario
    tenga que escribir a mano). Cada entrada trae fuente, título/descripción,
    autor cuando aplica, licencia y enlace — formato simple tipo ficha.
    """
    lineas = ["=" * 60, " BIBLIOGRAFÍA Y FUENTES", "=" * 60, ""]

    def _seccion(titulo, items, formateador):
        if not items:
            return
        lineas.append(f" {titulo} ({len(items)})")
        lineas.append("-" * 40)
        for i, item in enumerate(items, start=1):
            lineas.append(f"[{i}] {formateador(item)}")
        lineas.append("")

    _seccion("ARTÍCULOS Y ENSAYOS", ensayos, lambda e:
              f"{e['titulo']} — {e['url']} (licencia: {e['licencia']})")
    _seccion("IMÁGENES", imagenes, lambda im:
              f"{im.get('descripcion', 'Sin descripción')} — autor: {im.get('autor', 'No especificado')} "
              f"— {im.get('url_fuente', im.get('url_descarga', ''))} (licencia: {im.get('licencia', 'N/D')}, fuente: {im.get('fuente', 'N/D')})")
    _seccion("VIDEOS", videos, lambda v:
              f"{v['titulo']} — {v['url']} (licencia: {v['licencia']}, fuente: {v['fuente']})")
    _seccion("REPOSITORIOS Y PROYECTOS", repositorios, lambda r:
              f"{r['nombre']} — {r['url']} (licencia: {r['licencia']}, {r['estrellas']}⭐)")

    if len(lineas) == 4:  # no se agregó ninguna sección
        lineas.append(" No se encontraron fuentes con licencia libre para los términos buscados.")

    return "\n".join(lineas)


def escribir_contenido(carpeta_raiz: str, tema: str, guia_texto: str, preguntas: list):
    os.makedirs(os.path.join(carpeta_raiz, "1_Contexto"), exist_ok=True)
    os.makedirs(os.path.join(carpeta_raiz, "2_Trivia_y_Evaluacion"), exist_ok=True)

    with open(os.path.join(carpeta_raiz, "1_Contexto", "Guia_Docente.txt"), "w", encoding="utf-8") as f:
        f.write(guia_texto)

    trivia_data = {"tema": tema, "preguntas": preguntas}
    with open(os.path.join(carpeta_raiz, "2_Trivia_y_Evaluacion", "Trivia.json"), "w", encoding="utf-8") as f:
        json.dump(trivia_data, f, ensure_ascii=False, indent=4)


def escribir_bibliografia(carpeta_raiz: str, bibliografia_texto: str):
    carpeta = os.path.join(carpeta_raiz, "1_Contexto")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "Bibliografia.txt"), "w", encoding="utf-8") as f:
        f.write(bibliografia_texto)
