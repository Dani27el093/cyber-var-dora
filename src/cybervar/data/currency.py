"""Normalización monetaria: moneda original -> EUR del año de referencia."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger(__name__)


def add_eur_2025(frame: pd.DataFrame, reference_dir: Path, reference_year: int = 2025) -> pd.DataFrame:
    """Añade pérdidas en EUR nominales y en EUR del año de referencia.

    Pasos:
        1. Convertir el importe a EUR del año del incidente con el tipo medio anual.
        2. Inflactar/deflactar a EUR del año de referencia con el HICP de la eurozona.
    """
    fx_path = reference_dir / "fx_rates.csv"
    hicp_path = reference_dir / "hicp_ea20.csv"
    if not fx_path.exists() or not hicp_path.exists():
        raise FileNotFoundError(
            f"Faltan tablas de referencia en {reference_dir}. "
            "Ejecuta: python scripts/build_reference_data.py"
        )

    fx = pd.read_csv(fx_path)
    hicp = pd.read_csv(hicp_path)
    if reference_year not in set(hicp["year"]):
        raise ValueError(f"El HICP no contiene el año de referencia {reference_year}")

    reference_hicp = float(hicp.loc[hicp["year"].eq(reference_year), "hicp"].iloc[0])
    fx_long = fx.melt(id_vars="year", var_name="currency", value_name="fx_rate").rename(
        columns={"currency": "loss_currency"}
    )

    result = frame.copy()
    result["year"] = pd.to_numeric(result["year"], errors="coerce").astype("Int64")
    result["loss_currency"] = result["loss_currency"].fillna("USD").str.upper()
    result["_row_order"] = range(len(result))

    working = result.merge(
        fx_long,
        on=["year", "loss_currency"],
        how="left",
        validate="many_to_one",
    )
    working = working.merge(
        hicp.rename(columns={"hicp": "hicp_index"}),
        on="year",
        how="left",
        validate="many_to_one",
    )

    working["loss_eur"] = working["loss_amount"] / working["fx_rate"]
    working["loss_eur_2025"] = working["loss_eur"] * reference_hicp / working["hicp_index"]
    working["fx_missing"] = working["loss_amount"].notna() & working["fx_rate"].isna()

    missing_fx = int(working["fx_missing"].sum())
    if missing_fx:
        LOGGER.warning("Hay %s pérdidas sin tipo de cambio disponible", missing_fx)

    return working.sort_values("_row_order").drop(columns=["_row_order"]).reset_index(drop=True)
