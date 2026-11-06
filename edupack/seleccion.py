import os
import re
import shutil
import threading
import time
import uuid

from edupack import jobs, videos, repos, essays, content, packager


_LOCK = threading.RLock()
_EN_PROCESO = set()

_CATEGORIAS = {
    "videos": "videos",
    "repositorios": "repositorios",
    "ensayos": "ensayos",
}

_CARPETAS = {
    "videos": "3b_Videos",
    "repositorios": "4_Repositorios",
    "ensayos": "5_Ensayos_y_Articulos",
}


class SeleccionInvalida(ValueError):
    pass


class JobNoDisponible(Exception):
    pass


class VersionConflicto(Exception):
    def __init__(self, version_actual):
        self.version_actual = version_actual
        super().__init__(f"Versión desactualizada. Versión actual: {version_actual}")


class ReempaquetadoEnCurso(Exception):
    pass


class ZipOcupado(Exception):
    pass


def _obtener_job_listo(job_id):
    if not jobs.es_id_valido(job_id):
        raise JobNoDisponible("Identificador de trabajo inválido.")

    job = jobs.obtener_job(job_id)

    if not job or job.get("estado") != "listo":
        raise JobNoDisponible("El trabajo no existe o todavía no está listo.")

    if not isinstance(job.get("resultado"), dict):
        raise JobNoDisponible("El trabajo no contiene resultados disponibles.")

    return job


def _normalizar_seleccion(job):
    actual = job.get("seleccion") or {}

    version = actual.get("version", 0)
    zip_version = actual.get("zip_version", 0)
    excluidos = actual.get("excluidos", [])

    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version < 0
    ):
        version = 0

    if (
        isinstance(zip_version, bool)
        or not isinstance(zip_version, int)
        or zip_version < 0
    ):
        zip_version = 0

    if not isinstance(excluidos, list):
        excluidos = []

    return {
        "version": version,
        "zip_version": zip_version,
        "excluidos": list(excluidos),
    }


def seleccion_de_job(job):
    if not isinstance(job, dict):
        return {
            "version": 0,
            "zip_version": 0,
            "excluidos": [],
        }

    return _normalizar_seleccion(job)


def _validar_excluidos(job, excluidos):
    if not isinstance(excluidos, list):
        raise SeleccionInvalida("excluidos debe ser una lista.")

    resultado = job["resultado"]
    normalizados = []

    for clave in excluidos:
        if not isinstance(clave, str):
            raise SeleccionInvalida("Cada exclusión debe ser texto.")

        coincidencia = re.fullmatch(
            r"(videos|repositorios|ensayos):(0|[1-9][0-9]*)",
            clave,
        )

        if not coincidencia:
            raise SeleccionInvalida(f"Clave de selección inválida: {clave}")

        categoria, indice_texto = coincidencia.groups()
        indice = int(indice_texto)
        elementos = resultado.get(_CATEGORIAS[categoria], [])

        if not isinstance(elementos, list) or indice >= len(elementos):
            raise SeleccionInvalida(f"Índice fuera de rango: {clave}")

        if clave in normalizados:
            raise SeleccionInvalida(f"Clave duplicada: {clave}")

        normalizados.append(clave)

    return sorted(
        normalizados,
        key=lambda item: (
            item.split(":")[0],
            int(item.split(":")[1]),
        ),
    )


def guardar_seleccion(job_id, excluidos, version):
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise SeleccionInvalida("version debe ser un entero no negativo.")

    with _LOCK:
        job = _obtener_job_listo(job_id)
        seleccion = _normalizar_seleccion(job)

        if version != seleccion["version"]:
            raise VersionConflicto(seleccion["version"])

        nuevas_exclusiones = _validar_excluidos(job, excluidos)

        if nuevas_exclusiones == seleccion["excluidos"]:
            return seleccion

        seleccion["excluidos"] = nuevas_exclusiones
        seleccion["version"] += 1

        job["seleccion"] = seleccion
        jobs._escribir_estado(job_id, job)

        return seleccion


def _filtrar_resultados(resultados, categoria, excluidos):
    excluidos_indices = {
        int(clave.split(":")[1])
        for clave in excluidos
        if clave.startswith(categoria + ":")
    }

    return [
        elemento
        for indice, elemento in enumerate(resultados)
        if indice not in excluidos_indices
    ]


