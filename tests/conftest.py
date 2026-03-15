from pathlib import Path

import pandas as pd
import pytest

from inat_report.loader import load_csv


@pytest.fixture(scope="session")
def beetles_2024_df() -> pd.DataFrame:
    return load_csv(Path("data/observations-beetles-of-cyprus-2024.csv"))
