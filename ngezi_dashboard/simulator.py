"""
Simulated data generator for the Ngezi Concentrator dashboard.

Generates realistic production data based on typical Ngezi plant parameters.
All values are synthetic — no real operational data is used.
"""

import numpy as np
import pandas as pd

from .config import KPI_REGISTRY, PLANT_NAME

# Seed for reproducibility
_RNG = np.random.default_rng(42)

# ---------------------------------------------------------------------------
# Typical plant parameters (realistic ranges)
# ---------------------------------------------------------------------------
_MONTHLY_PARAMS = {
    "crushed_tonnage": {"budget": 125_000, "std": 3_000, "bias": 1.02},
    "milling_rate_tph": {"budget": 520, "std": 8, "bias": 1.01},
    "milled_tonnage": {"budget": 124_000, "std": 3_500, "bias": 1.02},
    "grind_pct_minus75": {"budget": 78, "std": 1.5, "bias": 0.98},
    "plant_running_time_pct": {"budget": 97, "std": 0.8, "bias": 1.01},
    "mass_pull_pct": {"budget": 2.1, "std": 0.08, "bias": 0.99},
    "recovery_6e_pct": {"budget": 79, "std": 0.6, "bias": 1.005},
    "mill_ball_consumption_gt": {"budget": 540, "std": 25, "bias": 1.08},
    "filter_cake_moisture_pct": {"budget": 13.5, "std": 0.5, "bias": 0.95},
    "metal_unaccounted_for_pct": {"budget": 2.0, "std": 0.4, "bias": 0.6},
    "raw_water_m3t": {"budget": 1.0, "std": 0.04, "bias": 0.95},
    "total_cost": {"budget": 9.8, "std": 0.3, "bias": 0.98},
}

_PROJECTS = [
    ("a", "Portal sealing — Phase 2", "AS", "2025-12-15", "completed", "Sealed and inspected successfully"),
    ("b", "TSF wall stability assessment", "AS", "2026-01-20", "completed", "Geotechnical report submitted"),
    ("c", "Seismic monitoring upgrade", "AS", "2026-02-28", "in_progress", "Sensors 60% installed, calibration ongoing"),
    ("d", "Piezocone testing — annual review", "AS", "2026-03-15", "in_progress", "Third-party audit scheduled for March"),
    ("e", "Drainage system expansion — MTSF", "AS", "2026-04-30", "in_progress", "Trenching 40% complete, awaiting pipe delivery"),
    ("f", "Collector dosage optimisation trial", "TM", "2026-01-31", "completed", "Reduced collector by 8% with stable recovery"),
    ("g", "Reagent suite cost reduction", "TM", "2026-03-31", "in_progress", "Alternative depressant trial in Week 3"),
    ("h", "Mill 2 mega liner installation", "AS", "2025-11-30", "completed", "All liners installed, mill restarted 28 Nov"),
    ("i", "Return water dam lining repair", "AS", "2026-05-30", "pending", "Awaiting contractor mobilisation"),
    ("j", "Curtain drain — Phase 3 extension", "AS", "2026-02-15", "in_progress", "70% trenching complete"),
    ("k", "Jetrodding programme — Q1", "AS", "2026-03-30", "pending", "Scheduled for mid-March start"),
    ("l", "Bench drain design — south wall", "AS", "2026-04-15", "in_progress", "Design review with SRK complete, construction pending"),
]

_CONSUMABLES = [
    ("Collector (Chemcol 2015i)", "reagent", 265, 270),
    ("Activator (CuSO4)", "reagent", 4.8, 5.0),
    ("Depressant (Finnfix)", "reagent", 39, 42),
    ("Depressant (Depramin 170)", "reagent", 12.5, 15.0),
    ("NaSH", "reagent", 8.2, 10.0),
    ("Frother (Sasfroth)", "reagent", 48, 50),
    ("Dowfroth", "reagent", 6.5, 8.0),
    ("Anionic Floc (3110)", "reagent", 3.2, 4.0),
    ("Coagulant (CQ50)", "reagent", 1.8, 2.5),
    ("Steel Balls", "reagent", 558, 540),
    ("Raw water", "water", 0.92, 1.0),
    ("Recycled water", "water", 0.45, 0.50),
    ("Total water", "water", 1.37, 1.50),
]

