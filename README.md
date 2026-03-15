# iNaturalist Report Generator

CLI-инструмент для генерации годовых отчётов по биоразнообразию на основе данных [iNaturalist](https://www.inaturalist.org/).

Скачивает наблюдения через API, вычисляет аналитику, строит графики и карты, генерирует тексты через OpenAI, собирает HTML-статью для публикации в iNaturalist journal.

## Быстрый старт

```bash
# Установка
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Полный пайплайн для Beetles of Cyprus 2025
inat-report fetch beetles_cyprus
inat-report summary beetles_cyprus --year 2025
inat-report generate beetles_cyprus --year 2025
inat-report render beetles_cyprus --year 2025
inat-report publish beetles_cyprus --year 2025
```

## Конфигурация

Создайте `.env` в корне проекта:

```env
OPENAI_API_KEY=sk-...
```

## Пайплайн

### 1. fetch — скачать данные

```bash
inat-report fetch beetles_cyprus              # все годы (инкрементально)
inat-report fetch beetles_cyprus --year 2025  # один год
```

Скачивает наблюдения из iNaturalist API. Проверяет количество по месяцам — перекачивает только изменившиеся. Сохраняет CSV + raw JSON кэш.

### 2. summary — аналитика

```bash
inat-report summary beetles_cyprus --year 2025               # один год
inat-report summary beetles_cyprus --year 2025 --compare-year 2024  # со сравнением
inat-report summary beetles_cyprus                           # динамика по всем годам
```

Вычисляет метрики, строит графики (matplotlib), карту (folium), обогащает данные фотографиями и аватарками из API.

Выход: `reports/beetles_cyprus/2025/` — summary.json, tables.json, charts/, maps/

### 3. generate — тексты через LLM

```bash
inat-report generate beetles_cyprus --year 2025
inat-report generate beetles_cyprus --year 2025 --model gpt-5.4
```

Отправляет метрики в OpenAI, получает structured JSON с текстами по секциям (title, lead, описания, профили новых видов, conclusion).

Выход: `article_texts.json` — LLM пишет только тексты, не HTML.

### 4. render — сборка HTML

```bash
inat-report render beetles_cyprus --year 2025
```

Собирает финальный `article.html` из текстов LLM + данных с фотографиями по Jinja2-шаблону. HTML использует только теги, разрешённые iNaturalist.

### 5. publish — публикация

```bash
inat-report publish beetles_cyprus --year 2025
```

Загружает графики и карту на GitHub Pages, генерирует `article_publish.html` с абсолютными URL. Готов для копирования в iNaturalist journal post.

## Датасеты

Конфиги в `configs/`:

| Конфиг | Проект | ID |
|--------|--------|----|
| beetles_cyprus | Beetles of Cyprus | 198173 |
| birds_cyprus | Birds of Cyprus | 183301 |
| butterflies_moths_cyprus | Butterflies and Moths of Cyprus | 221789 |
| mammals_cyprus | Mammals of Cyprus | 228122 |
| biodiversity_cyprus | Biodiversity of Cyprus (Research Grade) | 275298 |

Для нового датасета — создайте YAML в `configs/`:

```yaml
slug: my_dataset
title: My Dataset
taxon_common_name: insects
source:
  csv_pattern: "observations-my-dataset-{year}.csv"
  data_dir: "data"
  project_id: 123456
geojson_path: "data/cyprus.geojson"
```

## Промпты

Редактируемые файлы в `prompts/` — меняют поведение LLM без правки кода:

- `system.md` — роль и правила
- `article_year.md` — структура годовой статьи
- `article_alltime.md` — структура обзора за все годы

## Разработка

```bash
# Тесты
pytest

# CI проверки (обязательно после каждого изменения)
ruff format src/ tests/ && ruff check src/ tests/ && mypy -p inat_report
```

## Лицензия

MIT
