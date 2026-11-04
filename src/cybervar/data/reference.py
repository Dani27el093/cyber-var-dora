"""Descarga y construcción de tablas de referencia (tipos de cambio e inflación)."""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import pandas as pd
import requests

LOGGER = logging.getLogger(__name__)

ECB_FX_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
EUROSTAT_HICP_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
    "prc_hicp_aind/A.INX_A_AVG.CP00.EA20?format=TSV&compressed=false"
)
CURRENCIES = ["USD", "GBP", "THB", "INR", "ZAR", "CAD", "AUD", "CZK", "KRW", "SGD"]


def fetch_fx_rates(start_year: int = 2005, end_year: int = 2025) -> pd.DataFrame:
    """Descarga el histórico diario del BCE y calcula medias anuales (unidades por EUR)."""
    response = requests.get(ECB_FX_URL, timeout=60)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
        member = next(name for name in bundle.namelist() if name.lower().endswith(".csv"))
        with bundle.open(member) as handle:
            frame = pd.read_csv(handle)

    frame = frame.loc[:, [column for column in frame.columns if column and not column.startswith("Unnamed")]]
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date"]).set_index("Date")

    for currency in CURRENCIES:
        frame[currency] = pd.to_numeric(frame[currency], errors="coerce")

    annual = frame[CURRENCIES].resample("YS").mean()
    annual.index = annual.index.year
    annual = annual.loc[(annual.index >= start_year) & (annual.index <= end_year)]
    annual.index.name = "year"
    annual["EUR"] = 1.0
    return annual.reset_index()


def fetch_hicp(reference_year: int = 2025) -> pd.DataFrame:
    """Descarga el índice HICP anual medio de la eurozona (EA20, 2015=100)."""
    response = requests.get(EUROSTAT_HICP_URL, timeout=60)
    response.raise_for_status()

    lines = [line for line in response.text.splitlines() if line.strip()]
    header = lines[0].split("\t")
    years = [int(year.strip()) for year in header[1:]]

    values = lines[1].split("\t")[1:]
    parsed: dict[int, float] = {}
    for year, raw in zip(years, values):
        cleaned = raw.strip().replace(":", "")
        if cleaned:
            parsed[year] = float(cleaned)

    frame = pd.DataFrame({"year": list(parsed), "hicp": list(parsed.values())}).sort_values("year")
    frame = frame.loc[frame["year"] <= reference_year].reset_index(drop=True)
    return frame


def build_reference_tables(reference_dir: Path, start_year: int = 2005, end_year: int = 2025) -> dict[str, Path]:
    """Genera `fx_rates.csv` y `hicp_ea20.csv` en el directorio de referencia."""
    reference_dir.mkdir(parents=True, exist_ok=True)

    fx = fetch_fx_rates(start_year=start_year, end_year=end_year)
    fx_path = reference_dir / "fx_rates.csv"
    fx.to_csv(fx_path, index=False, float_format="%.6f")

    hicp = fetch_hicp(reference_year=end_year)
    hicp_path = reference_dir / "hicp_ea20.csv"
    hicp.to_csv(hicp_path, index=False, float_format="%.4f")

    LOGGER.info("Tipos de cambio guardados en %s (%s filas)", fx_path, len(fx))
    LOGGER.info("HICP guardado en %s (%s filas)", hicp_path, len(hicp))
    return {"fx": fx_path, "hicp": hicp_path}
