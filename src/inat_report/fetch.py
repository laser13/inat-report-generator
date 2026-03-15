"""Fetch observations from iNaturalist API using pyinaturalist."""

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import typer
from pyinaturalist import (
    get_observation_identifiers,
    get_observation_observers,
    get_observation_species_counts,
    get_observations,
    get_projects_by_id,
    get_taxa_by_id,
)

# iNaturalist recommends ~1 req/sec; we use 1.2s to be safe
API_DELAY = 1.2


def _api_call(func: Any, **kwargs: Any) -> Any:
    """Call an API function with rate limiting and retry on 429."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            time.sleep(API_DELAY)
            return func(**kwargs)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 10 * (attempt + 1)
                typer.echo(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


def resolve_project(query: str) -> dict[str, Any]:
    """Resolve a project URL, slug or ID to project info.

    Accepts:
        - Full URL: https://www.inaturalist.org/projects/beetles-of-cyprus
        - Slug: beetles-of-cyprus
        - Numeric ID: 198173
    """
    url_match = re.search(r"inaturalist\.org/projects/([^/?#]+)", query)
    if url_match:
        query = url_match.group(1)

    if query.isdigit():
        result = get_projects_by_id(int(query))
    else:
        result = get_projects_by_id(query)

    if not result or "results" not in result or not result["results"]:
        raise ValueError(f"Project not found: {query}")

    project = result["results"][0]
    return {
        "id": project["id"],
        "title": project["title"],
        "slug": project["slug"],
    }


def _get_api_count(project_id: int, year: int) -> int:
    """Get observation count for a project+year. Lightweight — no data transferred."""
    resp = _api_call(
        get_observations,
        project_id=project_id,
        d1=f"{year}-01-01",
        d2=f"{year}-12-31",
        per_page=0,
        count_only=True,
    )
    return resp.get("total_results", 0)


def _get_year_range(project_id: int) -> tuple[int, int] | None:
    """Get the year range of observations in a project."""
    oldest = _api_call(
        get_observations,
        project_id=project_id,
        per_page=1,
        order="asc",
        order_by="observed_on",
    )
    oldest_results = oldest.get("results", [])
    if not oldest_results:
        return None

    first_year = (oldest_results[0].get("observed_on_details") or {}).get("year")
    if not first_year:
        return None

    return int(first_year), date.today().year


def fetch_all(
    project_id: int,
    output_dir: Path,
    slug: str,
) -> dict[int, Path]:
    """Fetch observations, downloading only years where count changed.

    1. Lightweight count_only requests per year (no data transferred)
    2. Compare counts with local CSVs
    3. Full download only for changed years

    Returns:
        Dict of year -> CSV path for each year that was written.
    """
    # 1. Determine year range
    typer.echo(f"Checking project {project_id}...")
    year_range = _get_year_range(project_id)
    if not year_range:
        typer.echo("  No observations found.")
        return {}

    first_year, last_year = year_range
    typer.echo(f"  Year range: {first_year}–{last_year}")

    # 2. Get counts per year (lightweight — only count, no data)
    typer.echo("Checking counts per year...")
    api_counts: dict[int, int] = {}
    for yr in range(first_year, last_year + 1):
        cnt = _get_api_count(project_id, yr)
        if cnt > 0:
            api_counts[yr] = cnt

    # 3. Compare with local CSVs
    years_to_fetch: list[int] = []
    for yr, api_count in sorted(api_counts.items()):
        csv_path = output_dir / f"observations-{slug.replace('_', '-')}-{yr}.csv"
        local_count = _count_csv_rows(csv_path)

        if local_count == api_count:
            typer.echo(f"  {yr}: {api_count} obs — up to date")
        elif local_count is not None:
            typer.echo(f"  {yr}: {local_count} → {api_count} — will re-fetch")
            years_to_fetch.append(yr)
        else:
            typer.echo(f"  {yr}: {api_count} obs — new, will fetch")
            years_to_fetch.append(yr)

    if not years_to_fetch:
        typer.echo("\nAll years up to date.")
        return {}

    # 4. Fetch only changed years
    typer.echo(f"\nFetching {len(years_to_fetch)} year(s)...")
    written: dict[int, Path] = {}
    for yr in years_to_fetch:
        csv_path = fetch_year(project_id, yr, output_dir, slug)
        written[yr] = csv_path

    # 5. Update all-time CSV from per-year CSVs
    typer.echo("Updating all-time CSV...")
    all_dfs = []
    for yr in sorted(api_counts):
        csv_path = output_dir / f"observations-{slug.replace('_', '-')}-{yr}.csv"
        if csv_path.exists():
            all_dfs.append(pd.read_csv(csv_path, low_memory=False))
    if all_dfs:
        all_df = pd.concat(all_dfs, ignore_index=True)
        all_csv = output_dir / f"observations-{slug.replace('_', '-')}.csv"
        all_df.to_csv(all_csv, index=False)
        typer.echo(f"  {all_csv} ({len(all_df)} obs)")

    return written


def fetch_year(
    project_id: int,
    year: int,
    output_dir: Path,
    slug: str,
) -> Path:
    """Fetch observations for a year, checking per-month to minimize downloads.

    1. Check count per month via count_only
    2. Compare with local monthly cache
    3. Download only changed months
    4. Assemble into yearly CSV
    """
    import calendar

    raw_dir = output_dir / "raw" / slug / str(year)
    raw_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"  Checking {year} by month...")
    all_month_obs: list[dict[str, Any]] = []
    months_fetched = 0

    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        d1 = f"{year}-{month:02d}-01"
        d2 = f"{year}-{month:02d}-{last_day:02d}"

        # Lightweight count check
        api_count = _api_call(
            get_observations,
            project_id=project_id,
            d1=d1,
            d2=d2,
            per_page=0,
            count_only=True,
        ).get("total_results", 0)

        if api_count == 0:
            continue

        # Check local monthly cache
        month_json = raw_dir / f"{month:02d}.json"
        local_count = None
        cached_obs: list[dict[str, Any]] = []
        if month_json.exists():
            with open(month_json) as f:
                cached_obs = json.load(f)
            local_count = len(cached_obs)

        if local_count == api_count:
            typer.echo(f"    {year}-{month:02d}: {api_count} obs — cached")
            all_month_obs.extend(cached_obs)
        else:
            status = f"{local_count} → {api_count}" if local_count else f"{api_count} new"
            typer.echo(f"    {year}-{month:02d}: {status} — fetching")
            resp = _api_call(
                get_observations,
                project_id=project_id,
                d1=d1,
                d2=d2,
                per_page=200,
                page="all",
            )
            month_obs = resp.get("results", [])
            with open(month_json, "w") as f:
                json.dump(month_obs, f, ensure_ascii=False, default=str)
            all_month_obs.extend(month_obs)
            months_fetched += 1

    typer.echo(f"    Total: {len(all_month_obs)} obs ({months_fetched} months fetched)")

    # Save combined raw JSON
    with open(raw_dir / "observations.json", "w") as f:
        json.dump(all_month_obs, f, ensure_ascii=False, default=str)

    # Fetch aggregates (always refresh — they're lightweight)
    _fetch_aggregates(project_id, year, raw_dir)

    # Resolve family names from ancestor_ids
    typer.echo("    Resolving family names...")
    family_lookup = _resolve_families(all_month_obs)

    # Write yearly CSV
    csv_path = _observations_to_csv(
        all_month_obs, output_dir, slug, year, family_lookup=family_lookup
    )
    typer.echo(f"    CSV: {csv_path}")
    return csv_path


def _fetch_aggregates(project_id: int, year: int, raw_dir: Path) -> None:
    """Fetch species counts, observers, identifiers for a year."""
    date_params = {"d1": f"{year}-01-01", "d2": f"{year}-12-31"}

    species = _api_call(get_observation_species_counts, project_id=project_id, **date_params)
    with open(raw_dir / "species_counts.json", "w") as f:
        json.dump(species.get("results", []), f, ensure_ascii=False, default=str)

    observers = _api_call(get_observation_observers, project_id=project_id, **date_params)
    with open(raw_dir / "observers.json", "w") as f:
        json.dump(observers.get("results", []), f, ensure_ascii=False, default=str)

    identifiers = _api_call(get_observation_identifiers, project_id=project_id, **date_params)
    with open(raw_dir / "identifiers.json", "w") as f:
        json.dump(identifiers.get("results", []), f, ensure_ascii=False, default=str)


def _count_csv_rows(path: Path) -> int | None:
    """Count rows in existing CSV, or None if file doesn't exist."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, usecols=[0])
        return len(df)
    except Exception:
        return None


