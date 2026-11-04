# Metodología

> Documento en construcción. Se completará durante las fases 3-5 con los resultados definitivos.

## 1. Enfoque

Se utiliza un **Loss Distribution Approach (LDA)**:

1. **Frecuencia:** número de incidentes por año, \(N \sim \mathrm{Poisson}(\lambda)\).
2. **Severidad:** pérdida por incidente, \(X \sim F_\theta\) (cola pesada).
3. **Pérdida agregada anual:** \(L = \sum_{i=1}^{N} X_i\), con \(L=0\) si \(N=0\).
4. **VaR:** \( \mathrm{VaR}_\alpha = \inf\{l : P(L \le l) \ge \alpha\} \).

## 2. Datos

- Fuente: VCDB (VERIS Community Database), archivo combinado `data/joined/vcdb.json.zip`.
- Universo: incidentes del sector financiero y de seguros (NAICS 52*).
- Variable de pérdida: `impact.overall_amount`; si falta, punto medio del rango o suma de componentes numéricos.
- Limitación principal: solo 61 incidentes financieros tienen importe declarado.

## 3. Decisiones pendientes

Ver [`decisiones.md`](decisiones.md). Las más relevantes:

- severidad *pooled* vs. solo finanzas;
- definición de \(\lambda\);
- tratamiento de outliers y umbral de recolección;
- normalización monetaria a EUR.

## 4. Validación

- Kolmogorov-Smirnov, Anderson-Darling y Cramér-von Mises sobre la muestra (con corrección por parámetros estimados).
- AIC/BIC para comparación entre familias.
- Bootstrap para intervalos de confianza de los parámetros y del VaR.
- Análisis de convergencia del Montecarlo.
- Sensibilidad a \(\lambda\), umbral, distribución y tipo de cambio.

## 5. Limitaciones

- El VCDB no es un censo: la frecuencia observada refleja cobertura mediática.
- Sesgo de selección hacia incidentes públicos y de gran tamaño.
- Heterogeneidad de monedas, años y definiciones de pérdida.
- El VaR no es una medida coherente de riesgo; se reporta junto con Expected Shortfall.
