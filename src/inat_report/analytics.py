"""Deterministic analytics computations on observation DataFrames."""

from typing import Any

import pandas as pd


def compute_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Compute high-level summary metrics."""
    species_df = df[df["scientific_name"].notna() & (df["scientific_name"] != "")]
    quality_counts = df["quality_grade"].value_counts().to_dict()
    has_coords = df["latitude"].notna() & df["longitude"].notna()
    return {
        "total_observations": len(df),
        "total_species": species_df["scientific_name"].nunique(),
        "total_observers": df["user_login"].nunique(),
        "total_families": df["family_name"].dropna().nunique(),
        "quality_grade_counts": quality_counts,
        "research_grade_pct": round(quality_counts.get("research", 0) / max(len(df), 1) * 100, 1),
        "needs_id_count": quality_counts.get("needs_id", 0),
        "with_coords_pct": round(has_coords.sum() / max(len(df), 1) * 100, 1),
        "first_observation_date": (str(df["observed_on"].min().date()) if len(df) > 0 else None),
        "last_observation_date": (str(df["observed_on"].max().date()) if len(df) > 0 else None),
    }


def compute_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Compute monthly observation and species counts."""
    monthly_obs = (
        df.groupby("observed_month")
        .agg(
            observations=("observation_id", "count"),
            species=("scientific_name", "nunique"),
            observers=("user_login", "nunique"),
        )
        .reset_index()
    )
    monthly_obs = monthly_obs.rename(columns={"observed_month": "month"})
    return monthly_obs.sort_values("month")


def compute_top_species(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Top species by observation count."""
    return (
        df[df["scientific_name"].notna()]
        .groupby("scientific_name")
        .agg(
            count=("observation_id", "count"),
            family_name=("family_name", "first"),
            common_name=("common_name", "first"),
        )
        .reset_index()
        .sort_values("count", ascending=False)
        .head(n)
    )


def compute_top_families(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    """Top families by observation count and species richness."""
    return (
        df[df["family_name"].notna()]
        .groupby("family_name")
        .agg(
            observations=("observation_id", "count"),
            species=("scientific_name", "nunique"),
        )
        .reset_index()
        .sort_values("observations", ascending=False)
        .head(n)
    )


def compute_top_observers(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top observers by number of observations and unique species."""
    return (
        df.groupby("user_login")
        .agg(
            observations=("observation_id", "count"),
            species=("scientific_name", "nunique"),
            user_name=("user_name", "first"),
        )
        .reset_index()
        .sort_values("observations", ascending=False)
        .head(n)
    )


def compute_singleton_species(df: pd.DataFrame) -> pd.DataFrame:
    """Species observed only once (singletons)."""
    species_counts = df.groupby("scientific_name")["observation_id"].count()
    singletons = species_counts[species_counts == 1].index
    return df[df["scientific_name"].isin(singletons)][
        [
            "scientific_name",
            "common_name",
            "family_name",
            "user_login",
            "observed_on",
            "observation_url",
        ]
    ].sort_values("scientific_name")


def compute_yearly_dynamics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute year-over-year dynamics across all data.

    Returns DataFrame with columns:
        year, observations, species, observers, families,
        new_species (first seen that year), cumulative_species
    """
    years = sorted(df["observed_year"].dropna().unique())
    all_seen: set[str] = set()
    rows = []

    for year in years:
        year_df = df[df["observed_year"] == year]
        year_species = set(year_df["scientific_name"].dropna().unique())
        new_species = year_species - all_seen
        all_seen.update(year_species)

        rows.append(
            {
                "year": int(year),
                "observations": len(year_df),
                "species": len(year_species),
                "observers": year_df["user_login"].nunique(),
                "families": year_df["family_name"].dropna().nunique(),
                "new_species": len(new_species),
                "cumulative_species": len(all_seen),
            }
        )

    return pd.DataFrame(rows)


def compute_district_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Observation and species counts by district.

    Checks district_name and state_name columns, preferring whichever has actual data.
    Normalizes district names to match GeoJSON.
    """
    DISTRICT_NORMALIZE: dict[str, str] = {
        "Kyrenia": "Kerynia",
        "Northern Cyprus": "Kerynia",
        "Girne": "Kerynia",
        "Akrotiri": "British Overseas Territory (Akrotiri)",
        "Dhekelia": "British Overseas Territory (Dhekelia)",
        "Iskele": "Famagusta",
        "Gazimağusa": "Famagusta",
        "Güzelyurt": "Nicosia",
    }
    col = None
    for candidate in ["district_name", "state_name"]:
        if candidate in df.columns and df[candidate].notna().any():
            col = candidate
            break
    if col is None:
        return pd.DataFrame(columns=["district", "observations", "species"])

    work = df[df[col].notna()].copy()
    work["_district"] = work[col].map(lambda x: DISTRICT_NORMALIZE.get(x, x))
    return (
        work.groupby("_district")
        .agg(
            observations=("observation_id", "count"),
            species=("scientific_name", "nunique"),
        )
        .reset_index()
        .rename(columns={"_district": "district"})
        .sort_values("observations", ascending=False)
    )
