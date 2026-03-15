"""Render final HTML article from LLM texts + enriched data."""

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

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


def render_article(
    texts_path: Path,
    tables_path: Path,
    summary_path: Path,
    output_path: Path,
    year: int | None = None,
) -> Path:
    """Render HTML article from structured LLM texts + enriched data tables.

    Args:
        texts_path: Path to article_texts.json (from generate step).
        tables_path: Path to tables.json (from summary step, enriched).
        summary_path: Path to summary.json.
        output_path: Where to write article.html.
        year: Report year for display.
    """
    with open(texts_path) as f:
        texts = json.load(f)
    # Normalize smart quotes/dashes to ASCII for safe HTML rendering
    texts = _normalize_text(texts)
    with open(tables_path) as f:
        data = json.load(f)
    with open(summary_path) as f:
        summary = json.load(f)

    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)), keep_trailing_newline=True)
    template = env.get_template("article.html.j2")

    # Build lookup: scientific_name -> observation photo info for new species
    new_species_photos: dict[str, dict[str, str]] = {}
    for item in data.get("rich_singletons", []):
        new_species_photos[item["scientific_name"]] = item

    html = template.render(
        texts=texts,
        data=data,
        summary=summary,
        year=year or "All Time",
        month_names=MONTH_NAMES,
        new_species_photos=new_species_photos,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _normalize_text(obj: object) -> object:
    """Replace smart quotes/dashes with ASCII equivalents recursively."""
    replacements = {
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote (apostrophe)
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2026": "...",  # ellipsis
    }
    if isinstance(obj, str):
        for old, new in replacements.items():
            obj = obj.replace(old, new)
        return obj
    if isinstance(obj, dict):
        return {k: _normalize_text(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_text(item) for item in obj]
    return obj
