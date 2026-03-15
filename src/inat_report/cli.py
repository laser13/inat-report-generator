"""CLI entry point using Typer."""

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="iNaturalist annual biodiversity report generator.")


@app.command()
def fetch(
    dataset: str = typer.Argument(help="Dataset slug, e.g. 'beetles_cyprus'"),
    year: Optional[int] = typer.Option(
        None, "--year", "-y", help="Fetch single year (default: all years)"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-p", help="Override project URL/slug/ID"
    ),
    config_dir: Path = typer.Option(Path("configs"), "--config-dir"),
) -> None:
    """Fetch observations from iNaturalist API and save as CSV.

    Without --year: fetches ALL observations, splits by year, updates only changed.
    With --year: fetches just that year.
    """
    from inat_report.config import load_config
    from inat_report.fetch import fetch_all, fetch_year, resolve_project

    # Load config
    config_path = config_dir / f"{dataset}.yaml"
    if not config_path.exists():
        typer.echo(f"Config not found: {config_path}", err=True)
        raise typer.Exit(code=1)
    config = load_config(config_path)

    # Resolve project
    project_query = project or str(config.source.project_id or config.source.project_query or "")
    if not project_query:
        typer.echo("No project specified. Set source.project_id in config.", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Resolving project: {project_query}")
    project_info = resolve_project(project_query)
    typer.echo(f"  Found: {project_info['title']} (ID: {project_info['id']})")

    data_dir = Path(config.source.data_dir)

    if year is not None:
        # Fetch single year
        csv_path = fetch_year(
            project_id=project_info["id"],
            year=year,
            output_dir=data_dir,
            slug=config.slug,
        )
        typer.echo(f"\nDone! CSV: {csv_path}")
    else:
        # Fetch all years, update only changed
        written = fetch_all(
            project_id=project_info["id"],
            output_dir=data_dir,
            slug=config.slug,
        )
        if written:
            typer.echo(f"\nUpdated {len(written)} year(s): {', '.join(str(y) for y in written)}")
        else:
            typer.echo("\nAll years up to date, nothing to download.")
    typer.echo(f"Data dir: {data_dir}")


@app.command()
def summary(
    dataset: str = typer.Argument(help="Dataset slug, e.g. 'beetles_cyprus'"),
    year: Optional[int] = typer.Option(
        None, "--year", "-y", help="Single year (default: all-time dynamics)"
    ),
    compare_year: Optional[int] = typer.Option(
        None, "--compare-year", "-c", help="Year to compare against"
    ),
    config_dir: Path = typer.Option(Path("configs"), "--config-dir"),
    output_dir: Path = typer.Option(Path("reports"), "--output-dir"),
) -> None:
    """Compute analytics, generate charts and map, save summary JSON.

    Without --year: all-time dynamics across all years.
    With --year: single year statistics.
    """
    from inat_report.config import load_config

    config_path = config_dir / f"{dataset}.yaml"
    if not config_path.exists():
        typer.echo(f"Config not found: {config_path}", err=True)
        raise typer.Exit(code=1)
    config = load_config(config_path)
    typer.echo(f"Loaded config: {config.title}")

    if year is not None:
        _summary_single_year(config, year, compare_year, output_dir)
    else:
        _summary_all_time(config, output_dir)


def _summary_all_time(config: object, output_dir: Path) -> None:
    """All-time dynamics: year-over-year trends, cumulative species, etc."""
    import json

    from inat_report.analytics import (
        compute_summary,
        compute_top_families,
        compute_top_observers,
        compute_top_species,
        compute_yearly_dynamics,
    )
    from inat_report.charts import chart_top_species, chart_yearly_dynamics
    from inat_report.config import DatasetConfig
    from inat_report.loader import load_csv
    from inat_report.maps import generate_map

    assert isinstance(config, DatasetConfig)
    data_dir = Path(config.source.data_dir)

    # Load all-time CSV
    if config.source.csv_all_time:
        csv_path = data_dir / config.source.csv_all_time
    else:
        typer.echo("No all-time CSV configured (source.csv_all_time)", err=True)
        raise typer.Exit(code=1)
    if not csv_path.exists():
        typer.echo(f"CSV not found: {csv_path}", err=True)
        typer.echo("Run 'inat-report fetch' first.")
        raise typer.Exit(code=1)

    typer.echo(f"Loading {csv_path}...")
    df = load_csv(csv_path)
    typer.echo(f"Loaded {len(df)} observations")

    # Compute dynamics
    typer.echo("Computing yearly dynamics...")
    dynamics = compute_yearly_dynamics(df)
    summary_data = compute_summary(df)
    top_species = compute_top_species(df, n=config.report.top_species_count)
    top_families = compute_top_families(df)
    top_observers = compute_top_observers(df, n=config.report.top_observers_count)

    # Output dir
    report_dir = output_dir / config.slug / "all-time"
    charts_dir = report_dir / "charts"
    maps_dir = report_dir / "maps"
    charts_dir.mkdir(parents=True, exist_ok=True)
    maps_dir.mkdir(parents=True, exist_ok=True)

    # Save JSON
    with open(report_dir / "summary.json", "w") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    dynamics_records = dynamics.to_dict(orient="records")
    with open(report_dir / "dynamics.json", "w") as f:
        json.dump(dynamics_records, f, indent=2, ensure_ascii=False)

    tables = {
        "dynamics": dynamics_records,
        "top_species": top_species.to_dict(orient="records"),
        "top_families": top_families.to_dict(orient="records"),
        "top_observers": top_observers.to_dict(orient="records"),
    }
    with open(report_dir / "tables.json", "w") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False, default=str)

    typer.echo(f"Summary: {report_dir / 'summary.json'}")
    typer.echo(f"Dynamics: {report_dir / 'dynamics.json'}")

    # Print dynamics table
    typer.echo(f"\n{'Year':>6} {'Obs':>6} {'Species':>8} {'New':>5} {'Cumul':>6} {'Observers':>10}")
    typer.echo("-" * 50)
    for _, row in dynamics.iterrows():
        typer.echo(
            f"{int(row['year']):>6} {int(row['observations']):>6} "
            f"{int(row['species']):>8} {int(row['new_species']):>5} "
            f"{int(row['cumulative_species']):>6} {int(row['observers']):>10}"
        )

    # Charts
    if config.report.include_charts:
        typer.echo("\nGenerating charts...")
        chart_yearly_dynamics(dynamics, charts_dir / "yearly_dynamics.png", config.title)
        chart_top_species(top_species, charts_dir / "top_species_alltime.png", year=0)

    # Map
    if config.report.include_map:
        typer.echo("Generating map...")
        generate_map(
            df=df,
            geojson_path=Path(config.geojson_path),
            output_path=maps_dir / "observations_map.html",
            title=f"{config.title} — All Time",
        )

    typer.echo(f"\nDone! All artifacts in: {report_dir}")


