"""Year-over-year comparison logic."""

from typing import Any

import pandas as pd

from inat_report.analytics import compute_summary


def compare_years(
    current: pd.DataFrame,
    previous: pd.DataFrame,
    current_year: int,
    previous_year: int,
) -> dict[str, Any]:
    """Compare two years of observations and return change metrics."""
    curr_summary = compute_summary(current)
    prev_summary = compute_summary(previous)

    curr_species = set(current["scientific_name"].dropna().unique())
    prev_species = set(previous["scientific_name"].dropna().unique())
    new_species = sorted(curr_species - prev_species)
    lost_species = sorted(prev_species - curr_species)

    def _change(curr_val: int, prev_val: int) -> dict[str, Any]:
        diff = curr_val - prev_val
        pct = round(diff / max(prev_val, 1) * 100, 1)
        return {
            "current": curr_val,
            "previous": prev_val,
            "diff": diff,
            "pct_change": pct,
        }

    return {
        "current_year": current_year,
        "previous_year": previous_year,
        "observations_change": _change(
            curr_summary["total_observations"], prev_summary["total_observations"]
        ),
        "species_change": _change(curr_summary["total_species"], prev_summary["total_species"]),
        "observers_change": _change(
            curr_summary["total_observers"], prev_summary["total_observers"]
        ),
        "new_species": new_species,
        "lost_species": lost_species,
        "shared_species_count": len(curr_species & prev_species),
        "current_summary": curr_summary,
        "previous_summary": prev_summary,
    }
