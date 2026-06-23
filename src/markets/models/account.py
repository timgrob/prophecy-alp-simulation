from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    name: str
    cash: float = 0.0
    up: float = 0.0
    down: float = 0.0
