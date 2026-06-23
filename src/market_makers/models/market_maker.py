from __future__ import annotations

from abc import ABC, abstractmethod


class MarketMaker(ABC):
    """Abstract interface for market-making strategies.

    Subclasses receive the Market and an MMConfig at construction time and are
    responsible for posting and maintaining quotes via requote(). To add a new
    strategy: subclass MarketMaker, implement all abstract methods, place the
    file in src/market_makers/models/, and export it from src/market_makers/__init__.py.
    """

    @abstractmethod
    def requote(self, force: bool = False) -> None:
        """Cancel stale quotes and post a fresh ladder."""

    @abstractmethod
    def equity(self) -> float:
        """Mark-to-fair total value of the MM account."""

    @abstractmethod
    def inventory_value(self) -> float:
        """Mark-to-fair value of token holdings only (excludes cash)."""

    @abstractmethod
    def pnl(self) -> float:
        """Equity minus initial capital."""

    @abstractmethod
    def net_delta(self) -> float:
        """Unhedged directional exposure: UP held minus DOWN held."""

    @property
    @abstractmethod
    def requotes(self) -> int:
        """Total number of requote cycles executed."""
