"""Ajuste de distribuciones de severidad con truncamiento por umbral."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
from scipy import optimize, stats

LOGGER = logging.getLogger(__name__)

SUPPORTED_MODELS = ("lognormal", "weibull", "gamma", "pareto")
_SCIPY_NAMES = {"lognormal": "lognorm", "weibull": "weibull_min", "gamma": "gamma", "pareto": "pareto"}


@dataclass(frozen=True)
class SeverityFit:
    """Resultado del ajuste de una distribución de severidad."""

    name: str
    params: dict[str, float]
    threshold: float
    n: int
    loglik: float
    aic: float
    bic: float
    ks_stat: float
    ks_pvalue: float
    dist: stats.rv_continuous = field(repr=False, compare=False)
    frozen: stats.rv_frozen = field(repr=False, compare=False)

    def cdf(self, x: np.ndarray | float) -> np.ndarray:
        """CDF condicionada a superar el umbral."""
        base = self.frozen.cdf(self.threshold)
        return (self.frozen.cdf(x) - base) / (1.0 - base)

    def ppf(self, q: np.ndarray | float) -> np.ndarray:
        """Cuantil condicionado a superar el umbral."""
        base = self.frozen.cdf(self.threshold)
        return self.frozen.ppf(base + np.asarray(q) * (1.0 - base))

    def sample(self, size: int, rng: np.random.Generator) -> np.ndarray:
        """Muestrea pérdidas por encima del umbral."""
        return self.ppf(rng.uniform(size=size))

    def mean(self) -> float:
        """Media de la distribución truncada."""
        base = self.frozen.cdf(self.threshold)
        if self.name == "pareto":
            alpha = self.params["alpha"]
            if alpha <= 1:
                return float("inf")
            return alpha * self.threshold / (alpha - 1)
        if self.name == "lognormal":
            mu = self.params["mu"]
            sigma = self.params["sigma"]
            z = (np.log(self.threshold) - mu) / sigma
            return float(
                np.exp(mu + sigma**2 / 2) * stats.norm.sf(z - sigma) / stats.norm.sf(z)
            )
        # Integración numérica en escala logarítmica para colas pesadas
        upper = self.frozen.ppf(1 - 1e-10)
        if not np.isfinite(upper):
            upper = self.threshold * 1e9
        grid = np.exp(np.linspace(np.log(self.threshold), np.log(upper), 20_000))
        pdf = self.frozen.pdf(grid) / (1 - base)
        return float(np.trapezoid(grid * pdf, grid))


def _prepare(data: np.ndarray | pd.Series, threshold: float) -> np.ndarray:
    values = np.asarray(data, dtype=float)
    values = values[np.isfinite(values) & (values >= threshold)]
    return np.sort(values)


def _fit_truncated(
    frozen_factory: Callable[..., stats.rv_continuous],
    initial: np.ndarray,
    x: np.ndarray,
    threshold: float,
    bounds: list[tuple[float, float]] | None = None,
) -> np.ndarray:
    """Maximiza la verosimilitud de una distribución truncada por la izquierda."""

    def objective(theta: np.ndarray) -> float:
        frozen = frozen_factory(*theta)
        logpdf = frozen.logpdf(x)
        logsf = frozen.logsf(threshold)
        if not np.isfinite(logpdf).all() or not np.isfinite(logsf) or logsf > 0:
            return 1e12
        return float(-np.sum(logpdf - logsf))

    result = optimize.minimize(
        objective,
        np.asarray(initial, dtype=float),
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 5_000, "ftol": 1e-12},
    )
    if not result.success:
        LOGGER.debug("Optimización con aviso: %s", result.message)
    return result.x


def _fit_lognormal(x: np.ndarray, threshold: float) -> tuple[dict[str, float], stats.rv_frozen]:
    mu0 = float(np.mean(np.log(x)))
    sigma0 = max(float(np.std(np.log(x), ddof=1)), 1e-3)

    theta = _fit_truncated(
        lambda mu, log_sigma: stats.lognorm(s=np.exp(log_sigma), scale=np.exp(mu)),
        np.array([mu0, np.log(sigma0)]),
        x,
        threshold,
        bounds=[(-20.0, 40.0), (-6.0, 6.0)],
    )
    mu, sigma = float(theta[0]), float(np.exp(theta[1]))
    frozen = stats.lognorm(s=sigma, scale=np.exp(mu))
    return {"mu": mu, "sigma": sigma}, frozen


def _fit_weibull(x: np.ndarray, threshold: float) -> tuple[dict[str, float], stats.rv_frozen]:
    shape0, _, scale0 = stats.weibull_min.fit(x, floc=0)
    theta = _fit_truncated(
        lambda log_shape, log_scale: stats.weibull_min(c=np.exp(log_shape), scale=np.exp(log_scale)),
        np.array([np.log(shape0), np.log(scale0)]),
        x,
        threshold,
        bounds=[(-4.0, 8.0), (-4.0, 30.0)],
    )
    shape, scale = float(np.exp(theta[0])), float(np.exp(theta[1]))
    frozen = stats.weibull_min(c=shape, scale=scale)
    return {"shape": shape, "scale": scale}, frozen


def _fit_gamma(x: np.ndarray, threshold: float) -> tuple[dict[str, float], stats.rv_frozen]:
    shape0, _, scale0 = stats.gamma.fit(x, floc=0)
    theta = _fit_truncated(
        lambda log_shape, log_scale: stats.gamma(a=np.exp(log_shape), scale=np.exp(log_scale)),
        np.array([np.log(shape0), np.log(scale0)]),
        x,
        threshold,
        bounds=[(-3.0, 8.0), (-4.0, 30.0)],
    )
    shape, scale = float(np.exp(theta[0])), float(np.exp(theta[1]))
    frozen = stats.gamma(a=shape, scale=scale)
    return {"shape": shape, "scale": scale}, frozen


def _fit_pareto(x: np.ndarray, threshold: float) -> tuple[dict[str, float], stats.rv_frozen]:
    alpha0 = max(len(x) / np.sum(np.log(x / threshold)), 1.01)
    theta = _fit_truncated(
        lambda log_alpha: stats.pareto(b=np.exp(log_alpha), scale=threshold),
        np.array([np.log(alpha0)]),
        x,
        threshold,
        bounds=[(-3.0, 5.0)],
    )
    alpha = float(np.exp(theta[0]))
    frozen = stats.pareto(b=alpha, scale=threshold)
    return {"alpha": alpha}, frozen


_FITTERS = {
    "lognormal": _fit_lognormal,
    "weibull": _fit_weibull,
    "gamma": _fit_gamma,
    "pareto": _fit_pareto,
}


def fit_distribution(name: str, data: np.ndarray | pd.Series, threshold: float) -> SeverityFit:
    """Ajusta una distribución concreta y calcula AIC, BIC y KS."""
    if name not in _FITTERS:
        raise ValueError(f"Distribución no soportada: {name!r}")
    x = _prepare(data, threshold)
    if len(x) < 10:
        raise ValueError(f"Muestra insuficiente para ajustar {name}: n={len(x)}")

    params, frozen = _FITTERS[name](x, threshold)
    loglik = float(np.sum(frozen.logpdf(x) - frozen.logsf(threshold)))
    k = len(params)
    aic = 2 * k - 2 * loglik
    bic = k * np.log(len(x)) - 2 * loglik

    fit = SeverityFit(
        name=name,
        params=params,
        threshold=threshold,
        n=len(x),
        loglik=loglik,
        aic=float(aic),
        bic=float(bic),
        ks_stat=float("nan"),
        ks_pvalue=float("nan"),
        dist=getattr(stats, _SCIPY_NAMES[name]),
        frozen=frozen,
    )
    ks = stats.kstest(x, fit.cdf)
    return SeverityFit(
        name=fit.name,
        params=fit.params,
        threshold=fit.threshold,
        n=fit.n,
        loglik=fit.loglik,
        aic=fit.aic,
        bic=fit.bic,
        ks_stat=float(ks.statistic),
        ks_pvalue=float(ks.pvalue),
        dist=fit.dist,
        frozen=fit.frozen,
    )


def fit_all(data: np.ndarray | pd.Series, threshold: float) -> dict[str, SeverityFit]:
    """Ajusta todas las familias soportadas y omite las que no convergen."""
    fits: dict[str, SeverityFit] = {}
    for name in SUPPORTED_MODELS:
        try:
            fits[name] = fit_distribution(name, data, threshold)
            LOGGER.info(
                "Ajuste %-9s n=%s AIC=%.1f KS=%.4f (p=%.4f)",
                name,
                fits[name].n,
                fits[name].aic,
                fits[name].ks_stat,
                fits[name].ks_pvalue,
            )
        except Exception as exc:  # noqa: BLE001 - se documenta y se continúa
            LOGGER.warning("No se pudo ajustar %s: %s", name, exc)
    return fits


def bootstrap_ks_pvalue(
    fit: SeverityFit,
    n_boot: int = 200,
    seed: int = 42,
) -> float:
    """P-valor de KS por bootstrap paramétrico, reajustando en cada réplica."""
    rng = np.random.default_rng(seed)
    fitter = _FITTERS[fit.name]
    observed = fit.ks_stat
    exceedances = 0
    for _ in range(n_boot):
        sample = fit.sample(fit.n, rng)
        try:
            params, frozen = fitter(np.sort(sample), fit.threshold)
            replica = SeverityFit(
                name=fit.name,
                params=params,
                threshold=fit.threshold,
                n=len(sample),
                loglik=0.0,
                aic=0.0,
                bic=0.0,
                ks_stat=float("nan"),
                ks_pvalue=float("nan"),
                dist=fit.dist,
                frozen=frozen,
            )
            statistic = stats.kstest(sample, replica.cdf).statistic
        except Exception:  # noqa: BLE001
            continue
        exceedances += int(statistic >= observed)
    return (exceedances + 1) / (n_boot + 1)


def comparison_table(fits: dict[str, SeverityFit], bootstrap: bool = False, n_boot: int = 200) -> pd.DataFrame:
    """Tabla comparativa de ajustes ordenada por AIC."""
    rows = []
    for fit in fits.values():
        row = {
            "model": fit.name,
            "n": fit.n,
            "k": len(fit.params),
            "loglik": round(fit.loglik, 2),
            "aic": round(fit.aic, 2),
            "bic": round(fit.bic, 2),
            "ks_stat": round(fit.ks_stat, 4),
            "ks_pvalue": round(fit.ks_pvalue, 4),
            "params": ", ".join(f"{key}={value:.4g}" for key, value in fit.params.items()),
        }
        if bootstrap:
            row["ks_pvalue_boot"] = round(bootstrap_ks_pvalue(fit, n_boot=n_boot), 4)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("aic").reset_index(drop=True)


def prepare_sample(
    frame: pd.DataFrame,
    threshold: float,
    column: str = "loss_eur_2025",
    exclude_suspect: bool = True,
) -> pd.Series:
    """Filtra la muestra de severidad: ventana temporal, EUR disponible y umbral."""
    mask = frame["in_year_range"] & frame[column].notna() & (frame[column] >= threshold)
    if exclude_suspect:
        mask &= ~frame["loss_suspect"]
    return frame.loc[mask, column].astype(float)
