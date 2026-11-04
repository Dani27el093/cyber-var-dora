"""Descarga el VCDB y verifica su integridad."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybervar.config import load_config  # noqa: E402
from cybervar.data.download import download_vcdb  # noqa: E402
from cybervar.logging_utils import configure_logging  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga el dataset VCDB")
    parser.add_argument("--config", type=Path, default=None, help="Ruta alternativa a config.yaml")
    parser.add_argument("--force", action="store_true", help="Vuelve a descargar aunque exista")
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    paths = download_vcdb(config, force=args.force)

    print("\nArtefactos:")
    for name, path in paths.items():
        print(f"  {name:8s} {path}")


if __name__ == "__main__":
    main()