def _summary_single_year(
    config: object, year: int, compare_year: Optional[int], output_dir: Path
) -> None:
    """Single year statistics with optional comparison."""
    import json

    from inat_report.analytics import (
        compute_district_stats,
        compute_monthly,
        compute_singleton_species,
        compute_summary,
        compute_top_families,
        compute_top_observers,
        compute_top_species,
    )
    from inat_report.charts import (
        chart_cumulative_species,
        chart_monthly_observations,
        chart_top_species,
    )
    from inat_report.compare import compare_years
    from inat_report.config import DatasetConfig
    from inat_report.loader import load_csv
    from inat_report.maps import generate_map

    assert isinstance(config, DatasetConfig)
    data_dir = Path(config.source.data_dir)
    csv_name = config.source.csv_pattern.format(year=year)
    csv_path = data_dir / csv_name
    if not csv_path.exists():
        typer.echo(f"CSV not found: {csv_path}", err=True)
        typer.echo("Run 'inat-report fetch' first.")
        raise typer.Exit(code=1)

    typer.echo(f"Loading {csv_path}...")
    df = load_csv(csv_path)
    typer.echo(f"Loaded {len(df)} observations")

    typer.echo("Computing analytics...")
    summary_data = compute_summary(df)
    monthly = compute_monthly(df)
    top_species = compute_top_species(df, n=config.report.top_species_count)
    top_families = compute_top_families(df)
    top_observers = compute_top_observers(df, n=config.report.top_observers_count)
    singletons = compute_singleton_species(df)
    district_stats = compute_district_stats(df)

    report_dir = output_dir / config.slug / str(year)
    charts_dir = report_dir / "charts"
    maps_dir = report_dir / "maps"
    charts_dir.mkdir(parents=True, exist_ok=True)
    maps_dir.mkdir(parents=True, exist_ok=True)

    # Comparison
    comparison = None
    if compare_year is not None:
        df_prev = _load_comparison_data(config, data_dir, compare_year)
        if df_prev is not None and len(df_prev) > 0:
            typer.echo(f"Comparing {year} vs {compare_year} ({len(df_prev)} observations)...")
            comparison = compare_years(df, df_prev, year, compare_year)

    # Save JSONs
    with open(report_dir / "summary.json", "w") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    typer.echo(f"Summary: {report_dir / 'summary.json'}")

    if comparison:
        with open(report_dir / "compare.json", "w") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False, default=str)
        typer.echo(f"Comparison: {report_dir / 'compare.json'}")

    # Compute new species (first recorded this year vs all previous years)
    new_species_list: list[str] = []
    if config.source.csv_all_time:
        alltime_path = data_dir / config.source.csv_all_time
        if alltime_path.exists():
            df_all = load_csv(alltime_path)
            prev_species = set(
                df_all[df_all["observed_year"] < year]["scientific_name"].dropna().unique()
            )
            current_species = set(df["scientific_name"].dropna().unique())
            new_species_list = sorted(current_species - prev_species)
            typer.echo(f"New species this year: {len(new_species_list)}")

    tables = {
        "monthly": monthly.to_dict(orient="records"),
        "top_species": top_species.to_dict(orient="records"),
        "top_families": top_families.to_dict(orient="records"),
        "top_observers": top_observers.to_dict(orient="records"),
        "singleton_count": len(singletons),
        "district_stats": district_stats.to_dict(orient="records")
        if len(district_stats) > 0
        else [],
        "new_species": new_species_list,
    }

    # Enrich with photos/avatars from raw API data
    from inat_report.enrich import enrich_tables

    raw_dir = data_dir / "raw" / config.slug / str(year)
    if raw_dir.exists():
        typer.echo("Enriching with photos and avatars from API data...")
        tables = enrich_tables(tables, raw_dir)

    with open(report_dir / "tables.json", "w") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False, default=str)
    typer.echo(f"Tables: {report_dir / 'tables.json'}")

    # Map
    if config.report.include_map:
        typer.echo("Generating map...")
        generate_map(
            df=df,
            geojson_path=Path(config.geojson_path),
            output_path=maps_dir / "observations_map.html",
            title=f"{config.title} {year}",
        )

    # Charts
    if config.report.include_charts:
        typer.echo("Generating charts...")
        chart_monthly_observations(monthly, charts_dir / "monthly_observations.png", year)
        chart_cumulative_species(df, charts_dir / "cumulative_species.png", year)
        chart_top_species(top_species, charts_dir / "top_species.png", year)

    typer.echo(f"\nDone! All artifacts in: {report_dir}")


