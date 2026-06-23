from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from sortedcontainers import SortedDict

BUY_UP = "BUY_UP"
SELL_UP = "SELL_UP"
BUY_DOWN = "BUY_DOWN"
SELL_DOWN = "SELL_DOWN"

INTENT_SIDE = {BUY_UP: "bid", SELL_DOWN: "bid", SELL_UP: "ask", BUY_DOWN: "ask"}
EPS = 1e-9


def _clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass
class Order:
    oid: int
    owner: str
    intent: str
    price: int
    qty: float

    @property
    def side(self) -> str:
        return INTENT_SIDE[self.intent]


class OrderBook:
    def __init__(self) -> None:
        self.bids: SortedDict = SortedDict()
        self.asks: SortedDict = SortedDict()
        self._loc: dict[int, tuple[str, int]] = {}

    def _book(self, side: str) -> SortedDict:
        return self.bids if side == "bid" else self.asks

    def best_bid(self) -> int | None:
        return self.bids.peekitem(-1)[0] if self.bids else None

    def best_ask(self) -> int | None:
        return self.asks.peekitem(0)[0] if self.asks else None

    def mid(self) -> float | None:
        b, a = self.best_bid(), self.best_ask()
        return (a + b) / 2 if (b is not None and a is not None) else None

    def spread(self) -> int | None:
        b, a = self.best_bid(), self.best_ask()
        return (a - b) if (b is not None and a is not None) else None

    def add(self, order: Order) -> None:
        book = self._book(order.side)
        if order.price not in book:
            book[order.price] = deque()
        book[order.price].append(order)
        self._loc[order.oid] = (order.side, order.price)

    def cancel_get(self, oid: int) -> Order | None:
        loc = self._loc.pop(oid, None)
        if loc is None:
            return None
        side, price = loc
        book = self._book(side)
        dq = book.get(price)
        if not dq:
            return None
        found = None
        for i, o in enumerate(dq):
            if o.oid == oid:
                found = o
                del dq[i]
                break
        if not dq:
            del book[price]
        return found

    def levels(self, side: str, n: int) -> list[tuple[int, float]]:
        book = self._book(side)
        items = reversed(book.items()) if side == "bid" else book.items()
        out: list[tuple[int, float]] = []
        for price, dq in items:
            out.append((price, sum(o.qty for o in dq)))
            if len(out) >= n:
                break
        return out
