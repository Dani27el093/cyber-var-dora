# Registro de decisiones

Este documento recoge las decisiones metodológicas y técnicas del proyecto, con su justificación y estado.

Estados: **Tomada**, **Propuesta** (default aplicado, revisable) y **Pendiente**.

---

## Técnicas

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| T1 | Python 3.12 con `.venv` | Tomada | Compatibilidad estable con pandas/scipy; entorno aislado. |
| T2 | Estructura `src/` + `scripts/` + `tests/` | Tomada | Lógica reutilizable separada de los puntos de entrada; facilita testing y CI. |
| T3 | Configuración en YAML | Tomada | Parámetros separados del código; sin valores mágicos. |
| T4 | Dataset combinado `data/joined/vcdb.json.zip` | Tomada | Conserva la estructura VERIS (importes, moneda, industria) y excluye web skimmers repetitivos. |
| T5 | Datos brutos y procesados fuera de Git | Tomada | El JSON pesa ~21 MB; se regeneran con scripts. |
| T6 | Verificación SHA-256 de la descarga | Tomada | Trazabilidad de la versión exacta del dataset. |
| T7 | Salida en Parquet | Tomada | Tipos preservados y lectura rápida. |
| T8 | CI con GitHub Actions (pytest) | Tomada | Tests en cada push; workflow en verde. |
| T9 | `pandas>=2.2,<3` | Tomada | Windows Application Control bloquea DLLs de pandas 3.1; 2.3.3 funciona. |
| T10 | `pyarrow>=15,<18` | Tomada | Las wheels de pyarrow ≥18 están bloqueadas por la misma política; 17.0.0 funciona. |
| T11 | Tablas de referencia versionadas | Tomada | Tipos BCE e HICP Eurostat en CSV pequeños; evita depender de red en cada ejecución. |

## Datos y definición de pérdida

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| D1 | Filtro de finanzas: NAICS `52*` | Tomada | Incluye banca, seguros, valores y actividades auxiliares. |
| D2 | Importe: `impact.overall_amount` si existe | Tomada | Es el total declarado; evita doble conteo. |
| D3 | Si no hay total: suma de componentes numéricos | Tomada | Recupera información de `impact.loss[]`; se marca la fuente. |
| D4 | Rangos (`overall_min/max_amount`): punto medio | Tomada | Aproximación estándar cuando solo se publica un intervalo. |
| D5 | Moneda ausente: USD por defecto, con flag | Tomada | VCDB es mayoritariamente estadounidense; el flag permite excluirla. |
| D6 | No eliminar outliers; tratar la cola | Tomada | Eliminarlos sesgaría el VaR a la baja. Se marca el registro de 1·10¹² USD como error de codificación y se excluye del ajuste. |
| D7 | Umbral de recolección de 10.000 € | Tomada | El VCDB infrarreporta pérdidas pequeñas; el umbral es explícito y sensible. |
| D8 | Normalización a EUR 2025 (FX BCE + HICP Eurostat) | Tomada | DORA es europea; permite comparar años y monedas. |
| D9 | `loss_suspect` para importes ≥1·10¹¹ | Tomada | Evita que un error de codificación distorsione la cola. |

## Modelado y simulación

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| M1 | Severidad *pooled* + sensibilidad de finanzas | Tomada | n=61 en finanzas es insuficiente; pooled (n=283) da un ajuste más estable. |
| M2 | λ como escenario (1/5/20) | Tomada | El VCDB no es un censo; la frecuencia real no es estimable. |
| M3 | VaR 95/99/99,9% + Expected Shortfall | Tomada | El 99,9% aislado es inestable; ES captura la cola. |
| M4 | 200.000 escenarios, vectorizado | Tomada | Reduce el error de simulación del percentil 99,9%. |
| M5 | Modelo agregado (sin dependencia entre eventos) | Tomada | Prioriza un resultado defendible y extensible. |
| M6 | Business case: Weibull finanzas como central y Lognormal pooled como estrés | Propuesta | Lognormal gana en AIC/KS, pero su cola extrema es inestable; Weibull es más robusta para planificación. Pendiente de confirmación. |

## Negocio y entrega

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| N1 | DORA como capital económico interno | Tomada | DORA no prescribe una fórmula de VaR; evita una afirmación incorrecta. |
| N2 | Documentación en español | Tomada | Coherente con el idioma del proyecto; se puede añadir un abstract en inglés. |
| N3 | Licencia | Pendiente | Definir MIT u otra antes de publicar. |
| N4 | `Instrucciones de proyecto.md` fuera del repo | Propuesta | Es un documento de trabajo interno; se puede incluir si se desea. |

---

## Decisiones resueltas

1. El proyecto es portfolio/académico, sin fecha límite ni rúbrica que obligue a una metodología cerrada.
2. Severidad: *pooled* con sensibilidad de finanzas.
3. Frecuencia: escenarios 1/5/20.
4. Outliers: no se eliminan; se marca el error de codificación y se usa truncamiento/cola.
5. Moneda: EUR 2025.
6. Repositorio público: <https://github.com/Dani27el093/cyber-var-dora>.

## Preguntas abiertas

1. ¿Se adopta Weibull de finanzas como modelo central del business case y Lognormal pooled como estrés (M6)?
2. ¿Se incluye `Instrucciones de proyecto.md` en el repositorio?
3. ¿Qué licencia se aplica?
4. ¿Se añade un abstract en inglés al README?
