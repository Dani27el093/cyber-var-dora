"""Construye los datasets procesados a partir del JSON del VCDB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cybervar.config import load_config  # noqa: E402
from cybervar.data.etl import build_datasets  # noqa: E402
from cybervar.logging_utils import configure_logging  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera incidents_all.parquet e incidents_finance.parquet")
    parser.add_argument("--config", type=Path, default=None, help="Ruta alternativa a config.yaml")
    parser.add_argument("--input", type=Path, default=None, help="JSON de entrada (por defecto, el descargado)")
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    input_path = args.input or config.data.raw_dir / config.data.extracted_name
    if not input_path.exists():
        raise SystemExit(f"No existe {input_path}. Ejecuta antes: python scripts/download_data.py")

    frame, paths = build_datasets(input_path, config)

    print("\nResumen:")
    print(f"  Incidentes totales:          {len(frame):,}")
    print(f"  Finanzas y seguros:          {int(frame['is_finance'].sum()):,}")
    print(f"  Con importe (todos):         {int(frame['loss_amount'].notna().sum()):,}")
    print(f"  Con importe (finanzas):      {int(frame.loc[frame['is_finance'], 'loss_amount'].notna().sum()):,}")
    print("\nArtefactos:")
    for name, path in paths.items():
        print(f"  {name:8s} {path}")


if __name__ == "__main__":
    main()
