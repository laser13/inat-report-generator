"""Tests for fetch module — CSV conversion from API JSON."""

from pathlib import Path

from inat_report.fetch import _observations_to_csv


def _make_obs(
    obs_id: int = 1,
    location: object = None,
    geojson: dict | None = None,
    taxon_name: str = "Coccinella septempunctata",
    taxon_rank: str = "species",
    family: str = "Coccinellidae",
    user_login: str = "testuser",
) -> dict:
    """Build a minimal observation dict matching iNaturalist API format."""
    obs: dict = {
        "id": obs_id,
        "observed_on_details": {"date": "2025-03-01"},
        "time_observed_at": "2025-03-01T10:00:00+00:00",
        "quality_grade": "research",
        "license_code": "CC-BY-NC",
        "positional_accuracy": 10,
        "place_guess": "Limassol, Cyprus",
        "species_guess": "Seven-spot ladybird",
        "num_identification_agreements": 2,
        "num_identification_disagreements": 0,
        "captive": False,
        "user": {"id": 100, "login": user_login, "name": "Test User"},
        "taxon": {
            "id": 12345,
            "name": taxon_name,
            "rank": taxon_rank,
            "preferred_common_name": "Seven-spot Ladybird",
            "iconic_taxon_name": "Insecta",
            "ancestors": [
                {"rank": "kingdom", "name": "Animalia"},
                {"rank": "order", "name": "Coleoptera"},
                {"rank": "family", "name": family},
            ],
        },
        "photos": [{"url": "https://example.com/square.jpg"}],
    }
    if location is not None:
        obs["location"] = location
    if geojson is not None:
        obs["geojson"] = geojson
    return obs


def test_location_as_list(tmp_path: Path):
    """API returns location as [lat, lon] list."""
    obs = _make_obs(location=[34.67, 32.86])
    csv_path = _observations_to_csv([obs], tmp_path, "test", 2025)

    import pandas as pd

    df = pd.read_csv(csv_path)
    assert len(df) == 1
    assert abs(df.iloc[0]["latitude"] - 34.67) < 0.01
    assert abs(df.iloc[0]["longitude"] - 32.86) < 0.01


def test_location_as_string(tmp_path: Path):
    """Fallback: location as comma-separated string."""
    obs = _make_obs(location="35.0, 33.2")
    csv_path = _observations_to_csv([obs], tmp_path, "test", 2025)

    import pandas as pd

    df = pd.read_csv(csv_path)
    assert abs(df.iloc[0]["latitude"] - 35.0) < 0.01
    assert abs(df.iloc[0]["longitude"] - 33.2) < 0.01


def test_location_from_geojson(tmp_path: Path):
    """Fallback: coordinates from geojson when location is None."""
    obs = _make_obs(
        location=None,
        geojson={"type": "Point", "coordinates": [32.86, 34.67]},
    )
    csv_path = _observations_to_csv([obs], tmp_path, "test", 2025)

    import pandas as pd

    df = pd.read_csv(csv_path)
    assert abs(df.iloc[0]["latitude"] - 34.67) < 0.01
    assert abs(df.iloc[0]["longitude"] - 32.86) < 0.01


def test_location_none(tmp_path: Path):
    """No location data at all — should not crash."""
    obs = _make_obs(location=None, geojson=None)
    csv_path = _observations_to_csv([obs], tmp_path, "test", 2025)

    import pandas as pd

    df = pd.read_csv(csv_path)
    assert len(df) == 1
    assert pd.isna(df.iloc[0]["latitude"])


def test_csv_columns(tmp_path: Path):
    """CSV should have expected columns for the loader."""
    obs = _make_obs(location=[34.67, 32.86])
    csv_path = _observations_to_csv([obs], tmp_path, "test", 2025)

    import pandas as pd

    df = pd.read_csv(csv_path)
    required = [
        "id", "observed_on", "user_login", "scientific_name",
        "taxon_family_name", "latitude", "longitude", "quality_grade",
    ]
    for col in required:
        assert col in df.columns, f"Missing column: {col}"


def test_csv_works_with_loader(tmp_path: Path):
    """CSV produced by fetch should be loadable by our loader."""
    obs = _make_obs(location=[34.67, 32.86])
    csv_path = _observations_to_csv([obs], tmp_path, "test", 2025)

    from inat_report.loader import load_csv

    df = load_csv(csv_path)
    assert len(df) == 1
    assert df.iloc[0]["scientific_name"] == "Coccinella septempunctata"
    assert df.iloc[0]["family_name"] == "Coccinellidae"
    assert df.iloc[0]["observed_year"] == 2025


def test_real_raw_json_if_available(tmp_path: Path):
    """If we have real fetched data, test conversion on it."""
    raw_path = Path("data/raw/beetles_of_cyprus_2025/2025/observations.json")
    if not raw_path.exists():
        return  # skip if no real data

    import json

    with open(raw_path) as f:
        observations = json.load(f)

    csv_path = _observations_to_csv(observations, tmp_path, "beetles_cyprus", 2025)

    from inat_report.loader import load_csv

    df = load_csv(csv_path)
    assert len(df) > 100
    assert df["latitude"].notna().sum() > 0
    assert df["scientific_name"].notna().sum() > 0
