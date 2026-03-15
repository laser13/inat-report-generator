"""LLM-based article text generation using OpenAI API with structured output."""

import json
from pathlib import Path
from typing import Any

import typer
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text().strip()


# --- Pydantic schema for structured LLM response ---


class SpeciesProfile(BaseModel):
    scientific_name: str
    description: str


class ArticleTexts(BaseModel):
    title: str
    lead: str
    year_in_numbers_intro: str
    observers_text: str
    biodiversity_text: str
    top_species_text: str
    new_species_profiles: list[SpeciesProfile]
    rare_sightings_text: str
    seasonal_text: str
    geography_text: str
    identifiers_text: str
    comparison_text: str | None = None
    limitations_text: str
    conclusion: str


# --- Main function ---


def generate_texts(
    summary_path: Path,
    output_path: Path,
    title: str,
    year: int | None = None,
    extra_paths: dict[str, Path] | None = None,
    model: str = "gpt-5.4",
    language: str = "en",
) -> Path:
    """Generate article texts as structured JSON using OpenAI API.

    Returns path to article_texts.json.
    """
    client = OpenAI()

    with open(summary_path) as f:
        summary = json.load(f)

    extra_data: dict[str, Any] = {}
    for name, path in (extra_paths or {}).items():
        with open(path) as f:
            extra_data[name] = json.load(f)

    system_prompt = _load_prompt("system.md")
    user_prompt = _build_prompt(title, year, summary, extra_data, language)

    typer.echo(f"  Calling {model}...")
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=ArticleTexts,
        temperature=0.7,
        max_completion_tokens=8000,
    )

    choice = response.choices[0]
    typer.echo(f"  Finish reason: {choice.finish_reason}")
    if response.usage:
        typer.echo(
            f"  Tokens: {response.usage.prompt_tokens} prompt"
            f" + {response.usage.completion_tokens} completion"
        )

    parsed = choice.message.parsed
    if parsed is None:
        typer.echo("  ERROR: No structured response from LLM!", err=True)
        if choice.message.refusal:
            typer.echo(f"  Refusal: {choice.message.refusal}", err=True)
        raise typer.Exit(code=1)

    # Save structured JSON
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = parsed.model_dump()
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Save prompt log for reproducibility
    prompt_log = output_path.parent / "llm_prompt.md"
    prompt_log.write_text(f"# System Prompt\n\n{system_prompt}\n\n# User Prompt\n\n{user_prompt}")

    return output_path


def _build_prompt(
    title: str,
    year: int | None,
    summary: dict[str, Any],
    extra_data: dict[str, Any],
    language: str,
) -> str:
    lang_instruction = ""
    if language != "en":
        lang_instruction = f"\n\nIMPORTANT: Write ALL text fields in {language} language.\n"

    period = "all-time" if year is None else str(year)

    prompt = f"""Generate article texts for "{title}" ({period}).
{lang_instruction}
## Summary

```json
{json.dumps(summary, indent=2, ensure_ascii=False)}
```
"""

    if "tables.json" in extra_data:
        tables = extra_data["tables.json"]
        # Send compact data — only what LLM needs for writing
        compact: dict[str, Any] = {}
        for key in [
            "monthly",
            "top_species",
            "top_families",
            "top_observers",
            "singleton_count",
            "district_stats",
            "new_species",
        ]:
            if key in tables:
                compact[key] = tables[key]
        prompt += f"""
## Analytics Tables

```json
{json.dumps(compact, indent=2, ensure_ascii=False)}
```
"""

    if "dynamics.json" in extra_data:
        prompt += f"""
## Year-over-Year Dynamics

```json
{json.dumps(extra_data["dynamics.json"], indent=2, ensure_ascii=False)}
```
"""

    if "compare.json" in extra_data:
        comp = extra_data["compare.json"]
        compact_comp = {
            "current_year": comp.get("current_year"),
            "previous_year": comp.get("previous_year"),
            "observations_change": comp.get("observations_change"),
            "species_change": comp.get("species_change"),
            "observers_change": comp.get("observers_change"),
            "new_species_count": len(comp.get("new_species", [])),
            "lost_species_count": len(comp.get("lost_species", [])),
            "new_species_sample": comp.get("new_species", [])[:20],
        }
        prompt += f"""
## Comparison with Previous Year

```json
{json.dumps(compact_comp, indent=2, ensure_ascii=False)}
```
"""

    prompt += """
## Instructions

Generate texts for each article section. Return structured JSON matching the schema.

For `new_species_profiles`: pick up to 10 most interesting species from the new_species list.
For each, write 2-4 sentences about biology, appearance, habitat, and why it's notable.
Use your biological knowledge but mark uncertain facts.

For `limitations_text`: MUST mention these three points:
1) iNaturalist data reflects observer activity, not a census
2) absence of records does not mean absence of species
3) year-to-year changes may reflect effort changes

All text fields: plain text only (no HTML, no Markdown). Will be placed into HTML templates.
"""
    return prompt
