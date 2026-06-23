from __future__ import annotations

import math
from typing import TYPE_CHECKING

from src.markets.models.order import EPS, SELL_DOWN, SELL_UP, _clamp
from ..config import MMConfig
from .market_maker import MarketMaker

if TYPE_CHECKING:
    from src.markets.models.market import Market

_MIN_SIZE = 1.0  # skip levels below this token quantity to avoid dust orders


class FullBookLP(MarketMaker):
    """
    Gaussian-distributed full-book liquidity provider.

    Quotes `levels` levels per side with a 1¢ minimum spread:
    - SELL_DOWN bids at prices: mid, mid-1, …, mid-(levels-1)
    - SELL_UP   asks at prices: mid+1, mid+2, …, mid+levels
    where mid = floor(inventory-skewed fair value).

    Size at each level follows a Gaussian centred on skewed_fair, normalised
    so that total tokens per side equals cfg.buffer at full taper=1. The taper
    scales the total deployment down near resolution:

        taper_ask = exp(-k × progress × P(UP wins))
        taper_bid = exp(-k × progress × P(DOWN wins))

    When UP is almost certain (fair → 100), asks shrink toward zero (LP stops
    selling winning tokens below face value) while bids stay full (selling
    near-worthless DOWN tokens for cash is profitable). This mirrors how
    options MMs reduce ITM delta exposure near expiry.
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

        if (
            not force
            and self._last_quote_fair is not None
            and abs(m.fair - self._last_quote_fair) < c.requote_threshold
        ):
            return

        # epoch progress for resolution taper (0 at start, 1 at resolution)
        if m.cfg.resolution_step > 0:
            steps_in_epoch = m.step_no % m.cfg.resolution_step or m.cfg.resolution_step
            progress = steps_in_epoch / m.cfg.resolution_step
        else:
            progress = 0.0

        p_up = m.fair / 100.0
        p_down = 1.0 - p_up

        # asymmetric taper: the side likely to win shrinks near resolution
        taper_ask = math.exp(-c.resolution_taper_k * progress * p_up)
        taper_bid = math.exp(-c.resolution_taper_k * progress * p_down)

        # inventory skew: shift the quote centre to reduce the over-held side
        net_delta = m.mm.up - m.mm.down
        skewed_fair = _clamp(
            m.fair - c.skew_cents * net_delta / max(c.buffer, 1.0), 2.0, 98.0
        )
        mid = int(skewed_fair)  # floor — best bid at mid, best ask at mid+1

        sigma = max(c.sigma, 0.5)

        # --- build price lists and raw Gaussian weights -----------------------
        ask_prices = [mid + 1 + k for k in range(c.levels) if mid + 1 + k <= 99]
        bid_prices = [mid - k     for k in range(c.levels) if mid - k >= 1]

        def gauss(p: int) -> float:
            return math.exp(-0.5 * ((p - skewed_fair) / sigma) ** 2)

        ask_g = [gauss(p) for p in ask_prices]
        bid_g = [gauss(p) for p in bid_prices]

        # Normalise Gaussian weights so total per side = buffer at taper=1.
        # Then multiply by the taper so total deployed scales with the taper.
        sum_g_ask = sum(ask_g) or 1.0
        sum_g_bid = sum(bid_g) or 1.0
        ask_base = c.buffer / sum_g_ask * taper_ask
        bid_base = c.buffer / sum_g_bid * taper_bid

        ask_sizes = [(p, g * ask_base) for p, g in zip(ask_prices, ask_g)]
        bid_sizes = [(p, g * bid_base) for p, g in zip(bid_prices, bid_g)]

        # filter dust
        ask_sizes = [(p, s) for p, s in ask_sizes if s >= _MIN_SIZE]
        bid_sizes = [(p, s) for p, s in bid_sizes if s >= _MIN_SIZE]

        # --- token inventory --------------------------------------------------
        up_needed   = sum(s for _, s in ask_sizes)
        down_needed = sum(s for _, s in bid_sizes)

        deficit = max(
            max(0.0, up_needed   - m.mm.up),
            max(0.0, down_needed - m.mm.down),
        )
        if deficit > EPS:
            m.mint_set(m.mm, deficit)

        # burn only when holding substantially more than needed
        excess = min(m.mm.up - up_needed, m.mm.down - down_needed) - c.buffer * 0.5
        if excess > EPS:
            m.burn_set(m.mm, excess)

        # --- post orders ------------------------------------------------------
        for price, size in ask_sizes:
            o, _ = m.submit("MM", SELL_UP, price, size, allow_rest=True)
            if o is not None:
                self._oids.append(o.oid)

        for price, size in bid_sizes:
            o, _ = m.submit("MM", SELL_DOWN, price, size, allow_rest=True)
            if o is not None:
                self._oids.append(o.oid)

        self._requotes += 1
        self._last_quote_fair = m.fair

    def equity(self) -> float:
        m = self._market
        f = m.fair / 100.0
        return m.mm.cash + m.mm.up * f + m.mm.down * (1.0 - f)

    def inventory_value(self) -> float:
        m = self._market
        f = m.fair / 100.0
        return m.mm.up * f + m.mm.down * (1.0 - f)

    def pnl(self) -> float:
        return self.equity() - self._cfg.mm_capital

    def net_delta(self) -> float:
        return self._market.mm.up - self._market.mm.down
