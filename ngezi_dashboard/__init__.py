"""
Ngezi Concentrator — Mine Manager Oversight Dashboard

Analytics backend for transforming Excel/Word production reports
into a unified, dashboard-ready data layer.

To swap Excel inputs for a database feed:
    Replace loader functions in ngezi_dashboard.loaders with SQL queries
    against a time-series database (e.g. InfluxDB or TimescaleDB) reading
    from belt weigh-sensor and DCS historian exports. The fact-table schemas
    remain unchanged.

To connect to Streamlit/Dash:
    Call dashboard.get_manager_overview(period) to get a plain dict suitable
    for rendering cards, trend charts (Plotly), and project status tables.

To add new KPIs:
    Add an entry to config.KPI_REGISTRY mapping kpi_name to its direction,
    unit, and amber_band, then ensure the relevant loader emits a row with
    that kpi_name.
"""
