"""Genera las tablas de referencia de tipos de cambio e inflación."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybervar.config import load_config  # noqa: E402
from cybervar.data.reference import build_reference_tables  # noqa: E402
from cybervar.logging_utils import configure_logging  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga tipos BCE e HICP de Eurostat")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--start-year", type=int, default=2005)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    paths = build_reference_tables(
        config.data.reference_dir,
        start_year=args.start_year,
        end_year=args.end_year,
    )

    print("\nArtefactos:")
    for name, path in paths.items():
        print(f"  {name:5s} {path}")


if __name__ == "__main__":
    main()
