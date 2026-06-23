from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TraderConfig:
    n_traders: int = 12
    trader_cash: float = 1e7
    informed_frac: float = 0.4
    trader_noise: float = 6.0
    market_frac: float = 0.6
    flow_per_step: int = 3
    avg_size: float = 25.0
