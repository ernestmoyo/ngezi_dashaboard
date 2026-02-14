# Ngezi Concentrator — Mine Manager Oversight Dashboard

Analytics backend for transforming Excel workbooks and Word narrative reports from the **Ngezi Platinum Concentrator** (Zimbabwe) into a unified, dashboard-ready data layer.

## Overview

The Ngezi Concentrator plant generates production data from weigh sensors on conveyor belts, which flows through manual entry into Excel workbooks and Word weekly reports. This project consolidates those fragmented sources into a clean star-schema data model with automated KPI tracking and RAG (Red/Amber/Green) performance classification.

### What it does

- **Ingests** messy multi-row-header Excel files and Word documents
- **Transforms** raw data into fact and dimension tables (star schema)
- **Computes** variance, RAG classification, and executive summaries
- **Outputs** dashboard-ready DataFrames and dicts for any front-end

### Data Sources

| File | Purpose |
|------|---------|
| `KPIs - Q3 FY2020.xlsx` | Quarterly KPI scorecard — Actual vs Budget |
| `Copy of Mill ball trends.xlsx` | Monthly mill-ball consumption & stock projection |
| `October 2021 - Week 5r.docx` | Weekly narrative report with project tracker |
| `October 2021 07.10.21.xlsx` | Weekly Excel with daily production, consumables, grind |

### KPIs Tracked

| KPI | Unit | Direction |
|-----|------|-----------|
| Crushed Tonnage | t | Higher is better |
| Milling Rate | tph | Higher is better |
| Milled Tonnage | t | Higher is better |
| Grind (%-75 microns) | % | Higher is better |
| Plant Running Time | % | Higher is better |
| Mass Pull | % | Higher is better |
| 6E Recovery | % | Higher is better |
| Mill Ball Consumption | g/t | Lower is better |
| Filter Cake Moisture | % | Lower is better |
| Metal Unaccounted For | % | Lower is better |
| Raw Water Consumption | m3/t | Lower is better |
| Total Cost | USD | Lower is better |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline
python main.py
```

This runs end-to-end ingestion, transformation, and prints a smoke-test summary including all acceptance criteria checks.

## Project Structure

```
ngezi_dashboard/
├── __init__.py              # Package docs & extensibility notes
├── config.py                # KPI registry, file paths, constants
├── loaders/
│   ├── __init__.py
│   ├── kpi_scorecard.py     # FY20 Q3 KPI scorecard loader
│   ├── mill_ball.py         # Mill-ball trends & supplier inventory
│   ├── weekly_report.py     # Weekly Excel + Word document loaders
│   └── utils.py             # Header detection, date normalisation
├── transforms.py            # Fact & dimension table builders
├── kpis.py                  # Variance, RAG classification, aggregation
└── dashboard.py             # Manager overview entry points
main.py                      # End-to-end pipeline & smoke tests
requirements.txt             # Python dependencies
```

## Data Model

### Fact Tables

- **`fact_monthly_kpi`** — One row per KPI per period. Columns: `period`, `plant`, `kpi_name`, `actual`, `budget`, `variance`, `variance_pct`, `direction`, `rag`, `comments`
- **`fact_monthly_consumables`** — One row per consumable per month. Steel balls from mill-ball trends, reagents and water from weekly reports
- **`fact_daily_plant`** — One row per day with milled tonnage actual vs target (Oct 2021)
- **`fact_project_status`** — Snapshot-based project status for Gantt/timeline tracking

### Dimension Tables

- **`dim_project`** — 12 capital and compliance projects with responsible person and planned completion date

## Usage in Code

```python
from ngezi_dashboard.loaders import load_kpi_scorecard, load_projects_from_docx
from ngezi_dashboard.transforms import build_fact_monthly_kpi
from ngezi_dashboard.dashboard import get_manager_overview

# Load and transform
kpi_df = load_kpi_scorecard("path/to/KPIs.xlsx")
fact_kpi = build_fact_monthly_kpi(kpi_df)

# Get executive summary with RAG
overview = get_manager_overview(fact_kpi, "2020-Q3")
# Returns: {"period": "2020-Q3", "crushing": {"actual": ..., "rag": "green"}, ...}
```

## Extending

- **Swap Excel for database:** Replace loader functions with SQL queries against InfluxDB/TimescaleDB reading from belt weigh-sensor and DCS historian exports
- **Connect to Streamlit/Dash:** Call `get_manager_overview(period)` to populate cards and trend charts
- **Add new KPIs:** Add an entry to `KPI_REGISTRY` in `config.py` with direction, unit, and amber band

## Domain Reference

| Term | Meaning |
|------|---------|
| **6E** | Six platinum-group elements: Pt, Pd, Rh, Ru, Ir, Os |
| **4E** | Pt, Pd, Rh, Au |
| **Grind -75 um** | % of milled product passing a 75-micron sieve |
| **Mass pull** | % of feed tonnage reporting to concentrate |
| **g/t** | Grams per tonne (mill-ball consumption, metal grades) |
| **m3/t** | Cubic metres of water per tonne of ore processed |
| **TSF** | Tailings Storage Facility |
| **RAG** | Red / Amber / Green traffic-light classification |
| **tph** | Tonnes per hour |
| **FY20 Q3** | Zimplats fiscal year 2020, quarter 3 |
