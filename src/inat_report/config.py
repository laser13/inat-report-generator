"""Dataset configuration models and YAML loader."""

from pathlib import Path

import yaml
from pydantic import BaseModel


class SourceConfig(BaseModel):
    csv_pattern: str
    csv_all_time: str | None = None
    data_dir: str = "data"
    project_id: int | None = None
    project_query: str | None = None  # URL, slug, or name to resolve


class LLMConfig(BaseModel):
    model: str = "gpt-5.4"
    language: str = "en"


class ReportConfig(BaseModel):
    language: str = "en"
    top_species_count: int = 20
    top_observers_count: int = 10
    top_identifiers_count: int = 10
    include_map: bool = True
    include_charts: bool = True


class DatasetConfig(BaseModel):
    slug: str
    title: str
    taxon_common_name: str
    source: SourceConfig
    report: ReportConfig = ReportConfig()
    llm: LLMConfig = LLMConfig()
    geojson_path: str = "data/cyprus.geojson"


def load_config(path: Path) -> DatasetConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return DatasetConfig(**raw)
