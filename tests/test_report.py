from pathlib import Path

import pandas as pd

from inat_report.analytics import (
    compute_district_stats,
    compute_monthly,
    compute_singleton_species,
    compute_summary,
    compute_top_families,
    compute_top_observers,
    compute_top_species,
)
from inat_report.report import render_report


def test_render_report(beetles_2024_df: pd.DataFrame, tmp_path: Path):
    summary = compute_summary(beetles_2024_df)
    monthly = compute_monthly(beetles_2024_df)
    top_species = compute_top_species(beetles_2024_df, n=15)
    top_families = compute_top_families(beetles_2024_df, n=10)
    top_observers = compute_top_observers(beetles_2024_df, n=10)
    singletons = compute_singleton_species(beetles_2024_df)
    district_stats = compute_district_stats(beetles_2024_df)

    mid_year_species = beetles_2024_df[
        (beetles_2024_df["observed_month"] <= 6) & beetles_2024_df["scientific_name"].notna()
    ]["scientific_name"].nunique()
    cumulative_mid_year_pct = round(mid_year_species / max(summary["total_species"], 1) * 100)

    output = tmp_path / "report.md"
    render_report(
        output_path=output,
        title="Beetles of Cyprus",
        year=2024,
        summary=summary,
        monthly=monthly,
        top_species=top_species,
        top_families=top_families,
        top_observers=top_observers,
        singleton_count=len(singletons),
        cumulative_mid_year_pct=cumulative_mid_year_pct,
        district_stats=district_stats,
    )

    assert output.exists()
    content = output.read_text()
    assert "Beetles of Cyprus" in content
    assert "2024" in content
    assert "Highlights" in content
    assert "Limitations" in content
    assert "iNaturalist data reflect" in content
