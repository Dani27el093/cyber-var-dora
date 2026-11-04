"""Descarga y verificación del dataset VCDB."""

from __future__ import annotations

import hashlib
import logging
import zipfile
from pathlib import Path

import requests

from cybervar.config import Config

LOGGER = logging.getLogger(__name__)
CHUNK_SIZE = 1 << 20  # 1 MiB


def sha256sum(path: Path) -> str:
    """Calcula el SHA-256 de un archivo."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path, force: bool = False) -> Path:
    """Descarga un archivo por streaming, con escritura atómica."""
    if destination.exists() and not force:
        LOGGER.info("Ya existe %s; se reutiliza (usa --force para descargar de nuevo)", destination)
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")

    LOGGER.info("Descargando %s", url)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        written = 0
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                handle.write(chunk)
                written += len(chunk)
                if total:
                    LOGGER.debug("Progreso: %.1f%%", 100 * written / total)

    temporary.replace(destination)
    LOGGER.info("Descargado %.1f MB en %s", written / (1 << 20), destination)
    return destination


def extract_json(archive: Path, destination_dir: Path, expected_name: str, force: bool = False) -> Path:
    """Extrae el JSON del ZIP y devuelve su ruta."""
    target = destination_dir / expected_name
    if target.exists() and not force:
        LOGGER.info("Ya existe %s; se reutiliza", target)
        return target

    destination_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        members = [name for name in bundle.namelist() if name.lower().endswith(".json")]
        if not members:
            raise ValueError(f"El archivo {archive} no contiene ningún JSON")
        member = expected_name if expected_name in members else members[0]
        if member != expected_name:
            LOGGER.warning("Se esperaba %s pero se extrae %s", expected_name, member)
        bundle.extract(member, destination_dir)

    extracted = destination_dir / member
    if extracted != target:
        extracted.replace(target)
    LOGGER.info("JSON extraído en %s", target)
    return target


def write_checksum(path: Path) -> Path:
    """Guarda un sidecar `.sha256` con el hash del archivo."""
    checksum_path = path.with_name(path.name + ".sha256")
    checksum_path.write_text(f"{sha256sum(path)}  {path.name}\n", encoding="utf-8")
    LOGGER.info("SHA-256: %s", checksum_path.read_text(encoding="utf-8").strip())
    return checksum_path


def download_vcdb(config: Config, force: bool = False) -> dict[str, Path]:
    """Descarga, verifica y extrae el VCDB. Devuelve las rutas relevantes."""
    config.ensure_dirs()
    archive = download_file(config.data.source_url, config.data.raw_dir / config.data.archive_name, force=force)
    checksum = write_checksum(archive)
    json_path = extract_json(
        archive,
        config.data.raw_dir,
        config.data.extracted_name,
        force=force,
    )
    return {"archive": archive, "checksum": checksum, "json": json_path}
