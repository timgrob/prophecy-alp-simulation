from __future__ import annotations

from typing import TYPE_CHECKING

from src.markets.models.order import EPS, SELL_DOWN, SELL_UP, _clamp
from ..config import MMConfig
from .market_maker import MarketMaker

if TYPE_CHECKING:
    from src.markets.models.market import Market


class BinaryAwareMM(MarketMaker):
    """
    Binary-market-appropriate market maker.

    Spread widens at maximum uncertainty (fair ≈ 50¢) and narrows near resolution
    (fair → 0 or 100¢), inverse to Avellaneda-Stoikov. Inventory skew is weighted
    by P(wrong outcome at resolution) rather than raw token imbalance, so the MM
    only hedges hard when it actually matters.
    """

    def __init__(self, market: Market, cfg: MMConfig) -> None:
        self._market = market
        self._cfg = cfg
        self._oids: list[int] = []
        self._last_quote_fair: float | None = None
        self._requotes = 0
        market.mm = market._new_account("MM", cfg.mm_capital)

    @property
    def requotes(self) -> int:
        return self._requotes

    def requote(self, force: bool = False) -> None:
        m = self._market
        c = self._cfg

        for oid in self._oids:
            m.cancel(oid)
        self._oids.clear()

        if m.fair <= c.no_quote_threshold or m.fair >= 100 - c.no_quote_threshold:
            burnable = min(m.mm.up, m.mm.down)
            if burnable > EPS:
                m.burn_set(m.mm, burnable)
            self._last_quote_fair = m.fair
            return

        if (
            not force
            and self._last_quote_fair is not None
            and abs(m.fair - self._last_quote_fair) < c.requote_threshold
        ):
            return

        deficit = max(0.0, c.buffer - min(m.mm.up, m.mm.down))
        if deficit > EPS:
            m.mint_set(m.mm, deficit)
        excess = min(m.mm.up, m.mm.down) - 2 * c.buffer
        if excess > EPS:
            m.burn_set(m.mm, excess)

        # dynamic spread: widens at 50¢ (max adverse selection), narrows near 0/100¢
        p = m.fair / 100
        uncertainty = 4 * p * (1 - p)  # 1.0 at p=0.5, 0.0 at p=0 or 1
        half_spread = max(1, round(c.half_spread * (1 + c.informed_frac * uncertainty)))

        # risk-weighted reservation price: skew only bites when holding the wrong side
        net_delta = m.mm.up - m.mm.down
        p_wrong = (1 - p) if net_delta > 0 else p
        risk_score = net_delta * p_wrong / max(c.buffer, 1.0)
        res = _clamp(m.fair - c.skew_cents * risk_score, 2, 98)

        per_level = max(1.0, (c.buffer / max(c.levels, 1)) * 0.4 * c.size_mult)
        for k in range(c.levels):
            ask_p = int(round(res + half_spread + k * c.level_step))
            bid_p = int(round(res - half_spread - k * c.level_step))
            size = per_level * (1.0 - 0.12 * k)
            if 1 <= ask_p <= 99:
                o, _ = m.submit("MM", SELL_UP, ask_p, size, allow_rest=True)
                if o is not None:
                    self._oids.append(o.oid)
            if 1 <= bid_p <= 99:
                o, _ = m.submit("MM", SELL_DOWN, bid_p, size, allow_rest=True)
                if o is not None:
                    self._oids.append(o.oid)

        self._requotes += 1
        self._last_quote_fair = m.fair

    def equity(self) -> float:
        m = self._market
        f = m.fair / 100
        return m.mm.cash + m.mm.up * f + m.mm.down * (1 - f)

    def inventory_value(self) -> float:
        m = self._market
        f = m.fair / 100
        return m.mm.up * f + m.mm.down * (1 - f)

    def pnl(self) -> float:
        return self.equity() - self._cfg.mm_capital

    def net_delta(self) -> float:
        return self._market.mm.up - self._market.mm.down
