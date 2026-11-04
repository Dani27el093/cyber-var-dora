# Datos de referencia

Tablas pequeñas y versionadas que permiten normalizar importes a EUR 2025:

- `fx_rates.csv`: tipos de cambio medios anuales (unidades de moneda por EUR) para USD, GBP, THB, INR, ZAR, CAD, AUD, CZK, KRW y SGD. Fuente: BCE (`eurofxref-hist`).
- `hicp_ea20.csv`: índice HICP anual medio de la eurozona (EA20, 2015=100). Fuente: Eurostat (`prc_hicp_aind`).

Se regeneran con:

```powershell
python scripts/build_reference_data.py
```

Los importes originales se conservan en `loss_amount` y `loss_currency`; la conversión se añade en `loss_eur`, `loss_eur_2025` y los flags `fx_missing` y `loss_currency_assumed`.
