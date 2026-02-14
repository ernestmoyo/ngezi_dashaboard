"""
Ngezi Concentrator — Interactive Dashboard

Run with:  streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngezi_dashboard.config import (
    KPI_SCORECARD_FILE,
    MILL_BALL_FILE,
    WEEKLY_DOCX_FILE,
    WEEKLY_EXCEL_FILE,
    KPI_REGISTRY,
)
from ngezi_dashboard.loaders import (
    load_kpi_scorecard,
    load_mill_ball_trends,
    load_projects_from_docx,
    load_weekly_consumables,
    load_daily_data,
    load_weekly_crushing_milling,
    load_weekly_metal_production,
)
from ngezi_dashboard.transforms import (
    build_fact_monthly_kpi,
    build_fact_monthly_consumables,
    build_dim_project,
    build_fact_project_status,
    build_fact_daily_plant,
)
from ngezi_dashboard.dashboard import (
    get_manager_overview,
    get_monthly_management_summary,
)
from ngezi_dashboard.kpis import classify_performance

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Ngezi Concentrator Dashboard",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

RAG_COLORS = {
    "green": "#2ecc71",
    "amber": "#f39c12",
    "red": "#e74c3c",
    "grey": "#95a5a6",
}


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data
def load_all_data():
    kpi_scorecard = load_kpi_scorecard(str(KPI_SCORECARD_FILE))
    mill_ball = load_mill_ball_trends(str(MILL_BALL_FILE))
    projects = load_projects_from_docx(str(WEEKLY_DOCX_FILE))

    weekly_consumables = None
    daily_data = None
    crushing_milling = None
    metal_production = None

    if WEEKLY_EXCEL_FILE.exists():
        try:
            weekly_consumables = load_weekly_consumables(str(WEEKLY_EXCEL_FILE))
        except Exception:
            pass
        try:
            daily_data = load_daily_data(str(WEEKLY_EXCEL_FILE))
        except Exception:
            pass
        try:
            crushing_milling = load_weekly_crushing_milling(str(WEEKLY_EXCEL_FILE))
        except Exception:
            pass
        try:
            metal_production = load_weekly_metal_production(str(WEEKLY_EXCEL_FILE))
        except Exception:
            pass

    fact_kpi = build_fact_monthly_kpi(kpi_scorecard)
    fact_consumables = build_fact_monthly_consumables(mill_ball, weekly_consumables)
    dim_project = build_dim_project(projects)
    fact_project = build_fact_project_status(projects)
    fact_daily = build_fact_daily_plant(daily_data)

    return {
        "fact_kpi": fact_kpi,
        "fact_consumables": fact_consumables,
        "dim_project": dim_project,
        "fact_project": fact_project,
        "fact_daily": fact_daily,
        "mill_ball": mill_ball,
        "weekly_consumables": weekly_consumables,
        "crushing_milling": crushing_milling,
        "metal_production": metal_production,
    }


data = load_all_data()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("Ngezi Concentrator")
st.sidebar.markdown("Mine Manager Oversight Dashboard")
st.sidebar.divider()

available_periods = sorted(data["fact_kpi"]["period"].unique().tolist())
selected_period = st.sidebar.selectbox("Select Period", available_periods, index=available_periods.index("2020-Q3") if "2020-Q3" in available_periods else 0)

page = st.sidebar.radio(
    "Navigate",
    ["Executive Summary", "KPI Details", "Daily Production", "Consumables", "Projects"],
)

st.sidebar.divider()
st.sidebar.caption("Data: Ngezi Platinum Concentrator, Zimbabwe")

# ---------------------------------------------------------------------------
# Helper: RAG metric card
# ---------------------------------------------------------------------------
def rag_card(label: str, actual, budget, var_pct, rag: str, unit: str = ""):
    color = RAG_COLORS.get(rag, RAG_COLORS["grey"])
    actual_str = f"{actual:,.1f}" if actual is not None else "N/A"
    budget_str = f"{budget:,.1f}" if budget is not None else "N/A"
    var_str = f"{var_pct:+.1f}%" if var_pct is not None else "N/A"

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, {color}22, {color}11);
                    border-left: 4px solid {color};
                    border-radius: 8px; padding: 16px; margin-bottom: 8px;">
            <div style="font-size: 13px; color: #888; font-weight: 600; text-transform: uppercase;">{label}</div>
            <div style="font-size: 28px; font-weight: 700; color: #222; margin: 4px 0;">{actual_str} <span style="font-size: 14px; color: #888;">{unit}</span></div>
            <div style="font-size: 13px; color: #666;">
                Budget: {budget_str} {unit} &nbsp;|&nbsp;
                <span style="color: {color}; font-weight: 600;">{var_str}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===========================================================================
# PAGE: Executive Summary
# ===========================================================================
if page == "Executive Summary":
    st.title("Executive Summary")
    st.caption(f"Period: **{selected_period}**")

    overview = get_manager_overview(data["fact_kpi"], selected_period)

    # Top-level RAG cards
    cols = st.columns(3)
    domains = [
        ("Crushing", "crushing", "t"),
        ("Milling", "milling", "t"),
        ("6E Recovery", "recovery", "%"),
        ("Mill Balls", "mill_balls", "g/t"),
        ("Water", "water", "m3/t"),
        ("Total Cost", "cost", "USD/t"),
    ]

    for i, (label, key, unit) in enumerate(domains):
        with cols[i % 3]:
            m = overview.get(key, {})
            rag_card(label, m.get("actual"), m.get("budget"), m.get("var_pct"), m.get("rag", "grey"), unit)

    st.divider()

    # KPI summary table
    st.subheader("Full KPI Breakdown")
    mgmt = get_monthly_management_summary(data["fact_kpi"], selected_period)
    if not mgmt.empty:
        display_df = mgmt.copy()
        display_df["actual"] = display_df["actual"].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
        display_df["budget"] = display_df["budget"].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
        display_df["variance"] = display_df["variance"].apply(lambda x: f"{x:+,.2f}" if pd.notna(x) else "")
        display_df["variance_pct"] = display_df["variance_pct"].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "")

        def color_rag(val):
            colors = {"green": "#2ecc71", "amber": "#f39c12", "red": "#e74c3c", "grey": "#95a5a6"}
            return f"background-color: {colors.get(val, '#ffffff')}22; color: {colors.get(val, '#333')}"

        styled = display_df.style.map(color_rag, subset=["rag"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

    # Variance chart
    st.subheader("Variance by KPI")
    chart_df = get_monthly_management_summary(data["fact_kpi"], selected_period)
    if not chart_df.empty:
        chart_df = chart_df.dropna(subset=["variance_pct"])
        colors = [RAG_COLORS.get(r, "#95a5a6") for r in chart_df["rag"]]

        fig = go.Figure(go.Bar(
            x=chart_df["variance_pct"],
            y=chart_df["kpi_name"],
            orientation="h",
            marker_color=colors,
            text=chart_df["variance_pct"].apply(lambda x: f"{x:+.1f}%"),
            textposition="outside",
        ))
        fig.update_layout(
            height=400,
            xaxis_title="Variance %",
            yaxis_title="",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=40),
        )
        fig.add_vline(x=0, line_dash="dash", line_color="#888")
        st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# PAGE: KPI Details
# ===========================================================================
elif page == "KPI Details":
    st.title("KPI Details Across Periods")

    fact_kpi = data["fact_kpi"]
    kpi_names = sorted(fact_kpi["kpi_name"].unique().tolist())
    selected_kpi = st.selectbox("Select KPI", kpi_names)

    kpi_data = fact_kpi[fact_kpi["kpi_name"] == selected_kpi].sort_values("period")

    if not kpi_data.empty:
        registry = KPI_REGISTRY.get(selected_kpi, {})
        direction = registry.get("direction", "higher_is_better")
        unit = registry.get("unit", "")

        col1, col2 = st.columns([2, 1])

        with col1:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=kpi_data["period"],
                y=kpi_data["actual"],
                name="Actual",
                marker_color="#3498db",
            ))
            fig.add_trace(go.Scatter(
                x=kpi_data["period"],
                y=kpi_data["budget"],
                name="Budget",
                mode="lines+markers",
                line=dict(color="#e74c3c", width=2, dash="dash"),
                marker=dict(size=8),
            ))
            fig.update_layout(
                title=f"{selected_kpi} — Actual vs Budget",
                yaxis_title=unit,
                barmode="group",
                height=400,
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Period Breakdown**")
            for _, row in kpi_data.iterrows():
                rag = classify_performance(
                    row["actual"], row["budget"], direction,
                    registry.get("amber_band", 5.0)
                ) if pd.notna(row["actual"]) and pd.notna(row["budget"]) else "grey"
                color = RAG_COLORS[rag]
                var_str = f"{row['variance_pct']:+.1f}%" if pd.notna(row['variance_pct']) else "N/A"
                st.markdown(
                    f"<div style='border-left: 3px solid {color}; padding: 4px 8px; margin: 4px 0;'>"
                    f"<b>{row['period']}</b>: {var_str}</div>",
                    unsafe_allow_html=True,
                )

        # Comments
        comments = kpi_data["comments"].dropna().unique()
        if len(comments) > 0:
            st.info(f"Manager comment: {comments[0]}")


# ===========================================================================
# PAGE: Daily Production
# ===========================================================================
elif page == "Daily Production":
    st.title("Daily Production — October 2021")

    fact_daily = data["fact_daily"]

    if fact_daily.empty or fact_daily["milled_tonnage_actual"].isna().all():
        st.warning("No daily production data available.")
    else:
        col1, col2, col3 = st.columns(3)

        total_actual = fact_daily["milled_tonnage_actual"].sum()
        total_target = fact_daily["milled_tonnage_target"].sum()
        days_with_data = fact_daily["milled_tonnage_actual"].notna().sum()

        with col1:
            st.metric("Total Milled (Actual)", f"{total_actual:,.0f} t")
        with col2:
            st.metric("Total Target", f"{total_target:,.0f} t")
        with col3:
            var_pct = ((total_actual - total_target) / total_target * 100) if total_target else 0
            st.metric("Variance", f"{var_pct:+.1f}%", delta=f"{total_actual - total_target:+,.0f} t")

        # Daily chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=fact_daily["date"],
            y=fact_daily["milled_tonnage_actual"],
            name="Actual",
            marker_color="#3498db",
        ))
        fig.add_trace(go.Scatter(
            x=fact_daily["date"],
            y=fact_daily["milled_tonnage_target"],
            name="Target",
            mode="lines",
            line=dict(color="#e74c3c", width=2, dash="dash"),
        ))
        fig.update_layout(
            title="Daily Milled Tonnage",
            yaxis_title="Tonnes",
            xaxis_title="Date",
            height=400,
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Daily variance chart
        daily_var = fact_daily.copy()
        daily_var["variance"] = daily_var["milled_tonnage_actual"] - daily_var["milled_tonnage_target"]
        daily_var["color"] = daily_var["variance"].apply(lambda x: "#2ecc71" if x >= 0 else "#e74c3c")

        fig2 = go.Figure(go.Bar(
            x=daily_var["date"],
            y=daily_var["variance"],
            marker_color=daily_var["color"],
        ))
        fig2.update_layout(
            title="Daily Variance (Actual - Target)",
            yaxis_title="Tonnes",
            height=300,
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="#888")
        st.plotly_chart(fig2, use_container_width=True)

        # Cumulative chart
        daily_var["cum_actual"] = daily_var["milled_tonnage_actual"].cumsum()
        daily_var["cum_target"] = daily_var["milled_tonnage_target"].cumsum()

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=daily_var["date"], y=daily_var["cum_actual"],
            name="Cumulative Actual", fill="tozeroy",
            line=dict(color="#3498db"),
        ))
        fig3.add_trace(go.Scatter(
            x=daily_var["date"], y=daily_var["cum_target"],
            name="Cumulative Target",
            line=dict(color="#e74c3c", dash="dash"),
        ))
        fig3.update_layout(
            title="Cumulative Milled Tonnage",
            yaxis_title="Tonnes",
            height=350,
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig3, use_container_width=True)


# ===========================================================================
# PAGE: Consumables
# ===========================================================================
elif page == "Consumables":
    st.title("Consumables")

    tab1, tab2 = st.tabs(["Reagents & Water (Oct 2021)", "Mill Ball Trends"])

    with tab1:
        wc = data.get("weekly_consumables")
        if wc is not None and not wc.empty:
            # Split reagents and water
            reagents = wc[wc["category"] == "reagent"].copy()
            water = wc[wc["category"] == "water"].copy()

            if not reagents.empty:
                st.subheader("Reagent Consumption (g/t)")
                reagents_display = reagents[reagents["actual"] > 0].copy()
                if not reagents_display.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=reagents_display["consumable"],
                        y=reagents_display["actual"],
                        name="Actual",
                        marker_color="#3498db",
                    ))
                    fig.add_trace(go.Bar(
                        x=reagents_display["consumable"],
                        y=reagents_display["budget"],
                        name="Budget",
                        marker_color="#e74c3c",
                        opacity=0.5,
                    ))
                    fig.update_layout(
                        barmode="group", height=350,
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig, use_container_width=True)

                st.dataframe(reagents[["consumable", "actual", "budget", "var", "var_pct"]],
                             use_container_width=True, hide_index=True)

            if not water.empty:
                st.subheader("Water Consumption (m3/t)")
                st.dataframe(water[["consumable", "actual", "budget", "var", "var_pct"]],
                             use_container_width=True, hide_index=True)
        else:
            st.info("No weekly consumables data available.")

    with tab2:
        mb = data["mill_ball"]
        if not mb.empty:
            st.subheader("Mill Ball Stock Projection")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=mb["month"], y=mb["mill1_stock_remaining"],
                name="Remaining Stock (t)",
                mode="lines+markers",
                line=dict(color="#e74c3c", width=2),
                fill="tozeroy",
                fillcolor="rgba(231, 76, 60, 0.1)",
            ))
            fig.add_trace(go.Bar(
                x=mb["month"], y=mb["mill1_steel_t"],
                name="Monthly Consumption (t)",
                marker_color="#3498db",
                opacity=0.7,
            ))
            fig.update_layout(
                title="Mill 1 (Anhui) — Stock Depletion Forecast",
                yaxis_title="Tonnes",
                height=400,
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Starting Stock", f"{mb['mill1_stock_remaining'].iloc[0]:,.0f} t")
            with col2:
                st.metric("Ending Stock", f"{mb['mill1_stock_remaining'].iloc[-1]:,.0f} t")
            with col3:
                total_consumed = mb["mill1_steel_t"].sum()
                st.metric("Total Consumed", f"{total_consumed:,.0f} t")

            st.dataframe(mb, use_container_width=True, hide_index=True)
        else:
            st.info("No mill ball data available.")


# ===========================================================================
# PAGE: Projects
# ===========================================================================
elif page == "Projects":
    st.title("Concentrator Projects")
    st.caption("Snapshot: 5 November 2021 (Week 5, October)")

    dim_proj = data["dim_project"]
    fact_proj = data["fact_project"]

    if dim_proj.empty:
        st.warning("No project data available.")
    else:
        merged = dim_proj.merge(fact_proj, on="project_id", how="left")

        # Status summary cards
        status_counts = merged["status"].value_counts()
        cols = st.columns(4)
        status_config = [
            ("completed", "Completed", "#2ecc71"),
            ("in_progress", "In Progress", "#f39c12"),
            ("pending", "Pending", "#e74c3c"),
            ("delayed", "Delayed", "#8e44ad"),
        ]
        for i, (status, label, color) in enumerate(status_config):
            with cols[i]:
                count = status_counts.get(status, 0)
                st.markdown(
                    f"<div style='text-align:center; padding:12px; background:{color}15; "
                    f"border-radius:8px; border-top:3px solid {color};'>"
                    f"<div style='font-size:28px; font-weight:700; color:{color};'>{count}</div>"
                    f"<div style='font-size:13px; color:#666;'>{label}</div></div>",
                    unsafe_allow_html=True,
                )

        st.divider()

        # Gantt-style timeline
        st.subheader("Project Timeline")
        gantt_data = merged.dropna(subset=["planned_completion"]).copy()
        if not gantt_data.empty:
            gantt_data["start"] = pd.Timestamp("2021-06-01")
            gantt_data["end"] = gantt_data["planned_completion"]

            status_colors = {
                "completed": "#2ecc71",
                "in_progress": "#f39c12",
                "pending": "#e74c3c",
                "delayed": "#8e44ad",
                "unknown": "#95a5a6",
            }

            fig = go.Figure()
            for _, row in gantt_data.iterrows():
                color = status_colors.get(row["status"], "#95a5a6")
                fig.add_trace(go.Bar(
                    x=[(row["end"] - row["start"]).days],
                    y=[row["project_name"][:40]],
                    orientation="h",
                    base=row["start"],
                    marker_color=color,
                    showlegend=False,
                    hovertemplate=(
                        f"<b>{row['project_name']}</b><br>"
                        f"Status: {row['status']}<br>"
                        f"Due: {row['planned_completion'].strftime('%d %b %Y')}<br>"
                        f"Responsible: {row['responsible']}"
                        "<extra></extra>"
                    ),
                ))

            # Add snapshot date line
            fig.add_vline(
                x=pd.Timestamp("2021-11-05").timestamp() * 1000,
                line_dash="dash", line_color="#333",
                annotation_text="Report Date",
            )

            fig.update_layout(
                height=max(300, len(gantt_data) * 35),
                xaxis_type="date",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Full project table
        st.subheader("Project Details")

        def status_badge(status):
            colors = {
                "completed": "#2ecc71",
                "in_progress": "#f39c12",
                "pending": "#e74c3c",
                "delayed": "#8e44ad",
            }
            return colors.get(status, "#95a5a6")

        display_cols = ["project_id", "project_name", "responsible", "planned_completion", "status", "comments"]
        available_cols = [c for c in display_cols if c in merged.columns]
        st.dataframe(merged[available_cols], use_container_width=True, hide_index=True)
