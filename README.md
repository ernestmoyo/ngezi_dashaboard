# Ngezi Concentrator — Mine Manager Oversight Dashboard

Interactive analytics dashboard for the **Ngezi Platinum Concentrator** (Zimplats Holdings, Member of the Implats Group).

Transforms production data from conveyor belt weigh sensors, DCS historian exports, and operational reports into a unified dashboard with real-time KPI tracking, RAG performance classification, and executive summaries.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open **http://localhost:8501** in your browser.

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Executive Summary** | Top-level RAG cards for 6 key domains, full KPI table with variance breakdown |
| **KPI Trends** | Monthly actual vs budget tracking with performance indicators |
| **Daily Production** | Daily milled tonnage, variance waterfall, and cumulative tracking |
| **Consumables** | Reagent and water consumption analysis, mill ball stock depletion forecast |
| **Projects** | Capital and compliance project tracker with Gantt timeline |

## KPIs Tracked

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
| Total Cost | USD/t | Lower is better |

## Project Structure

```
ngezi_dashboard/
├── __init__.py
├── config.py           # KPI registry, constants
├── simulator.py        # Simulated production data generator
├── loaders/            # Data ingestion from Excel/Word sources
├── transforms.py       # Fact/dimension table builders
├── kpis.py             # Variance, RAG classification, aggregation
└── dashboard.py        # Dashboard output functions
app.py                  # Streamlit interactive dashboard
main.py                 # CLI pipeline with smoke tests
```

## Architecture

The backend follows a star-schema data model:

- **fact_monthly_kpi** — One row per KPI per period with actual, budget, variance, and RAG
- **fact_monthly_consumables** — Reagent, water, and steel ball consumption tracking
- **fact_daily_plant** — Daily milled tonnage, milling rate, recovery, availability
- **dim_project / fact_project_status** — Capital project tracking with Gantt support

## Extending

- **Database integration:** Replace loaders with SQL queries against InfluxDB/TimescaleDB reading from belt weigh-sensor and DCS historian exports
- **New KPIs:** Add an entry to `KPI_REGISTRY` in `config.py` with direction, unit, and amber band
- **Deployment:** The Streamlit app can be deployed to Streamlit Cloud, or served behind a reverse proxy

## Domain Reference

| Term | Meaning |
|------|---------|
| **6E** | Six platinum-group elements: Pt, Pd, Rh, Ru, Ir, Os |
| **4E** | Pt, Pd, Rh, Au |
| **Grind -75 um** | % of milled product passing a 75-micron sieve |
| **Mass pull** | % of feed tonnage reporting to concentrate |
| **g/t** | Grams per tonne |
| **m3/t** | Cubic metres of water per tonne of ore |
| **TSF** | Tailings Storage Facility |
| **RAG** | Red / Amber / Green traffic-light classification |
| **tph** | Tonnes per hour |
