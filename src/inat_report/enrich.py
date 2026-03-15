"""Enrich analytics tables with photos and links from raw API JSON."""

import json
from pathlib import Path
from typing import Any


def enrich_tables(tables: dict[str, Any], raw_dir: Path) -> dict[str, Any]:
    """Add photo URLs, avatar URLs, and links from raw API data to tables.

    Args:
        tables: Existing tables dict (from analytics).
        raw_dir: Path to data/raw/{slug}/{year}/ with API JSON files.

    Returns:
        Enriched tables dict with additional fields.
    """
    tables["rich_observers"] = _enrich_observers(raw_dir)
    tables["rich_identifiers"] = _enrich_identifiers(raw_dir)
    tables["rich_species"] = _enrich_species(raw_dir)
    tables["rich_singletons"] = _enrich_singletons(tables, raw_dir)
    return tables


def _load_raw(raw_dir: Path, filename: str) -> list[dict[str, Any]]:
    """Load a raw API JSON file, return empty list if missing."""
    path = raw_dir / filename
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def _enrich_observers(raw_dir: Path) -> list[dict[str, Any]]:
    """Extract top observers with avatars from raw observers.json."""
    raw = _load_raw(raw_dir, "observers.json")
    result = []
    for item in raw[:20]:  # top 20
        user = item.get("user") or {}
        result.append(
            {
                "login": user.get("login", ""),
                "name": user.get("name", ""),
                "icon_url": user.get("icon", ""),
                "observations": item.get("observation_count", 0),
                "species": item.get("species_count", 0),
            }
        )
    return result


def _enrich_identifiers(raw_dir: Path) -> list[dict[str, Any]]:
    """Extract top identifiers with avatars from raw identifiers.json."""
    raw = _load_raw(raw_dir, "identifiers.json")
    result = []
    for item in raw[:20]:  # top 20
        user = item.get("user") or {}
        result.append(
            {
                "login": user.get("login", ""),
                "name": user.get("name", ""),
                "icon_url": user.get("icon", ""),
                "count": item.get("count", 0),
            }
        )
    return result


def _enrich_species(raw_dir: Path) -> list[dict[str, Any]]:
    """Extract top species with photos from raw species_counts.json."""
    raw = _load_raw(raw_dir, "species_counts.json")
    result = []
    for item in raw[:30]:  # top 30
        taxon = item.get("taxon") or {}
        photo = taxon.get("default_photo") or {}
        ancestors = taxon.get("ancestors") or []
        family = next((a["name"] for a in ancestors if a.get("rank") == "family"), "")
        result.append(
            {
                "taxon_id": taxon.get("id"),
                "scientific_name": taxon.get("name", ""),
                "common_name": taxon.get("preferred_common_name", ""),
                "rank": taxon.get("rank", ""),
                "family": family,
                "photo_url": photo.get("medium_url", photo.get("url", "")),
                "square_url": photo.get("square_url", photo.get("url", "")),
                "count": item.get("count", 0),
            }
        )
    return result


def _enrich_singletons(tables: dict[str, Any], raw_dir: Path) -> list[dict[str, Any]]:
    """Match singleton species with their observation photos."""
    observations = _load_raw(raw_dir, "observations.json")

    # Build a map: scientific_name -> first observation with photo
    species_obs: dict[str, dict[str, Any]] = {}
    for obs in observations:
        taxon = obs.get("taxon") or {}
        name = taxon.get("name", "")
        if not name or name in species_obs:
            continue
        photos = obs.get("photos") or []
        photo_url = ""
        if photos:
            photo_url = photos[0].get("url", "").replace("square", "medium")
        user = obs.get("user") or {}
        species_obs[name] = {
            "observation_id": obs.get("id"),
            "photo_url": photo_url,
            "observer_login": user.get("login", ""),
            "observer_name": user.get("name", ""),
            "observed_on": (obs.get("observed_on_details") or {}).get("date", ""),
        }

    # Match with singleton species from analytics
    # tables may have "new_species" list — use those
    new_species = tables.get("new_species", [])
    result = []
    for sp_name in new_species:
        obs_data = species_obs.get(sp_name, {})
        result.append(
            {
                "scientific_name": sp_name,
                "observation_id": obs_data.get("observation_id"),
                "photo_url": obs_data.get("photo_url", ""),
                "observer_login": obs_data.get("observer_login", ""),
                "observer_name": obs_data.get("observer_name", ""),
                "observed_on": obs_data.get("observed_on", ""),
            }
        )
    return result
