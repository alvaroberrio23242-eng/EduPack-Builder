# EduPack Builder

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Status](https://img.shields.io/badge/status-en%20desarrollo-orange)

App web para armar paquetes educativos completos sobre **cualquier tema** — guía docente, trivia, imágenes, videos, repositorios de código y artículos, todo filtrado por licencia libre y empaquetado en un `.zip` listo para el aula.

No es un generador de contenido con IA: busca y filtra material que ya existe con licencia abierta, y organiza lo que tú escribes (guía y preguntas) en un paquete estructurado.

## Qué hace

| Recurso | Fuente | Qué trae |
|---|---|---|
| 🖼️ Imágenes | Wikimedia Commons + Openverse | Fotos con licencia CC-BY / CC0 / dominio público |
| 🎬 Videos | Wikimedia Commons + Internet Archive | Enlaces directos con licencia libre (no descarga el archivo completo) |
| 💻 Repositorios | GitHub | Repos y plantillas de proyecto relacionadas con el tema |
| 📄 Ensayos | Wikipedia | Artículos existentes (CC BY-SA) para usar como referencia |
| 📝 Guía + trivia | Formulario | Lo que tú escribas, estructurado y empaquetado |

## Capturas

*(agrega aquí un par de screenshots del formulario y la vista previa — le dan mucho más contexto a quien visite el repo)*

## Cómo correrlo localmente

```bash
git clone https://github.com/alvaroberrio23242-eng/EduPack-Builder.git
cd EduPack-Builder
pip install -r requirements.txt
python app.py
```

Abre `http://localhost:5000`.

## Estructura

```
app.py                     # rutas Flask
edupack/
  content.py                # arma la guía y valida la trivia
  images.py                  # busca y descarga imágenes por licencia libre
  videos.py                   # busca videos con licencia libre (no descarga el archivo)
  repos.py                     # busca repositorios y plantillas en GitHub
  essays.py                     # busca artículos existentes en Wikipedia
  packager.py                    # empaqueta todo en .zip
  jobs.py                         # ejecuta la generación en segundo plano y guarda el historial
templates/                        # HTML (formulario, progreso, vista previa, historial)
static/                            # CSS, JS y el video de fondo
data/jobs/                          # paquetes generados + historial.json (se crea solo)
```

## Por qué existe

Nace de automatizar dos scripts de consola sueltos en uno solo, configurable desde una interfaz web en lugar de editar código para cada tema nuevo.

## Para desplegarlo online

Cualquier servicio que corra Flask sirve (Render, Railway, PythonAnywhere, Fly.io).
- Definir `SECRET_KEY` y quitar `debug=True` antes de producción.
- `data/jobs/` necesita almacenamiento persistente si quieres que el historial sobreviva a un redeploy.
- Las búsquedas requieren salida a internet (Wikimedia, Openverse, GitHub y Wikipedia); ninguna pide clave de API.

## Roadmap

- [ ] Generación automática de la guía con IA (opcional, sin reemplazar el texto propio)
- [ ] Descarga real del video (hoy solo enlaza, por tamaño)
- [ ] Exportar la trivia en formato compatible con Kahoot/Quizizz
