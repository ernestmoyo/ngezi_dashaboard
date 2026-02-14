# Ngezi Concentrator — Mine Manager Oversight Dashboard

## System Role

You are a senior data engineer and analytics developer. Your client is the Concentrator Mine Manager at **Ngezi Platinum Concentrator** (Zimbabwe). He currently receives performance data through a combination of Excel workbooks and Word narrative reports. Your task is to design and implement a **production-grade Python analytics backend** that transforms these fragmented sources into a unified, dashboard-ready data layer.

The code must be robust, modular, and defensive against the messy multi-row-header Excel layouts described below. It should be suitable for eventual deployment behind a Streamlit or Dash front end, or for integration with a direct sensor/database feed.

---

## 1  Source Files

You have four files. Treat them as the canonical data sources. File names below are normalised; map them to whichever path they sit in on disk.

### 1.1  `KPIs_Q3_FY2020.xlsx`

**Purpose:** Quarterly KPI scorecard — Actual vs Budget across multiple time horizons.

| Detail | Value |
|--------|-------|
| Sheets | `FY20 Q3` (primary), `Sheet1` (summary aggregates) |
| Layout | Rows 3–4 are a **two-row merged header**: Row 3 carries period groups (`Quarter 1`, `Quarter 2 to date`, `August`, `Quarter 3`, `FY2020 YTD`); Row 4 carries sub-columns (`Actual`, `Budget`, `Var %`). Data runs rows 5–18. Column B holds the KPI label. |
| Key KPIs (column B) | `Crushed tonnage`, `Milling rate t/h`, `Milled tonnage`, `Grind (%-75 microns)`, `Plant running time %`, `Mass pull (%)`, `6E Recovery (%)`, `Mill Ball consumption g/t`, `Filter cake moisture (%)`, `Metal Unaccounted For (%)`, `Raw water consumption (m3/t)`, `Total Cost` |
| Gotchas | First two data rows (`Tis`, `BMS external audits`) are safety/audit KPIs with zero values — skip them for plant analytics. Some KPIs have `None` values in earlier quarters (data only available from Q3 onward). The `Comments` column (R) provides the manager's qualitative assessment per KPI. |

### 1.2  `Copy_of_Mill_ball_trends_rev_1.xlsx`

**Purpose:** Monthly mill-ball procurement, consumption forecast, and grind projection.

| Detail | Value |
|--------|-------|
| Sheets | `Sheet1`, `Sheet2`, `Changed` (all share the same structure with minor parameter variations) |
| Layout | Rows 3–7: supplier-level ball inventory (Vega, Maggotteaux, Anhui, Frusina) with columns for size (mm), unit weight (kg), monthly quantities, and running total. Row 10 onward: projected milled tonnage and consumption calculations by month (Sep 2020 → May 2021). Key computed rows include `Projected Milled tonnage`, `Mill 1 tonnage`, `Consumption g/t` (budget = 600 or 550), and `Steel /t` or `Mill balls used, t`. |
| Gotchas | Dates appear as `datetime` objects in some sheets and as Excel serial numbers (e.g., 44075 = 2020-09-01) in `Changed`. Columns N onward hold the monthly time series; columns B–L hold supplier-level detail. Some cells contain labels (`Mille`, `Stock`) acting as section separators rather than data. |

### 1.3  `October_2021_Week_5r.docx`

**Purpose:** Weekly narrative report for the week ending ~5 November 2021.

| Detail | Value |
|--------|-------|
| Sections | Introduction → People Issues → Production (Crushing, Milling, Metal Production, Consumables, Water Consumption) → Ngezi Concentrator Projects → TSF Management → Other TSF Areas → Focus Areas for the Week |
| Tables | **One table** (13 rows × 5 columns): `Item | Project | Responsibility | Completion date | Comments`. Lists capital and compliance projects (portal sealing, inundation study, seismic unit, piezocone audit, etc.) with responsible person initials, target dates, and status commentary. |
| Key narratives | Milled tonnage 1.6% above target; ounces 2% above target; recovery on track. All reagents within budget. Mill ball consumption within budget. Water consumption within budget; Chitsuwa dam draining at 0.6 m³/s; leak monitoring ongoing per Stewart Scot recommendation. |

