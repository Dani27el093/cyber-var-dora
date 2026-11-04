"""Tests de la capa de ingesta y ETL."""

from __future__ import annotations

import pandas as pd
import pytest

from cybervar.config import load_config
from cybervar.data.etl import (
    extract_loss,
    extract_record,
    filter_finance,
    parse_amount,
    parse_employee_band,
)


@pytest.fixture(scope="module")
def config():
    return load_config()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1000, 1000.0),
        (1500.5, 1500.5),
        ("$1,000,000", 1_000_000.0),
        ("250000", 250_000.0),
        ("1000-5000", 3000.0),
        ("1,000 to 5,000", 3000.0),
        ("Unknown", None),
        ("", None),
        (None, None),
        (True, None),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,000 to 9,999", 5499.5),
        ("Over 100000", 100000.0),
        ("Under 10", 10.0),
        ("Unknown", None),
    ],
)
def test_parse_employee_band(raw, expected):
    assert parse_employee_band(raw) == expected


def test_loss_prefers_overall_amount(config):
    record = {
        "impact": {
            "overall_amount": 100_000,
            "iso_currency_code": "USD",
            "loss": [
                {"variety": "Legal and regulatory", "amount": 60_000},
                {"variety": "Brand damage", "amount": 20_000},
            ],
        }
    }
    loss = extract_loss(record, config)
    assert loss["loss_amount"] == 100_000
    assert loss["loss_source"] == "overall_amount"
    assert loss["loss_currency"] == "USD"
    assert loss["n_loss_components"] == 2


def test_loss_falls_back_to_components(config):
    record = {
        "impact": {
            "loss": [
                {"variety": "Legal and regulatory", "amount": 60_000},
                {"variety": "Brand damage", "amount": 20_000},
            ]
        }
    }
    loss = extract_loss(record, config)
    assert loss["loss_amount"] == 80_000
    assert loss["loss_source"] == "components_sum"


def test_loss_range_midpoint(config):
    record = {"impact": {"overall_min_amount": 10_000, "overall_max_amount": 30_000}}
    loss = extract_loss(record, config)
    assert loss["loss_amount"] == 20_000
    assert loss["loss_source"] == "range_midpoint"


def test_missing_currency_is_flagged(config):
    record = {"impact": {"overall_amount": 50_000}}
    loss = extract_loss(record, config)
    assert loss["loss_currency"] == "USD"
    assert loss["loss_currency_assumed"] is True


def test_extract_record_year_fallback(config):
    record = {
        "incident_id": "abc",
        "victim": {"industry": "522110", "country": ["US"]},
        "plus": {"dbir_year": 2019},
        "timeline": {},
        "impact": {"overall_amount": 1_000},
    }
    row = extract_record(record, config)
    assert row["year"] == 2019
    assert row["dbir_year"] == 2019
    assert row["is_finance"] is True
    assert row["industry_sector"] == "Finance and insurance"


def test_finance_filter(config):
    frame = pd.DataFrame(
        {
            "incident_id": ["1", "2", "3"],
            "industry_code": ["522110", "622110", None],
        }
    )
    filtered = filter_finance(frame, config.data.finance_naics_prefix)
    assert filtered["incident_id"].tolist() == ["1"]
