# 🔋 BESS Arbitrage & Battery Degradation Optimization Engine

> **Mathematical optimization framework (Linear Programming via HiGHS) for grid-scale Battery Energy Storage Systems (BESS) co-optimizing EPEX Spot Day-Ahead arbitrage spreads against marginal cell degradation and cycle aging.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Optimization Engine](https://img.shields.io/badge/Solver-SciPy%20HiGHS-blueviolet.svg)](https://docs.scipy.org/doc/scipy/reference/optimize.linprog-highs.html)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bess-arbitrage-degradation-engine-agp4qpxtz6sfwt24bafoxj.streamlit.app/)

---

## 📊 Dashboard & Dispatch Preview

![BESS Arbitrage Simulation Results](bess_arbitrage_simulation_results.png)

---

## 📌 Problem Context & Objectives

Aggressive cycling on minor price spreads often destroys asset value faster than it captures revenue, as battery State of Health (SOH) degrades with each throughput MWh. 

This engine solves the multi-period dispatch schedule by:
1. **Dynamic Arbitrage Dispatch**: Exploiting peak-to-trough price differentials and negative pricing hours on the EPEX Spot market.
2. **Marginal Degradation Cost Formulation**: Explicitly penalizing cell aging (€/Throughput MWh) within the LP objective function to prevent uneconomic cycling.
3. **Physical Storage Envelope Constraints**: Enforcing Round-Trip Efficiency ($\eta_{\text{rt}}$), C-rate bounds, and operational State of Charge ($\text{SOC}$) limits.

---

## 🔬 Mathematical Formulation

### 1. Objective Function
Minimize total net cost (maximize net economic arbitrage profit) over time horizon $T$:

$$\min_{P_{\text{ch}}, P_{\text{dis}}, E} \sum_{t=1}^{T} \left( C_{\text{spot}}(t) \cdot P_{\text{ch}}(t) \cdot \Delta t - C_{\text{spot}}(t) \cdot P_{\text{dis}}(t) \cdot \Delta t + C_{\text{deg}} \cdot \big(P_{\text{ch}}(t) + P_{\text{dis}}(t)\big) \cdot \Delta t \right)$$

### 2. Marginal Degradation Cost ($C_{\text{deg}}$)
Based on battery pack CAPEX depreciation and rated cycle life:

$$C_{\text{deg}} = \frac{\text{CAPEX}_{\text{BESS}} \times \Delta \text{SOH}_{\text{target}}}{N_{\text{cycles}} \times E_{\text{capacity}} \times \text{DoD}_{\text{rated}}}$$

### 3. State of Charge Dynamics & Operational Constraints
* **Energy Balance:**
  $$E(t) = E(t-1) + \eta_{\text{ch}} \cdot P_{\text{ch}}(t) \cdot \Delta t - \frac{1}{\eta_{\text{dis}}} \cdot P_{\text{dis}}(t) \cdot \Delta t$$
* **Power Bounds:**
  $$0 \le P_{\text{ch}}(t) \le P_{\text{max}}, \quad 0 \le P_{\text{dis}}(t) \le P_{\text{max}}$$
* **Energy Boundaries:**
  $$\text{SOC}_{\text{min}} \cdot E_{\text{capacity}} \le E(t) \le \text{SOC}_{\text{max}} \cdot E_{\text{capacity}}$$

---

## 📂 Repository Architecture

```text
bess-arbitrage-degradation-engine/
│
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated PyTest CI/CD pipeline
├── src/
│   ├── __init__.py
│   ├── battery_model.py         # Cell degradation & aging calculations
│   └── arbitrage_optimizer.py   # SciPy HiGHS linear programming solver
├── tests/
│   ├── __init__.py
│   └── test_bess_engine.py      # Unit & boundary constraint tests
├── app.py                       # Interactive Streamlit dashboard
├── bess_simulation.py           # Standalone simulation & plot script
├── bess_arbitrage_simulation_results.png # Visual benchmark plot
├── requirements.txt
├── README.md
└── .gitignore
