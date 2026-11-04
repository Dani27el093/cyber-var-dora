# Diccionario de datos

Salida del ETL: `data/processed/incidents_all.parquet` (10.047 filas) e `incidents_finance.parquet` (893 filas, NAICS 52*).

## Identificación y tiempo

| Columna | Tipo | Descripción |
|---|---|---|
| `incident_id` | texto | Identificador único del incidente en el VCDB. |
| `year` | entero | Año del incidente (`timeline.incident.year`); si falta, se usa `plus.dbir_year`. |
| `dbir_year` | entero | Año de edición del DBIR en el que se publicó el registro. |
| `in_year_range` | booleano | `True` si el año está en la ventana de análisis (2005-2025). |

## Víctima e industria

| Columna | Tipo | Descripción |
|---|---|---|
| `industry_code` | texto | Código NAICS de la víctima (2-6 dígitos). |
| `industry_sector` | texto | Etiqueta del sector a 2 dígitos (p. ej., "Finance and insurance"). |
| `is_finance` | booleano | `True` si el código NAICS empieza por 52. |
| `country` | texto | País o países de la víctima, separados por coma. |
| `employee_count_raw` | texto | Banda de empleados tal como aparece en el VCDB. |
| `employee_count_midpoint` | decimal | Punto medio numérico de la banda de empleados. |
| `revenue_raw` | texto | Banda de ingresos declarada, si existe. |

## Pérdida

| Columna | Tipo | Descripción |
|---|---|---|
| `loss_amount` | decimal | Importe del incidente en la moneda original. |
| `loss_currency` | texto | Código ISO de la moneda; si falta, se asigna USD (ver flag). |
| `loss_currency_assumed` | booleano | `True` si la moneda no estaba informada y se asumió USD. |
| `loss_source` | texto | `overall_amount`, `range_midpoint`, `components_sum` o `missing`. |
| `loss_suspect` | booleano | `True` si el importe supera el umbral de sospecha (1·10¹¹). |
| `fx_rate` | decimal | Unidades de moneda por EUR del año del incidente. |
| `hicp_index` | decimal | Índice HICP de la eurozona del año del incidente (2015=100). |
| `loss_eur` | decimal | Importe convertido a EUR del año del incidente. |
| `loss_eur_2025` | decimal | Importe normalizado a EUR de 2025 (FX + inflación). |
| `fx_missing` | booleano | `True` si no hay tipo de cambio para la moneda/año. |
| `loss_rating` | texto | Valoración cualitativa de severidad (Minor/Moderate/Major). |
| `loss_component_varieties` | texto | Categorías de pérdida declaradas, separadas por `;`. |
| `loss_component_sum` | decimal | Suma de los componentes numéricos (puede coexistir con el total). |
| `n_loss_components` | entero | Número de componentes de pérdida declarados. |
| `loss_notes` | texto | Notas libres sobre la pérdida. |

## Tipología del incidente

| Columna | Tipo | Descripción |
|---|---|---|
| `action_hacking` | booleano | Presencia de acción de hacking. |
| `action_malware` | booleano | Presencia de malware. |
| `action_social` | booleano | Ingeniería social. |
| `action_error` | booleano | Error humano o de proceso. |
| `action_misuse` | booleano | Uso indebido por parte de un actor con privilegios. |
| `action_physical` | booleano | Acción física. |
| `action_environmental` | booleano | Evento ambiental. |
| `actor_internal` | booleano | Actor interno. |
| `actor_external` | booleano | Actor externo. |
| `actor_partner` | booleano | Tercero o socio. |
| `cia_confidentiality` | booleano | Afectación de confidencialidad. |
| `cia_integrity` | booleano | Afectación de integridad. |
| `cia_availability` | booleano | Afectación de disponibilidad. |

## Campos de control

| Columna | Tipo | Descripción |
|---|---|---|
| `security_incident` | texto | Confirmación del incidente (Confirmed, False positive, etc.). |
| `analysis_status` | texto | Estado de análisis del registro en el VCDB. |
| `source_id` | texto | Fuente del registro. |
| `summary` | texto | Resumen narrativo del incidente. |
