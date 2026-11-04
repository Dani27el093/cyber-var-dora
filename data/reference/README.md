# Datos de referencia

Archivos pequeños y versionados que permiten normalizar importes:

- `fx_rates.csv`: tipos de cambio anuales promedio a EUR (fuente BCE / Frankfurter).
- `hicp.csv`: índice de precios armonizado de la eurozona (fuente Eurostat).

Se incorporarán en la fase de normalización monetaria. Mientras tanto, los importes se conservan en su moneda original con la columna `loss_currency` y el flag `loss_currency_assumed`.