def _resolve_families(observations: list[dict[str, Any]]) -> dict[int, str]:
    """Build taxon_id -> family_name map by resolving ancestor_ids via API.

    Collects all unique potential family IDs (from ancestor_ids), fetches them
    in batches, returns mapping for family-rank taxa.
    """
    # Collect all unique ancestor_ids across observations
    all_ancestor_ids: set[int] = set()
    for obs in observations:
        taxon = obs.get("taxon") or {}
        for aid in taxon.get("ancestor_ids", []):
            all_ancestor_ids.add(aid)

    if not all_ancestor_ids:
        return {}

    # Fetch taxa in batches of 30 (API limit)
    family_map: dict[int, str] = {}  # ancestor_id -> family_name
    batch_ids = sorted(all_ancestor_ids)
    for i in range(0, len(batch_ids), 30):
        batch = batch_ids[i : i + 30]
        resp = _api_call(get_taxa_by_id, taxon_id=batch)
        for t in resp.get("results", []):
            if t.get("rank") == "family":
                family_map[t["id"]] = t["name"]

    # Build taxon_id -> family_name (find which ancestor is the family)
    result: dict[int, str] = {}
    for obs in observations:
        taxon = obs.get("taxon") or {}
        tid = taxon.get("id")
        if not tid or tid in result:
            continue
        for aid in taxon.get("ancestor_ids", []):
            if aid in family_map:
                result[tid] = family_map[aid]
                break

    typer.echo(f"    Resolved {len(result)} taxa to {len(family_map)} families")
    return result


