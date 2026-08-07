"""
Generación de contenido pedagógico.
A diferencia de la versión original, nada aquí está atado a un tema fijo:
el tema, el contexto y las preguntas de trivia los define quien usa la herramienta
a través del formulario.
"""
import os
import json


def construir_guia(tema: str, objetivos: str, contexto: str) -> str:
    """Arma el texto de la guía docente a partir de lo que la persona escribió en el formulario."""
    lineas = [
        "=" * 60,
        f" GUÍA DOCENTE: {tema.upper()}",
        "=" * 60,
        "",
        " OBJETIVOS DE APRENDIZAJE:",
        objetivos.strip() or "(sin definir)",
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


def escribir_contenido(carpeta_raiz: str, tema: str, guia_texto: str, preguntas: list):
    os.makedirs(os.path.join(carpeta_raiz, "1_Contexto"), exist_ok=True)
    os.makedirs(os.path.join(carpeta_raiz, "2_Trivia_y_Evaluacion"), exist_ok=True)

    with open(os.path.join(carpeta_raiz, "1_Contexto", "Guia_Docente.txt"), "w", encoding="utf-8") as f:
        f.write(guia_texto)

    trivia_data = {"tema": tema, "preguntas": preguntas}
    with open(os.path.join(carpeta_raiz, "2_Trivia_y_Evaluacion", "Trivia.json"), "w", encoding="utf-8") as f:
        json.dump(trivia_data, f, ensure_ascii=False, indent=4)