### 1.4  Additional context (not provided as files — for domain enrichment)

- **Mill-ball addition strategy (Aug 2020):** Narrative document describing the rationale for ball-size selection, supplier diversification, and target consumption rates. Use the `Consumption g/t` budget values from file 1.2 as the authoritative targets.
- **Weekly Excel report (`October-2021-07.10.21.xlsx`):** Multi-sheet workbook with daily production data, FAZ inspection records, TSF checklists, DATA and DATA 2 sheets with progressive month/quarter aggregations. If this file is provided, parse it for daily granularity data (see Section 3.3).

---

## 2  Deliverable: Analytics Backend

Build a Python package (or a single well-organised module) with the following components.

### 2.1  Data Ingestion Layer

Write **one loader function per source file**. Each function must:

1. Auto-detect the effective header row by scanning for signature strings (e.g., a row containing both `Actual` and `Budget`; or a row containing `KPI`).
2. Drop decoration rows (titles, blank rows, merged-header remnants, section-separator labels like `Mille` or `Stock`).
3. Rename columns to snake_case canonical names.
4. Coerce types: numerics to `float64`, dates to `pd.Timestamp`, percentages stored as decimals (0.78 → 78.0) normalised to a consistent convention (always 0–100).
5. Return a clean `pd.DataFrame` with a docstring documenting assumptions.

```python
# Example signature
def load_kpi_scorecard(path: str) -> pd.DataFrame:
    """
    Loads FY20 Q3 KPI scorecard.
    
    Assumptions
    -----------
    - Header spans rows 3-4 (0-indexed: 2-3).
    - KPI labels are in column B (index 1).
    - First two data rows (Tis, BMS external audits) are non-plant KPIs and are dropped.
    
    Returns
    -------
    DataFrame with columns:
        kpi, q1_actual, q1_budget, q1_var_pct, ..., fy20_ytd_actual, fy20_ytd_budget, fy20_ytd_var_pct, comments
    """
```

Handle the mill-ball file's mixed date formats explicitly:

```python
def _normalise_date(val):
    """Convert Excel serial number or datetime to pd.Timestamp."""
    if isinstance(val, (int, float)):
        return pd.Timestamp("1899-12-30") + pd.Timedelta(days=int(val))
    return pd.Timestamp(val)
```

### 2.2  Data Model — Fact and Dimension Tables

Transform ingested data into the following target schemas. Use `pd.DataFrame` for storage; optionally define `pydantic` or `dataclass` models for validation.

#### `fact_monthly_kpi`

Grain: **plant × month**. One row per KPI per month.

| Column | Type | Source |
|--------|------|--------|
| `month` | `date` | Derived from period headers in KPIs file; from date columns in mill-ball file |
| `plant` | `str` | Hard-coded `"Ngezi Concentrator"` |
| `kpi_name` | `str` | Canonical name (e.g., `crushed_tonnage`, `milling_rate_tph`, `grind_pct_minus75`, `recovery_6e_pct`, `mill_ball_consumption_gt`, `raw_water_m3t`, `total_cost`) |
| `actual` | `float` | Value from `Actual` column |
| `budget` | `float` | Value from `Budget` column |
| `variance` | `float` | `actual - budget` |
| `variance_pct` | `float` | `(actual - budget) / budget * 100` if budget ≠ 0 else `None` |
| `direction` | `str` | `"higher_is_better"` or `"lower_is_better"` — drives RAG logic |
| `comments` | `str` | From Comments column where available |

Melt the wide KPI scorecard into this long format. Merge mill-ball monthly time series into the same table under `kpi_name = "mill_ball_consumption_gt"`.

#### `fact_daily_plant` (contingent on weekly Excel file)

Grain: **plant × date**. One row per day.

| Column | Type |
|--------|------|
| `date` | `date` |
| `plant` | `str` |
| `crushed_tonnage_actual` | `float` |
| `crushed_tonnage_target` | `float` |
| `milled_tonnage_actual` | `float` |
| `milled_tonnage_target` | `float` |
| `milling_rate_tph_actual` | `float` |
| `recovery_pct_actual` | `float` |
| `recovery_pct_target` | `float` |
| `oz_produced_actual` | `float` |
| `oz_produced_target` | `float` |
| `crusher_availability_pct` | `float` |
| `mill_availability_pct` | `float` |

