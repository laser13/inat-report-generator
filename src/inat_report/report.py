"""Report rendering using Jinja2 templates."""

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader

import inat_report

MONTH_NAMES = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def render_report(
    output_path: Path,
    title: str,
    year: int,
    summary: dict[str, Any],
    monthly: pd.DataFrame,
    top_species: pd.DataFrame,
    top_families: pd.DataFrame,
    top_observers: pd.DataFrame,
    singleton_count: int,
    cumulative_mid_year_pct: int,
    district_stats: pd.DataFrame | None = None,
    comparison: dict[str, Any] | None = None,
    has_map: bool = True,
) -> Path:
    """Render Markdown report from analytics results using Jinja2 template."""
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), keep_trailing_newline=True)
    template = env.get_template("report.md.j2")

    peak_row = monthly.loc[monthly["observations"].idxmax()]
    peak_month = int(peak_row["month"])
    peak_observations = int(peak_row["observations"])

    total_obs = summary["total_observations"]
    top5_obs = int(top_observers.head(5)["observations"].sum())
    top5_obs_pct = round(top5_obs / max(total_obs, 1) * 100, 1)

    content = template.render(
        title=title,
        year=year,
        summary=summary,
        monthly=monthly,
        month_names=MONTH_NAMES,
        peak_month=peak_month,
        peak_observations=peak_observations,
        cumulative_end_pct=cumulative_mid_year_pct,
        top_species=top_species,
        top_families=top_families,
        top_observers=top_observers,
        singleton_count=singleton_count,
        top5_obs_pct=top5_obs_pct,
        district_stats=district_stats,
        comparison=comparison,
        has_map=has_map,
        generated_date=date.today().isoformat(),
        version=inat_report.__version__,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content)
    return output_path
