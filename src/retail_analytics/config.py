"""Run settings: where the data is, where output goes, and what to analyse."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data_dir: Path = Path("data")
    output_dir: Path = Path("output")
    stores: tuple[str, ...] = ()
