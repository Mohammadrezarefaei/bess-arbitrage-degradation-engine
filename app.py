import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from src.arbitrage_optimizer import optimize_bess_dispatch
import streamlit as st

st.set_page_config(
    page_title="BESS Arbitrage & Degradation Engine",
    page_icon="🔋",
    layout="wide",
)

st.markdown(
    """
<style>
    div[data-testid="stMetric"] {
        background-color: #050b1f;
        border: 2px solid #0055ff;
        padding: 16px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 14px rgba(0, 85, 255, 0.25);
    }
    div[data-testid="stMetricLabel"] {
        color: #ffffff;
        font-size: 0.9rem;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        color: #ffffff;
        font-size: 1.6rem;
        font-weight: 700;
    }
    hr {
        border-top: 1px solid #0044ff;
        margin: 25px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🔋 BESS Arbitrage & Cell Degradation Optimization Engine")
st.markdown(
    "<p style='color: #cbd5e1; font-size: 1.05rem; margin-top: -10px;'>"
    "Linear Programming (HiGHS) co-optimization of EPEX Spot Day-Ahead"
    " arbitrage spreads against <b style='color: #00ddff;'>battery cell"
    " degradation & cycle aging</b>.</p>",
    unsafe_allow_html=True,
)

# Sidebar
st.sidebar.markdown("### ⚙️ BESS System Architecture")
power_mw = st.sidebar.slider(
    "Rated Power (MW)", min_value=1.0, max_value=50.0, value=10.0, step=1.0
)
capacity_mwh = st.sidebar.slider(
    "Storage Capacity (MWh)",
    min_value=2.0,
    max_value=100.0,
    value=20.0,
    step=2.0,
)
rte_pct = (
    st.sidebar.slider(
        "Round-Trip Efficiency (%)",
        min_value=75.0,
        max_value=96.0,
        value=88.0,
        step=0.5,
    )
    / 100.0
)
capex_per_mwh = st.sidebar.number_input(
    "Battery Pack CAPEX (€/MWh)",
    min_value=100000,
    max_value=300000,
    value=180000,
    step=10000,
)

horizon_days = st.sidebar.slider(
    "Simulation Horizon (Days)", min_value=3, max_value=14, value=7, step=1
)

# Synthetic Market Prices
n_hours = horizon_days * 24
dates = pd.date_range("2026-08-01 00:00:00", periods=n_hours, freq="h")
hours = dates.hour.to_numpy()
dayofweek = dates.dayofweek.to_numpy()

solar_dip = np.maximum(0, np.sin((hours - 6) * np.pi / 12)) * 55.0
evening_peak = np.maximum(0, np.sin((hours - 17) * np.pi / 4)) * 70.0
base_price = 75.0 + evening_peak - solar_dip
weekend_discount = np.where(dayofweek >= 5, 0.75, 1.0)
noise = np.random.normal(0, 8.0, n_hours)

spot_prices = (base_price * weekend_discount) + noise
spot_prices[hours == 13] -= 35.0  # Noon negative spread injection

df = optimize_bess_dispatch(
    spot_prices,
    dates,
    power_rating_mw=power_mw,
    capacity_mwh=capacity_mwh,
    round_trip_efficiency=rte_pct,
    capex_per_mwh_eur=capex_per_mwh,
)

# Metrics
gross_revenue = np.sum(df["discharge_mw"] * df["spot_price_eur_mwh"])
charge_cost = np.sum(df["charge_mw"] * df["spot_price_eur_mwh"])
gross_pnl = gross_revenue - charge_cost
total_degradation = df["hourly_degradation_eur"].sum()
net_profit = gross_pnl - total_degradation
efc_cycles = (df["charge_mw"].sum() + df["discharge_mw"].sum()) / (
    2.0 * capacity_mwh
)

# KPI Cards
k1, k2, k3, k4 = st.columns(4)
k1.metric("Gross Arbitrage Revenue", f"€{gross_pnl:,.2f}")
k2.metric("Cell Degradation Cost", f"€{total_degradation:,.2f}")
k3.metric("Net Optimized Profit", f"€{net_profit:,.2f}")
k4.metric("Equivalent Full Cycles", f"{efc_cycles:.2f} Cycles")

st.markdown("<hr>", unsafe_allow_html=True)

# Styling
pure_blue_legend = dict(
    orientation="h",
    yanchor="bottom",
    y=1.05,
    xanchor="right",
    x=1.0,
    bgcolor="#003cd2",
    bordercolor="#ffffff",
    borderwidth=2,
    font=dict(color="#ffffff", size=12, family="Arial, sans-serif"),
)

pure_blue_hover = dict(
    bgcolor="#002db3",
    bordercolor="#ffffff",
    font=dict(color="#ffffff", size=13, family="Arial, sans-serif"),
)

# Plot 1: Dispatch Strategy & Pricing
st.markdown("#### 1. EPEX Spot Pricing & BESS Physical Dispatch (MW)")
fig1 = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.10,
    subplot_titles=(
        "EPEX Spot Day-Ahead Price (€/MWh)",
        "Optimal Dispatch Schedule: Discharge (+) / Charge (-)",
    ),
)

fig1.add_trace(
    go.Scatter(
        x=df["timestamp"],
        y=df["spot_price_eur_mwh"],
        name="EPEX Spot (€/MWh)",
        line=dict(color="#fbbf24", width=2.0),
    ),
    row=1,
    col=1,
)

fig1.add_trace(
    go.Bar(
        x=df["timestamp"],
        y=df["discharge_mw"],
        name="Discharge (MW)",
        marker_color="#10b981",
    ),
    row=2,
    col=1,
)
fig1.add_trace(
    go.Bar(
        x=df["timestamp"],
        y=-df["charge_mw"],
        name="Charge (MW)",
        marker_color="#ef4444",
    ),
    row=2,
    col=1,
)

fig1.update_layout(
    template="plotly_dark",
    plot_bgcolor="#060913",
    paper_bgcolor="#060913",
    height=480,
    margin=dict(l=20, r=20, t=55, b=20),
    legend=pure_blue_legend,
    hoverlabel=pure_blue_hover,
    hovermode="x unified",
)
fig1.update_xaxes(gridcolor="#1e293b")
fig1.update_yaxes(gridcolor="#1e293b")

st.plotly_chart(fig1, use_container_width=True)

# Plot 2: State of Charge (SOC %) Tracking
st.markdown("#### 2. Battery State of Charge (SOC %) Envelope Tracking")
fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=df["timestamp"],
        y=df["soc_percent"],
        name="State of Charge (SOC %)",
        line=dict(color="#3b82f6", width=2.4),
    )
)
fig2.add_hline(
    y=90.0,
    line_dash="dash",
    line_color="#ef4444",
    annotation_text="Max Safety Limit (90%)",
)
fig2.add_hline(
    y=10.0,
    line_dash="dash",
    line_color="#ef4444",
    annotation_text="Min Safety Limit (10%)",
)

fig2.update_layout(
    template="plotly_dark",
    plot_bgcolor="#060913",
    paper_bgcolor="#060913",
    height=360,
    margin=dict(l=20, r=20, t=45, b=20),
    legend=pure_blue_legend,
    hoverlabel=pure_blue_hover,
    xaxis=dict(gridcolor="#1e293b", title="Timeline"),
    yaxis=dict(gridcolor="#1e293b", title="State of Charge [%]"),
    hovermode="x unified",
)
st.plotly_chart(fig2, use_container_width=True)
