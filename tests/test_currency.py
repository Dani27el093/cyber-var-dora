"""Tests de normalización monetaria."""

from __future__ import annotations

import pandas as pd
import pytest

from cybervar.config import load_config
from cybervar.data.currency import add_eur_2025


def test_usd_loss_is_converted_and_inflated():
    config = load_config()
    frame = pd.DataFrame(
        {
            "incident_id": ["a"],
            "year": [2010],
            "loss_amount": [10_000.0],
            "loss_currency": ["USD"],
            "loss_currency_assumed": [False],
            "loss_suspect": [False],
        }
    )
    result = add_eur_2025(frame, config.data.reference_dir, reference_year=2025)

    fx = pd.read_csv(config.data.reference_dir / "fx_rates.csv").set_index("year")
    hicp = pd.read_csv(config.data.reference_dir / "hicp_ea20.csv").set_index("year")["hicp"]
    expected = 10_000 / fx.loc[2010, "USD"] * hicp.loc[2025] / hicp.loc[2010]

    assert result.loc[0, "loss_eur_2025"] == pytest.approx(expected, rel=1e-9)
    assert bool(result.loc[0, "fx_missing"]) is False


def test_eur_loss_has_no_fx_conversion():
    config = load_config()
    frame = pd.DataFrame(
        {
            "incident_id": ["b"],
            "year": [2020],
            "loss_amount": [100_000.0],
            "loss_currency": ["EUR"],
            "loss_currency_assumed": [False],
            "loss_suspect": [False],
        }
    )
    result = add_eur_2025(frame, config.data.reference_dir, reference_year=2025)
    hicp = pd.read_csv(config.data.reference_dir / "hicp_ea20.csv").set_index("year")["hicp"]
    expected = 100_000 * hicp.loc[2025] / hicp.loc[2020]
    assert result.loc[0, "loss_eur_2025"] == pytest.approx(expected, rel=1e-9)
