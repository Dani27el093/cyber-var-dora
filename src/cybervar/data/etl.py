"""ETL del VCDB: de registros VERIS a un dataset tabular de pérdidas."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

from cybervar.config import Config
from cybervar.data.currency import add_eur_2025

LOGGER = logging.getLogger(__name__)

NAICS_SECTOR_LABELS = {
    "11": "Agriculture, forestry and fishing",
    "21": "Mining and quarrying",
    "22": "Utilities",
    "23": "Construction",
    "31": "Manufacturing",
    "32": "Manufacturing",
    "33": "Manufacturing",
    "42": "Wholesale trade",
    "44": "Retail trade",
    "45": "Retail trade",
    "48": "Transportation and warehousing",
    "49": "Transportation and warehousing",
    "51": "Information",
    "52": "Finance and insurance",
    "53": "Real estate",
    "54": "Professional, scientific and technical services",
    "55": "Management of companies",
    "56": "Administrative and support services",
    "61": "Educational services",
    "62": "Health care and social assistance",
    "71": "Arts, entertainment and recreation",
    "72": "Accommodation and food services",
    "81": "Other services",
    "92": "Public administration",
}

ACTION_CATEGORIES = ("hacking", "malware", "social", "error", "misuse", "physical", "environmental")

_NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_RANGE_RE = re.compile(
    r"^([\d,]+(?:\.\d+)?)\s*(?:-|–|—|to)\s*([\d,]+(?:\.\d+)?)$",
    re.IGNORECASE,
)
_EMPLOYEE_RANGE_RE = re.compile(r"(\d+)\s*(?:to|-|–|—)\s*(\d+)", re.IGNORECASE)


def _as_text(value: Any) -> str | None:
    """Convierte un valor escalar en texto limpio; devuelve None si está vacío."""
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return _as_text(_first_value(value))
    text = str(value).strip()
    if not text or text.lower() in {"unknown", "n/a", "na", "none", "null", "nan"}:
        return None
    return text


def _first_value(value: Any) -> Any:
    """Devuelve el primer valor no vacío de una lista (VERIS usa listas en varios campos)."""
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if item not in (None, ""):
                return item
        return None
    return value


def parse_amount(value: Any) -> float | None:
    """Normaliza importes de VERIS: números, cadenas con separadores y rangos.

    Ejemplos:
        "1,000,000" -> 1000000.0
        "$250,000"  -> 250000.0
        "1000-5000" -> 3000.0 (punto medio)
        "Unknown"   -> None
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if pd.notna(value) else None

    text = str(value).strip().replace("$", "").replace("€", "").replace("£", "").replace("¥", "")
    text = text.replace(" ", "")
    if not text:
        return None

    range_match = _RANGE_RE.match(text)
    if range_match:
        low = float(range_match.group(1).replace(",", ""))
        high = float(range_match.group(2).replace(",", ""))
        return (low + high) / 2

    cleaned = text.replace(",", "")
    if _NUMBER_RE.match(cleaned):
        return float(cleaned)
    return None


def parse_employee_band(value: Any) -> float | None:
    """Convierte bandas de empleados ("1,000 to 9,999", "Over 100000") a un punto medio."""
    text = _as_text(value)
    if text is None:
        return None
    normalized = text.lower().replace(",", "")
    match = _EMPLOYEE_RANGE_RE.search(normalized)
    if match:
        return (int(match.group(1)) + int(match.group(2))) / 2
    for pattern in (r"(?:over|more than|>)\s*(\d+)", r"(?:under|less than|<)\s*(\d+)"):
        match = re.search(pattern, normalized)
        if match:
            return float(match.group(1))
    match = re.search(r"(\d+)", normalized)
    return float(match.group(1)) if match else None


def normalize_currency(value: Any) -> str | None:
    """Valida y normaliza un código ISO de moneda de tres letras."""
    text = _as_text(value)
    if text is None:
        return None
    code = text.upper()
    return code if len(code) == 3 and code.isalpha() else None


def _iter_loss_components(raw: Any) -> list[dict[str, Any]]:
    """Acepta lista, dict único o dict indexado de componentes de pérdida."""
    if raw is None:
        return []
    if isinstance(raw, dict):
        items: list[Any] = [raw] if {"variety", "amount", "rating"} & set(raw) else list(raw.values())
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        items = [raw]

    components: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        components.append(
            {
                "variety": _as_text(item.get("variety")),
                "amount": parse_amount(item.get("amount")),
                "rating": _as_text(item.get("rating")),
            }
        )
    return components


