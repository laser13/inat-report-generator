from pathlib import Path

import pandas as pd

from inat_report.loader import load_csv


def test_load_beetles_csv():
    df = load_csv(Path("data/observations-beetles-of-cyprus-2024.csv"))
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 100
    assert "observation_id" in df.columns
    assert "observed_on" in df.columns
    assert "user_login" in df.columns
    assert "scientific_name" in df.columns
    assert "family_name" in df.columns
    assert "latitude" in df.columns
    assert "longitude" in df.columns
    assert "quality_grade" in df.columns
    assert "observed_year" in df.columns
    assert "observed_month" in df.columns


def test_load_csv_types():
    df = load_csv(Path("data/observations-beetles-of-cyprus-2024.csv"))
    assert pd.api.types.is_datetime64_any_dtype(df["observed_on"])
    assert pd.api.types.is_numeric_dtype(df["latitude"])
    assert pd.api.types.is_numeric_dtype(df["longitude"])
    assert pd.api.types.is_integer_dtype(df["observed_year"])
    assert pd.api.types.is_integer_dtype(df["observed_month"])


def test_load_csv_filters_year():
    df = load_csv(Path("data/observations-beetles-of-cyprus.csv"), year=2023)
    assert len(df) > 0
    assert (df["observed_year"] == 2023).all()