def _reemplazar_zip(zip_tmp, zip_destino):
    for intento in range(5):
        try:
            os.replace(zip_tmp, zip_destino)
            return
        except PermissionError:
            if intento == 4:
                raise ZipOcupado(
                    "El ZIP está siendo utilizado por otro proceso."
                )
            time.sleep(0.05)


def reempaquetar(job_id):
    if not jobs.es_id_valido(job_id):
        raise JobNoDisponible("Identificador de trabajo inválido.")

    with _LOCK:
        if job_id in _EN_PROCESO:
            raise ReempaquetadoEnCurso(
                "Ya existe un reempaquetado en curso para este trabajo."
            )

        _EN_PROCESO.add(job_id)

        carpeta_temporal = None
        zip_tmp = None

        try:
            job = _obtener_job_listo(job_id)
            resultado = job["resultado"]
            seleccion = _normalizar_seleccion(job)

            excluidos = _validar_excluidos(
                job,
                seleccion["excluidos"],
            )

            carpeta_job = jobs._carpeta_job(job_id)
            carpeta_original = os.path.join(carpeta_job, "paquete")
            zip_destino = resultado.get("zip_path")

            if not os.path.isdir(carpeta_original):
                raise JobNoDisponible("No se encuentra el paquete original.")

            if not zip_destino or not os.path.isfile(zip_destino):
                raise JobNoDisponible("No se encuentra el ZIP original.")

            carpeta_temporal = os.path.join(
                carpeta_job,
                "_sel_" + uuid.uuid4().hex[:10],
            )

            carpeta_nueva = os.path.join(carpeta_temporal, "paquete")
            os.makedirs(carpeta_temporal, exist_ok=False)

            shutil.copytree(carpeta_original, carpeta_nueva)

            videos_filtrados = _filtrar_resultados(
                resultado.get("videos", []),
                "videos",
                excluidos,
            )
            repos_filtrados = _filtrar_resultados(
                resultado.get("repositorios", []),
                "repositorios",
                excluidos,
            )
            ensayos_filtrados = _filtrar_resultados(
                resultado.get("ensayos", []),
                "ensayos",
                excluidos,
            )

            categorias_con_exclusiones = {
                "videos": any(k.startswith("videos:") for k in excluidos),
                "repositorios": any(k.startswith("repositorios:") for k in excluidos),
                "ensayos": any(k.startswith("ensayos:") for k in excluidos),
            }

            if categorias_con_exclusiones["videos"]:
                ruta = os.path.join(carpeta_nueva, _CARPETAS["videos"])
                if os.path.isdir(ruta):
                    shutil.rmtree(ruta)
                videos.escribir_videos(carpeta_nueva, videos_filtrados)

            if categorias_con_exclusiones["repositorios"]:
                ruta = os.path.join(carpeta_nueva, _CARPETAS["repositorios"])
                if os.path.isdir(ruta):
                    shutil.rmtree(ruta)
                repos.escribir_repositorios(carpeta_nueva, repos_filtrados)

            if categorias_con_exclusiones["ensayos"]:
                ruta = os.path.join(carpeta_nueva, _CARPETAS["ensayos"])
                if os.path.isdir(ruta):
                    shutil.rmtree(ruta)
                essays.escribir_ensayos(carpeta_nueva, ensayos_filtrados)

            if any(categorias_con_exclusiones.values()):
                bibliografia = content.construir_bibliografia(
                    resultado.get("imagenes", []),
                    videos_filtrados,
                    ensayos_filtrados,
                    repos_filtrados,
                )
                content.escribir_bibliografia(carpeta_nueva, bibliografia)

            zip_tmp = zip_destino + ".tmp"

            if os.path.exists(zip_tmp):
                os.remove(zip_tmp)

            packager.empaquetar(carpeta_nueva, zip_tmp)
            _reemplazar_zip(zip_tmp, zip_destino)

            job_actualizado = jobs.obtener_job(job_id)
            seleccion_actual = _normalizar_seleccion(job_actualizado)

            seleccion_actual["zip_version"] = seleccion_actual["version"]
            job_actualizado["seleccion"] = seleccion_actual

            jobs._escribir_estado(job_id, job_actualizado)

            return seleccion_actual

        finally:
            if zip_tmp and os.path.exists(zip_tmp):
                try:
                    os.remove(zip_tmp)
                except OSError:
                    pass

            if carpeta_temporal and os.path.isdir(carpeta_temporal):
                shutil.rmtree(carpeta_temporal, ignore_errors=True)

            _EN_PROCESO.discard(job_id)
