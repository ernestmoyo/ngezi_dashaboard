"""
Data transforms: melt, pivot, and merge raw loader outputs into
star-schema fact and dimension tables.
"""

import logging

import pandas as pd

from .config import (
    KPI_LABEL_MAP,
    KPI_REGISTRY,
    PLANT_NAME,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mapping from KPI scorecard period prefixes to approximate months
# ---------------------------------------------------------------------------
_PERIOD_TO_MONTHS = {
    "q1": [
        pd.Timestamp("2019-07-01"),
        pd.Timestamp("2019-08-01"),
        pd.Timestamp("2019-09-01"),
    ],
    "q2_ytd": None,  # cumulative — skip for monthly grain
    "aug": [pd.Timestamp("2020-08-01")],
    "q3": None,  # cumulative — represented as quarter
    "fy20_ytd": None,  # cumulative
}

# For KPI scorecard, we store Q1, Aug, Q3, FY20_YTD as period labels
# rather than individual months, since the scorecard is quarterly.
_PERIOD_LABELS = {
    "q1": "2020-Q1",
    "q2_ytd": "2020-Q2-YTD",
    "aug": "2020-08",
    "q3": "2020-Q3",
    "fy20_ytd": "FY2020-YTD",
}


def build_fact_monthly_kpi(kpi_scorecard_df: pd.DataFrame) -> pd.DataFrame:
    """Melt the wide KPI scorecard into a long fact table.

    Parameters
    ----------
    kpi_scorecard_df : Wide-format DataFrame from load_kpi_scorecard().

    Returns
    -------
    fact_monthly_kpi DataFrame with columns:
        period, plant, kpi_name, actual, budget, variance, variance_pct,
        direction, comments
    """
    rows = []

    for _, kpi_row in kpi_scorecard_df.iterrows():
        raw_label = kpi_row["kpi"]
        kpi_name = KPI_LABEL_MAP.get(raw_label, raw_label)
        registry = KPI_REGISTRY.get(kpi_name, {})
        direction = registry.get("direction", "higher_is_better")
        comments = kpi_row.get("comments")

        for prefix, period_label in _PERIOD_LABELS.items():
            actual_col = f"{prefix}_actual"
            budget_col = f"{prefix}_budget"
            var_col = f"{prefix}_var_pct"

            actual = kpi_row.get(actual_col)
            budget = kpi_row.get(budget_col)
            var_pct = kpi_row.get(var_col)

            # Skip if both actual and budget are missing
            if pd.isna(actual) and pd.isna(budget):
                continue

            # Compute variance
            variance = None
            if pd.notna(actual) and pd.notna(budget):
                variance = actual - budget

            rows.append({
                "period": period_label,
                "plant": PLANT_NAME,
                "kpi_name": kpi_name,
                "actual": actual,
                "budget": budget,
                "variance": variance,
                "variance_pct": var_pct,
                "direction": direction,
                "comments": comments,
            })

    df = pd.DataFrame(rows)
    logger.info("Built fact_monthly_kpi with %d rows", len(df))
    return df


def build_fact_monthly_consumables(
    mill_ball_df: pd.DataFrame,
    weekly_consumables_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build monthly consumables fact table.

    Merges mill-ball consumption from the trend file with reagent/water
    data from the weekly report.

    Parameters
    ----------
    mill_ball_df : From load_mill_ball_trends().
    weekly_consumables_df : From load_weekly_consumables() (optional).

    Returns
    -------
    fact_monthly_consumables DataFrame with columns:
        month, plant, consumable, actual, budget, variance, variance_pct
    """
    rows = []

    # Steel balls from mill-ball trends
    # mill1_consumption_gt = budget rate (g/t); mill1_steel_t = actual steel used (tonnes)
    # projected_milled_tonnage = the tonnage basis for the projection
    if not mill_ball_df.empty:
        for _, row in mill_ball_df.iterrows():
            month = row.get("month")
            actual_steel_t = row.get("mill1_steel_t")  # actual steel consumed (tonnes)
            budget_rate = row.get("mill1_consumption_gt")  # budget consumption rate (g/t)
            tonnage = row.get("projected_milled_tonnage")

            # Budget steel usage = budget_rate * tonnage / 1_000_000
            budget_steel_t = None
            if pd.notna(budget_rate) and pd.notna(tonnage) and tonnage > 0:
                budget_steel_t = budget_rate * tonnage / 1_000_000

            variance = None
            variance_pct = None
            if pd.notna(actual_steel_t) and pd.notna(budget_steel_t) and budget_steel_t != 0:
                variance = actual_steel_t - budget_steel_t
                variance_pct = (variance / budget_steel_t) * 100

            rows.append({
                "month": month,
                "plant": PLANT_NAME,
                "consumable": "steel_balls",
                "actual": actual_steel_t,
                "budget": budget_steel_t,
                "variance": variance,
                "variance_pct": variance_pct,
            })

    # Reagents and water from weekly report
    if weekly_consumables_df is not None and not weekly_consumables_df.empty:
        # The weekly report gives current-period consumables, not monthly series.
        # We tag them with a generic period.
        for _, row in weekly_consumables_df.iterrows():
            actual = row.get("actual")
            budget = row.get("budget")
            variance = row.get("var")
            var_pct = row.get("var_pct")

            rows.append({
                "month": pd.Timestamp("2021-10-01"),  # October 2021 report
                "plant": PLANT_NAME,
                "consumable": row.get("consumable", "unknown"),
                "actual": actual,
                "budget": budget,
                "variance": variance,
                "variance_pct": var_pct,
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["month"] = pd.to_datetime(df["month"])

    logger.info("Built fact_monthly_consumables with %d rows", len(df))
    return df


def build_dim_project(projects_df: pd.DataFrame) -> pd.DataFrame:
    """Build project dimension table from Word document projects.

    Returns
    -------
    dim_project DataFrame with columns:
        project_id, project_name, responsible, planned_completion
    """
    if projects_df.empty:
        return pd.DataFrame(
            columns=["project_id", "project_name", "responsible", "planned_completion"]
        )

    dim = projects_df[["project_id", "project_name", "responsible", "planned_completion"]].copy()
    logger.info("Built dim_project with %d rows", len(dim))
    return dim


def build_fact_project_status(
    projects_df: pd.DataFrame,
    snapshot_date: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build project status fact table.

    Each ingestion of a weekly report appends rows with the snapshot_date,
    enabling status-over-time tracking for Gantt/timeline widgets.

    Parameters
    ----------
    projects_df : From load_projects_from_docx().
    snapshot_date : Date of the report. Defaults to 2021-11-05 (Week 5 Oct 2021).

    Returns
    -------
    fact_project_status DataFrame with columns:
        snapshot_date, project_id, status, comments
    """
    if snapshot_date is None:
        snapshot_date = pd.Timestamp("2021-11-05")

    if projects_df.empty:
        return pd.DataFrame(
            columns=["snapshot_date", "project_id", "status", "comments"]
        )

    fact = projects_df[["project_id", "status", "comments"]].copy()
    fact.insert(0, "snapshot_date", snapshot_date)

    logger.info("Built fact_project_status with %d rows", len(fact))
    return fact


def build_fact_daily_plant(daily_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build daily plant fact table from DATA (2) sheet.

    Parameters
    ----------
    daily_df : From load_daily_data(). If None or empty, returns an empty
               DataFrame with the correct schema.

    Returns
    -------
    fact_daily_plant DataFrame with columns:
        date, plant, crushed_tonnage_actual, crushed_tonnage_target,
        milled_tonnage_actual, milled_tonnage_target, milling_rate_tph_actual,
        recovery_pct_actual, recovery_pct_target, oz_produced_actual,
        oz_produced_target, crusher_availability_pct, mill_availability_pct
    """
    schema_cols = [
        "date", "plant",
        "crushed_tonnage_actual", "crushed_tonnage_target",
        "milled_tonnage_actual", "milled_tonnage_target",
        "milling_rate_tph_actual",
        "recovery_pct_actual", "recovery_pct_target",
        "oz_produced_actual", "oz_produced_target",
        "crusher_availability_pct", "mill_availability_pct",
    ]

    if daily_df is None or daily_df.empty:
        logger.warning(
            "No daily data available. Returning empty fact_daily_plant with schema."
        )
        return pd.DataFrame(columns=schema_cols)

    # Map available columns from DATA (2) to the target schema.
    # DATA (2) has: date, daily_actual, daily_target, mtd_actual, mtd_target, mtd_var_pct
    # daily_actual/target represent milled tonnage.
    result = pd.DataFrame({
        "date": daily_df["date"],
        "plant": PLANT_NAME,
        "crushed_tonnage_actual": None,
        "crushed_tonnage_target": None,
        "milled_tonnage_actual": daily_df.get("daily_actual"),
        "milled_tonnage_target": daily_df.get("daily_target"),
        "milling_rate_tph_actual": None,
        "recovery_pct_actual": None,
        "recovery_pct_target": None,
        "oz_produced_actual": None,
        "oz_produced_target": None,
        "crusher_availability_pct": None,
        "mill_availability_pct": None,
    })

    logger.info("Built fact_daily_plant with %d rows", len(result))
    return result
