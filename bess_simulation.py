"""Reproducible 7-day BESS arbitrage simulation on synthetic prices.

Prices are synthetic (seed 42), not market data. Run from repo root:
    python bess_simulation.py
"""
import numpy as np
import pandas as pd

from src.arbitrage_optimizer import optimize_bess_dispatch

CAPACITY_MWH = 20.0


def synthetic_prices(days: int = 7, seed: int = 42):
    dates = pd.date_range("2026-08-01", periods=24 * days, freq="h")
    np.random.seed(seed)
    h = dates.hour.to_numpy()
    dow = dates.day_of_week.to_numpy()
    base = 75 + np.maximum(0, np.sin((h - 17) * np.pi / 4)) * 70
    base = base - np.maximum(0, np.sin((h - 6) * np.pi / 12)) * 55
    prices = base * np.where(dow >= 5, 0.75, 1.0)
    prices = prices + np.random.normal(0, 8, len(dates))
    prices[h == 13] -= 35
    return dates, prices


def main():
    dates, prices = synthetic_prices()
    df = optimize_bess_dispatch(prices, dates, capacity_mwh=CAPACITY_MWH)
    gross = df.hourly_gross_pnl_eur.sum()
    deg = df.hourly_degradation_eur.sum()
    efc = (df.charge_mw.sum() + df.discharge_mw.sum()) / (2 * CAPACITY_MWH)
    print(f"gross {gross:.2f} EUR | degradation {deg:.2f} EUR | net {gross - deg:.2f} EUR | EFC {efc:.2f}")
    df.to_csv("bess_arbitrage_simulation_2026.csv", index=False)


if __name__ == "__main__":
    main()
