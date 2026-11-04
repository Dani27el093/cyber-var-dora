"""Ejecuta el EDA y genera figuras y tabla resumen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybervar.config import load_config  # noqa: E402
from cybervar.logging_utils import configure_logging  # noqa: E402
from cybervar.reporting.eda import run_eda  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Análisis exploratorio del dataset procesado")
    parser.add_argument("--config", type=Path, default=None, help="Ruta alternativa a config.yaml")
    parser.add_argument("--all", type=Path, default=None, help="Parquet con todos los sectores")
    parser.add_argument("--finance", type=Path, default=None, help="Parquet solo de finanzas")
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    summary = run_eda(config, all_path=args.all, finance_path=args.finance)

    print("\nResumen del EDA:")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
