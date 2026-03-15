# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CLI tool that fetches iNaturalist biodiversity data, computes analytics, generates charts/maps, produces article texts via OpenAI (structured JSON), and renders final HTML articles. Four-step pipeline: `fetch` → `summary` → `generate` → `render`.

## Commands

```bash
# Setup
source .venv/bin/activate
pip install -e ".[dev]"

# CI checks (run after EVERY code change)
ruff format src/ tests/ && ruff check src/ tests/ && mypy -p inat_report

# Tests
pytest                                    # all tests
pytest tests/test_analytics.py -v         # single module
pytest tests/test_fetch.py::test_location_as_list -v  # single test

# CLI — full pipeline
inat-report fetch beetles_cyprus                        # fetch all years (incremental)
inat-report fetch beetles_cyprus --year 2025            # single year
inat-report summary beetles_cyprus --year 2025          # analytics + charts + map for one year
inat-report summary beetles_cyprus                      # all-time dynamics across all years
inat-report generate beetles_cyprus --year 2025         # LLM → article_texts.json (structured)
inat-report render beetles_cyprus --year 2025           # article_texts.json + tables.json → article.html
```

## Architecture

```
fetch → CSV → summary (analytics + charts + map + enrich) → generate (LLM → JSON) → render (JSON + data → HTML)
```

```
src/inat_report/
├── cli.py          — Typer CLI: fetch, summary, generate, render commands
├── config.py       — Pydantic models for YAML dataset configs (defaults: model=gpt-5.4)
├── fetch.py        — iNaturalist API client (pyinaturalist), incremental monthly caching, family resolution
├── loader.py       — CSV loading + column normalization (COLUMN_MAP)
├── analytics.py    — Deterministic metrics: summary, monthly, yearly_dynamics, top species/families/observers, singletons, districts
├── compare.py      — Year-over-year comparison (new/lost species, count changes)
├── enrich.py       — Add photos/avatars from raw API JSON (observers, species, identifiers, singletons)
├── charts.py       — Matplotlib: monthly bars, cumulative species, top species barh, yearly dynamics (4-panel)
├── maps.py         — Folium: clustered observation points + Cyprus district boundaries from GeoJSON
├── llm.py          — OpenAI structured output (Pydantic schema → article_texts.json)
├── render.py       — Jinja2 HTML rendering from LLM texts + enriched data tables
└── templates/
    ├── article.html.j2   — HTML article template (iNaturalist-compatible tags)
    └── report.md.j2      — Legacy Markdown template

prompts/
├── system.md             — LLM system prompt (plain text output, no HTML)
├── article_year.md       — Article structure for single year
└── article_alltime.md    — Article structure for all-time overview
```

## Pipeline detail

### Step 1: fetch
- Resolves project from config `source.project_id` (or `--project` override)
- Without `--year`: checks count per year via `count_only` API, then per-month within changed years
- Only downloads months where count differs from cached `data/raw/{slug}/{year}/{MM}.json`
- Resolves family names from `ancestor_ids` via batch `get_taxa_by_id` API calls
- Rate limiting: 1.2s between requests + exponential backoff retry on 429
- Outputs: per-year CSV + all-time CSV + raw JSON cache

### Step 2: summary
- With `--year`: single year stats (summary.json, tables.json, charts, map)
- Without `--year`: all-time dynamics (dynamics.json, yearly_dynamics chart)
- Enriches tables.json with photos/avatars from raw API data (enrich.py)
- Computes new species (first recorded this year vs all previous years)
- tables.json includes: monthly, top_species, top_families, top_observers, new_species, rich_observers, rich_species, rich_identifiers, rich_singletons

### Step 3: generate
- Sends summary.json + tables.json (compact) to OpenAI
- Uses Pydantic schema (ArticleTexts) for structured JSON output
- Returns article_texts.json with fields: title, lead, year_in_numbers_intro, observers_text, biodiversity_text, top_species_text, new_species_profiles[], seasonal_text, geography_text, identifiers_text, comparison_text, limitations_text, conclusion
- LLM writes plain text only — no HTML, no Markdown
- Prompt files editable in prompts/ without code changes

### Step 4: render
- Combines article_texts.json + tables.json → article.html via Jinja2
- Code controls layout: tables with photos/avatars, species cards, observer grids
- LLM texts inserted as plain text between data blocks
- HTML uses only iNaturalist-allowed tags (a, b, br, h1-h6, i, img, li, ol, p, table, td, th, tr, ul, etc.)
- Smart quotes/dashes normalized to ASCII
- Charts referenced as relative paths (charts/*.png) — for iNaturalist journal need external hosting

## Dataset configs

YAML files in `configs/` — only unique params, defaults from config.py. Key fields:
- `slug`, `title`, `taxon_common_name`
- `source.project_id` (iNaturalist project ID), `source.csv_pattern`, `source.csv_all_time`
- `llm.model` (default: gpt-5.4), `llm.language`

Five pre-configured: beetles_cyprus, birds_cyprus, butterflies_moths_cyprus, mammals_cyprus, biodiversity_cyprus.

## Data paths

```
data/
├── observations-{slug}-{year}.csv   — per-year observations (from fetch)
├── observations-{slug}.csv          — all-time combined
├── raw/{slug}/{year}/{MM}.json      — monthly API cache
├── raw/{slug}/{year}/observations.json — combined year observations
├── raw/{slug}/{year}/species_counts.json, observers.json, identifiers.json
└── cyprus.geojson                   — district boundaries

reports/{slug}/{year}/
├── summary.json          — core metrics
├── tables.json           — analytics tables + enriched photos/avatars
├── compare.json          — year-over-year comparison (if --compare-year)
├── article_texts.json    — LLM-generated texts (structured JSON)
├── article.html          — final rendered article
├── llm_prompt.md         — full prompt sent to LLM (for reproducibility)
├── charts/
│   ├── monthly_observations.png
│   ├── cumulative_species.png
│   └── top_species.png
└── maps/
    └── observations_map.html

reports/{slug}/all-time/
├── summary.json, dynamics.json, tables.json
├── charts/yearly_dynamics.png, top_species_alltime.png
└── maps/observations_map.html
```

## Environment

- Python ≥3.12
- `OPENAI_API_KEY` in `.env` (loaded via python-dotenv) — required for `generate`
- Tests use real CSV data from `data/` (not mocked)

## Known limitations

- Charts in article.html use relative paths — for iNaturalist journal posts, PNGs need to be uploaded to external hosting and URLs replaced
- District names normalization is hardcoded in analytics.py (CSV names → GeoJSON names)
- API `get_observations` doesn't return `ancestors` — family names resolved via separate batch `get_taxa_by_id` calls during fetch
- `_resolve_families` makes extra API calls (~2 per year of data) adding ~30s to fetch

## Design docs

- `docs/design-article-pipeline.md` — architecture of the generate→render pipeline (LLM JSON + code HTML)
