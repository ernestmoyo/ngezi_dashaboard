"""
KPI computation functions — pure functions with no side effects.

Provides variance calculation, RAG classification, daily-to-monthly
aggregation, and executive summary generation.
"""

import logging

import pandas as pd

from .config import KPI_REGISTRY

logger = logging.getLogger(__name__)


def calc_variance(actual: float, budget: float) -> tuple[float, float | None]:
    """Return (absolute_variance, pct_variance).

    pct_variance is None if budget == 0.
    """
    absolute = actual - budget
    if budget == 0:
        return absolute, None
    pct = (absolute / budget) * 100
    return absolute, pct


def classify_performance(
    actual: float,
    budget: float,
    direction: str,
    amber_band_pct: float = 5.0,
) -> str:
    """Return 'green', 'amber', or 'red' RAG classification.

    Logic
    -----
    - direction='higher_is_better':
        green  if actual >= budget
        amber  if actual >= budget * (1 - amber_band_pct/100)
        red    otherwise

    - direction='lower_is_better':
        green  if actual <= budget
        amber  if actual <= budget * (1 + amber_band_pct/100)
        red    otherwise
    """
    if pd.isna(actual) or pd.isna(budget):
        return "grey"

    if budget == 0:
        return "grey"

    if direction == "higher_is_better":
        if actual >= budget:
            return "green"
        threshold = budget * (1 - amber_band_pct / 100)
        if actual >= threshold:
            return "amber"
        return "red"
    else:  # lower_is_better
        if actual <= budget:
            return "green"
        threshold = budget * (1 + amber_band_pct / 100)
        if actual <= threshold:
            return "amber"
        return "red"


def summarise_daily_to_monthly(df_daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fact_daily_plant to monthly grain.

    Rules
    -----
    - Tonnages: sum
    - Rates (tph): mean (proxy for weighted average when running hours unavailable)
    - Percentages (recovery, availability): mean
    - Ounces: sum

    Parameters
    ----------
    df_daily : fact_daily_plant DataFrame with a 'date' column.

    Returns
    -------
    Monthly aggregated DataFrame indexed by month.
    """
    if df_daily.empty:
        logger.warning("Empty daily DataFrame — returning empty monthly summary")
        return pd.DataFrame()

    df = df_daily.copy()
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    sum_cols = [
        "crushed_tonnage_actual", "crushed_tonnage_target",
        "milled_tonnage_actual", "milled_tonnage_target",
        "oz_produced_actual", "oz_produced_target",
    ]
    mean_cols = [
        "milling_rate_tph_actual",
        "recovery_pct_actual", "recovery_pct_target",
        "crusher_availability_pct", "mill_availability_pct",
    ]

    # Filter to columns that actually exist and have data
    available_sum = [c for c in sum_cols if c in df.columns]
    available_mean = [c for c in mean_cols if c in df.columns]

    agg_dict = {}
    for col in available_sum:
        agg_dict[col] = "sum"
    for col in available_mean:
        agg_dict[col] = "mean"

    if not agg_dict:
        return pd.DataFrame()

    result = df.groupby("month").agg(agg_dict).reset_index()
    result.insert(1, "plant", df["plant"].iloc[0] if "plant" in df.columns else "Ngezi Concentrator")

    logger.info("Summarised daily data to %d monthly rows", len(result))
    return result


def get_executive_summary(
    monthly_kpis: pd.DataFrame,
    target_period: str,
) -> dict:
    """Return a dict suitable for top-level dashboard cards.

    Parameters
    ----------
    monthly_kpis : fact_monthly_kpi DataFrame.
    target_period : Period string to filter on (e.g. "2020-Q3").

    Returns
    -------
    Dict with structure:
    {
        "period": "2020-Q3",
        "crushing": {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
        "milling":  {"actual": ..., "budget": ..., "var_pct": ..., "rag": "amber"},
        "recovery": {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
        "mill_balls": {"actual": ..., "budget": ..., "var_pct": ..., "rag": "red"},
        "water":     {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
        "cost":      {"actual": ..., "budget": ..., "var_pct": ..., "rag": "green"},
    }
    """
    # KPI name -> dashboard domain mapping
    domain_map = {
        "crushed_tonnage": "crushing",
        "milled_tonnage": "milling",
        "recovery_6e_pct": "recovery",
        "mill_ball_consumption_gt": "mill_balls",
        "raw_water_m3t": "water",
        "total_cost": "cost",
    }

    period_df = monthly_kpis[monthly_kpis["period"] == target_period]

    summary: dict = {"period": target_period}

    for kpi_name, domain in domain_map.items():
        kpi_rows = period_df[period_df["kpi_name"] == kpi_name]

        if kpi_rows.empty:
            summary[domain] = {
                "actual": None,
                "budget": None,
                "var_pct": None,
                "rag": "grey",
            }
            continue

        row = kpi_rows.iloc[0]
        actual = row.get("actual")
        budget = row.get("budget")
        var_pct = row.get("variance_pct")
        direction = row.get("direction", "higher_is_better")

        registry = KPI_REGISTRY.get(kpi_name, {})
        amber_band = registry.get("amber_band", 5.0)

        rag = "grey"
        if pd.notna(actual) and pd.notna(budget):
            rag = classify_performance(actual, budget, direction, amber_band)

        summary[domain] = {
            "actual": actual if pd.notna(actual) else None,
            "budget": budget if pd.notna(budget) else None,
            "var_pct": var_pct if pd.notna(var_pct) else None,
            "rag": rag,
        }

    return summary
