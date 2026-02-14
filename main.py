"""
Ngezi Concentrator — End-to-end analytics pipeline.

Runs the full data pipeline from source files to dashboard-ready outputs
and prints smoke-test summaries.

Usage:
    python main.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngezi_dashboard.config import (
    KPI_SCORECARD_FILE,
    MILL_BALL_FILE,
    WEEKLY_DOCX_FILE,
    WEEKLY_EXCEL_FILE,
)
from ngezi_dashboard.loaders import (
    load_kpi_scorecard,
    load_mill_ball_trends,
    load_projects_from_docx,
    load_weekly_consumables,
    load_daily_data,
)
from ngezi_dashboard.transforms import (
    build_fact_monthly_kpi,
    build_fact_monthly_consumables,
    build_dim_project,
    build_fact_project_status,
    build_fact_daily_plant,
)
from ngezi_dashboard.kpis import get_executive_summary
from ngezi_dashboard.dashboard import (
    get_manager_overview,
    get_monthly_management_summary,
    get_project_status_summary,
    get_available_periods,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the full analytics pipeline and print smoke-test outputs."""

    print("=" * 70)
    print("  NGEZI CONCENTRATOR — Mine Manager Oversight Dashboard")
    print("  Analytics Pipeline Smoke Test")
    print("=" * 70)
    print()

    # ------------------------------------------------------------------
    # 1. Load source data
    # ------------------------------------------------------------------
    print("[ 1 ] LOADING SOURCE DATA")
    print("-" * 40)

    # KPI Scorecard
    kpi_scorecard = load_kpi_scorecard(str(KPI_SCORECARD_FILE))
    print(f"\nKPI Scorecard: {len(kpi_scorecard)} rows loaded")
    print(kpi_scorecard[["kpi", "q3_actual", "q3_budget", "q3_var_pct"]].to_string(index=False))

    # Mill Ball Trends
    mill_ball = load_mill_ball_trends(str(MILL_BALL_FILE))
    print(f"\nMill Ball Trends: {len(mill_ball)} rows loaded")
    if not mill_ball.empty:
        print(mill_ball.head().to_string(index=False))

    # Weekly Report — Projects from Word doc
    projects = load_projects_from_docx(str(WEEKLY_DOCX_FILE))
    print(f"\nProjects (from Word doc): {len(projects)} rows loaded")
    if not projects.empty:
        print(projects[["project_id", "project_name", "status"]].to_string(index=False))

    # Weekly Report — Consumables
    weekly_consumables = None
    try:
        weekly_consumables = load_weekly_consumables(str(WEEKLY_EXCEL_FILE))
        print(f"\nWeekly Consumables: {len(weekly_consumables)} rows loaded")
        if not weekly_consumables.empty:
            print(weekly_consumables.head().to_string(index=False))
    except Exception as e:
        logger.warning("Could not load weekly consumables: %s", e)

    # Weekly Report — Daily data
    daily_data = None
    try:
        daily_data = load_daily_data(str(WEEKLY_EXCEL_FILE))
        print(f"\nDaily Data (Oct 2021): {len(daily_data)} rows loaded")
        if not daily_data.empty:
            print(daily_data.head().to_string(index=False))
    except Exception as e:
        logger.warning("Could not load daily data: %s", e)

    # ------------------------------------------------------------------
    # 2. Build fact & dimension tables
    # ------------------------------------------------------------------
    print("\n")
    print("[ 2 ] BUILDING FACT & DIMENSION TABLES")
    print("-" * 40)

    # fact_monthly_kpi
    fact_kpi = build_fact_monthly_kpi(kpi_scorecard)
    print(f"\nfact_monthly_kpi: {len(fact_kpi)} rows")
    print(fact_kpi.head(15).to_string(index=False))

    # fact_monthly_consumables
    fact_consumables = build_fact_monthly_consumables(mill_ball, weekly_consumables)
    print(f"\nfact_monthly_consumables: {len(fact_consumables)} rows")
    if not fact_consumables.empty:
        print(fact_consumables.head(10).to_string(index=False))

    # dim_project + fact_project_status
    dim_project = build_dim_project(projects)
    fact_project = build_fact_project_status(projects)
    print(f"\ndim_project: {len(dim_project)} rows")
    if not dim_project.empty:
        print(dim_project.to_string(index=False))
    print(f"\nfact_project_status: {len(fact_project)} rows")
    if not fact_project.empty:
        print(fact_project[["snapshot_date", "project_id", "status"]].to_string(index=False))

    # fact_daily_plant
    fact_daily = build_fact_daily_plant(daily_data)
    print(f"\nfact_daily_plant: {len(fact_daily)} rows")
    if not fact_daily.empty:
        cols_to_show = ["date", "milled_tonnage_actual", "milled_tonnage_target"]
        available = [c for c in cols_to_show if c in fact_daily.columns]
        print(fact_daily[available].head(10).to_string(index=False))

    # ------------------------------------------------------------------
    # 3. Dashboard outputs
    # ------------------------------------------------------------------
    print("\n")
    print("[ 3 ] DASHBOARD OUTPUTS")
    print("-" * 40)

    # Available periods
    periods = get_available_periods(fact_kpi)
    print(f"\nAvailable periods: {periods}")

    # Monthly management summary for Q3
    target_period = "2020-Q3"
    print(f"\nMonthly Management Summary — {target_period}:")
    mgmt_summary = get_monthly_management_summary(fact_kpi, target_period)
    if not mgmt_summary.empty:
        print(mgmt_summary.to_string(index=False))

    # Executive summary / Manager overview
    print(f"\nExecutive Summary — {target_period}:")
    overview = get_manager_overview(fact_kpi, target_period)
    for domain, metrics in overview.items():
        if domain == "period":
            print(f"  Period: {metrics}")
        else:
            print(f"  {domain:12s} | {metrics}")

    # Project status
    print("\nProject Status Summary:")
    project_summary = get_project_status_summary(dim_project, fact_project)
    if not project_summary.empty:
        print(project_summary[
            ["project_id", "project_name", "status", "planned_completion"]
        ].to_string(index=False))

    # ------------------------------------------------------------------
    # 4. Acceptance criteria verification
    # ------------------------------------------------------------------
    print("\n")
    print("[ 4 ] ACCEPTANCE CRITERIA CHECKS")
    print("-" * 40)

    # Check 1: fact_monthly_kpi has >= 10 rows for Q3
    q3_rows = fact_kpi[fact_kpi["period"] == "2020-Q3"]
    check1 = len(q3_rows) >= 10
    print(f"\n  [{'PASS' if check1 else 'FAIL'}] Q3 FY2020 has {len(q3_rows)} KPI rows (need >= 10)")

    # Check 2: get_manager_overview returns well-formed dict
    check2_domains = {"crushing", "milling", "recovery", "mill_balls", "water", "cost"}
    check2 = check2_domains.issubset(set(overview.keys()))
    print(f"  [{'PASS' if check2 else 'FAIL'}] Manager overview has all 6 domains: {check2_domains & set(overview.keys())}")

    # Check 3: Project status table has all 12 rows
    check3 = len(projects) >= 12
    print(f"  [{'PASS' if check3 else 'FAIL'}] Project table has {len(projects)} rows (need >= 12)")

    # Check 4: Mill-ball monthly time series present
    steel_rows = fact_consumables[fact_consumables["consumable"] == "steel_balls"] if not fact_consumables.empty else pd.DataFrame()
    check4 = len(steel_rows) >= 4
    print(f"  [{'PASS' if check4 else 'FAIL'}] Steel balls has {len(steel_rows)} monthly rows")

    # Check 5: Spot-check variance — Crushed tonnage Q1 Var% ~ -1.04%
    crushed_q1 = fact_kpi[
        (fact_kpi["kpi_name"] == "crushed_tonnage") & (fact_kpi["period"] == "2020-Q1")
    ]
    if not crushed_q1.empty:
        var_pct = crushed_q1.iloc[0]["variance_pct"]
        check5 = var_pct is not None and abs(var_pct - (-1.04)) < 1.0
        print(f"  [{'PASS' if check5 else 'FAIL'}] Crushed tonnage Q1 Var% = {var_pct:.2f}% (expect ~ -1.04%)")
    else:
        print(f"  [INFO] Crushed tonnage Q1 data not available (may be formula-dependent)")

    print("\n" + "=" * 70)
    print("  Pipeline complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
