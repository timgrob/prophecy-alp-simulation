from __future__ import annotations

import random
from collections import deque
from typing import TYPE_CHECKING

from .account import Account
from .order import (
    EPS, BUY_DOWN, BUY_UP, SELL_DOWN, SELL_UP,
    Order, OrderBook, _clamp,
)
from ..config import MarketConfig

if TYPE_CHECKING:
    from src.market_makers.models.market_maker import MarketMaker
    from src.traders.models.trader_pool import TraderPool


class Market:
    def __init__(self, cfg: MarketConfig) -> None:
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.book = OrderBook()
        self.accounts: dict[str, Account] = {}
        self.backing = 0.0
        self._oid = 0
        self.fair = float(cfg.init_fair)
        self.last: int | None = None
        self.trades = 0
        self.volume = 0.0
        self.epoch_trades = 0
        self.epoch_volume = 0.0
        self.step_no = 0
        self.log: deque[str] = deque(maxlen=cfg.log_len)
        self.history: list[dict] = []
        self.epoch: int = 1
        self.epoch_results: list[dict] = []
        self._true_outcome: float = self._draw_outcome()
        # set by the caller (app.py) after construction
        self.mm: Account | None = None
        self.market_maker: MarketMaker
        self.trader_pool: TraderPool

        self._log(f"market reset · fair {self.fair:.0f}c")

    def _draw_outcome(self) -> float:
        return 100.0 if self.rng.random() < self.cfg.init_fair / 100 else 0.0

    # ---- bookkeeping helpers -------------------------------------------------
    def _new_account(self, name: str, cash: float) -> Account:
        a = Account(name, cash=cash)
        self.accounts[name] = a
        return a

    def _next_oid(self) -> int:
        self._oid += 1
        return self._oid

    def _log(self, msg: str) -> None:
        self.log.appendleft(f"[{self.step_no:>4}] {msg}")

    # ---- complete-set primitives ---------------------------------------------
    def mint_set(self, acc: Account, q: float) -> float:
        q = min(q, acc.cash)
        if q <= EPS:
            return 0.0
        acc.cash -= q
        acc.up += q
        acc.down += q
        self.backing += q
        return q

    def burn_set(self, acc: Account, q: float) -> float:
        q = min(q, acc.up, acc.down)
        if q <= EPS:
            return 0.0
        acc.up -= q
        acc.down -= q
        acc.cash += q
        self.backing -= q
        return q

    # ---- escrow --------------------------------------------------------------
    def _escrow(self, acc: Account, intent: str, price: int, qty: float, sign: int) -> None:
        dp = price / 100
        if intent == BUY_UP:
            acc.cash += sign * qty * dp
        elif intent == BUY_DOWN:
            acc.cash += sign * qty * (1 - dp)
        elif intent == SELL_UP:
            acc.up += sign * qty
        elif intent == SELL_DOWN:
            acc.down += sign * qty

    def _max_affordable(self, acc: Account, intent: str, price: int, qty: float) -> float:
        dp = price / 100
        if intent == BUY_UP:
            return max(0.0, min(qty, acc.cash / dp)) if dp > 0 else 0.0
        if intent == BUY_DOWN:
            return max(0.0, min(qty, acc.cash / (1 - dp))) if dp < 1 else 0.0
        if intent == SELL_UP:
            return max(0.0, min(qty, acc.up))
        if intent == SELL_DOWN:
            return max(0.0, min(qty, acc.down))
        return 0.0

    # ---- settlement: one cross at the maker's price --------------------------
    def _settle(self, B: Order, A: Order, q: float, fp: int) -> str:
        fb = fp / 100
        bacc, aacc = self.accounts[B.owner], self.accounts[A.owner]

        if B.intent == BUY_UP:
            bacc.cash += q * (B.price - fp) / 100
        if A.intent == BUY_DOWN:
            aacc.cash += q * (fp - A.price) / 100

        if B.intent == BUY_UP and A.intent == SELL_UP:
            bacc.up += q
            aacc.cash += q * fb
            case = "transfer-UP"
        elif B.intent == BUY_UP and A.intent == BUY_DOWN:
            bacc.up += q
            aacc.down += q
            self.backing += q
            case = "MINT"
        elif B.intent == SELL_DOWN and A.intent == SELL_UP:
            self.backing -= q
            aacc.cash += q * fb
            bacc.cash += q * (1 - fb)
            case = "BURN"
        else:
            aacc.down += q
            bacc.cash += q * (1 - fb)
            case = "transfer-DOWN"

        self.trades += 1
        self.volume += q
        self.epoch_trades += 1
        self.epoch_volume += q
        self.last = fp
        return case

    # ---- matching ------------------------------------------------------------
    def _match(self, taker: Order) -> tuple[float, list[str]]:
        cases: list[str] = []
        if taker.side == "bid":
            opp = self.book.asks
            def best():
                return opp.peekitem(0) if opp else None
            def crosses(p):
                return taker.price >= p
        else:
            opp = self.book.bids
            def best():
                return opp.peekitem(-1) if opp else None
            def crosses(p):
                return taker.price <= p

        while taker.qty > EPS and opp:
            price, dq = best()
            if not crosses(price):
                break
            maker = dq[0]
            q = min(taker.qty, maker.qty)
            B, A = (taker, maker) if taker.side == "bid" else (maker, taker)
            cases.append(self._settle(B, A, q, price))
            taker.qty -= q
            maker.qty -= q
            if maker.qty <= EPS:
                dq.popleft()
                self.book._loc.pop(maker.oid, None)
                if not dq:
                    del opp[price]
        return taker.qty, cases

    def submit(self, owner: str, intent: str, price: int, qty: float,
               allow_rest: bool) -> tuple[Order | None, list[str]]:
        acc = self.accounts[owner]
        price = int(_clamp(round(price / self.cfg.tick) * self.cfg.tick, 1, 99))
        qty = self._max_affordable(acc, intent, price, qty)
        if qty <= EPS:
            return None, []
        self._escrow(acc, intent, price, qty, sign=-1)
        order = Order(self._next_oid(), owner, intent, price, qty)
        residual, cases = self._match(order)
        if residual > EPS:
            if allow_rest:
                order.qty = residual
                self.book.add(order)
            else:
                self._escrow(acc, intent, price, residual, sign=+1)
        return order, cases

    def cancel(self, oid: int) -> None:
        o = self.book.cancel_get(oid)
        if o is not None:
            self._escrow(self.accounts[o.owner], o.intent, o.price, o.qty, sign=+1)

    def flush_traders(self) -> int:
        oids = [o.oid for o in self._resting_orders() if o.owner != "MM"]
        for oid in oids:
            self.cancel(oid)
        return len(oids)

    # ---- resolution ----------------------------------------------------------
    def resolve(self) -> str:
        for oid in list(self.book._loc.keys()):
            self.cancel(oid)
        winner = "UP" if self._true_outcome == 100.0 else "DOWN"
        for acc in self.accounts.values():
            acc.cash += acc.up if winner == "UP" else acc.down
            acc.up = 0.0
            acc.down = 0.0
        self.backing = 0.0
        self._log(f"RESOLVED epoch {self.epoch} → {winner} wins · fair {self.fair:.1f}¢")
        self.epoch_results.append({
            "epoch": self.epoch,
            "winner": winner,
            "fair_at_resolution": round(self.fair, 2),
            "step": self.step_no,
        })
        self._start_new_epoch()
        return winner

    def _start_new_epoch(self) -> None:
        self.epoch += 1
        self.fair = float(self.cfg.init_fair)
        self._true_outcome = self._draw_outcome()
        self.last = None
        self.epoch_trades = 0
        self.epoch_volume = 0.0
        self.book = OrderBook()
        self._log(f"epoch {self.epoch} started · fair {self.fair:.0f}¢")

    # ---- the simulation step -------------------------------------------------
    def step(self) -> None:
        self.step_no += 1
        if self.cfg.resolution_step > 0:
            steps_in_epoch = self.step_no % self.cfg.resolution_step or self.cfg.resolution_step
            progress = steps_in_epoch / self.cfg.resolution_step
            drift = self.cfg.convergence_rate * progress * (self._true_outcome - self.fair)
            noise_scale = self.cfg.vol * (1.0 - 0.5 * progress)
        else:
            drift = 0.0
            noise_scale = self.cfg.vol
        self.fair = _clamp(self.fair + drift + self.rng.gauss(0, noise_scale), 1, 99)
        self.market_maker.requote(force=True)
        self.trader_pool.run_step()
        self.history.append({
            "step": self.step_no,
            "epoch": self.epoch,
            "fair": round(self.fair, 2),
            "mid": self.book.mid(),
            "last": self.last,
        })
        if self.cfg.resolution_step > 0 and self.step_no % self.cfg.resolution_step == 0:
            self.resolve()

    # ---- solvency readouts ---------------------------------------------------
    def _resting_orders(self):
        for book in (self.book.bids, self.book.asks):
            for dq in book.values():
                yield from dq

    def _escrowed_tokens(self) -> tuple[float, float]:
        up = sum(o.qty for o in self._resting_orders() if o.intent == SELL_UP)
        down = sum(o.qty for o in self._resting_orders() if o.intent == SELL_DOWN)
        return up, down

    def total_up(self) -> float:
        return sum(a.up for a in self.accounts.values()) + self._escrowed_tokens()[0]

    def total_down(self) -> float:
        return sum(a.down for a in self.accounts.values()) + self._escrowed_tokens()[1]

    def check_invariant(self, tol: float = 1e-6) -> bool:
        return (abs(self.backing - self.total_up()) < tol
                and abs(self.backing - self.total_down()) < tol)
