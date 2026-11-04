"""Tests de los modelos de severidad y frecuencia."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cybervar.config import load_config
from cybervar.models.frequency import annual_counts, diagnose
from cybervar.models.severity import (
    fit_all,
    fit_distribution,
    prepare_sample,
)


@pytest.fixture(scope="module")
def synthetic_lognormal():
    rng = np.random.default_rng(7)
    sample = rng.lognormal(mean=11.5, sigma=1.2, size=3_000)
    sample = sample[sample >= 10_000][:600]
    return sample


def test_fit_lognormal_recovers_parameters(synthetic_lognormal):
    fit = fit_distribution("lognormal", synthetic_lognormal, threshold=10_000)
    assert fit.n == len(synthetic_lognormal)
    assert fit.params["sigma"] == pytest.approx(1.2, rel=0.15)
    assert fit.ks_stat < 0.1
    assert np.isfinite(fit.aic)


def test_fit_all_returns_multiple_models(synthetic_lognormal):
    fits = fit_all(synthetic_lognormal, threshold=10_000)
    assert {"lognormal", "weibull", "gamma"}.issubset(fits)
    assert all(fit.n == len(synthetic_lognormal) for fit in fits.values())


def test_prepare_sample_filters_threshold_and_suspect():
    frame = pd.DataFrame(
        {
            "loss_eur_2025": [5_000, 50_000, 1e12, None],
            "in_year_range": [True, True, True, True],
            "loss_suspect": [False, False, True, False],
        }
    )
    sample = prepare_sample(frame, threshold=10_000)
    assert sample.tolist() == [50_000.0]


def test_annual_counts_fills_missing_years():
    frame = pd.DataFrame({"year": [2010, 2010, 2011, 2013]})
    counts = annual_counts(frame, 2010, 2013)
    assert counts.tolist() == [2, 1, 0, 1]


def test_diagnose_returns_poisson_estimate():
    counts = pd.Series([1, 2, 3, 4, 5])
    diagnostic = diagnose(counts)
    assert diagnostic.lambda_mle == pytest.approx(3.0)
    assert diagnostic.n_years == 5
    assert diagnostic.dispersion == pytest.approx(2.5 / 3.0)


def test_reference_files_exist():
    config = load_config()
    assert (config.data.reference_dir / "fx_rates.csv").exists()
    assert (config.data.reference_dir / "hicp_ea20.csv").exists()
