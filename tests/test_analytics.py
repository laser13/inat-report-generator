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


def test_compute_summary(beetles_2024_df: pd.DataFrame) -> None:
    summary = compute_summary(beetles_2024_df)
    assert summary["total_observations"] > 0
    assert summary["total_species"] > 0
    assert summary["total_observers"] > 0
    assert summary["total_families"] > 0
    assert "quality_grade_counts" in summary
    assert "research" in summary["quality_grade_counts"]


def test_compute_monthly(beetles_2024_df: pd.DataFrame) -> None:
    monthly = compute_monthly(beetles_2024_df)
    assert isinstance(monthly, pd.DataFrame)
    assert "month" in monthly.columns
    assert "observations" in monthly.columns
    assert "species" in monthly.columns
    assert len(monthly) <= 12


def test_compute_top_species(beetles_2024_df: pd.DataFrame) -> None:
    top = compute_top_species(beetles_2024_df, n=10)
    assert isinstance(top, pd.DataFrame)
    assert len(top) == 10
    assert "scientific_name" in top.columns
    assert "count" in top.columns
    assert top["count"].is_monotonic_decreasing


def test_compute_top_observers(beetles_2024_df: pd.DataFrame) -> None:
    top = compute_top_observers(beetles_2024_df, n=5)
    assert isinstance(top, pd.DataFrame)
    assert len(top) == 5
    assert "user_login" in top.columns
    assert "observations" in top.columns
    assert "species" in top.columns


def test_compute_top_families(beetles_2024_df: pd.DataFrame) -> None:
    top = compute_top_families(beetles_2024_df, n=10)
    assert isinstance(top, pd.DataFrame)
    assert len(top) == 10
    assert "family_name" in top.columns
    assert "observations" in top.columns
    assert "species" in top.columns


def test_compute_singleton_species(beetles_2024_df: pd.DataFrame) -> None:
    singletons = compute_singleton_species(beetles_2024_df)
    assert isinstance(singletons, pd.DataFrame)
    assert "scientific_name" in singletons.columns
    assert "user_login" in singletons.columns
    assert len(singletons) > 0


def test_compute_district_stats(beetles_2024_df: pd.DataFrame) -> None:
    stats = compute_district_stats(beetles_2024_df)
    assert isinstance(stats, pd.DataFrame)
    assert "district" in stats.columns
    assert "observations" in stats.columns
    assert "species" in stats.columns
