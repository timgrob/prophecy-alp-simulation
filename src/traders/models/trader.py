from __future__ import annotations

from typing import TYPE_CHECKING

from src.markets.models.order import BUY_DOWN, BUY_UP, SELL_DOWN, SELL_UP, _clamp
from ..config import TraderConfig

if TYPE_CHECKING:
    from src.markets.models.account import Account
    from src.markets.models.market import Market


class Trader:
    """Single virtual market participant."""

    def __init__(self, account: Account, informed: bool, cfg: TraderConfig) -> None:
        self._account = account
        self._informed = informed
        self._cfg = cfg

    def act(self, market: Market) -> None:
        m = market
        c = self._cfg
        t = self._account
        noise = 1.5 if self._informed else c.trader_noise
        belief = _clamp(m.fair + m.rng.gauss(0, noise), 1, 99)
        size = max(1.0, m.rng.gauss(c.avg_size, c.avg_size * 0.3))

        if t.up > 1 and m.rng.random() < 0.12:
            self._submit(m, SELL_UP, market_order=True, size=min(size, t.up))
            return
        if t.down > 1 and m.rng.random() < 0.12:
            self._submit(m, SELL_DOWN, market_order=True, size=min(size, t.down))
            return

        wants_up = belief >= (m.book.mid() or m.fair)
        is_market = m.rng.random() < c.market_frac
        if wants_up:
            intent = BUY_UP
            price = 99 if is_market else int(round(belief))
        else:
            intent = BUY_DOWN
            price = 1 if is_market else int(round(belief))
        self._submit(m, intent, market_order=is_market, size=size, price=price)

    def _submit(self, market: Market, intent: str, market_order: bool,
                size: float, price: int | None = None) -> None:
        m = market
        t = self._account
        if price is None:
            price = 99 if intent in (BUY_UP, SELL_DOWN) else 1
        order, cases = m.submit(t.name, intent, price, size, allow_rest=not market_order)
        if order is None:
            return
        kind = "mkt" if market_order else "lim"
        verb = {BUY_UP: "buy UP", SELL_UP: "sell UP",
                BUY_DOWN: "buy DOWN", SELL_DOWN: "sell DOWN"}[intent]
        if cases:
            tally = "+".join(cases) if len(set(cases)) > 1 else f"{cases[0]} x{len(cases)}"
            m._log(f"{t.name} {kind} {verb} {size:.0f} @ {m.last}c -> {tally}")
        elif not market_order:
            m._log(f"{t.name} lim {verb} {order.qty:.0f} @ {order.price}c (resting)")
