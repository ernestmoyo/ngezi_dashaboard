"""
Ngezi Concentrator — Mine Manager Oversight Dashboard

Run with:  streamlit run app.py
"""

import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ngezi_dashboard.config import KPI_REGISTRY
from ngezi_dashboard.kpis import classify_performance
from ngezi_dashboard.simulator import (
    generate_quarterly_kpis,
    generate_monthly_kpis,
    generate_daily_production,
    generate_projects,
    generate_consumables,
    generate_mill_ball_forecast,
)

# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------
ZIMPLATS_NAVY = "#003B71"
ZIMPLATS_BLUE = "#0066B3"
ZIMPLATS_LIGHT = "#E8F0FE"
ZIMPLATS_WHITE = "#FFFFFF"
ZIMPLATS_GREY = "#F5F7FA"
ACCENT_GREEN = "#27AE60"
ACCENT_AMBER = "#F39C12"
ACCENT_RED = "#E74C3C"

RAG_COLORS = {"green": ACCENT_GREEN, "amber": ACCENT_AMBER, "red": ACCENT_RED, "grey": "#95A5A6"}
RAG_BG = {"green": "#E8F8F0", "amber": "#FEF5E7", "red": "#FDEDEC", "grey": "#F2F3F4"}

LOGO_PATH = Path(__file__).parent / "assets" / "zimplats_logo.png"

# Proper display names for KPIs
KPI_DISPLAY_NAMES = {
    "crushed_tonnage": "Crushed Tonnage",
    "milling_rate_tph": "Milling Rate",
    "milled_tonnage": "Milled Tonnage",
    "grind_pct_minus75": "Grind (%-75 microns)",
    "plant_running_time_pct": "Plant Running Time",
    "mass_pull_pct": "Mass Pull",
    "recovery_6e_pct": "6E Recovery",
    "mill_ball_consumption_gt": "Mill Ball Consumption",
    "filter_cake_moisture_pct": "Filter Cake Moisture",
    "metal_unaccounted_for_pct": "Metal Unaccounted For",
    "raw_water_m3t": "Raw Water Consumption",
    "total_cost": "Total Cost",
}

KPI_UNITS = {
    "crushed_tonnage": "t",
    "milling_rate_tph": "tph",
    "milled_tonnage": "t",
    "grind_pct_minus75": "%",
    "plant_running_time_pct": "%",
    "mass_pull_pct": "%",
    "recovery_6e_pct": "%",
    "mill_ball_consumption_gt": "g/t",
    "filter_cake_moisture_pct": "%",
    "metal_unaccounted_for_pct": "%",
    "raw_water_m3t": "m\u00b3/t",
    "total_cost": "USD/t",
}


def kpi_label(name: str) -> str:
    return KPI_DISPLAY_NAMES.get(name, name.replace("_", " ").title())


def kpi_unit(name: str) -> str:
    return KPI_UNITS.get(name, "")