def _observations_to_csv(
    observations: list[dict[str, Any]],
    output_dir: Path,
    slug: str,
    year: int,
    filename: Path | None = None,
    family_lookup: dict[int, str] | None = None,
) -> Path:
    """Convert raw API observations to a CSV matching iNaturalist export format."""
    rows = []
    for obs in observations:
        taxon = obs.get("taxon") or {}
        user = obs.get("user") or {}
        lat, lon = (None, None)
        location = obs.get("location")
        if isinstance(location, (list, tuple)) and len(location) == 2:
            lat, lon = float(location[0]), float(location[1])
        elif isinstance(location, str) and "," in location:
            parts = location.split(",")
            if len(parts) == 2:
                try:
                    lat, lon = float(parts[0].strip()), float(parts[1].strip())
                except ValueError:
                    pass
        if lat is None and obs.get("geojson"):
            coords = obs["geojson"].get("coordinates", [])
            if len(coords) == 2:
                lon, lat = float(coords[0]), float(coords[1])

        ancestors = {a.get("rank", ""): a.get("name", "") for a in taxon.get("ancestors", [])}
        photos = obs.get("photos", [])
        photo_url = photos[0].get("url", "").replace("square", "medium") if photos else ""

        rows.append(
            {
                "id": obs.get("id"),
                "observed_on": obs.get("observed_on_details", {}).get("date", ""),
                "time_observed_at": obs.get("time_observed_at", ""),
                "user_id": user.get("id"),
                "user_login": user.get("login", ""),
                "user_name": user.get("name", ""),
                "quality_grade": obs.get("quality_grade", ""),
                "license": obs.get("license_code", ""),
                "url": f"https://www.inaturalist.org/observations/{obs.get('id', '')}",
                "image_url": photo_url,
                "latitude": lat,
                "longitude": lon,
                "positional_accuracy": obs.get("positional_accuracy"),
                "place_guess": obs.get("place_guess", ""),
                "species_guess": obs.get("species_guess", ""),
                "scientific_name": taxon.get("name", ""),
                "common_name": taxon.get("preferred_common_name", ""),
                "iconic_taxon_name": taxon.get("iconic_taxon_name", ""),
                "taxon_id": taxon.get("id"),
                "taxon_kingdom_name": ancestors.get("kingdom", ""),
                "taxon_phylum_name": ancestors.get("phylum", ""),
                "taxon_class_name": ancestors.get("class", ""),
                "taxon_order_name": ancestors.get("order", ""),
                "taxon_family_name": ancestors.get("family", "")
                or (family_lookup or {}).get(taxon.get("id"), ""),
                "taxon_subfamily_name": ancestors.get("subfamily", ""),
                "taxon_genus_name": ancestors.get("genus", ""),
                "taxon_species_name": (
                    taxon.get("name", "") if taxon.get("rank") == "species" else ""
                ),
                "num_identification_agreements": obs.get("num_identification_agreements", 0),
                "num_identification_disagreements": obs.get("num_identification_disagreements", 0),
                "captive_cultivated": obs.get("captive", False),
            }
        )

    df = pd.DataFrame(rows)
    if filename:
        csv_path = filename
    else:
        csv_path = output_dir / f"observations-{slug.replace('_', '-')}-{year}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return csv_path