_SUPPLIERS = [
    ("Vega", "70mm steelballs", 1000, 380),
    ("Maggotteaux", "60mm steelballs", 900, 320),
    ("Anhui", "70mm steelballs", 1000, 1450),
    ("Frusina", "60mm steelballs", 900, 440),
]


def generate_monthly_kpis(
    start_month: str = "2025-07-01",
    n_months: int = 8,
) -> pd.DataFrame:
    """Generate simulated monthly KPI data.

    Produces n_months of data starting from start_month, with realistic
    variance around budget values.
    """
    months = pd.date_range(start_month, periods=n_months, freq="MS")
    rows = []

    for month in months:
        for kpi_name, params in _MONTHLY_PARAMS.items():
            budget = params["budget"]
            actual = budget * params["bias"] + _RNG.normal(0, params["std"])
            actual = round(actual, 2)

            registry = KPI_REGISTRY.get(kpi_name, {})
            direction = registry.get("direction", "higher_is_better")

            variance = actual - budget
            var_pct = (variance / budget * 100) if budget != 0 else None

            rows.append({
                "period": month.strftime("%Y-%m"),
                "month": month,
                "plant": PLANT_NAME,
                "kpi_name": kpi_name,
                "actual": actual,
                "budget": budget,
                "variance": round(variance, 2),
                "variance_pct": round(var_pct, 2) if var_pct else None,
                "direction": direction,
                "comments": None,
            })

    return pd.DataFrame(rows)


def generate_quarterly_kpis() -> pd.DataFrame:
    """Generate simulated quarterly KPI summary for the current fiscal year."""
    quarters = {
        "FY2026-Q1": ("2025-07-01", 3),
        "FY2026-Q2": ("2025-10-01", 3),
        "FY2026-Q3-MTD": ("2026-01-01", 2),  # current quarter, 2 months in
    }

    monthly = generate_monthly_kpis("2025-07-01", 8)
    rows = []

    for q_label, (start, n) in quarters.items():
        start_ts = pd.Timestamp(start)
        end_ts = start_ts + pd.DateOffset(months=n)
        q_data = monthly[(monthly["month"] >= start_ts) & (monthly["month"] < end_ts)]

        for kpi_name in _MONTHLY_PARAMS:
            kpi_data = q_data[q_data["kpi_name"] == kpi_name]
            if kpi_data.empty:
                continue

            registry = KPI_REGISTRY.get(kpi_name, {})
            direction = registry.get("direction", "higher_is_better")

            # Tonnages sum, rates/percentages average
            if kpi_name in ("crushed_tonnage", "milled_tonnage", "total_cost"):
                actual = kpi_data["actual"].sum()
                budget = kpi_data["budget"].sum()
            else:
                actual = kpi_data["actual"].mean()
                budget = kpi_data["budget"].mean()

            variance = actual - budget
            var_pct = (variance / budget * 100) if budget != 0 else None

            rows.append({
                "period": q_label,
                "plant": PLANT_NAME,
                "kpi_name": kpi_name,
                "actual": round(actual, 2),
                "budget": round(budget, 2),
                "variance": round(variance, 2),
                "variance_pct": round(var_pct, 2) if var_pct else None,
                "direction": direction,
                "comments": None,
            })

    return pd.DataFrame(rows)


