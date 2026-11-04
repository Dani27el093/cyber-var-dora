"""Tests del motor de Montecarlo."""

from __future__ import annotations

import numpy as np
import pytest

from cybervar.models.severity import fit_distribution
from cybervar.simulation.montecarlo import (
    convergence_path,
    run_scenarios,
    simulate_aggregate,
    var_es,
)


@pytest.fixture(scope="module")
def fit():
    rng = np.random.default_rng(11)
    sample = rng.lognormal(mean=11.0, sigma=1.0, size=2_000)
    sample = sample[sample >= 10_000][:400]
    return fit_distribution("lognormal", sample, threshold=10_000)


def test_zero_frequency_gives_zero_losses(fit):
    rng = np.random.default_rng(1)
    losses = simulate_aggregate(fit, lam=0, n_years=500, rng=rng)
    assert losses.shape == (500,)
    assert np.all(losses == 0)


def test_simulation_is_non_negative(fit):
    rng = np.random.default_rng(2)
    losses = simulate_aggregate(fit, lam=3, n_years=1_000, rng=rng)
    assert losses.shape == (1_000,)
    assert np.all(losses >= 0)


def test_var_and_es_are_ordered(fit):
    rng = np.random.default_rng(3)
    losses = simulate_aggregate(fit, lam=5, n_years=20_000, rng=rng)
    table = var_es(losses, (0.95, 0.99, 0.999))
    assert table["var"].is_monotonic_increasing
    assert (table["es"] >= table["var"]).all()


def test_run_scenarios_returns_all_combinations(fit):
    results = run_scenarios({"lognormal": fit}, (1, 5), (0.95, 0.99), n_scenarios=2_000, seed=4)
    assert len(results) == 4
    assert set(results["lambda"]) == {1, 5}


def test_convergence_path_grows(fit):
    frame = convergence_path(fit, lam=1, level=0.99, max_scenarios=20_000, seed=5, n_points=10)
    assert frame["n_scenarios"].is_monotonic_increasing
    assert len(frame) == 10
