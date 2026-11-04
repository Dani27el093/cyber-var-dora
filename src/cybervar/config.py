"""Carga tipada de la configuración del proyecto."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


@dataclass(frozen=True)
class DataConfig:
    """Parámetros de ingesta y filtrado del dataset."""

    source_url: str
    archive_name: str
    extracted_name: str
    finance_naics_prefix: str
    min_year: int
    max_year: int
    raw_dir: Path
    processed_dir: Path
    reference_dir: Path


@dataclass(frozen=True)
class LossConfig:
    """Reglas de extracción y normalización de pérdidas."""

    prefer_overall_amount: bool
    include_component_sum: bool
    range_policy: str
    missing_currency_default: str
    min_threshold_eur: float
    suspect_amount_threshold: float


@dataclass(frozen=True)
class SimulationConfig:
    """Parámetros del motor de Montecarlo."""

    n_scenarios: int
    confidence_levels: tuple[float, ...]


@dataclass(frozen=True)
class FrequencyConfig:
    """Escenarios de frecuencia anual (incidentes materiales por año)."""

    lambda_scenarios: tuple[float, ...]
    lambda_base: float


@dataclass(frozen=True)
class Config:
    """Configuración completa del proyecto."""

    name: str
    reference_year: int
    random_seed: int
    data: DataConfig
    losses: LossConfig
    frequency: FrequencyConfig
    simulation: SimulationConfig
    outputs_dir: Path

    def ensure_dirs(self) -> None:
        """Crea los directorios de trabajo si no existen."""
        for path in (
            self.data.raw_dir,
            self.data.processed_dir,
            self.data.reference_dir,
            self.outputs_dir / "figures",
            self.outputs_dir / "tables",
            self.outputs_dir / "logs",
        ):
            path.mkdir(parents=True, exist_ok=True)


def _resolve(path_value: str | Path) -> Path:
    """Resuelve una ruta relativa contra la raíz del proyecto."""
    path = Path(path_value).expanduser()
    return path if path.is_absolute() else PROJECT_ROOT / path


def _require(mapping: dict[str, Any], key: str, section: str) -> Any:
    if key not in mapping:
        raise KeyError(f"Falta la clave '{key}' en la sección '{section}' de config.yaml")
    return mapping[key]


def load_config(path: str | Path | None = None) -> Config:
    """Lee `config/config.yaml` y devuelve una configuración validada."""
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    project = raw.get("project", {})
    paths = raw.get("paths", {})
    data_raw = raw.get("data", {})
    losses_raw = raw.get("losses", {})
    simulation_raw = raw.get("simulation", {})
    frequency_raw = raw.get("frequency", {})

    data = DataConfig(
        source_url=_require(data_raw, "source_url", "data"),
        archive_name=_require(data_raw, "archive_name", "data"),
        extracted_name=_require(data_raw, "extracted_name", "data"),
        finance_naics_prefix=str(_require(data_raw, "finance_naics_prefix", "data")),
        min_year=int(_require(data_raw, "min_year", "data")),
        max_year=int(_require(data_raw, "max_year", "data")),
        raw_dir=_resolve(_require(paths, "raw_dir", "paths")),
        processed_dir=_resolve(_require(paths, "processed_dir", "paths")),
        reference_dir=_resolve(_require(paths, "reference_dir", "paths")),
    )

    range_policy = str(losses_raw.get("range_policy", "midpoint")).lower()
    if range_policy != "midpoint":
        raise ValueError(f"range_policy no soportada: {range_policy!r} (usa 'midpoint')")

    confidence_levels = tuple(
        sorted(float(level) for level in _require(simulation_raw, "confidence_levels", "simulation"))
    )
    if not confidence_levels or any(not 0 < level < 1 for level in confidence_levels):
        raise ValueError("confidence_levels debe contener valores entre 0 y 1")

    simulation = SimulationConfig(
        n_scenarios=int(_require(simulation_raw, "n_scenarios", "simulation")),
        confidence_levels=confidence_levels,
    )
    if simulation.n_scenarios < 1_000:
        raise ValueError("n_scenarios debe ser al menos 1.000")

    lambda_scenarios = tuple(
        sorted(float(value) for value in _require(frequency_raw, "lambda_scenarios", "frequency"))
    )
    if not lambda_scenarios or any(value < 0 for value in lambda_scenarios):
        raise ValueError("lambda_scenarios debe contener valores no negativos")
    lambda_base = float(_require(frequency_raw, "lambda_base", "frequency"))
    if lambda_base not in lambda_scenarios:
        raise ValueError("lambda_base debe estar incluido en lambda_scenarios")

    return Config(
        name=str(_require(project, "name", "project")),
        reference_year=int(_require(project, "reference_year", "project")),
        random_seed=int(_require(project, "random_seed", "project")),
        data=data,
        losses=LossConfig(
            prefer_overall_amount=bool(losses_raw.get("prefer_overall_amount", True)),
            include_component_sum=bool(losses_raw.get("include_component_sum", True)),
            range_policy=range_policy,
            missing_currency_default=str(losses_raw.get("missing_currency_default", "USD")),
            min_threshold_eur=float(losses_raw.get("min_threshold_eur", 0.0)),
            suspect_amount_threshold=float(losses_raw.get("suspect_amount_threshold", 1e11)),
        ),
        frequency=FrequencyConfig(
            lambda_scenarios=lambda_scenarios,
            lambda_base=lambda_base,
        ),
        simulation=simulation,
        outputs_dir=_resolve(_require(paths, "outputs_dir", "paths")),
    )
