"""Diagnóstico de frecuencia anual y modelos de recuento."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class FrequencyDiagnostic:
    """Resumen de los recuentos anuales observados en el VCDB."""

    n_years: int
    mean: float
    variance: float
    dispersion: float
    lambda_mle: float
    lambda_se: float
    poisson_pvalue: float


def annual_counts(frame: pd.DataFrame, start_year: int, end_year: int) -> pd.Series:
    """Serie de incidentes por año, completada con ceros en los años sin datos."""
    counts = frame.dropna(subset=["year"]).groupby("year").size()
    index = pd.Index(range(start_year, end_year + 1), name="year")
    return counts.reindex(index, fill_value=0).astype(int)


def diagnose(counts: pd.Series) -> FrequencyDiagnostic:
    """Estima λ por máxima verosimilitud y comprueba sobredispersión.

    La prueba de dispersión compara la varianza muestral con la media. Un
    contraste chi-cuadrado formal se incluye como referencia, pero con series
    truncadas por cobertura mediática el resultado es solo descriptivo.
    """
    values = counts.to_numpy(dtype=float)
    n = len(values)
    mean = float(values.mean())
    variance = float(values.var(ddof=1)) if n > 1 else 0.0
    dispersion = variance / mean if mean > 0 else float("nan")

    statistic = (n - 1) * variance / mean if mean > 0 else float("nan")
    pvalue = float(stats.chi2.sf(statistic, df=n - 1)) if mean > 0 else float("nan")

    return FrequencyDiagnostic(
        n_years=n,
        mean=mean,
        variance=variance,
        dispersion=dispersion,
        lambda_mle=mean,
        lambda_se=float(np.sqrt(mean / n)) if mean > 0 else 0.0,
        poisson_pvalue=pvalue,
    )