@app.command()
def generate(
    dataset: str = typer.Argument(help="Dataset slug, e.g. 'beetles_cyprus'"),
    year: Optional[int] = typer.Option(
        None, "--year", "-y", help="Report year (default: all-time)"
    ),
    config_dir: Path = typer.Option(Path("configs"), "--config-dir"),
    output_dir: Path = typer.Option(Path("reports"), "--output-dir"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="OpenAI model override"),
) -> None:
    """Generate article draft using OpenAI LLM from summary data.

    Without --year: generates from all-time summary.
    With --year: generates for a specific year.
    """
    from inat_report.config import load_config
    from inat_report.llm import generate_texts

    config_path = config_dir / f"{dataset}.yaml"
    if not config_path.exists():
        typer.echo(f"Config not found: {config_path}", err=True)
        raise typer.Exit(code=1)
    config = load_config(config_path)

    report_dir = output_dir / config.slug / (str(year) if year else "all-time")
    summary_path = report_dir / "summary.json"
    if not summary_path.exists():
        typer.echo(f"Summary not found: {summary_path}", err=True)
        typer.echo("Run 'inat-report summary' first.")
        raise typer.Exit(code=1)

    extra_paths: dict[str, Path] = {}
    for name in ["compare.json", "dynamics.json", "tables.json"]:
        p = report_dir / name
        if p.exists():
            extra_paths[name] = p

    llm_model = model or config.llm.model
    typer.echo(f"Generating texts with {llm_model}...")
    typer.echo(f"  Data: summary.json + {', '.join(extra_paths.keys()) or 'no extras'}")

    texts_path = generate_texts(
        summary_path=summary_path,
        output_path=report_dir / "article_texts.json",
        title=config.title,
        year=year,
        extra_paths=extra_paths,
        model=llm_model,
        language=config.llm.language,
    )

    typer.echo(f"\nDone! Texts: {texts_path}")
    typer.echo(f"Prompt log: {report_dir / 'llm_prompt.md'}")
    typer.echo("Run 'inat-report render' to build the final HTML article.")


