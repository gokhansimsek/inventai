"""Run settings: where the data is, where output goes, and what to analyse.

Settings come from an optional YAML file, overridden by CLI flags. Everything is
validated up front, so a typo or an impossible value stops the run before any
work is done.
"""

from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from retail_analytics.errors import ConfigError


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data_dir: Path = Path("data")
    output_dir: Path = Path("output")
    stores: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    date_from: date | None = None
    date_to: date | None = None
    as_of: date = Field(default_factory=date.today)
    price_tolerance: float = Field(default=0.5, gt=0)

    @model_validator(mode="after")
    def _date_range_is_ordered(self) -> Self:
        """Reject a date range that ends before it starts.

        Returns:
            Self: The validated settings.

        Raises:
            ValueError: If ``date_from`` is after ``date_to``.
        """
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError(f"date_from {self.date_from} is after date_to {self.date_to}")
        return self


def load_settings(config_path: Path | None, overrides: Mapping[str, Any]) -> Settings:
    """Build settings from a YAML file and CLI overrides.

    Args:
        config_path (Path | None): YAML file to read; None uses defaults only.
        overrides (Mapping[str, Any]): Values from the command line. None and empty
            values are ignored, so an unset flag keeps the file's value.

    Returns:
        Settings: The validated settings.

    Raises:
        ConfigError: If the file is missing, is not a YAML mapping, or any value is
            invalid.
    """
    values: dict[str, Any] = {}
    source = "command line"
    if config_path is not None:
        source = str(config_path)
        if not config_path.is_file():
            raise ConfigError(f"Config file not found: {config_path}")
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ConfigError(f"Config file {config_path} must contain a mapping of settings")
        values.update(loaded)
    values.update({k: v for k, v in overrides.items() if v not in (None, (), [])})

    try:
        return Settings.model_validate(values)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in error['loc']) or 'settings'}: {error['msg']}"
            for error in exc.errors()
        )
        raise ConfigError(f"Invalid configuration ({source}): {problems}") from None
