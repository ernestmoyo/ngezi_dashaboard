"""
Dashboard-ready output functions.

These are the primary entry points for a Streamlit/Dash front end.
Each function returns plain dicts or DataFrames suitable for rendering
cards, charts, and tables.
"""

import logging

import pandas as pd

from .config import KPI_REGISTRY, PLANT_NAME
from .kpis import classify_performance, get_executive_summary

logger = logging.getLogger(__name__)


def get_manager_overview(
    monthly_kpis: pd.DataFrame,
    selected_period: str,
) -> dict:
    """Single entry point a Streamlit app would call to populate cards and sparklines.

    Parameters
    ----------
    monthly_kpis : fact_monthly_kpi DataFrame.
    selected_period : Period string (e.g. "2020-Q3").

    Returns
    -------
    Executive summary dict with RAG classifications for all six domains.
    """
    return get_executive_summary(monthly_kpis, selected_period)


def get_monthly_management_summary(
    monthly_kpis: pd.DataFrame,
    selected_period: str,
) -> pd.DataFrame:
    """Monthly management summary: one row per KPI for a selected period.

    Returns
    -------
    DataFrame with columns:
        kpi_name, actual, budget, variance, variance_pct, rag, comments
    """
    period_df = monthly_kpis[monthly_kpis["period"] == selected_period].copy()

    if period_df.empty:
        logger.warning("No data for period '%s'", selected_period)
        return pd.DataFrame(
            columns=["kpi_name", "actual", "budget", "variance", "variance_pct", "rag", "comments"]
        )

    # Add RAG classification
    rag_values = []
    for _, row in period_df.iterrows():
        kpi_name = row["kpi_name"]
        registry = KPI_REGISTRY.get(kpi_name, {})
        direction = registry.get("direction", row.get("direction", "higher_is_better"))
        amber_band = registry.get("amber_band", 5.0)

        actual = row.get("actual")
        budget = row.get("budget")

        if pd.notna(actual) and pd.notna(budget):
            rag = classify_performance(actual, budget, direction, amber_band)
        else:
            rag = "grey"
        rag_values.append(rag)

    period_df["rag"] = rag_values

    result = period_df[
        ["kpi_name", "actual", "budget", "variance", "variance_pct", "rag", "comments"]
    ].reset_index(drop=True)

    return result


def get_project_status_summary(
    dim_project: pd.DataFrame,
    fact_project_status: pd.DataFrame,
) -> pd.DataFrame:
    """Merged project status table for dashboard display.

    Returns
    -------
    DataFrame with columns:
        project_id, project_name, responsible, planned_completion,
        status, comments, snapshot_date
    """
    if dim_project.empty or fact_project_status.empty:
        return pd.DataFrame()

    merged = dim_project.merge(
        fact_project_status,
        on="project_id",
        how="left",
    )

    return merged


def get_available_periods(monthly_kpis: pd.DataFrame) -> list[str]:
    """Return sorted list of available period strings for UI dropdowns."""
    if monthly_kpis.empty:
        return []
    return sorted(monthly_kpis["period"].unique().tolist())


def get_consumables_summary(
    fact_consumables: pd.DataFrame,
    month: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Consumables summary for a given month.

    Parameters
    ----------
    fact_consumables : fact_monthly_consumables DataFrame.
    month : Filter to a specific month. If None, return all.

    Returns
    -------
    DataFrame with RAG classification added.
    """
    if fact_consumables.empty:
        return fact_consumables

    df = fact_consumables.copy()
    if month is not None:
        df = df[df["month"] == month]

    # All consumables are "lower_is_better" (want to consume less)
    rag_values = []
    for _, row in df.iterrows():
        actual = row.get("actual")
        budget = row.get("budget")
        if pd.notna(actual) and pd.notna(budget) and budget != 0:
            rag = classify_performance(actual, budget, "lower_is_better", 5.0)
        else:
            rag = "grey"
        rag_values.append(rag)

    df["rag"] = rag_values
    return df
