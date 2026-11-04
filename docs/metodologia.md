# Metodología

Documento técnico del modelo de cuantificación del VaR por ciberriesgo. Acompaña al código de `src/cybervar/` y a los resultados de `outputs/`.

## 1. Objetivo y alcance

Se estima la distribución anual de pérdidas por incidentes de ciberseguridad en el sector financiero mediante un **Loss Distribution Approach (LDA)**:

\[
L = \sum_{i=1}^{N} X_i
\]

donde \(N\) es el número de incidentes materiales en un año y \(X_i\) es la pérdida de cada incidente. El VaR es el percentil \(\alpha\) de \(L\):

\[
\mathrm{VaR}_\alpha = \inf\{l : P(L \le l) \ge \alpha\}
\]

El alcance es una **entidad financiera genérica**; no se modela una cartera concreta ni se incorporan datos internos. El resultado es capital económico interno y una herramienta de apetito de riesgo, no una cifra regulatoria prescrita.

## 2. Datos y normalización

**Fuente:** VCDB (VERIS Community Database), archivo combinado `data/joined/vcdb.json.zip`, que excluye ~5.000 brechas repetitivas de web skimmers.

**Universo:** incidentes con código NAICS 52* (finanzas y seguros). Universo completo: 10.047 incidentes; finanzas: 893.

**Variable de pérdida:** `impact.overall_amount`. Si falta, se usa el punto medio del rango (`overall_min_amount`, `overall_max_amount`) o la suma de componentes numéricos, en ese orden. La fuente queda registrada en `loss_source`.

**Filtros:**

- Ventana temporal 2005-2025 (`in_year_range`).
- Pérdida en EUR 2025 disponible.
- Umbral de recolección \(u = 10.000\) € (`loss_eur_2025 >= u`).
- Exclusión del registro de 1·10¹² USD (Yahoo, 2016), marcado como `loss_suspect` por ser incompatible con las cifras públicas.

**Normalización monetaria:**

1. Tipo de cambio medio anual del BCE (unidades de moneda por EUR): \(A_{\text{EUR},t} = A_{\text{moneda},t} / \text{FX}_t\).
2. Inflación con el HICP anual medio de la eurozona (EA20, 2015=100): \(A_{\text{EUR},2025} = A_{\text{EUR},t} \cdot \frac{\text{HICP}_{2025}}{\text{HICP}_t}\).

Los tipos y el HICP se generan con `scripts/build_reference_data.py` y se versionan en `data/reference/`.

**Tamaños de muestra:** 283 pérdidas *pooled* y 49 de finanzas por encima del umbral.

## 3. Frecuencia

El VCDB **no es un censo**: el número de incidentes por año depende de la cobertura mediática y de la política de publicación. La serie de finanzas tiene una media de ~42 incidentes al año en 2005-2025, una cifra que representa el mercado agregado, no una entidad individual. Por eso λ no se estima del VCDB.

Se usan **escenarios de negocio**:

| Escenario | λ (incidentes materiales/año) | Interpretación |
|---|---:|---|
| Bajo | 1 | Entidad con pocos incidentes materiales |
| Base | 5 | Banco mediano con exposición relevante |
| Alto | 20 | Entidad sistémica o año adverso |

La frecuencia se modela como \(N \sim \mathrm{Poisson}(\lambda)\). El diagnóstico de sobredispersión del VCDB se calcula con `models/frequency.py` y se reporta solo como referencia descriptiva.

**Nota:** λ se define sobre incidentes **por encima del umbral** de 10.000 €. No es la frecuencia de todos los incidentes, sino la de incidentes materiales que entran en el modelo de severidad.

## 4. Severidad

### 4.1 Distribuciones candidatas

| Modelo | Parámetros | Cola |
|---|---|---|
| Lognormal | \(\mu, \sigma\) | Subexponencial |
| Weibull | forma \(k\), escala \(\lambda\) | Subexponencial si \(k<1\) |
| Gamma | forma \(a\), escala \(\theta\) | Subexponencial si \(a<1\) |
| Pareto (tipo I) | \(\alpha\), escala \(u\) | Power law |

### 4.2 Verosimilitud con truncamiento

Como solo se observan pérdidas por encima de \(u\), se maximiza la verosimilitud truncada:

\[
\ell(\theta) = \sum_{i=1}^{n} \left[ \log f(x_i;\theta) - \log(1 - F(u;\theta)) \right]
\]

Para la Pareto tipo I el soporte es \([u, \infty)\), por lo que el truncamiento es inherente y el MLE de \(\alpha\) es:

\[
\hat{\alpha} = \frac{n}{\sum_{i=1}^{n} \log(x_i/u)}
\]

Si \(\hat{\alpha} \le 1\), la media es infinita y el modelo se excluye de la simulación (se documenta como caso degenerado).

### 4.3 Selección

- **Kolmogorov-Smirnov** sobre la CDF truncada.
- **AIC** y **BIC** para comparar familias con distinto número de parámetros.
- **QQ-plots** en escala logarítmica para inspeccionar la cola.
- **Sensibilidad:** se repite el ajuste con la muestra solo de finanzas y con umbrales alternativos.

Los p-valores de KS son aproximados porque los parámetros se estiman; se interpretan junto con AIC/BIC y los QQ-plots, no como un test formal definitivo.

## 5. Simulación y métricas

Para cada combinación de modelo y λ:

1. \(N_j \sim \mathrm{Poisson}(\lambda)\) para \(j=1,\dots,200.000\) años.
2. \(X_{j,i} \sim F_\theta(\cdot \mid X > u)\).
3. \(L_j = \sum_{i=1}^{N_j} X_{j,i}\).

La simulación es vectorizada: se muestrean todos los eventos de una vez y se agregan por año con `np.bincount`.

**Métricas:**

- \(\mathrm{VaR}_\alpha\): cuantil empírico con método `higher`.
- \(\mathrm{ES}_\alpha = E[L \mid L \ge \mathrm{VaR}_\alpha]\).
- Error de simulación del VaR por **medias de lotes** (20 lotes).
- Convergencia del VaR al aumentar el número de escenarios.

## 6. Resultados

### 6.1 Comparación de modelos (pooled, u=10.000 €)

| Modelo | AIC | BIC | KS | p-valor | Parámetros |
|---|---:|---:|---:|---:|---|
| **Lognormal** | **8.749,5** | **8.756,7** | **0,066** | **0,160** | μ=12,49; σ=2,96 |
| Weibull | 8.761,2 | 8.768,5 | 0,088 | 0,023 | k=0,213; λ=135.321 |
| Gamma | 8.831,9 | 8.839,2 | 0,242 | 0,000 | a=0,050; θ=1,40·10⁸ |
| Pareto | 8.842,6 | 8.846,2 | 0,218 | 0,000 | α=0,249 |

Lognormal es la mejor por AIC y KS. Weibull es competitiva y más estable en la cola extrema; Gamma y Pareto ajustan mal.

### 6.2 Muestra de finanzas (u=10.000 €, n=49)

| Modelo | AIC | KS | p-valor | Parámetros |
|---|---:|---:|---:|---|
| **Lognormal** | **1.586,1** | **0,087** | **0,821** | μ=13,70; σ=2,52 |
| Weibull | 1.588,8 | 0,103 | 0,641 | k=0,307; λ=1,41·10⁶ |
| Gamma | 1.593,9 | 0,157 | 0,161 | a=0,050; θ=1,15·10⁸ |
| Pareto | 1.615,3 | 0,261 | 0,002 | α=0,213 |

La conclusión se mantiene, pero la muestra es pequeña y los intervalos de confianza serían amplios.

### 6.3 VaR y ES (pooled, Lognormal)

| λ | VaR 95% (M€) | VaR 99% (M€) | VaR 99,9% (M€) | ES 99,9% (M€) |
|---:|---:|---:|---:|---:|
| 1 | 45 | 323 | 3.353 | 11.827 |
| 5 | 338 | 1.560 | 10.796 | 30.921 |
| 20 | 1.467 | 5.510 | 31.542 | 107.651 |

### 6.4 Rango entre modelos (VaR 99,9%, M€)

| λ | Gamma | Weibull | Lognormal |
|---:|---:|---:|---:|
| 1 | 535 | 1.730 | 3.353 |
| 5 | 852 | 4.315 | 10.796 |
| 20 | 1.522 | 8.510 | 31.542 |

En finanzas (λ=5): 705 / 1.753 / 6.939 M€. El rango supera un orden de magnitud.

## 7. Riesgo de modelo

El resultado no es una cifra única. Las tres fuentes de incertidumbre son:

1. **Elección de distribución:** la cola extrema no está identificada por los datos. Lognormal extrapola pérdidas individuales muy por encima del máximo observado; Gamma las subestima; Weibull queda en un punto intermedio.
2. **Frecuencia:** λ es un supuesto de negocio, no una estimación. Pasar de 1 a 20 incidentes multiplica el VaR por ~9-10.
3. **Muestra:** 49 pérdidas de finanzas son insuficientes para estimar la cola al 99,9%; la muestra *pooled* mejora la estimación pero introduce el supuesto de homogeneidad entre sectores.

Por eso el VaR debe comunicarse como **rango** y complementarse con escenarios y stress testing.

## 8. Convergencia

El gráfico [`figures/var_convergence.png`](figures/var_convergence.png) muestra que el VaR al 99,9% es inestable con menos de ~10⁵ escenarios. Con 10.000 simulaciones (el mínimo del brief), el percentil 99,9% son solo 10 observaciones y el resultado depende de si aparece o no un evento extremo. Se recomienda:

- ≥200.000 escenarios para el 99,9%.
- Reportar el error de simulación por lotes.
- Fijar semilla y repetir con varias semillas para medir la variabilidad.

## 9. Limitaciones

- El VCDB no es un censo y sobrerrepresenta incidentes públicos y grandes.
- La moneda y el año del incidente no siempre coinciden con la fecha de la pérdida; se usa el año del incidente y el tipo medio anual.
- El 32% de las pérdidas de finanzas no declara moneda; se asume USD y se marca con `loss_currency_assumed`.
- No se modela dependencia entre incidentes ni entre tipos de evento; el modelo es agregado.
- No se incluyen pérdidas reputacionales no monetizadas ni costes de continuidad de negocio.
- El VaR no es una medida coherente; se reporta junto con ES.

## 10. Reproducibilidad

```powershell
python scripts/build_reference_data.py
python scripts/build_dataset.py
python scripts/run_eda.py
python scripts/fit_severity.py
python scripts/run_simulation.py
```

Parámetros en `config/config.yaml`, semilla en `random_seed` y resultados en `outputs/`. Los datos brutos no se versionan; se descargan con `scripts/download_data.py` y se verifican con SHA-256.
