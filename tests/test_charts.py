from pathlib import Path

import pandas as pd

from inat_report.analytics import compute_monthly, compute_top_species
from inat_report.charts import (
    chart_cumulative_species,
    chart_monthly_observations,
    chart_top_species,
)


def test_chart_monthly_observations(beetles_2024_df: pd.DataFrame, tmp_path: Path) -> None:
    monthly = compute_monthly(beetles_2024_df)
    out = tmp_path / "monthly.png"
    chart_monthly_observations(monthly, out, year=2024)
    assert out.exists()
    assert out.stat().st_size > 5000


def test_chart_cumulative_species(beetles_2024_df: pd.DataFrame, tmp_path: Path) -> None:
    out = tmp_path / "cumulative.png"
    chart_cumulative_species(beetles_2024_df, out, year=2024)
    assert out.exists()
    assert out.stat().st_size > 5000


def test_chart_top_species(beetles_2024_df: pd.DataFrame, tmp_path: Path) -> None:
    top = compute_top_species(beetles_2024_df, n=15)
    out = tmp_path / "top_species.png"
    chart_top_species(top, out, year=2024)
    assert out.exists()
    assert out.stat().st_size > 5000