# ---------------------------------------------------------------------------
# Page config & global CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Ngezi Concentrator Dashboard",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: {ZIMPLATS_NAVY};
    }}
    section[data-testid="stSidebar"] * {{
        color: {ZIMPLATS_WHITE} !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label {{
        color: {ZIMPLATS_WHITE} !important;
        font-weight: 500;
    }}

    /* Header bar */
    .header-bar {{
        background: linear-gradient(135deg, {ZIMPLATS_NAVY}, {ZIMPLATS_BLUE});
        padding: 20px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        gap: 20px;
    }}
    .header-bar h1 {{
        color: white !important;
        font-size: 24px !important;
        margin: 0 !important;
        padding: 0 !important;
    }}
    .header-bar p {{
        color: rgba(255,255,255,0.8) !important;
        font-size: 14px !important;
        margin: 4px 0 0 0 !important;
    }}

    /* KPI Cards */
    .kpi-card {{
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 12px;
        border: 1px solid #E5E8EB;
        transition: box-shadow 0.2s;
    }}
    .kpi-card:hover {{
        box-shadow: 0 4px 12px rgba(0,59,113,0.1);
    }}
    .kpi-label {{
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: {ZIMPLATS_NAVY};
        margin-bottom: 6px;
    }}
    .kpi-value {{
        font-size: 30px;
        font-weight: 700;
        color: {ZIMPLATS_NAVY};
    }}
    .kpi-unit {{
        font-size: 13px;
        color: #8899AA;
        font-weight: 400;
    }}
    .kpi-meta {{
        font-size: 12px;
        color: #8899AA;
        margin-top: 8px;
    }}
    .kpi-badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }}

    /* Status pills */
    .status-completed {{ background: #E8F8F0; color: #27AE60; }}
    .status-in_progress {{ background: #FEF5E7; color: #F39C12; }}
    .status-pending {{ background: #FDEDEC; color: #E74C3C; }}
    .status-delayed {{ background: #F4ECF7; color: #8E44AD; }}

    /* Hide default Streamlit header */
    header[data-testid="stHeader"] {{
        background: transparent;
    }}

    /* Table styling */
    .stDataFrame th {{
        background: {ZIMPLATS_NAVY} !important;
        color: white !important;
    }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Load simulated data (cached)
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    quarterly = generate_quarterly_kpis()
    monthly = generate_monthly_kpis()
    daily = generate_daily_production()
    dim_project, fact_project = generate_projects()
    consumables = generate_consumables()
    mill_ball = generate_mill_ball_forecast()

    return {
        "quarterly": quarterly,
        "monthly": monthly,
        "daily": daily,
        "dim_project": dim_project,
        "fact_project": fact_project,
        "consumables": consumables,
        "mill_ball": mill_ball,
    }


data = load_data()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=200)
st.sidebar.markdown("### Ngezi Concentrator")
st.sidebar.caption("Mine Manager Oversight Dashboard")
st.sidebar.divider()

available_periods = sorted(data["quarterly"]["period"].unique().tolist())
selected_period = st.sidebar.selectbox(
    "Period",
    available_periods,
    index=len(available_periods) - 1,
)

page = st.sidebar.radio(
    "Navigation",
    ["Executive Summary", "KPI Trends", "Daily Production", "Consumables", "Projects"],
)

st.sidebar.divider()
st.sidebar.caption("Zimplats Holdings Limited")
st.sidebar.caption("Member of the Implats Group")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def render_header(title: str, subtitle: str = ""):
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f'<div class="header-bar"><div><h1>{title}</h1>{sub_html}</div></div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# RAG Card
# ---------------------------------------------------------------------------
def rag_card(label: str, actual, budget, var_pct, rag: str, unit: str = ""):
    color = RAG_COLORS.get(rag, RAG_COLORS["grey"])
    bg = RAG_BG.get(rag, RAG_BG["grey"])

    if actual is not None and abs(actual) >= 1000:
        actual_str = f"{actual:,.0f}"
    elif actual is not None:
        actual_str = f"{actual:,.2f}"
    else:
        actual_str = "N/A"

    if budget is not None and abs(budget) >= 1000:
        budget_str = f"{budget:,.0f}"
    elif budget is not None:
        budget_str = f"{budget:,.2f}"
    else:
        budget_str = "N/A"

    var_str = f"{var_pct:+.1f}%" if var_pct is not None else "N/A"
    arrow = "\u25b2" if var_pct is not None and var_pct > 0 else "\u25bc" if var_pct is not None and var_pct < 0 else ""

    st.markdown(f"""
    <div class="kpi-card" style="background: {bg}; border-left: 4px solid {color};">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{actual_str} <span class="kpi-unit">{unit}</span></div>
        <div class="kpi-meta">
            Budget: {budget_str} {unit} &nbsp;&middot;&nbsp;
            <span class="kpi-badge" style="background: {color}18; color: {color};">{arrow} {var_str}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ===========================================================================
# PAGE: Executive Summary
# ===========================================================================
if page == "Executive Summary":
    render_header("Executive Summary", f"Period: {selected_period}")

    qtr = data["quarterly"]
    period_data = qtr[qtr["period"] == selected_period]

    # Top 6 KPI cards
    domains = [
        ("crushed_tonnage", "Crushed Tonnage", "t"),
        ("milled_tonnage", "Milled Tonnage", "t"),
        ("recovery_6e_pct", "6E Recovery", "%"),
        ("mill_ball_consumption_gt", "Mill Ball Consumption", "g/t"),
        ("raw_water_m3t", "Raw Water Consumption", "m\u00b3/t"),
        ("total_cost", "Total Cost", "USD/t"),
    ]

    cols = st.columns(3)
    for i, (kpi_name, label, unit) in enumerate(domains):
        row = period_data[period_data["kpi_name"] == kpi_name]
        with cols[i % 3]:
            if not row.empty:
                r = row.iloc[0]
                registry = KPI_REGISTRY.get(kpi_name, {})
                rag = classify_performance(
                    r["actual"], r["budget"],
                    registry.get("direction", "higher_is_better"),
                    registry.get("amber_band", 5.0),
                )
                rag_card(label, r["actual"], r["budget"], r["variance_pct"], rag, unit)
            else:
                rag_card(label, None, None, None, "grey", unit)

    st.markdown("<br>", unsafe_allow_html=True)

    # Full KPI table
    col_table, col_chart = st.columns([1, 1])

    with col_table:
        st.markdown(f"#### All KPIs \u2014 {selected_period}")
        if not period_data.empty:
            display = period_data[["kpi_name", "actual", "budget", "variance", "variance_pct"]].copy()
            display["KPI"] = display["kpi_name"].map(kpi_label)
            display["Unit"] = display["kpi_name"].map(kpi_unit)
            display["Actual"] = display["actual"].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
            display["Budget"] = display["budget"].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "")
            display["Variance"] = display["variance"].apply(lambda x: f"{x:+,.2f}" if pd.notna(x) else "")
            display["Var %"] = display["variance_pct"].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "")

            rag_list = []
            for _, r in period_data.iterrows():
                reg = KPI_REGISTRY.get(r["kpi_name"], {})
                if pd.notna(r["actual"]) and pd.notna(r["budget"]):
                    rag_list.append(classify_performance(
                        r["actual"], r["budget"],
                        reg.get("direction", "higher_is_better"),
                        reg.get("amber_band", 5.0),
                    ))
                else:
                    rag_list.append("grey")
            display["Status"] = rag_list

            st.dataframe(
                display[["KPI", "Actual", "Budget", "Variance", "Var %", "Unit", "Status"]],
                use_container_width=True, hide_index=True, height=460,
            )

    with col_chart:
        st.markdown("#### Variance by KPI")
        if not period_data.empty:
            chart_data = period_data.dropna(subset=["variance_pct"]).copy()
            chart_data["display_name"] = chart_data["kpi_name"].map(kpi_label)

            rag_colors = []
            for _, r in chart_data.iterrows():
                reg = KPI_REGISTRY.get(r["kpi_name"], {})
                if pd.notna(r["actual"]) and pd.notna(r["budget"]):
                    rag_colors.append(RAG_COLORS[classify_performance(
                        r["actual"], r["budget"],
                        reg.get("direction", "higher_is_better"),
                        reg.get("amber_band", 5.0),
                    )])
                else:
                    rag_colors.append(RAG_COLORS["grey"])

            fig = go.Figure(go.Bar(
                x=chart_data["variance_pct"],
                y=chart_data["display_name"],
                orientation="h",
                marker_color=rag_colors,
                text=chart_data["variance_pct"].apply(lambda x: f"{x:+.1f}%"),
                textposition="outside",
                textfont=dict(size=11),
            ))
            fig.update_layout(
                height=440,
                xaxis_title="Variance %",
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=40, t=10, b=40),
                font=dict(family="Segoe UI, sans-serif"),
            )
            fig.add_vline(x=0, line_dash="dash", line_color=ZIMPLATS_NAVY, line_width=1)
            st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# PAGE: KPI Trends
# ===========================================================================
elif page == "KPI Trends":
    render_header("KPI Trends", "Monthly performance tracking")

    monthly = data["monthly"]
    kpi_options = {kpi_label(k): k for k in sorted(monthly["kpi_name"].unique())}
    selected_display = st.selectbox("Select KPI", list(kpi_options.keys()))
    selected_kpi = kpi_options[selected_display]

    kpi_data = monthly[monthly["kpi_name"] == selected_kpi].sort_values("month")
    registry = KPI_REGISTRY.get(selected_kpi, {})
    direction = registry.get("direction", "higher_is_better")
    unit = kpi_unit(selected_kpi)

    if not kpi_data.empty:
        col1, col2 = st.columns([3, 1])

        with col1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=kpi_data["month"],
                y=kpi_data["actual"],
                name="Actual",
                mode="lines+markers",
                line=dict(color=ZIMPLATS_BLUE, width=3),
                marker=dict(size=8, color=ZIMPLATS_BLUE),
                fill="tozeroy",
                fillcolor=f"rgba(0,102,179,0.08)",
            ))
            fig.add_trace(go.Scatter(
                x=kpi_data["month"],
                y=kpi_data["budget"],
                name="Budget",
                mode="lines+markers",
                line=dict(color=ACCENT_RED, width=2, dash="dash"),
                marker=dict(size=6, symbol="diamond", color=ACCENT_RED),
            ))
            fig.update_layout(
                title=dict(text=f"{selected_display} \u2014 Actual vs Budget", font=dict(size=16, color=ZIMPLATS_NAVY)),
                yaxis_title=unit,
                height=420,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Segoe UI, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Monthly Performance**")
            for _, row in kpi_data.iterrows():
                rag = classify_performance(
                    row["actual"], row["budget"], direction,
                    registry.get("amber_band", 5.0),
                ) if pd.notna(row["actual"]) and pd.notna(row["budget"]) else "grey"
                color = RAG_COLORS[rag]
                month_label = row["month"].strftime("%b %Y")
                var_str = f"{row['variance_pct']:+.1f}%" if pd.notna(row["variance_pct"]) else ""
                st.markdown(
                    f"<div style='border-left: 3px solid {color}; padding: 6px 10px; "
                    f"margin: 4px 0; border-radius: 0 4px 4px 0; background: {RAG_BG[rag]};'>"
                    f"<b style='color:{ZIMPLATS_NAVY};'>{month_label}</b>"
                    f"<span style='float:right; color:{color}; font-weight:600;'>{var_str}</span></div>",
                    unsafe_allow_html=True,
                )


# ===========================================================================
# PAGE: Daily Production
# ===========================================================================
elif page == "Daily Production":
    render_header("Daily Production", "February 2026 \u2014 Month to Date")

    daily = data["daily"]

    col1, col2, col3, col4 = st.columns(4)
    total_actual = daily["milled_tonnage_actual"].sum()
    total_target = daily["milled_tonnage_target"].sum()
    avg_rate = daily["milling_rate_tph_actual"].mean()
    avg_recovery = daily["recovery_pct_actual"].mean()

    with col1:
        st.metric("Milled Tonnage", f"{total_actual:,.0f} t",
                   delta=f"{total_actual - total_target:+,.0f} t")
    with col2:
        st.metric("Target", f"{total_target:,.0f} t")
    with col3:
        st.metric("Avg Milling Rate", f"{avg_rate:,.0f} tph")
    with col4:
        st.metric("Avg Recovery", f"{avg_recovery:.1f}%")

    # Daily tonnage chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["date"], y=daily["milled_tonnage_actual"],
        name="Actual", marker_color=ZIMPLATS_BLUE, opacity=0.85,
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["milled_tonnage_target"],
        name="Target", mode="lines",
        line=dict(color=ACCENT_RED, width=2, dash="dash"),
    ))
    fig.update_layout(
        title=dict(text="Daily Milled Tonnage", font=dict(color=ZIMPLATS_NAVY)),
        yaxis_title="Tonnes", height=380,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Variance and cumulative side by side
    c1, c2 = st.columns(2)

    with c1:
        variance = daily["milled_tonnage_actual"] - daily["milled_tonnage_target"]
        colors = [ACCENT_GREEN if v >= 0 else ACCENT_RED for v in variance]
        fig2 = go.Figure(go.Bar(
            x=daily["date"], y=variance, marker_color=colors,
        ))
        fig2.update_layout(
            title=dict(text="Daily Variance", font=dict(color=ZIMPLATS_NAVY)),
            yaxis_title="Tonnes", height=320,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Segoe UI, sans-serif"),
        )
        fig2.add_hline(y=0, line_dash="dash", line_color="#AAA")
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=daily["date"], y=daily["cum_actual"],
            name="Cumulative Actual", fill="tozeroy",
            line=dict(color=ZIMPLATS_BLUE, width=2),
            fillcolor="rgba(0,102,179,0.1)",
        ))
        fig3.add_trace(go.Scatter(
            x=daily["date"], y=daily["cum_target"],
            name="Cumulative Target",
            line=dict(color=ACCENT_RED, dash="dash", width=2),
        ))
        fig3.update_layout(
            title=dict(text="Cumulative Tonnage", font=dict(color=ZIMPLATS_NAVY)),
            yaxis_title="Tonnes", height=320,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Segoe UI, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig3, use_container_width=True)

    # Daily data table
    with st.expander("View Daily Data"):
        display_daily = daily[["date", "milled_tonnage_actual", "milled_tonnage_target",
                               "milling_rate_tph_actual", "recovery_pct_actual",
                               "crusher_availability_pct", "mill_availability_pct"]].copy()
        display_daily.columns = [
            "Date", "Milled Tonnage (Actual)", "Milled Tonnage (Target)",
            "Milling Rate (tph)", "Recovery (%)",
            "Crusher Availability (%)", "Mill Availability (%)",
        ]
        st.dataframe(display_daily, use_container_width=True, hide_index=True)


# ===========================================================================
# PAGE: Consumables
# ===========================================================================
elif page == "Consumables":
    render_header("Consumables", "Reagents, Water, and Mill Ball Consumption")

    tab1, tab2 = st.tabs(["Reagents & Water", "Mill Ball Forecast"])

    with tab1:
        consumables = data["consumables"]
        reagents = consumables[consumables["category"] == "reagent"].copy()
        water = consumables[consumables["category"] == "water"].copy()

        st.markdown("#### Reagent Consumption (g/t)")
        active_reagents = reagents[reagents["actual"] > 0].copy()
        if not active_reagents.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=active_reagents["consumable"], y=active_reagents["actual"],
                name="Actual", marker_color=ZIMPLATS_BLUE,
            ))
            fig.add_trace(go.Bar(
                x=active_reagents["consumable"], y=active_reagents["budget"],
                name="Budget", marker_color=ZIMPLATS_NAVY, opacity=0.3,
            ))
            fig.update_layout(
                barmode="group", height=380,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Segoe UI, sans-serif"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

        display_reagents = reagents[["consumable", "actual", "budget", "var", "var_pct"]].copy()
        display_reagents.columns = ["Consumable", "Actual (g/t)", "Budget (g/t)", "Variance", "Variance %"]
        st.dataframe(display_reagents, use_container_width=True, hide_index=True)

        st.markdown("#### Water Consumption (m\u00b3/t)")
        display_water = water[["consumable", "actual", "budget", "var", "var_pct"]].copy()
        display_water.columns = ["Source", "Actual (m\u00b3/t)", "Budget (m\u00b3/t)", "Variance", "Variance %"]
        st.dataframe(display_water, use_container_width=True, hide_index=True)

    with tab2:
        mb = data["mill_ball"]
        st.markdown("#### Mill Ball Stock Depletion Forecast")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=mb["month"], y=mb["mill1_stock_remaining"],
            name="Remaining Stock",
            mode="lines+markers",
            line=dict(color=ACCENT_RED, width=2),
            fill="tozeroy", fillcolor="rgba(231,76,60,0.08)",
        ))
        fig.add_trace(go.Bar(
            x=mb["month"], y=mb["mill1_steel_t"],
            name="Monthly Consumption",
            marker_color=ZIMPLATS_BLUE, opacity=0.7,
        ))
        fig.update_layout(
            title=dict(text="Mill 1 (Anhui) \u2014 Stock Projection", font=dict(color=ZIMPLATS_NAVY)),
            yaxis_title="Tonnes", height=420,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Segoe UI, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Starting Stock", f"{mb['mill1_stock_remaining'].iloc[0]:,.0f} t")
        with c2:
            st.metric("Ending Stock", f"{mb['mill1_stock_remaining'].iloc[-1]:,.0f} t")
        with c3:
            st.metric("Total Consumption", f"{mb['mill1_steel_t'].sum():,.0f} t")

        display_mb = mb.copy()
        display_mb.columns = ["Month", "Projected Tonnage", "Consumption Rate (g/t)",
                              "Steel Used (t)", "Stock Remaining (t)"]
        st.dataframe(display_mb, use_container_width=True, hide_index=True)


# ===========================================================================
# PAGE: Projects
# ===========================================================================
elif page == "Projects":
    render_header("Concentrator Projects", "Status as at 14 February 2026")

    dim_proj = data["dim_project"]
    fact_proj = data["fact_project"]
    merged = dim_proj.merge(fact_proj, on="project_id", how="left")

    # Status summary
    status_counts = merged["status"].value_counts()
    cols = st.columns(4)
    status_config = [
        ("completed", "Completed", ACCENT_GREEN),
        ("in_progress", "In Progress", ACCENT_AMBER),
        ("pending", "Pending", ACCENT_RED),
        ("delayed", "Delayed", "#8E44AD"),
    ]
    for i, (status, label, color) in enumerate(status_config):
        with cols[i]:
            count = status_counts.get(status, 0)
            st.markdown(
                f"<div style='text-align:center; padding:16px; background:{ZIMPLATS_WHITE}; "
                f"border-radius:10px; border-top:4px solid {color}; "
                f"box-shadow: 0 2px 8px rgba(0,0,0,0.05);'>"
                f"<div style='font-size:32px; font-weight:700; color:{color};'>{count}</div>"
                f"<div style='font-size:13px; color:{ZIMPLATS_NAVY}; font-weight:500;'>{label}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Gantt chart
    st.markdown("#### Project Timeline")
    gantt_data = merged.dropna(subset=["planned_completion"]).copy()
    if not gantt_data.empty:
        gantt_data["start"] = pd.Timestamp("2025-10-01")
        gantt_data["end"] = gantt_data["planned_completion"]

        status_colors = {
            "completed": ACCENT_GREEN,
            "in_progress": ACCENT_AMBER,
            "pending": ACCENT_RED,
            "delayed": "#8E44AD",
            "unknown": "#95A5A6",
        }

        # Build Gantt using Scatter with wide markers for full compatibility
        project_names = gantt_data["project_name"].str[:45].tolist()

        fig = go.Figure()

        for idx, (_, row) in enumerate(gantt_data.iterrows()):
            color = status_colors.get(row["status"], "#95A5A6")
            start = row["start"]
            end = row["end"]
            mid = start + (end - start) / 2

            fig.add_trace(go.Scatter(
                x=[start, end],
                y=[row["project_name"][:45], row["project_name"][:45]],
                mode="lines",
                line=dict(color=color, width=20),
                showlegend=False,
                hoverinfo="text",
                hovertext=(
                    f"<b>{row['project_name']}</b><br>"
                    f"Status: {row['status'].replace('_', ' ').title()}<br>"
                    f"Due: {row['planned_completion'].strftime('%d %b %Y')}<br>"
                    f"Responsible: {row['responsible']}"
                ),
            ))

        # Today marker
        fig.add_shape(
            type="line", x0="2026-02-14", x1="2026-02-14", y0=0, y1=1,
            yref="paper", line=dict(dash="dash", color=ACCENT_RED, width=2),
        )
        fig.add_annotation(
            x="2026-02-14", y=1.02, yref="paper",
            text="Today", showarrow=False,
            font=dict(color=ACCENT_RED, size=11, weight="bold"),
        )

        # Legend for statuses
        for status, label, color in [
            ("completed", "Completed", ACCENT_GREEN),
            ("in_progress", "In Progress", ACCENT_AMBER),
            ("pending", "Pending", ACCENT_RED),
        ]:
            if status in gantt_data["status"].values:
                fig.add_trace(go.Scatter(
                    x=[None], y=[None], mode="lines",
                    line=dict(color=color, width=10),
                    name=label,
                ))

        fig.update_layout(
            height=max(400, len(gantt_data) * 42),
            xaxis=dict(type="date", gridcolor="#E5E8EB"),
            yaxis=dict(autorange="reversed", gridcolor="#E5E8EB"),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=20, t=30, b=40),
            font=dict(family="Segoe UI, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Project details table
    st.markdown("#### Project Details")
    display_proj = merged[["project_id", "project_name", "responsible",
                           "planned_completion", "status", "comments"]].copy()
    display_proj.columns = ["ID", "Project", "Owner", "Target Date", "Status", "Comments"]
    display_proj["Status"] = display_proj["Status"].str.replace("_", " ").str.title()
    st.dataframe(display_proj, use_container_width=True, hide_index=True)
