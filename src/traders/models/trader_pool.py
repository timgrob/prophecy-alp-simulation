from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import TraderConfig
from .trader import Trader

if TYPE_CHECKING:
    from src.markets.models.market import Market


class TraderPool:
    """Collection of Trader instances; orchestrates the per-step flow."""

    def __init__(self, market: Market, cfg: TraderConfig) -> None:
        self._market = market
        self._cfg = cfg
        self._traders = [
            Trader(
                account=market._new_account(f"T{i + 1}", cfg.trader_cash),
                informed=(market.rng.random() < cfg.informed_frac),
                cfg=cfg,
            )
            for i in range(cfg.n_traders)
        ]

    def run_step(self) -> None:
        for _ in range(self._cfg.flow_per_step):
            trader = self._market.rng.choice(self._traders)
            trader.act(self._market)