def generate_daily_production(
    year: int = 2026,
    month: int = 2,
    days: int = 14,
) -> pd.DataFrame:
    """Generate simulated daily milled tonnage for the current month."""
    dates = pd.date_range(f"{year}-{month:02d}-01", periods=days, freq="D")
    daily_target = 11_650  # ~362k/month / 31 days

    rows = []
    cum_actual = 0
    cum_target = 0

    for date in dates:
        # Weekdays tend to have higher throughput
        is_weekend = date.dayofweek >= 5
        base = daily_target * (0.85 if is_weekend else 1.02)
        actual = base + _RNG.normal(0, 600)
        actual = max(actual, 7000)  # floor for shutdowns

        cum_actual += actual
        cum_target += daily_target

        rows.append({
            "date": date,
            "plant": PLANT_NAME,
            "milled_tonnage_actual": round(actual, 1),
            "milled_tonnage_target": daily_target,
            "crushed_tonnage_actual": round(actual * _RNG.uniform(0.98, 1.04), 1),
            "crushed_tonnage_target": round(daily_target * 1.01, 1),
            "milling_rate_tph_actual": round(520 + _RNG.normal(0, 12), 1),
            "recovery_pct_actual": round(79 + _RNG.normal(0, 0.8), 2),
            "recovery_pct_target": 79.0,
            "oz_produced_actual": round(actual * 3.45 / 31.1035 * (79 / 100), 1),
            "oz_produced_target": round(daily_target * 3.45 / 31.1035 * (79 / 100), 1),
            "crusher_availability_pct": round(95 + _RNG.uniform(0, 4), 1),
            "mill_availability_pct": round(94 + _RNG.uniform(0, 5), 1),
            "cum_actual": round(cum_actual, 1),
            "cum_target": round(cum_target, 1),
        })

    return pd.DataFrame(rows)


def generate_projects() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate simulated project dimension and status tables."""
    dim_rows = []
    status_rows = []
    snapshot_date = pd.Timestamp("2026-02-14")

    for pid, name, resp, completion, status, comment in _PROJECTS:
        dim_rows.append({
            "project_id": pid,
            "project_name": name,
            "responsible": resp,
            "planned_completion": pd.Timestamp(completion),
        })
        status_rows.append({
            "snapshot_date": snapshot_date,
            "project_id": pid,
            "status": status,
            "comments": comment,
        })

    return pd.DataFrame(dim_rows), pd.DataFrame(status_rows)


def generate_consumables() -> pd.DataFrame:
    """Generate simulated consumables data for the current period."""
    rows = []
    for name, category, actual_base, budget in _CONSUMABLES:
        actual = actual_base + _RNG.normal(0, actual_base * 0.03)
        actual = round(actual, 2)
        variance = round(actual - budget, 2)
        var_pct = round((variance / budget) * 100, 2) if budget != 0 else None

        rows.append({
            "category": category,
            "consumable": name,
            "actual": actual,
            "budget": budget,
            "var": variance,
            "var_pct": var_pct,
        })

    return pd.DataFrame(rows)


def generate_mill_ball_forecast(
    start_month: str = "2025-09-01",
    n_months: int = 10,
    starting_stock: float = 1200,
    consumption_gt: float = 600,
    projected_tonnage: float = 185_000,
    growth_rate: float = 1.01,
) -> pd.DataFrame:
    """Generate simulated mill ball stock depletion forecast."""
    months = pd.date_range(start_month, periods=n_months, freq="MS")
    rows = []
    stock = starting_stock

    for i, month in enumerate(months):
        tonnage = projected_tonnage * (growth_rate ** i)
        steel_used = consumption_gt * tonnage / 1_000_000
        stock -= steel_used

        rows.append({
            "month": month,
            "projected_milled_tonnage": round(tonnage, 0),
            "mill1_consumption_gt": consumption_gt,
            "mill1_steel_t": round(steel_used, 1),
            "mill1_stock_remaining": round(max(stock, 0), 1),
        })

    return pd.DataFrame(rows)


def generate_grind_trend(n_weeks: int = 36) -> pd.DataFrame:
    """Generate weekly grind and milling rate trend data."""
    months = [
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        "Jan", "Feb",
    ]
    rows = []
    week_counter = 0

    for month in months:
        for week in range(1, 6):
            if week_counter >= n_weeks:
                break
            grind = round(74 + _RNG.normal(0, 1.5), 2)
            rate = round(520 + _RNG.normal(0, 15), 1)
            rows.append({
                "month": month,
                "week": f"Week {week}",
                "grind_pct": grind,
                "milling_rate_tph": rate,
            })
            week_counter += 1

    return pd.DataFrame(rows)
