from pathlib import Path

import pandas as pd

from inat_report.maps import generate_map


def test_generate_map(beetles_2024_df: pd.DataFrame, tmp_path: Path) -> None:
    output = tmp_path / "map.html"
    generate_map(
        df=beetles_2024_df,
        geojson_path=Path("data/cyprus.geojson"),
        output_path=output,
        title="Beetles of Cyprus 2024",
    )
    assert output.exists()
    content = output.read_text()
    assert "leaflet" in content.lower() or "folium" in content.lower()
    assert len(content) > 1000
