"""Simulación de Montecarlo y cálculo de VaR / Expected Shortfall."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from cybervar.config import load_config  # noqa: E402
from cybervar.logging_utils import configure_logging  # noqa: E402
from cybervar.models.severity import fit_all, prepare_sample  # noqa: E402
from cybervar.reporting.model_plots import (  # noqa: E402
    plot_aggregate_distribution,
    plot_convergence,
    plot_var_by_lambda,
)
from cybervar.simulation.montecarlo import (  # noqa: E402
    convergence_path,
    run_scenarios,
    simulate_aggregate,
    var_es,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulación de Poisson compuesto y VaR")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--scenarios", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    configure_logging()
    config = load_config(args.config)
    threshold = args.threshold or config.losses.min_threshold_eur
    n_scenarios = args.scenarios or config.simulation.n_scenarios
    seed = args.seed or config.random_seed
    config.ensure_dirs()

    all_df = pd.read_parquet(config.data.processed_dir / "incidents_all.parquet")
    finance_df = pd.read_parquet(config.data.processed_dir / "incidents_finance.parquet")

    samples = {
        "pooled": prepare_sample(all_df, threshold),
        "finance": prepare_sample(finance_df, threshold),
    }
    fits_by_sample = {name: fit_all(sample, threshold) for name, sample in samples.items()}

    results = []
    for name, fits in fits_by_sample.items():
        frame = run_scenarios(
            fits,
            lambdas=config.frequency.lambda_scenarios,
            levels=config.simulation.confidence_levels,
            n_scenarios=n_scenarios,
            seed=seed,
        )
        frame.insert(0, "sample", name)
        results.append(frame)

    results_df = pd.concat(results, ignore_index=True)
    tables_dir = config.outputs_dir / "tables"
    figures_dir = config.outputs_dir / "figures"
    results_path = tables_dir / "var_results.csv"
    results_df.to_csv(results_path, index=False)
    print(f"\nResultados guardados en {results_path}")

    # Rango entre modelos para el nivel más alto
    top_level = max(config.simulation.confidence_levels)
    ranges = (
        results_df.loc[results_df["level"].eq(top_level)]
        .groupby(["sample", "lambda"])
        .agg(var_min=("var", "min"), var_median=("var", "median"), var_max=("var", "max"), es_max=("es", "max"))
        .reset_index()
    )
    ranges_path = tables_dir / "var_range.csv"
    ranges.to_csv(ranges_path, index=False)
    print(f"Rangos guardados en {ranges_path}")

    # Caso base: mejor AIC de la muestra pooled
    base_fit = min(fits_by_sample["pooled"].values(), key=lambda fit: fit.aic)
    base_lambda = config.frequency.lambda_base
    rng = np.random.default_rng(seed + int(base_lambda * 100))
    base_losses = simulate_aggregate(base_fit, base_lambda, n_scenarios, rng)
    base_var = var_es(base_losses, config.simulation.confidence_levels)
    base_var.insert(0, "lambda", base_lambda)
    base_var.insert(0, "model", base_fit.name)
    base_var.insert(0, "sample", "pooled")
    base_var_path = tables_dir / "var_base_case.csv"
    base_var.to_csv(base_var_path, index=False)

    print(f"\nCaso base: {base_fit.name}, lambda={base_lambda}, {n_scenarios:,} escenarios")
    print(base_var.to_string(index=False))

    plot_aggregate_distribution(
        base_losses,
        base_var,
        figures_dir / "aggregate_loss_distribution.png",
        f"Pérdida agregada anual · {base_fit.name} · λ={base_lambda} · {n_scenarios:,} escenarios",
    )
    plot_convergence(
        convergence_path(base_fit, base_lambda, top_level, n_scenarios, seed=seed),
        top_level,
        figures_dir / "var_convergence.png",
    )
    plot_var_by_lambda(
        results_df.loc[results_df["sample"].eq("pooled")],
        top_level,
        figures_dir / "var_by_lambda.png",
    )
    plot_var_by_lambda(
        results_df.loc[results_df["sample"].eq("finance")],
        top_level,
        figures_dir / "var_by_lambda_finance.png",
    )

    print("\nFiguras guardadas en", figures_dir)


if __name__ == "__main__":
    main()
