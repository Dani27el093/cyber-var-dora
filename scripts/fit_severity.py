"""Ajusta y compara distribuciones de severidad para la muestra pooled y la de finanzas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

from cybervar.config import load_config  # noqa: E402
from cybervar.logging_utils import configure_logging  # noqa: E402
from cybervar.models.severity import (  # noqa: E402
    comparison_table,
    fit_all,
    prepare_sample,
)
from cybervar.reporting.model_plots import plot_qq_grid  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ajuste de severidad (LDA)")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--threshold", type=float, default=None, help="Umbral en EUR 2025")
    parser.add_argument("--bootstrap", type=int, default=0, help="Réplicas para el p-valor KS bootstrap")
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    threshold = args.threshold or config.losses.min_threshold_eur
    config.ensure_dirs()

    all_df = pd.read_parquet(config.data.processed_dir / "incidents_all.parquet")
    finance_df = pd.read_parquet(config.data.processed_dir / "incidents_finance.parquet")

    samples = {
        "pooled": prepare_sample(all_df, threshold),
        "finance": prepare_sample(finance_df, threshold),
    }

    payload: dict[str, object] = {"threshold": threshold, "reference_year": config.reference_year, "samples": {}}
    tables_dir = config.outputs_dir / "tables"
    figures_dir = config.outputs_dir / "figures"

    for name, sample in samples.items():
        print(f"\n=== Muestra {name}: n={len(sample)} ===")
        fits = fit_all(sample, threshold)
        if not fits:
            raise SystemExit(f"No se pudo ajustar ninguna distribución para la muestra {name}")

        table = comparison_table(fits, bootstrap=args.bootstrap > 0, n_boot=args.bootstrap)
        table_path = tables_dir / f"severity_comparison_{name}.csv"
        table.to_csv(table_path, index=False)
        print(table.to_string(index=False))

        qq_path = figures_dir / f"severity_qq_{name}.png"
        plot_qq_grid(fits, sample, qq_path, f"QQ-plot · muestra {name} · umbral {threshold:,.0f} €")

        payload["samples"][name] = {
            model: {
                "params": fit.params,
                "n": fit.n,
                "loglik": fit.loglik,
                "aic": fit.aic,
                "bic": fit.bic,
                "ks_stat": fit.ks_stat,
                "ks_pvalue": fit.ks_pvalue,
            }
            for model, fit in fits.items()
        }

    params_path = tables_dir / "severity_params.json"
    params_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nParámetros guardados en {params_path}")


if __name__ == "__main__":
    main()
