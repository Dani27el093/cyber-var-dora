"""Análisis exploratorio y figuras de calidad del dataset."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend no interactivo para scripts y CI

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

from cybervar.config import Config

LOGGER = logging.getLogger(__name__)

COLOR_ALL = "#4C72B0"
COLOR_FINANCE = "#C44E52"
COLOR_ACCENT = "#DD8452"

KEY_COLUMNS = [
    "loss_amount",
    "loss_currency",
    "year",
    "industry_code",
    "country",
    "employee_count_raw",
    "summary",
]


def _describe(series: pd.Series, scope: str) -> list[dict[str, object]]:
    """Estadísticos descriptivos de una serie de pérdidas."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return []

    def row(metric: str, value: float) -> dict[str, object]:
        return {"scope": scope, "metric": metric, "value": round(float(value), 2)}

    return [
        row("loss_n", len(values)),
        row("loss_mean", values.mean()),
        row("loss_p50", values.quantile(0.50)),
        row("loss_p90", values.quantile(0.90)),
        row("loss_p95", values.quantile(0.95)),
        row("loss_p99", values.quantile(0.99)),
        row("loss_max", values.max()),
        row("loss_sum", values.sum()),
    ]


def summarize(all_df: pd.DataFrame, finance_df: pd.DataFrame) -> pd.DataFrame:
    """Construye una tabla métrica-valor con el perfil del dataset."""
    rows: list[dict[str, object]] = []

    def add(scope: str, metric: str, value: object) -> None:
        rows.append({"scope": scope, "metric": metric, "value": value})

    add("all", "incidents", len(all_df))
    add("all", "with_loss", int(all_df["loss_amount"].notna().sum()))
    add("all", "years_min", int(all_df["year"].min()) if all_df["year"].notna().any() else None)
    add("all", "years_max", int(all_df["year"].max()) if all_df["year"].notna().any() else None)
    add("all", "missing_industry_pct", round(100 * all_df["industry_code"].isna().mean(), 2))
    add("all", "missing_year_pct", round(100 * all_df["year"].isna().mean(), 2))

    add("all", "out_of_year_range", int((~all_df["in_year_range"]).sum()))
    add("all", "in_year_range", int(all_df["in_year_range"].sum()))

    add("finance", "incidents", len(finance_df))
    add("finance", "with_loss", int(finance_df["loss_amount"].notna().sum()))
    share = 100 * finance_df["loss_amount"].notna().mean() if len(finance_df) else 0.0
    add("finance", "with_loss_pct", round(float(share), 2))

    finance_loss = finance_df.loc[finance_df["loss_amount"].notna()]
    add("finance", "loss_currency_assumed", int(finance_loss["loss_currency_assumed"].sum()))
    for currency, count in finance_loss["loss_currency"].value_counts(dropna=False).items():
        label = currency if isinstance(currency, str) else "missing"
        add("finance", f"currency_{label}", int(count))
    for source, count in finance_loss["loss_source"].value_counts().items():
        add("finance", f"loss_source_{source}", int(count))

    rows.extend(_describe(finance_loss["loss_amount"], "finance_all_currencies"))
    usd_explicit = finance_loss.loc[
        finance_loss["loss_currency"].eq("USD") & ~finance_loss["loss_currency_assumed"],
        "loss_amount",
    ]
    usd_assumed = finance_loss.loc[
        finance_loss["loss_currency"].eq("USD") & finance_loss["loss_currency_assumed"],
        "loss_amount",
    ]
    usd_all = finance_loss.loc[finance_loss["loss_currency"].eq("USD"), "loss_amount"]
    rows.extend(_describe(usd_explicit, "finance_usd_explicit"))
    rows.extend(_describe(usd_assumed, "finance_usd_assumed"))
    rows.extend(_describe(usd_all, "finance_usd_incl_assumed"))
    rows.extend(
        _describe(
            all_df.loc[all_df["loss_currency"].eq("USD") & ~all_df["loss_currency_assumed"], "loss_amount"],
            "all_usd_explicit",
        )
    )

    return pd.DataFrame(rows)