def extract_loss(record: dict[str, Any], config: Config) -> dict[str, Any]:
    """Extrae el importe del incidente aplicando la regla de precedencia configurada."""
    impact = record.get("impact") or {}
    if not isinstance(impact, dict):
        impact = {}

    components = _iter_loss_components(impact.get("loss"))
    component_amounts = [item["amount"] for item in components if item["amount"] is not None]
    component_sum = float(sum(component_amounts)) if component_amounts else None

    overall = parse_amount(impact.get("overall_amount"))
    low = parse_amount(impact.get("overall_min_amount"))
    high = parse_amount(impact.get("overall_max_amount"))

    amount: float | None = None
    source = "missing"

    if config.losses.prefer_overall_amount and overall is not None and overall > 0:
        amount, source = overall, "overall_amount"
    elif config.losses.range_policy == "midpoint" and (low is not None or high is not None):
        bounds = [bound for bound in (low, high) if bound is not None]
        amount, source = sum(bounds) / len(bounds), "range_midpoint"
    elif config.losses.include_component_sum and component_sum is not None and component_sum > 0:
        amount, source = component_sum, "components_sum"

    currency = normalize_currency(impact.get("iso_currency_code"))
    currency_assumed = False
    if amount is not None and currency is None:
        currency = config.losses.missing_currency_default.upper()
        currency_assumed = True

    varieties = sorted({item["variety"] for item in components if item["variety"]})
    return {
        "loss_amount": float(amount) if amount is not None else None,
        "loss_currency": currency,
        "loss_currency_assumed": currency_assumed,
        "loss_source": source,
        "loss_suspect": bool(amount is not None and amount >= config.losses.suspect_amount_threshold),
        "loss_rating": _as_text(impact.get("overall_rating")),
        "loss_component_varieties": ";".join(varieties) if varieties else None,
        "loss_component_sum": component_sum,
        "n_loss_components": len(components),
        "loss_notes": _as_text(impact.get("notes")),
    }


def extract_timeline(record: dict[str, Any]) -> tuple[int | None, int | None]:
    """Devuelve (año del incidente, año DBIR) con fallback entre ambos."""
    timeline = record.get("timeline") or {}
    incident = timeline.get("incident") or {}
    plus = record.get("plus") or {}

    incident_year = pd.to_numeric(incident.get("year"), errors="coerce")
    dbir_year = pd.to_numeric(plus.get("dbir_year"), errors="coerce")
    year = incident_year if pd.notna(incident_year) else dbir_year
    return (
        int(year) if pd.notna(year) else None,
        int(dbir_year) if pd.notna(dbir_year) else None,
    )


def extract_victim(record: dict[str, Any]) -> dict[str, Any]:
    """Extrae industria, país, tamaño y datos de la víctima."""
    victim = record.get("victim") or {}
    industry = _as_text(victim.get("industry"))
    sector = industry.split(".")[0][:2] if industry else None

    countries = victim.get("country")
    if isinstance(countries, (list, tuple, set)):
        country_text = ", ".join(str(item) for item in countries if item) or None
    else:
        country_text = _as_text(countries)

    return {
        "industry_code": industry,
        "industry_sector": NAICS_SECTOR_LABELS.get(sector, "Other/unknown") if sector else None,
        "country": country_text,
        "employee_count_raw": _as_text(victim.get("employee_count")),
        "employee_count_midpoint": parse_employee_band(victim.get("employee_count")),
        "revenue_raw": _as_text(victim.get("revenue")),
    }


def extract_event_flags(record: dict[str, Any]) -> dict[str, bool]:
    """Marca categorías de acción, tipo de actor y dimensiones CIA."""
    action = record.get("action") or {}
    actor = record.get("actor") or {}
    attribute = record.get("attribute") or {}

    flags = {f"action_{category}": bool(action.get(category)) for category in ACTION_CATEGORIES}
    flags.update(
        {
            "actor_internal": bool(actor.get("internal")),
            "actor_external": bool(actor.get("external")),
            "actor_partner": bool(actor.get("partner")),
            "cia_confidentiality": bool(attribute.get("confidentiality")),
            "cia_integrity": bool(attribute.get("integrity")),
            "cia_availability": bool(attribute.get("availability")),
        }
    )
    return flags


