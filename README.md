# UP/DOWN single-book CLOB — Prophecy simulator

A simulator of a binary prediction market: **one order book** quotes the UP token price
in cents (1–99¢), and DOWN folds into the same book by inversion (*buy DOWN = sell UP*,
*sell DOWN = buy UP*). UP + DOWN always sum to 100¢. A **market maker provides the
liquidity** and **virtual traders generate the flow** that crosses its quotes. The market
resolves every N steps to a winner; the cycle then repeats for the next epoch.

## Run

```bash
uv run streamlit run app.py
```

Or with plain pip:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## What you're looking at

- **UP order book** — asks (red) above, bids (green) below, depth bars scaled to size.
  The bid side is UP-buyers + DOWN-sellers; the ask side is UP-sellers + DOWN-buyers.
- **Probability bar** — live mid price rendered as P(UP) / P(DOWN).
- **Market-maker panel** — cash, UP/DOWN inventory, complete sets, **net delta**
  (unhedged exposure), inventory mark, equity, and live **P&L**.
- **Price history** — fair value vs book mid vs last trade.
- **Epoch history** — each resolved epoch's winner and fair-at-resolution.
- **Event log** — every fill tagged with its settlement primitive: `transfer-UP`,
  `transfer-DOWN`, `MINT` (a UP-buyer crossing a DOWN-buyer creates a pair), or
  `BURN` (a UP-seller crossing a DOWN-seller destroys one).

## Market maker strategies

Three strategies are selectable from the dashboard:

### InventorySkew (default)
Classic ladder MM. Posts a configurable number of price levels symmetrically around a
reservation price, where the reservation price is shifted to offload the over-held side:

```
reservation = fair − skew_cents × net_delta / buffer
```

### BinaryAware
Extends InventorySkew with two binary-market-aware adjustments:

- **Dynamic spread** — widens near 50¢ (maximum outcome uncertainty) where adverse
  selection from informed traders is highest:
  `half_spread × (1 + informed_frac × 4·p·(1−p))`
- **Risk-weighted skew** — scales inventory skew by the probability of being wrong:
  `risk_score = net_delta × P(wrong outcome) / buffer`

### FullBookLP
A full-range liquidity provider that quotes up to 49 levels per side with a
**Gaussian size distribution** concentrated around the fair price.

**Quote placement** — a 1¢ minimum spread prevents self-crossing orders:
- SELL_DOWN bids at: `mid`, `mid−1`, …, `mid−(levels−1)`
- SELL_UP asks at: `mid+1`, `mid+2`, …, `mid+levels`

where `mid = floor(inventory-skewed fair)`.

**Size distribution** — Gaussian centred on `skewed_fair` with width `sigma`:

```
size(p) = exp(−0.5 × ((p − skewed_fair) / sigma)²) × normalised_base
```

Total tokens per side equals `buffer` at full deployment; levels below 1 token are
dropped to avoid dust orders.

**Asymmetric resolution taper** — as the epoch approaches resolution, the LP reduces
exposure on the side likely to win (to avoid selling winning tokens cheaply to informed
traders), while keeping the losing side full (offloading near-worthless tokens for cash
is profitable):

```
taper_ask = exp(−k × progress × P(UP wins))
taper_bid = exp(−k × progress × P(DOWN wins))
```

`k` (`Res. taper k`, default 4.0) controls aggressiveness. Higher k = faster withdrawal
of the dangerous side near resolution. This mirrors how options MMs reduce ITM delta
exposure near expiry.

## Multi-epoch resolution

Set **Resolve / N steps** to a non-zero value (e.g. 200). Every N steps:

1. A pre-determined true outcome (UP or DOWN) is revealed — fair value has been drifting
   toward it throughout the epoch under `convergence_rate`.
2. The market settles: UP token holders receive 100¢ if UP wins, 0¢ otherwise.
3. A new epoch opens with a fresh order book and a newly drawn true outcome.

The **fair value walk** uses a convergent drift:
```
progress = steps_in_epoch / resolution_step   # 0 → 1
drift = convergence_rate × progress × (true_outcome − fair)
```
Noise is halved in the final 20% of the epoch so fair value reliably reaches the
outcome by resolution.

## Controls

| Control | Effect |
|---|---|
| **Start flow / Stop** | Run virtual traders continuously |
| **Step ×1 / ×25** | Advance manually one or 25 steps |
| **Resolve now** | Force-resolve the current epoch immediately |
| **Flush traders** | Cancel all resting trader orders, leaving only MM quotes |
| **Apply & Reset** | Rebuild the market with the current parameter values |
| **Spread (¢)** | Tighten toward 2¢ → more adverse selection; widen → more edge per fill |
| **Levels/side** | Ladder depth (1–8 for InventorySkew/BinaryAware; up to 49 for FullBookLP) |
| **MM buffer** | Target token inventory per side the MM keeps minted |
| **Sigma (¢)** | FullBookLP: Gaussian width — controls how quickly size tapers off from fair |
| **Res. taper k** | FullBookLP: taper aggressiveness near resolution (0 = no taper) |
| **Informed %** | Fraction of traders with private information; raises adverse selection |
| **MM inf. est. %** | BinaryAwareMM: MM's own estimate of informed-trader fraction |
| **Convergence** | Drift strength toward true outcome (0 = pure random walk) |

## Solvency invariant

`backing == supply(UP) == supply(DOWN)` holds every step. UP can only be created paired
with DOWN (`mintSet`) and destroyed paired (`burnSet`), so the book is fully collateralised
by construction. The mid prices of UP and DOWN always sum to 100¢.

## Architecture

```
src/
├── markets/
│   ├── config.py              MarketConfig dataclass
│   └── models/
│       ├── market.py          Market engine: CLOB, settlement, epoch resolution
│       ├── order.py           Order, OrderBook, settlement primitives
│       └── account.py         Account (cash + UP + DOWN balances)
├── market_makers/
│   ├── config.py              MMConfig dataclass (shared by all strategies)
│   └── models/
│       ├── market_maker.py    Abstract base class
│       ├── inventory_skew_mm.py   InventorySkew strategy
│       ├── binary_aware_mm.py     BinaryAware strategy
│       └── full_book_lp.py        FullBookLP strategy
├── traders/
│   ├── config.py              TraderConfig dataclass
│   └── models/
│       ├── trader.py          Individual trader logic
│       └── trader_pool.py     Pool managing all virtual traders
└── static/
    └── styles.py              Streamlit CSS
app.py                         Streamlit dashboard
```

**Order book complexity.** The book is a `SortedDict` of price → FIFO deque: insert/cancel
are `O(log L)` in the number of active price levels (≤ 99), best bid/ask is `O(1)`, and
matching a taker is `O(F)` in the fills it generates. A full step is `O(flow · log L)`.