def plot_loss_distribution(finance_df: pd.DataFrame, output_dir: Path) -> Path | None:
    """Histograma de pérdidas en escala logarítmica (subconjunto USD)."""
    subset = finance_df.loc[
        finance_df["loss_amount"].gt(0)
        & finance_df["loss_currency"].eq("USD")
        & ~finance_df["loss_currency_assumed"]
    ]
    if len(subset) < 5:
        LOGGER.warning("Muy pocas pérdidas en USD para graficar la distribución")
        return None

    values = subset["loss_amount"].to_numpy()
    logs = np.log10(values)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(logs, bins=min(30, max(8, len(values) // 3)), color=COLOR_FINANCE, alpha=0.85, edgecolor="white")
    ax.axvline(np.median(logs), color=COLOR_ACCENT, linestyle="--", linewidth=1.5, label=f"Mediana: {np.median(values):,.0f} USD")
    ax.axvline(np.percentile(logs, 99), color="black", linestyle=":", linewidth=1.5, label=f"P99: {np.percentile(values, 99):,.0f} USD")

    ax.set_title(f"Distribución de pérdidas por incidente (finanzas, USD explícito, n={len(values)})")
    ax.set_xlabel("log10(pérdida en USD)")
    ax.set_ylabel("Número de incidentes")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()

    path = output_dir / "loss_distribution_finance_usd.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_incidents_by_year(all_df: pd.DataFrame, finance_df: pd.DataFrame, output_dir: Path) -> Path:
    """Evolución anual del número de incidentes (sesgo de cobertura)."""
    all_counts = all_df.dropna(subset=["year"]).groupby("year").size()
    finance_counts = finance_df.dropna(subset=["year"]).groupby("year").size()

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(all_counts.index, all_counts.values, marker="o", markersize=3, color=COLOR_ALL, label="Todos los sectores")
    ax.plot(finance_counts.index, finance_counts.values, marker="s", markersize=3, color=COLOR_FINANCE, label="Finanzas y seguros")
    ax.set_title("Incidentes registrados por año en el VCDB")
    ax.set_xlabel("Año del incidente")
    ax.set_ylabel("Número de incidentes")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    path = output_dir / "incidents_by_year.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_missingness(all_df: pd.DataFrame, finance_df: pd.DataFrame, output_dir: Path) -> Path:
    """Porcentaje de valores informados por campo clave."""
    columns = [column for column in KEY_COLUMNS if column in all_df.columns]
    coverage_all = all_df[columns].notna().mean().sort_values()
    coverage_finance = finance_df[columns].notna().mean().reindex(coverage_all.index)

    positions = np.arange(len(columns))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(positions - 0.2, coverage_all.values, height=0.38, color=COLOR_ALL, label="Todos")
    ax.barh(positions + 0.2, coverage_finance.fillna(0).values, height=0.38, color=COLOR_FINANCE, label="Finanzas")
    ax.set_yticks(positions)
    ax.set_yticklabels(coverage_all.index)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Fracción de registros con valor informado")
    ax.set_title("Cobertura de campos clave")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()

    path = output_dir / "data_quality.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def run_eda(
    config: Config,
    all_path: Path | None = None,
    finance_path: Path | None = None,
) -> pd.DataFrame:
    """Ejecuta el EDA, guarda la tabla resumen y las figuras."""
    all_path = all_path or config.data.processed_dir / "incidents_all.parquet"
    finance_path = finance_path or config.data.processed_dir / "incidents_finance.parquet"

    all_df = pd.read_parquet(all_path)
    finance_df = pd.read_parquet(finance_path)

    config.ensure_dirs()
    tables_dir = config.outputs_dir / "tables"
    figures_dir = config.outputs_dir / "figures"

    summary = summarize(all_df, finance_df)
    summary_path = tables_dir / "eda_summary.csv"
    summary.to_csv(summary_path, index=False)
    LOGGER.info("Resumen guardado en %s", summary_path)

    top_columns = [
        "incident_id",
        "year",
        "industry_code",
        "country",
        "loss_amount",
        "loss_currency",
        "loss_currency_assumed",
        "loss_source",
        "summary",
    ]
    top_losses = all_df.nlargest(20, "loss_amount")[top_columns]
    top_path = tables_dir / "top_losses.csv"
    top_losses.to_csv(top_path, index=False)
    LOGGER.info("Mayores pérdidas guardadas en %s", top_path)

    all_in_range = all_df.loc[all_df["in_year_range"]]
    finance_in_range = finance_df.loc[finance_df["in_year_range"]]

    for path in (
        plot_loss_distribution(finance_in_range, figures_dir),
        plot_incidents_by_year(all_in_range, finance_in_range, figures_dir),
        plot_missingness(all_df, finance_df, figures_dir),
    ):
        if path is not None:
            LOGGER.info("Figura guardada en %s", path)

    return summary
