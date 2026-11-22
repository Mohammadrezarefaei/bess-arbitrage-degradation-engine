import numpy as np
import pandas as pd
from src.arbitrage_optimizer import optimize_bess_dispatch
from src.battery_model import compute_marginal_degradation_cost


def test_marginal_degradation_calculation():
  deg_cost = compute_marginal_degradation_cost(
      capex_per_mwh_eur=180000.0,
      cycle_life_80_dod=5000,
      battery_capacity_mwh=20.0,
  )
  assert deg_cost > 0.0
  assert deg_cost < 10.0


def test_bess_energy_conservation_and_bounds():
  timestamps = pd.date_range("2026-08-01", periods=24, freq="h")
  prices = np.sin(np.linspace(0, 2 * np.pi, 24)) * 50.0 + 60.0

  df = optimize_bess_dispatch(
      prices,
      timestamps,
      power_rating_mw=10.0,
      capacity_mwh=20.0,
      soc_min_pct=0.10,
      soc_max_pct=0.90,
  )

  assert len(df) == 24
  assert (df["soc_percent"] >= 9.9).all()
  assert (df["soc_percent"] <= 90.1).all()
  assert (df["charge_mw"] <= 10.0).all()
  assert (df["discharge_mw"] <= 10.0).all()


def _run(prices, **kw):
    ts = pd.date_range("2026-08-01", periods=len(prices), freq="h")
    return optimize_bess_dispatch(np.array(prices, float), ts, **kw)


def test_battery_charges_and_discharges():
    df = _run([20] * 6 + [150] * 6 + [20] * 6 + [150] * 6)
    assert df["charge_mw"].sum() > 1.0
    assert df["discharge_mw"].sum() > 1.0


def test_no_simultaneous_charge_discharge_negative_prices():
    df = _run(([-80] * 6 + [100] * 2) * 3)
    assert (df["charge_mw"] * df["discharge_mw"] < 1e-6).all()


def test_terminal_soc_equals_initial():
    df = _run(
        [20] * 6 + [150] * 6 + [20] * 6 + [150] * 6,
        initial_soc_pct=0.5,
        terminal_soc_pct=0.5,
    )
    assert abs(df["soc_percent"].iloc[-1] - 50.0) < 1e-3


def test_degradation_cost_exact_value():
    cost = compute_marginal_degradation_cost()
    assert abs(cost - 9.0) < 1e-9


def test_degradation_cost_independent_of_capacity():
    vals = [
        compute_marginal_degradation_cost(battery_capacity_mwh=c)
        for c in (2.0, 20.0, 100.0)
    ]
    assert max(vals) - min(vals) < 1e-9
