"""Motor de Montecarlo para el modelo de Poisson compuesto."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from cybervar.models.severity import SeverityFit

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulationResult:
    """Resultado de una simulación anual agregada."""

    losses: np.ndarray
    model: str
    lam: float
    n_scenarios: int


def simulate_aggregate(
    fit: SeverityFit,
    lam: float,
    n_years: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Simula la pérdida agregada anual con frecuencia Poisson y severidad truncada."""
    counts = rng.poisson(lam, size=n_years)
    total_events = int(counts.sum())
    if total_events == 0:
        return np.zeros(n_years, dtype=float)

    severities = fit.sample(total_events, rng)
    year_index = np.repeat(np.arange(n_years), counts)
    return np.bincount(year_index, weights=severities, minlength=n_years)


def _batch_var_se(losses: np.ndarray, level: float, n_batches: int = 20) -> float:
    """Error estándar del VaR por medias de lotes."""
    batches = np.array_split(losses, n_batches)
    estimates = [np.quantile(batch, level, method="higher") for batch in batches if len(batch)]
    if len(estimates) < 2:
        return float("nan")
    return float(np.std(estimates, ddof=1) / np.sqrt(len(estimates)))


def var_es(losses: np.ndarray, levels: tuple[float, ...]) -> pd.DataFrame:
    """Calcula VaR, Expected Shortfall y error de simulación por nivel."""
    rows = []
    for level in levels:
        var = float(np.quantile(losses, level, method="higher"))
        tail = losses[losses >= var]
        es = float(tail.mean()) if len(tail) else var
        rows.append(
            {
                "level": level,
                "var": var,
                "es": es,
                "var_se": _batch_var_se(losses, level),
                "tail_observations": int(len(tail)),
            }
        )
    return pd.DataFrame(rows)


def run_scenarios(
    fits: dict[str, SeverityFit],
    lambdas: tuple[float, ...],
    levels: tuple[float, ...],
    n_scenarios: int,
    seed: int = 42,
) -> pd.DataFrame:
    """Ejecuta todas las combinaciones de modelo de severidad y λ."""
    rows = []

    for index, (model_name, fit) in enumerate(fits.items()):
        if model_name == "pareto" and fit.params.get("alpha", 2.0) <= 1.0:
            LOGGER.warning("Se omite Pareto con alpha<=1: la media y parte de la cola no son finitas")
            continue
        for lam in lambdas:
            scenario_rng = np.random.default_rng(seed + index * 1_000 + int(lam * 100))
            losses = simulate_aggregate(fit, lam, n_scenarios, scenario_rng)
            summary = var_es(losses, levels)
            summary.insert(0, "lambda", lam)
            summary.insert(0, "model", model_name)
            summary["mean_loss"] = float(losses.mean())
            summary["median_loss"] = float(np.median(losses))
            summary["p_zero"] = float(np.mean(losses == 0))
            rows.append(summary)

    return pd.concat(rows, ignore_index=True)


def convergence_path(
    fit: SeverityFit,
    lam: float,
    level: float,
    max_scenarios: int,
    seed: int = 42,
    n_points: int = 60,
) -> pd.DataFrame:
    """Evolución del VaR estimado al aumentar el número de escenarios."""
    rng = np.random.default_rng(seed)
    losses = simulate_aggregate(fit, lam, max_scenarios, rng)
    checkpoints = np.unique(np.logspace(2, np.log10(max_scenarios), n_points).astype(int))
    return pd.DataFrame(
        {
            "n_scenarios": checkpoints,
            "var": [np.quantile(losses[:n], level, method="higher") for n in checkpoints],
        }
    )
