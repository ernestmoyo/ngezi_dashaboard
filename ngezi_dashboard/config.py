"""
Configuration: KPI registry, file paths, constants.

KPI_REGISTRY maps each canonical KPI name to its evaluation direction,
display unit, and amber-band tolerance (percentage points).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# File paths — adjust these if source files move
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent

KPI_SCORECARD_FILE = DATA_DIR / "KPIs - Q3 FY2020 (1) (002).xlsx"
MILL_BALL_FILE = DATA_DIR / "Copy of Mill ball trends rev (1).xlsx"
WEEKLY_DOCX_FILE = DATA_DIR / "October   2021 - Week 5r.docx"
WEEKLY_EXCEL_FILE = DATA_DIR / "October 2021 07.10.21.xlsx"

# ---------------------------------------------------------------------------
# Plant identity
# ---------------------------------------------------------------------------
PLANT_NAME = "Ngezi Concentrator"

# ---------------------------------------------------------------------------
# KPI Registry
# ---------------------------------------------------------------------------
# direction: "higher_is_better" or "lower_is_better"
# unit: display unit string
# amber_band: percentage-point tolerance for amber classification
KPI_REGISTRY: dict[str, dict] = {
    "crushed_tonnage": {
        "direction": "higher_is_better",
        "unit": "t",
        "amber_band": 5.0,
    },
    "milling_rate_tph": {
        "direction": "higher_is_better",
        "unit": "tph",
        "amber_band": 5.0,
    },
    "milled_tonnage": {
        "direction": "higher_is_better",
        "unit": "t",
        "amber_band": 5.0,
    },
    "grind_pct_minus75": {
        "direction": "higher_is_better",
        "unit": "%",
        "amber_band": 3.0,
    },
    "plant_running_time_pct": {
        "direction": "higher_is_better",
        "unit": "%",
        "amber_band": 3.0,
    },
    "mass_pull_pct": {
        "direction": "higher_is_better",
        "unit": "%",
        "amber_band": 3.0,
    },
    "recovery_6e_pct": {
        "direction": "higher_is_better",
        "unit": "%",
        "amber_band": 2.0,
    },
    "mill_ball_consumption_gt": {
        "direction": "lower_is_better",
        "unit": "g/t",
        "amber_band": 5.0,
    },
    "filter_cake_moisture_pct": {
        "direction": "lower_is_better",
        "unit": "%",
        "amber_band": 3.0,
    },
    "metal_unaccounted_for_pct": {
        "direction": "lower_is_better",
        "unit": "%",
        "amber_band": 3.0,
    },
    "raw_water_m3t": {
        "direction": "lower_is_better",
        "unit": "m3/t",
        "amber_band": 5.0,
    },
    "total_cost": {
        "direction": "lower_is_better",
        "unit": "USD",
        "amber_band": 5.0,
    },
}

# Mapping from raw KPI labels (column B in scorecard) to canonical names
KPI_LABEL_MAP: dict[str, str] = {
    "Crushed tonnage": "crushed_tonnage",
    "Milling rate t/h": "milling_rate_tph",
    "Milled tonnage": "milled_tonnage",
    "Grind (%-75 microns)": "grind_pct_minus75",
    "Plant running time %": "plant_running_time_pct",
    "Mass pull (%)": "mass_pull_pct",
    "6E Recovery (%)": "recovery_6e_pct",
    "Mill Ball consumption g/t": "mill_ball_consumption_gt",
    "Filter cake moisture (%)": "filter_cake_moisture_pct",
    "Metal Unaccounted For (%)": "metal_unaccounted_for_pct",
    "Raw water consumption (m3/t)": "raw_water_m3t",
    "Total Cost": "total_cost",
}

# KPI labels to skip (safety/audit rows, not plant analytics)
KPI_SKIP_LABELS = {"Tis", "BMS external audits"}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TROY_OZ_PER_GRAM = 31.10348
EXCEL_EPOCH = "1899-12-30"
