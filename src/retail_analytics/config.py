"""Run settings: where the data is, where output goes, and what to analyse."""

from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data_dir: Path = Path("data")
    output_dir: Path = Path("output")
    stores: tuple[str, ...] = ()
    as_of: date = Field(default_factory=date.today)
    price_tolerance: float = Field(default=0.5, gt=0)
