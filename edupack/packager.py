import os
import zipfile


def empaquetar(carpeta_raiz: str, zip_destino: str):
    with zipfile.ZipFile(zip_destino, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(carpeta_raiz):
            for file in files:
                filepath = os.path.join(root, file)
                rel = os.path.relpath(filepath, os.path.dirname(carpeta_raiz))
                zipf.write(filepath, arcname=rel)
    return zip_destino
