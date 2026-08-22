import numpy as np
import pandas as pd
from scipy.optimize import linprog
from src.battery_model import compute_marginal_degradation_cost


def optimize_bess_dispatch(
    spot_prices_eur_mwh: np.ndarray,
    timestamps: pd.DatetimeIndex,
    power_rating_mw: float = 10.0,
    capacity_mwh: float = 20.0,
    round_trip_efficiency: float = 0.88,
    soc_min_pct: float = 0.10,
    soc_max_pct: float = 0.90,
    initial_soc_pct: float = 0.50,
    capex_per_mwh_eur: float = 180000.0,
) -> pd.DataFrame:
  """Optimizes BESS charge/discharge schedule against spot prices

  considering round-trip efficiency and marginal degradation costs.
  """
  T = len(spot_prices_eur_mwh)
  delta_t = 1.0

  eta_ch = float(np.sqrt(round_trip_efficiency))
  eta_dis = float(np.sqrt(round_trip_efficiency))

  degradation_cost_per_mwh = compute_marginal_degradation_cost(
      capex_per_mwh_eur=capex_per_mwh_eur, battery_capacity_mwh=capacity_mwh
  )

  # Objective vector: Minimize (Charge_Cost - Discharge_Revenue + Degradation_Cost)
  c_charge = spot_prices_eur_mwh + degradation_cost_per_mwh
  c_discharge = -1.0 * spot_prices_eur_mwh + degradation_cost_per_mwh
  c_energy = np.zeros(T)
  c = np.concatenate([c_charge, c_discharge, c_energy])

  # Energy balance equality constraints
  A_eq = np.zeros((T, 3 * T))
  b_eq = np.zeros(T)

  for t in range(T):
    A_eq[t, t] = -eta_ch * delta_t
    A_eq[t, T + t] = (1.0 / eta_dis) * delta_t
    A_eq[t, 2 * T + t] = 1.0
    if t > 0:
      A_eq[t, 2 * T + (t - 1)] = -1.0
    else:
      b_eq[0] = initial_soc_pct * capacity_mwh

  # Bounds
  bounds_charge = [(0.0, power_rating_mw) for _ in range(T)]
  bounds_discharge = [(0.0, power_rating_mw) for _ in range(T)]
  bounds_soc = [
      (soc_min_pct * capacity_mwh, soc_max_pct * capacity_mwh) for _ in range(T)
  ]
  bounds = bounds_charge + bounds_discharge + bounds_soc

  res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
  if not res.success:
    raise RuntimeError(f"Optimization failed: {res.message}")

  p_charge = res.x[:T]
  p_discharge = res.x[T : 2 * T]
  soc_energy = res.x[2 * T : 3 * T]
  soc_percent = (soc_energy / capacity_mwh) * 100.0

  return pd.DataFrame({
      "timestamp": timestamps,
      "spot_price_eur_mwh": np.round(spot_prices_eur_mwh, 2),
      "charge_mw": np.round(p_charge, 2),
      "discharge_mw": np.round(p_discharge, 2),
      "net_grid_flow_mw": np.round(p_discharge - p_charge, 2),
      "energy_mwh": np.round(soc_energy, 2),
      "soc_percent": np.round(soc_percent, 1),
      "hourly_gross_pnl_eur": np.round(
          (p_discharge - p_charge) * spot_prices_eur_mwh, 2
      ),
      "hourly_degradation_eur": np.round(
          (p_charge + p_discharge) * degradation_cost_per_mwh, 2
      ),
  })
