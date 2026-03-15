from pathlib import Path

from inat_report.compare import compare_years
from inat_report.loader import load_csv


def test_compare_years() -> None:
    df_2024 = load_csv(Path("data/observations-beetles-of-cyprus-2024.csv"))
    df_2023 = load_csv(Path("data/observations-beetles-of-cyprus.csv"), year=2023)
    result = compare_years(current=df_2024, previous=df_2023, current_year=2024, previous_year=2023)
    assert "current_year" in result
    assert "previous_year" in result
    assert "observations_change" in result
    assert "species_change" in result
    assert "new_species" in result
    assert "lost_species" in result
    assert isinstance(result["new_species"], list)
