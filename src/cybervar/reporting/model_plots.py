"""Figuras del ajuste de severidad y de la simulación."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cybervar.models.severity import SeverityFit

COLORS = ["#4C72B0", "#C44E52", "#55A868", "#8172B2", "#CCB974", "#64B5CD"]


def plot_qq_grid(
    fits: dict[str, SeverityFit],
    sample: np.ndarray | pd.Series,
    output_path: Path,
    title: str,
) -> Path:
    """Grid de QQ-plots empíricos frente a la distribución ajustada."""
    values = np.sort(np.asarray(sample, dtype=float))
    probabilities = (np.arange(1, len(values) + 1) - 0.5) / len(values)

    n_models = len(fits)
    columns = 2
    rows = int(np.ceil(n_models / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(10, 4.2 * rows), squeeze=False)

    for ax, (name, fit) in zip(axes.flat, fits.items()):
        theoretical = fit.ppf(probabilities)
        ax.scatter(theoretical, values, s=10, alpha=0.55, color=COLORS[0], edgecolors="none")
        lower = max(min(theoretical.min(), values.min()), 1)
        upper = max(theoretical.max(), values.max())
        ax.plot([lower, upper], [lower, upper], color="black", linestyle="--", linewidth=1)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_title(f"{name} · KS={fit.ks_stat:.3f}")
        ax.set_xlabel("Cuantil teórico (EUR 2025)")
        ax.set_ylabel("Cuantil empírico (EUR 2025)")
        ax.grid(alpha=0.25)

    for ax in axes.flat[n_models:]:
        ax.axis("off")

    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_convergence(frame: pd.DataFrame, level: float, output_path: Path) -> Path:
    """Convergencia del VaR estimado con el número de escenarios."""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(frame["n_scenarios"], frame["var"], color=COLORS[0], linewidth=1.8)
    ax.set_xscale("log")
    ax.set_title(f"Convergencia del VaR al {level:.1%}")
    ax.set_xlabel("Número de escenarios anuales simulados (escala log)")
    ax.set_ylabel("VaR (EUR 2025)")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_aggregate_distribution(
    losses: np.ndarray,
    var_levels: pd.DataFrame,
    output_path: Path,
    title: str,
) -> Path:
    """Histograma de pérdida agregada anual con las líneas de VaR."""
    positive = losses[losses > 0]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(np.log10(positive), bins=60, color=COLORS[1], alpha=0.85, edgecolor="white")

    for index, row in var_levels.iterrows():
        color = COLORS[(index + 2) % len(COLORS)]
        ax.axvline(np.log10(row["var"]), color=color, linestyle="--", linewidth=1.5, label=f"VaR {row['level']:.1%}: {row['var']:,.0f} €")

    ax.set_title(title)
    ax.set_xlabel("log10(pérdida agregada anual, EUR 2025)")
    ax.set_ylabel("Número de años simulados")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_var_by_lambda(results: pd.DataFrame, level: float, output_path: Path) -> Path:
    """VaR por modelo y escenario de frecuencia."""
    subset = results.loc[results["level"].eq(level)]
    fig, ax = plt.subplots(figsize=(9, 5))

    for index, (model, group) in enumerate(subset.groupby("model")):
        group = group.sort_values("lambda")
        ax.plot(group["lambda"], group["var"], marker="o", linewidth=1.7, color=COLORS[index % len(COLORS)], label=model)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(f"VaR al {level:.1%} según frecuencia anual y modelo de severidad")
    ax.set_xlabel("λ (incidentes materiales por año, escala log)")
    ax.set_ylabel("VaR (EUR 2025, escala log)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, which="both")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path
