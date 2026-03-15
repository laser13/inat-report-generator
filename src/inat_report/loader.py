"""CSV loading and column normalization."""

from pathlib import Path

import pandas as pd

COLUMN_MAP = {
    "id": "observation_id",
    "observed_on": "observed_on",
    "user_id": "user_id",
    "user_login": "user_login",
    "user_name": "user_name",
    "quality_grade": "quality_grade",
    "license": "license_code",
    "url": "observation_url",
    "image_url": "image_url",
    "sound_url": "sound_url",
    "latitude": "latitude",
    "longitude": "longitude",
    "positional_accuracy": "positional_accuracy",
    "place_guess": "place_guess",
    "place_county_name": "district_name",
    "place_state_name": "state_name",
    "place_country_name": "country_name",
    "species_guess": "species_guess",
    "scientific_name": "scientific_name",
    "common_name": "common_name",
    "iconic_taxon_name": "iconic_taxon_name",
    "taxon_id": "taxon_id",
    "taxon_order_name": "order_name",
    "taxon_family_name": "family_name",
    "taxon_subfamily_name": "subfamily_name",
    "taxon_genus_name": "genus_name",
    "taxon_species_name": "species_name",
    "taxon_subspecies_name": "subspecies_name",
    "num_identification_agreements": "id_agreements",
    "num_identification_disagreements": "id_disagreements",
    "captive_cultivated": "captive",
}


def load_csv(path: Path, year: int | None = None) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)

    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    df["observed_on"] = pd.to_datetime(df["observed_on"], errors="coerce")
    df["observed_year"] = df["observed_on"].dt.year.astype("Int64")
    df["observed_month"] = df["observed_on"].dt.month.astype("Int64")
    df["observed_day"] = df["observed_on"].dt.day.astype("Int64")

    for col in ["latitude", "longitude", "positional_accuracy"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if year is not None:
        df = df[df["observed_year"] == year].copy()

    return df