If the weekly Excel file is not present, generate a stub function that returns an empty DataFrame with the correct schema and a log warning.

#### `fact_monthly_consumables`

Grain: **plant × month × consumable**.

| Column | Type |
|--------|------|
| `month` | `date` |
| `plant` | `str` |
| `consumable` | `str` |
| `actual` | `float` |
| `budget` | `float` |
| `variance` | `float` |
| `variance_pct` | `float` |

Populate `steel_balls` rows from mill-ball file. Reagent rows (collector, depressant, frother) from the weekly Excel consumables sheet if available.

#### `dim_project` + `fact_project_status`

Extracted from the Word document's single table.

**`dim_project`:**

| Column | Type |
|--------|------|
| `project_id` | `str` |
| `project_name` | `str` |
| `responsible` | `str` |
| `planned_completion` | `date` |

**`fact_project_status`:**

| Column | Type |
|--------|------|
| `snapshot_date` | `date` |
| `project_id` | `str` |
| `status` | `str` |
| `comments` | `str` |

Use the item letter (`a`, `b`, `c`, …) as `project_id`. Parse the Word table programmatically with `python-docx`. Design the schema so that ingesting additional weekly reports appends rows to `fact_project_status`, enabling a simple Gantt or status-over-time widget.

---

### 2.3  KPI Computation Functions

Implement these as pure functions with no side effects.

```python
def calc_variance(actual: float, budget: float) -> tuple[float, float | None]:
    """Return (absolute_variance, pct_variance). pct_variance is None if budget == 0."""

def classify_performance(
    actual: float,
    budget: float,
    direction: str,
    amber_band_pct: float = 5.0
) -> str:
    """
    Return 'green', 'amber', or 'red'.
    
    Logic
    -----
    - direction='higher_is_better': green if actual >= budget, amber if within band, red otherwise.
    - direction='lower_is_better': green if actual <= budget, amber if within band, red otherwise.
    """

def summarise_daily_to_monthly(df_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate fact_daily_plant to monthly grain.
    
    Rules
    -----
    - Tonnages: sum
    - Rates (tph): weighted average by running hours
    - Percentages (recovery, availability): mean
    - Ounces: sum
    """

def get_executive_summary(
    monthly_kpis: pd.DataFrame,
    target_month: str
) -> dict:
    """
    Return a dict suitable for the top-level dashboard cards.
    
    Structure
    ---------
    {
        "period": "2020-Q3",
        "crushing": {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
        "milling":  {"actual": ..., "budget": ..., "var_pct": ..., "rag": "amber"},
        "recovery": {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
        "mill_balls": {"actual": ..., "budget": ..., "var_pct": ..., "rag": "red", "trend": "increasing"},
        "water":     {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
        "cost":      {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
    }
    """
```

---

### 2.4  Dashboard-Ready Outputs

Without requiring any web framework, produce:

1. **Monthly management summary DataFrame** — one row per KPI for a selected period, columns: `kpi_name`, `actual`, `budget`, `variance`, `variance_pct`, `rag`, `comments`. Print `.to_markdown()` as a smoke test.

2. **Daily October 2021 DataFrame** (if the weekly Excel is available) — indexed by date, with actual/target/variance columns for crushing, milling, ounces, recovery.

3. **`get_manager_overview(selected_month)` function** — returns the executive summary dict above. This is the single entry point a Streamlit app would call to populate cards and sparklines.

---

## 3  Technical Requirements

### 3.1  Handling Messy Excel Structures

The Excel files exhibit multi-row headers, `Unnamed:` columns, embedded subtotals, and section-separator labels. Your ingestion code must:

- **Scan for the header row** rather than hard-coding a row index. Search for a row where at least two cells match a known signature set (e.g., `{"Actual", "Budget", "Var %"}` for the KPI file; `{"Projected Milled tonnage"}` for the mill-ball file).
- **Reconstruct composite column names** from multi-row headers by concatenating parent group and child label (e.g., `q3_actual`, `q3_budget`, `q3_var_pct`).
- **Drop non-data rows** — rows where the KPI/label column is `None`, or contains a known skip-value (`Tis`, `BMS external audits`, `Mille`, `Stock`).
- **Comment assumptions** inline so a future maintainer can adjust when a new file version shifts by one row.

