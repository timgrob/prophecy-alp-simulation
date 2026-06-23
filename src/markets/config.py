from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketConfig:
    init_fair: float = 50.0
    vol: float = 0.6
    tick: int = 1
    seed: int = 0
    log_len: int = 60
    resolution_step: int = 0       # 0 = perpetual; >0 = resolve every N steps
    convergence_rate: float = 3.0  # drift strength toward true outcome (0 = pure random walk)
