# Datos

| Carpeta | Contenido | ¿Versionado? |
|---|---|---|
| `raw/` | Descarga original del VCDB (`vcdb.json.zip`, `vcdb_1-of-1.json`) y su SHA-256 | No |
| `processed/` | `incidents_all.parquet` e `incidents_finance.parquet` generados por el ETL | No |
| `reference/` | Tipos de cambio, índices de inflación y umbrales de calibración | Sí (archivos pequeños) |

## Regenerar todo

```powershell
python scripts/download_data.py
python scripts/build_dataset.py
python scripts/run_eda.py
```

## Fuente

VCDB (VERIS Community Database): <https://github.com/vz-risk/VCDB>

Se usa el archivo combinado `data/joined/vcdb.json.zip`, que excluye ~5.000 brechas repetitivas de web skimmers para no sesgar la muestra.