@app.command()
def render(
    dataset: str = typer.Argument(help="Dataset slug, e.g. 'beetles_cyprus'"),
    year: Optional[int] = typer.Option(
        None, "--year", "-y", help="Report year (default: all-time)"
    ),
    config_dir: Path = typer.Option(Path("configs"), "--config-dir"),
    output_dir: Path = typer.Option(Path("reports"), "--output-dir"),
) -> None:
    """Render final HTML article from LLM texts + data tables."""
    from inat_report.config import load_config
    from inat_report.render import render_article

    config_path = config_dir / f"{dataset}.yaml"
    if not config_path.exists():
        typer.echo(f"Config not found: {config_path}", err=True)
        raise typer.Exit(code=1)
    config = load_config(config_path)

    report_dir = output_dir / config.slug / (str(year) if year else "all-time")

    texts_path = report_dir / "article_texts.json"
    if not texts_path.exists():
        typer.echo(f"Texts not found: {texts_path}", err=True)
        typer.echo("Run 'inat-report generate' first.")
        raise typer.Exit(code=1)

    tables_path = report_dir / "tables.json"
    if not tables_path.exists():
        typer.echo(f"Tables not found: {tables_path}", err=True)
        typer.echo("Run 'inat-report summary' first.")
        raise typer.Exit(code=1)

    summary_path = report_dir / "summary.json"

    typer.echo("Rendering HTML article...")
    article_path = render_article(
        texts_path=texts_path,
        tables_path=tables_path,
        summary_path=summary_path,
        output_path=report_dir / "article.html",
        year=year,
    )
    typer.echo(f"\nDone! Article: {article_path}")


@app.command()
def publish(
    dataset: str = typer.Argument(help="Dataset slug, e.g. 'beetles_cyprus'"),
    year: Optional[int] = typer.Option(
        None, "--year", "-y", help="Report year (default: all-time)"
    ),
    config_dir: Path = typer.Option(Path("configs"), "--config-dir"),
    output_dir: Path = typer.Option(Path("reports"), "--output-dir"),
) -> None:
    """Upload charts/maps to GitHub Pages and produce article with absolute URLs."""
    from inat_report.config import load_config
    from inat_report.publish import make_publishable_html, publish_to_gh_pages

    config_path = config_dir / f"{dataset}.yaml"
    if not config_path.exists():
        typer.echo(f"Config not found: {config_path}", err=True)
        raise typer.Exit(code=1)
    config = load_config(config_path)

    year_str = str(year) if year else "all-time"
    report_dir = output_dir / config.slug / year_str

    article_path = report_dir / "article.html"
    if not article_path.exists():
        typer.echo(f"Article not found: {article_path}", err=True)
        typer.echo("Run 'inat-report render' first.")
        raise typer.Exit(code=1)

    # Push assets to gh-pages
    base_url = publish_to_gh_pages(report_dir, config.slug, year_str)
    typer.echo(f"\nAssets URL: {base_url}")

    # Produce publishable HTML with absolute URLs
    pub_path = make_publishable_html(
        article_path=article_path,
        output_path=report_dir / "article_publish.html",
        base_url=base_url,
    )
    typer.echo(f"Publishable article: {pub_path}")
    typer.echo("\nCopy content of article_publish.html into iNaturalist journal post editor.")


def _load_comparison_data(config: object, data_dir: Path, compare_year: int) -> object:
    """Try to load comparison year data from dedicated CSV or all-time CSV."""
    from inat_report.loader import load_csv

    csv_compare = config.source.csv_pattern.format(year=compare_year)
    csv_compare_path = data_dir / csv_compare
    if csv_compare_path.exists():
        return load_csv(csv_compare_path)

    if config.source.csv_all_time:
        all_time_path = data_dir / config.source.csv_all_time
        if all_time_path.exists():
            typer.echo(f"Loading comparison from all-time CSV, year={compare_year}...")
            return load_csv(all_time_path, year=compare_year)

    typer.echo(f"Warning: no data for {compare_year}, skipping comparison", err=True)
    return None


if __name__ == "__main__":
    app()
