from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MMConfig:
    half_spread: int = 3
    levels: int = 4
    level_step: int = 1
    size_mult: float = 1.0
    mm_capital: float = 100_000.0
    buffer: float = 2_000.0
    skew_cents: float = 8.0
    requote_threshold: int = 1
    no_quote_threshold: int = 5  # stop quoting when fair < this or > (100 - this)
    informed_frac: float = 0.3   # MM's estimate of informed-trader fraction (BinaryAwareMM only)
    sigma: float = 10.0          # Gaussian width in cents (FullBookLP)
    resolution_taper_k: float = 4.0  # resolution taper aggressiveness (FullBookLP)
