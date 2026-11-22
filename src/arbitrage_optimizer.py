
import numpy as np
import pandas as pd
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import lil_matrix

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
    terminal_soc_pct: float | None = None,
    capex_per_mwh_eur: float = 180000.0,
    dt_hours: float = 1.0,
) -> pd.DataFrame:
    """Optimize BESS arbitrage using a mixed-integer linear program."""

    prices = np.asarray(spot_prices_eur_mwh, dtype=float)
    timestamps = pd.DatetimeIndex(timestamps)

    if prices.ndim != 1 or len(prices) == 0:
        raise ValueError("Prices must be a non-empty 1D array.")

    T = len(prices)

    if len(timestamps) != T:
        raise ValueError("Prices and timestamps must have equal lengths.")

    if not np.isfinite(prices).all():
        raise ValueError("Prices must contain only finite values.")

    if power_rating_mw <= 0 or capacity_mwh <= 0:
        raise ValueError("Power and capacity must be positive.")

    if dt_hours <= 0:
        raise ValueError("dt_hours must be positive.")

    if not 0 < round_trip_efficiency <= 1:
        raise ValueError("Round-trip efficiency must be in (0, 1].")

    if not 0 <= soc_min_pct < soc_max_pct <= 1:
        raise ValueError("Invalid SoC limits.")

    if not soc_min_pct <= initial_soc_pct <= soc_max_pct:
        raise ValueError("Initial SoC is outside permitted limits.")

    if terminal_soc_pct is None:
        terminal_soc_pct = initial_soc_pct

    if not soc_min_pct <= terminal_soc_pct <= soc_max_pct:
        raise ValueError("Terminal SoC is outside permitted limits.")

    eta_ch = np.sqrt(round_trip_efficiency)
    eta_dis = np.sqrt(round_trip_efficiency)

    degradation_cost = compute_marginal_degradation_cost(
        capex_per_mwh_eur=capex_per_mwh_eur,
        battery_capacity_mwh=capacity_mwh,
    )

    # Variable order: charge, discharge, energy, binary mode
    n = 4 * T
    charge_idx = np.arange(T)
    discharge_idx = np.arange(T, 2 * T)
    energy_idx = np.arange(2 * T, 3 * T)
    mode_idx = np.arange(3 * T, 4 * T)

    # Objective: minimize energy procurement - sales + degradation
    objective = np.zeros(n)
    objective[charge_idx] = (
        prices + degradation_cost
    ) * dt_hours
    objective[discharge_idx] = (
        -prices + degradation_cost
    ) * dt_hours

    # Variable bounds
    lower = np.zeros(n)
    upper = np.full(n, np.inf)

    upper[charge_idx] = power_rating_mw
    upper[discharge_idx] = power_rating_mw

    lower[energy_idx] = soc_min_pct * capacity_mwh
    upper[energy_idx] = soc_max_pct * capacity_mwh

    upper[mode_idx] = 1.0

    integrality = np.zeros(n, dtype=int)
    integrality[mode_idx] = 1

    # Equality constraints: energy balance and terminal SoC
    A_eq = lil_matrix((T + 1, n))
    b_eq = np.zeros(T + 1)

    for t in range(T):
        A_eq[t, charge_idx[t]] = -eta_ch * dt_hours
        A_eq[t, discharge_idx[t]] = (
            dt_hours / eta_dis
        )
        A_eq[t, energy_idx[t]] = 1.0

        if t == 0:
            b_eq[t] = initial_soc_pct * capacity_mwh
        else:
            A_eq[t, energy_idx[t - 1]] = -1.0

    A_eq[T, energy_idx[-1]] = 1.0
    b_eq[T] = terminal_soc_pct * capacity_mwh

    equality = LinearConstraint(
        A_eq.tocsr(), b_eq, b_eq
    )

    # Binary operating mode:
    # charge <= Pmax * mode
    # discharge <= Pmax * (1 - mode)
    A_mode = lil_matrix((2 * T, n))
    mode_lb = np.full(2 * T, -np.inf)
    mode_ub = np.zeros(2 * T)

    for t in range(T):
        A_mode[2 * t, charge_idx[t]] = 1.0
        A_mode[2 * t, mode_idx[t]] = -power_rating_mw

        A_mode[2 * t + 1, discharge_idx[t]] = 1.0
        A_mode[2 * t + 1, mode_idx[t]] = power_rating_mw
        mode_ub[2 * t + 1] = power_rating_mw

    operating_mode = LinearConstraint(
        A_mode.tocsr(), mode_lb, mode_ub
    )

    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=[equality, operating_mode],
    )

    if not result.success or result.x is None:
        raise RuntimeError(
            f"MILP optimization failed: {result.message}"
        )

    charge = result.x[charge_idx]
    discharge = result.x[discharge_idx]
    energy = result.x[energy_idx]

    gross_pnl = (
        discharge - charge
    ) * prices * dt_hours

    degradation = (
        charge + discharge
    ) * degradation_cost * dt_hours

    return pd.DataFrame({
        "timestamp": timestamps,
        "spot_price_eur_mwh": prices,
        "charge_mw": charge,
        "discharge_mw": discharge,
        "net_grid_flow_mw": discharge - charge,
        "energy_mwh": energy,
        "soc_percent": energy / capacity_mwh * 100.0,
        "hourly_gross_pnl_eur": gross_pnl,
        "hourly_degradation_eur": degradation,
    })

