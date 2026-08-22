import numpy as np


def compute_marginal_degradation_cost(
    capex_per_mwh_eur: float = 180000.0,
    cycle_life_80_dod: int = 5000,
    battery_capacity_mwh: float = 20.0,
    target_soh_loss_pct: float = 0.20,
    nominal_dod: float = 0.80,
) -> float:
  """Calculates the marginal cell degradation cost per throughput MWh

  based on total battery CAPEX and rated cycle life.
  """
  total_deliverable_energy_mwh = (
      cycle_life_80_dod * battery_capacity_mwh * nominal_dod
  )
  depreciable_capex = capex_per_mwh_eur * target_soh_loss_pct
  return float(depreciable_capex / total_deliverable_energy_mwh)