### 3.2  Date Handling

- Excel serial numbers (e.g., `44075`) must be converted using the 1899-12-30 epoch.
- Native `datetime.datetime` objects must be cast to `pd.Timestamp`.
- All date columns in output DataFrames should be `datetime64[ns]` with timezone-naive UTC.

### 3.3  Extensibility Hooks

Include brief docstrings or comments at module level explaining:

- **How to swap Excel inputs for a database feed:** Replace loaders with SQL queries against a time-series database (e.g., InfluxDB or TimescaleDB) reading from belt weigh-sensor and DCS historian exports.
- **How to connect to Streamlit/Dash:** The `get_manager_overview()` function returns a plain dict; a Streamlit app would call it per selected period and render cards, trend charts (via Plotly), and a project status table.
- **How to add new KPIs:** Add a row to a `KPI_REGISTRY` dict mapping `kpi_name → {direction, unit, amber_band}`, then ensure the loader emits a row with that name.

### 3.4  Code Quality

- Type hints on all public functions.
- No global mutable state.
- Defensive `try/except` around file I/O with clear error messages.
- Use `logging` (not `print`) for diagnostics.
- Include a `if __name__ == "__main__":` block that runs the full pipeline end-to-end and prints `.head()` for each output table as a smoke test.

---

## 4  Suggested File Organisation

```
ngezi_dashboard/
├── __init__.py
├── config.py            # KPI_REGISTRY, file paths, constants
├── loaders/
│   ├── __init__.py
│   ├── kpi_scorecard.py  # load_kpi_scorecard()
│   ├── mill_ball.py      # load_mill_ball_trends()
│   ├── weekly_report.py  # load_weekly_excel(), load_projects_from_docx()
│   └── utils.py          # header detection, date normalisation, column renaming
├── models.py             # Pydantic / dataclass schemas (optional)
├── transforms.py         # Melt, pivot, merge into fact tables
├── kpis.py               # calc_variance, classify_performance, summarise_daily_to_monthly
├── dashboard.py          # get_manager_overview, get_executive_summary
└── main.py               # End-to-end pipeline, smoke-test prints
```

A single-file version is also acceptable for an initial prototype, provided the logical sections are clearly separated with section comments.

---

## 5  Acceptance Criteria

The code is considered complete when:

1. `python main.py` runs without errors against the provided files and prints a `fact_monthly_kpi` DataFrame with at least 10 KPI rows for the Q3 FY2020 period.
2. `get_manager_overview("2020-Q3")` returns a well-formed dict with RAG classifications for all six domains (crushing, milling, recovery, mill balls, water, cost).
3. The project status table extracted from the Word document contains all 12 project rows with parsed dates.
4. Mill-ball monthly time series (Sep 2020 → Feb 2021) is present in `fact_monthly_consumables` with actual and budget values.
5. All variance calculations are verified: a spot-check of `Crushed tonnage Q1 Var%` should yield approximately `−1.04%`, matching the source file.

---

## 6  Domain Reference

For context when naming columns and interpreting data:

| Term | Meaning |
|------|---------|
| **6E** | Six platinum-group elements: Pt, Pd, Rh, Ru, Ir, Os |
| **4E** | Pt, Pd, Rh, Au |
| **Grind −75 µm** | Percentage of milled product passing a 75-micron sieve — a measure of grinding fineness |
| **Mass pull** | Percentage of feed tonnage reporting to concentrate |
| **g/t** | Grams per tonne — standard unit for mill-ball consumption and metal grades |
| **m³/t** | Cubic metres of water per tonne of ore processed |
| **TSF** | Tailings Storage Facility |
| **FAZ** | Facility Assessment of Zimbabwe (weekly inspection checklist) |
| **FY20 Q3** | Zimplats fiscal year 2020, quarter 3 (typically Jan–Mar 2020) |
| **RAG** | Red / Amber / Green — traffic-light status classification |
| **DCS** | Distributed Control System — plant automation layer |
| **tph** | Tonnes per hour |
