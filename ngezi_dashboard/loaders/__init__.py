"""Data ingestion loaders for Ngezi Concentrator source files."""

from .kpi_scorecard import load_kpi_scorecard
from .mill_ball import load_mill_ball_trends
from .weekly_report import load_weekly_excel, load_weekly_crushing_milling
from .weekly_report import load_weekly_metal_production, load_weekly_consumables
from .weekly_report import load_projects_from_docx
from .weekly_report import load_grind_trend, load_daily_data

__all__ = [
    "load_kpi_scorecard",
    "load_mill_ball_trends",
    "load_weekly_excel",
    "load_weekly_crushing_milling",
    "load_weekly_metal_production",
    "load_weekly_consumables",
    "load_projects_from_docx",
    "load_grind_trend",
    "load_daily_data",
]
