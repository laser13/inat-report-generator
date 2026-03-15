"""Interactive map generation with Folium."""

import json
from pathlib import Path

import folium
import folium.plugins
import pandas as pd


def generate_map(
    df: pd.DataFrame,
    geojson_path: Path,
    output_path: Path,
    title: str = "Observations",
) -> Path:
    """Generate interactive Folium map with observation points and district boundaries."""
    center_lat = 35.0
    center_lon = 33.2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="OpenStreetMap")

    # District boundaries
    if geojson_path.exists():
        with open(geojson_path) as f:
            geojson_data = json.load(f)
        folium.GeoJson(
            geojson_data,
            name="Districts",
            style_function=lambda _: {
                "fillColor": "#228B22",
                "color": "#333333",
                "weight": 1.5,
                "fillOpacity": 0.08,
            },
            tooltip=folium.GeoJsonTooltip(fields=["district"], aliases=["District:"]),
        ).add_to(m)

    # Observation points with clustering
    valid = df[df["latitude"].notna() & df["longitude"].notna()].copy()
    marker_cluster = folium.plugins.MarkerCluster(name="Observations").add_to(m)

    for _, row in valid.iterrows():
        popup_html = (
            f"<b>{row.get('scientific_name', 'Unknown')}</b><br>"
            f"Observer: {row.get('user_login', '?')}<br>"
            f"Date: {str(row.get('observed_on', ''))[:10]}<br>"
            f"<a href='{row.get('observation_url', '#')}' target='_blank'>View on iNaturalist</a>"
        )
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=4,
            color="#e74c3c",
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(marker_cluster)

    folium.LayerControl().add_to(m)

    title_html = (
        f'<h3 style="position:fixed;z-index:100000;left:50%;'
        f"transform:translateX(-50%);background:white;padding:5px 15px;"
        f'border-radius:5px;box-shadow:0 2px 6px rgba(0,0,0,0.3)">'
        f"{title}</h3>"
    )
    m.get_root().html.add_child(folium.Element(title_html))  # type: ignore[attr-defined]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path