def extract_record(record: dict[str, Any], config: Config) -> dict[str, Any]:
    """Convierte un registro VERIS en una fila tabular."""
    year, dbir_year = extract_timeline(record)
    plus = record.get("plus") or {}
    victim = extract_victim(record)

    industry = victim["industry_code"]
    row: dict[str, Any] = {
        "incident_id": _as_text(record.get("incident_id")),
        "year": year,
        "dbir_year": dbir_year,
        "is_finance": bool(industry and industry.startswith(config.data.finance_naics_prefix)),
        "security_incident": _as_text(record.get("security_incident")),
        "analysis_status": _as_text(plus.get("analysis_status")),
        "source_id": _as_text(record.get("source_id")),
        "summary": _as_text(record.get("summary")),
        **victim,
        **extract_loss(record, config),
        **extract_event_flags(record),
    }
    row["in_year_range"] = bool(year is not None and config.data.min_year <= year <= config.data.max_year)
    return row


def load_records(json_path: str | Path) -> list[dict[str, Any]]:
    """Carga el JSON combinado del VCDB."""
    path = Path(json_path)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        if "incidents" in data and isinstance(data["incidents"], list):
            data = data["incidents"]
        else:
            data = list(data.values())

    if not isinstance(data, list):
        raise ValueError(f"Formato inesperado en {path}: se esperaba una lista de incidentes")
    return [item for item in data if isinstance(item, dict)]


def build_dataframe(records: list[dict[str, Any]], config: Config) -> pd.DataFrame:
    """Construye el DataFrame completo y normaliza tipos."""
    frame = pd.DataFrame(extract_record(record, config) for record in records)

    for column in ("year", "dbir_year", "n_loss_components"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Int64")

    for column in ("loss_amount", "loss_component_sum", "employee_count_midpoint"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)

    bool_columns = [column for column in frame.columns if column.startswith(("action_", "actor_", "cia_"))]
    bool_columns += ["is_finance", "in_year_range", "loss_currency_assumed", "loss_suspect"]
    for column in bool_columns:
        frame[column] = frame[column].fillna(False).astype(bool)

    frame = frame.sort_values(["year", "incident_id"], na_position="last").reset_index(drop=True)
    return frame


def filter_finance(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Filtra finanzas y seguros por prefijo NAICS (52 por defecto)."""
    mask = frame["industry_code"].fillna("").str.startswith(prefix)
    return frame.loc[mask].reset_index(drop=True)


def save_datasets(frame: pd.DataFrame, config: Config) -> dict[str, Path]:
    """Guarda el dataset completo y el de finanzas en Parquet."""
    config.ensure_dirs()
    finance = filter_finance(frame, config.data.finance_naics_prefix)

    all_path = config.data.processed_dir / "incidents_all.parquet"
    finance_path = config.data.processed_dir / "incidents_finance.parquet"
    frame.to_parquet(all_path, index=False)
    finance.to_parquet(finance_path, index=False)

    LOGGER.info("Guardados %s filas en %s", len(frame), all_path)
    LOGGER.info("Guardadas %s filas de finanzas en %s", len(finance), finance_path)
    return {"all": all_path, "finance": finance_path}


def build_datasets(json_path: str | Path, config: Config) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Pipeline completo: cargar JSON -> DataFrame -> Parquet."""
    records = load_records(json_path)
    LOGGER.info("Registros leídos: %s", len(records))

    frame = build_dataframe(records, config)
    frame = add_eur_2025(frame, config.data.reference_dir, config.reference_year)
    with_loss = int(frame["loss_amount"].notna().sum())
    finance_with_loss = int(frame.loc[frame["is_finance"], "loss_amount"].notna().sum())
    with_eur = int(frame["loss_eur_2025"].notna().sum())
    LOGGER.info(
        "Incidentes: %s | con importe: %s | con EUR: %s | finanzas: %s | finanzas con importe: %s",
        len(frame),
        with_loss,
        with_eur,
        int(frame["is_finance"].sum()),
        finance_with_loss,
    )

    paths = save_datasets(frame, config)
    return frame, paths
