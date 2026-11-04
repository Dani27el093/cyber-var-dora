"""Ejecuta el pipeline completo de principio a fin."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str) -> None:
    command = [sys.executable, str(SCRIPTS / script), *args]
    print(f"\n>>> {' '.join(command)}")
    subprocess.run(command, check=True, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline completo: datos, EDA, ajuste y simulación")
    parser.add_argument("--skip-download", action="store_true", help="Reutiliza el VCDB ya descargado")
    parser.add_argument("--skip-reference", action="store_true", help="Reutiliza tipos de cambio e HICP")
    args = parser.parse_args()

    if not args.skip_download:
        run("download_data.py")
    if not args.skip_reference:
        run("build_reference_data.py")

    run("build_dataset.py")
    run("run_eda.py")
    run("fit_severity.py")
    run("run_simulation.py")


if __name__ == "__main__":
    main()
