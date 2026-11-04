# Registro de decisiones

Este documento recoge las decisiones metodológicas y técnicas del proyecto, con su justificación y estado. Se actualizará a medida que avance el trabajo.

Estados: **Tomada**, **Propuesta** (default aplicado, revisable) y **Pendiente** (requiere decisión del autor).

---

## Técnicas

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| T1 | Python 3.12 con `.venv` | Tomada | Compatibilidad estable con pandas/scipy; entorno aislado y reproducible. |
| T2 | Estructura `src/` + `scripts/` + `tests/` | Tomada | Separación entre lógica reutilizable y puntos de entrada; facilita testing y CI. |
| T3 | Configuración en YAML | Tomada | Parámetros de negocio separados del código; evita valores mágicos. |
| T4 | Dataset combinado `data/joined/vcdb.json.zip` | Tomada | Conserva la estructura VERIS original (importes, moneda, industria) y excluye web skimmers repetitivos. |
| T5 | Datos brutos y procesados fuera de Git | Tomada | El JSON pesa ~21 MB y el CSV ~170 MB; se regeneran con scripts. |
| T6 | Verificación SHA-256 de la descarga | Tomada | Trazabilidad de la versión exacta del dataset utilizada. |
| T7 | Salida en Parquet | Tomada | Tipos preservados, lectura rápida y menor tamaño que CSV. |
| T8 | CI con GitHub Actions (pytest) | Tomada | Garantiza que los tests pasan en cada push. |
| T9 | `pandas>=2.2,<3` | Tomada | Windows Application Control bloquea DLLs de pandas 3.1; 2.3.3 funciona y es estable. |
| T10 | `pyarrow>=15,<18` | Tomada | Las wheels de pyarrow ≥18 están bloqueadas por la misma política; 17.0.0 funciona. |

## Datos y definición de pérdida

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| D1 | Filtro de finanzas: NAICS `52*` | Tomada | Incluye banca, seguros, valores y actividades auxiliares. |
| D2 | Importe: `impact.overall_amount` si existe | Propuesta | Es el total declarado del incidente; evita doble conteo de componentes. |
| D3 | Si no hay total: suma de componentes numéricos | Propuesta | Recupera información de `impact.loss[]`; se marca la fuente del dato. |
| D4 | Rangos (`overall_min/max_amount`): punto medio | Propuesta | Aproximación estándar cuando solo se publica un intervalo. |
| D5 | Moneda ausente: USD por defecto, con flag | Propuesta | VCDB es mayoritariamente estadounidense; el flag permite excluirla en sensibilidad. |
| D6 | No eliminar outliers; analizarlos y tratar la cola | Pendiente | Eliminarlos sesgaría el VaR a la baja, pero el plan original pedía limpiarlos. |
| D7 | Umbral de recolección (10.000 € propuesto) | Pendiente | El VCDB infrarreporta pérdidas pequeñas; el umbral debe ser explícito. |
| D8 | Normalización a EUR 2025 (FX + inflación) | Pendiente | DORA es europea, pero exige tipos del BCE e IPC armonizado. |
| D9 | Tratar el importe de 1·10¹² USD (Yahoo, 2016) como error de codificación | Propuesta | Es incompatible con las cifras públicas y distorsiona toda la cola; se excluirá en el ajuste y se documentará. |

## Modelado y simulación

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| M1 | Severidad *pooled* entre sectores (n=324) | Pendiente | n=61 en finanzas es insuficiente para un ajuste robusto. |
| M2 | λ como supuesto de escenario con sensibilidad | Pendiente | El VCDB no permite estimar una frecuencia real. |
| M3 | VaR a 95/99/99,9% + Expected Shortfall | Propuesta | El 99,9% aislado es inestable con muestras pequeñas; ES captura la cola. |
| M4 | ≥200.000 escenarios, vectorizado | Propuesta | Reduce el error de simulación del percentil 99,9%. |
| M5 | Modelo agregado antes que desagregado por evento DORA | Propuesta | Prioriza un resultado defendible y extensible. |

## Negocio y entrega

| # | Decisión | Estado | Justificación |
|---|---|---|---|
| N1 | Encuadre DORA como capital económico interno | Pendiente | DORA no prescribe una fórmula de VaR; evita una afirmación incorrecta. |
| N2 | README en español | Propuesta | Coherente con el idioma del proyecto; se puede añadir un abstract en inglés. |
| N3 | Licencia | Pendiente | Definir MIT u otra antes de publicar. |

---

## Preguntas abiertas

1. ¿El proyecto es académico, portfolio o encargo real? ¿Hay fecha límite o rúbrica que obligue a seguir las fases literalmente?
2. ¿Qué estrategia de severidad se adopta: solo finanzas (n=61), *pooled* (n=324), benchmarks externos o datos sintéticos?
3. ¿Cómo se fija λ: estimación VCDB, escenario (1/5/20 incidentes al año) o ambos?
4. ¿Se autoriza el tratamiento de cola (truncamiento/EVT) en lugar de eliminar outliers?
5. ¿Moneda y año de referencia: EUR 2025 o USD nominal?
6. ¿Repositorio público o privado? ¿Nombre definitivo?
