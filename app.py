"""
UP/DOWN single-book CLOB — Streamlit dashboard.

A market maker provides the liquidity (fair value -> spread -> inventory skew ->
re-quote); virtual traders generate the order flow that crosses its quotes. Run:

    uv run streamlit run app.py
"""
import time

import pandas as pd
import streamlit as st

from src.market_makers import BinaryAwareMM, FullBookLP, InventorySkewMM, MMConfig
from src.markets import Market, MarketConfig
from src.static.styles import _CSS
from src.traders import TraderConfig, TraderPool

# ---- Streamlit app -----------------------------------------------------------
st.set_page_config(
    page_title="Prophecy · UP/DOWN CLOB",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(_CSS, unsafe_allow_html=True)


# ---- session helpers ---------------------------------------------------------
def build_market() -> Market:
    s = st.session_state
    spread = max(2, int(s.spread))

    market_cfg = MarketConfig(
        init_fair=float(s.init_fair),
        vol=float(s.vol),
        tick=int(s.tick),
        seed=int(s.seed),
        resolution_step=int(s.resolution_step),
        convergence_rate=float(s.convergence_rate),
    )
    mm_cfg = MMConfig(
        half_spread=max(1, spread // 2),
        levels=int(s.levels),
        level_step=int(s.level_step),
        size_mult=float(s.size_mult),
        buffer=float(s.buffer),
        no_quote_threshold=int(s.no_quote_threshold),
        informed_frac=float(s.mm_informed_est) / 100.0,
        sigma=float(s.sigma),
        resolution_taper_k=float(s.resolution_taper_k),
    )
    trader_cfg = TraderConfig(
        flow_per_step=int(s.flow),
        avg_size=float(s.avg_size),
        informed_frac=float(s.informed) / 100.0,
    )

    m = Market(market_cfg)
    if s.mm_strategy == "BinaryAware":
        m.market_maker = BinaryAwareMM(m, mm_cfg)
    elif s.mm_strategy == "FullBookLP":
        m.market_maker = FullBookLP(m, mm_cfg)
    else:
        m.market_maker = InventorySkewMM(m, mm_cfg)
    m.trader_pool = TraderPool(m, trader_cfg)
    m.market_maker.requote(force=True)
    return m


def reset() -> None:
    st.session_state.market = build_market()
    st.session_state.running = False


# ---- session bootstrap -------------------------------------------------------
_DEFAULTS = dict(spread=6, levels=4, level_step=1, tick=1, size_mult=1.0,
                 buffer=2000, init_fair=50, vol=0.6, flow=3, avg_size=25,
                 informed=30, seed=0, view_levels=8, show_empty=False,
                 resolution_step=0, no_quote_threshold=5, convergence_rate=3.0,
                 mm_strategy="InventorySkew", mm_informed_est=30,
                 sigma=10.0, resolution_taper_k=4.0)
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

if "market" not in st.session_state:
    reset()

# ---- page header -------------------------------------------------------------
st.markdown(
    '<div class="site-header">'
    '<div class="site-title">'
    'Prophecy<span class="dot">·</span>UP / DOWN<span class="dot">·</span>CLOB'
    '</div>'
    '<div class="site-sub">'
    'single-book · inventory-skew market maker · binary prediction market'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ---- controls ----------------------------------------------------------------
def _group_label(text: str) -> str:
    return (
        f'<div style="font-family:ui-sans-serif,system-ui,sans-serif;font-size:10px;'
        f'font-weight:600;letter-spacing:0.1em;color:#444;text-transform:uppercase;'
        f'margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #1c1c1c;">'
        f'{text}</div>'
    )

g_market, g_mm, g_actions = st.columns([7, 6, 2.2])

with g_market:
    st.markdown(_group_label("Market &amp; Order Book"), unsafe_allow_html=True)
    mc = st.columns(5)
    mc[0].number_input("Init fair (¢)", 1, 99, key="init_fair")
    mc[1].number_input("Fair vol (¢)", 0.0, 5.0, key="vol", step=0.1)
    mc[2].number_input("Avg size", 1, 200, key="avg_size")
    mc[3].number_input("Flow/step", 1, 20, key="flow")
    mc[4].number_input("Informed %", 0, 100, key="informed", step=5)

    oc = st.columns(5)
    oc[0].number_input("Tick (¢)", 1, 5, key="tick")
    oc[1].number_input("View levels", 1, 50, key="view_levels")
    oc[2].number_input("Resolve / N steps", 0, 10000, key="resolution_step", step=100,
                       help="0 = never auto-resolves. Set to e.g. 200 to resolve every 200 steps.")
    oc[3].number_input("Convergence", 0.0, 10.0, key="convergence_rate", step=0.5,
                       help="Drift strength toward the true outcome as epoch progresses. 0 = pure random walk.")

with g_mm:
    st.markdown(_group_label("Market Maker"), unsafe_allow_html=True)
    mms = st.columns(1)
    mms[0].selectbox("Strategy", ["InventorySkew", "BinaryAware", "FullBookLP"], key="mm_strategy")

    mmb = st.columns(5)
    mmb[0].number_input("Levels/side", 1, 50, key="levels")
    mmb[1].number_input("Level step (¢)", 1, 10, key="level_step")
    mmb[2].number_input("Size mult", 0.2, 5.0, key="size_mult", step=0.2)
    mmb[3].number_input("MM buffer", 200, 20000, key="buffer", step=200)

    mm = st.columns(5)
    mm[0].number_input("Spread (¢)", 2, 40, key="spread", step=2)
    mm[1].number_input("Stop-quote ¢", 1, 20, key="no_quote_threshold")
    mm[2].number_input("MM inf. est. %", 0, 100, key="mm_informed_est", step=5,
                        help="BinaryAwareMM: MM's own estimate of informed-trader fraction.")
    mm[3].number_input("Sigma (¢)", 1.0, 50.0, key="sigma", step=1.0,
                        help="FullBookLP: Gaussian width — controls how fast size decreases further from fair.")
    mm[4].number_input("Res. taper k", 0.0, 10.0, key="resolution_taper_k", step=0.5,
                        help="FullBookLP: resolution taper aggressiveness (0 = no taper).")

with g_actions:
    st.markdown(_group_label("Controls"), unsafe_allow_html=True)
    if st.button("Apply & Reset", use_container_width=True):
        reset()
        st.rerun()
    running = st.session_state.running
    if st.button("⏸ Stop" if running else "▶ Start flow", use_container_width=True):
        st.session_state.running = not running
        st.rerun()
    if st.button("Step ×25", use_container_width=True):
        for _ in range(25):
            st.session_state.market.step()

m: Market = st.session_state.market

# advance one frame while running (loop is closed at the bottom of the script)
if st.session_state.running:
    m.step()


# ---- dynamic: atmosphere + probability bar -----------------------------------
def _atmos_bg(mid: float) -> str:
    """Book-panel background: subtle directional glow at ±10pp extremes."""
    t = mid / 100
    if t > 0.6:
        a = min((t - 0.6) * 0.6, 0.07)
        return (f"radial-gradient(ellipse at 85% 85%, "
                f"rgba(97,234,125,{a:.3f}) 0%, transparent 60%), #141414")
    if t < 0.4:
        a = min((0.4 - t) * 0.6, 0.07)
        return (f"radial-gradient(ellipse at 15% 85%, "
                f"rgba(220,11,74,{a:.3f}) 0%, transparent 60%), #141414")
    return "#141414"


def prob_bar_html(mkt: Market) -> str:
    mid = mkt.book.mid() if mkt.book.mid() is not None else mkt.fair
    pct = int(round(mid))
    sp = mkt.book.spread()
    last_str = f"{mkt.last}¢" if mkt.last is not None else "—"
    sp_str = f"{sp}¢" if sp is not None else "—"
    return (
        '<div class="prob-section">'
        '<div class="prob-header">'
        f'<span class="prob-side-label down">P(DOWN)&nbsp;{100 - pct}%</span>'
        '<div class="prob-center">'
        f'<div class="prob-mid-val">{mid:.1f}<span class="prob-mid-unit">¢</span></div>'
        f'<div class="prob-meta-line">spread&nbsp;{sp_str}&nbsp;·&nbsp;last&nbsp;{last_str}&nbsp;·&nbsp;step&nbsp;{mkt.step_no:,}</div>'
        '</div>'
        f'<span class="prob-side-label up">P(UP)&nbsp;{pct}%</span>'
        '</div>'
        '<div class="prob-track">'
        '<div class="prob-spectrum"></div>'
        f'<div class="prob-needle" style="left:{mid:.2f}%"></div>'
        '</div>'
        '</div>'
    )


# ---- order-book ladder -------------------------------------------------------
def ladder_html(mkt: Market, view_levels: int = 8, show_empty: bool = False) -> str:
    if show_empty:
        tick = mkt.cfg.tick
        ba, bb = mkt.book.best_ask(), mkt.book.best_bid()
        ask_prices = range(ba, ba + view_levels * tick, tick) if ba is not None else []
        bid_prices = range(bb, bb - view_levels * tick, -tick) if bb is not None else []
        asks = [(p, sum(o.qty for o in mkt.book.asks.get(p, []))) for p in ask_prices]
        bids = [(p, sum(o.qty for o in mkt.book.bids.get(p, []))) for p in bid_prices]
    else:
        asks = mkt.book.levels("ask", view_levels)
        bids = mkt.book.levels("bid", view_levels)
    sizes = [s for _, s in asks + bids if s > 0] or [1.0]
    smax = max(sizes)

    def row(side: str, price: int, size: float) -> str:
        empty = size <= 0
        w = 0 if empty else max(4, int(96 * size / smax))
        price_style = ' style="color:#2f2f2f"' if empty else ""
        size_str = "" if empty else f"{size:,.0f}"
        return (
            f'<div class="book-row {side}">'
            f'<span class="book-price"{price_style}>{price}¢</span>'
            f'<span class="book-size">{size_str}</span>'
            f'<div class="book-bar-track">'
            f'<div class="book-bar-fill" style="width:{w}%"></div>'
            f'</div>'
            f'</div>'
        )

    html = "".join(row("ask", p, s) for p, s in reversed(asks))

    sp = mkt.book.spread()
    mid = mkt.book.mid()
    mid_html = (f'<span class="spread-mid-num">{mid:.1f}¢</span>'
                f'<span class="spread-prob">&nbsp;·&nbsp;P(UP)&nbsp;{mid:.0f}%</span>'
                if mid is not None else '<span class="spread-mid-num">—</span>')
    sp_str = f"{sp}¢" if sp is not None else "—"
    html += (f'<div class="spread-divider">spread&nbsp;{sp_str}'
             f'&nbsp;&nbsp;{mid_html}</div>')

    html += "".join(row("bid", p, s) for p, s in bids)
    return html


def book_meta_html(mkt: Market) -> str:
    bb, ba = mkt.book.best_bid(), mkt.book.best_ask()
    last = f"{mkt.last}¢" if mkt.last is not None else "—"
    bb_s = f"{bb}¢" if bb is not None else "—"
    ba_s = f"{ba}¢" if ba is not None else "—"
    down_bid = f"{100 - ba}¢" if ba is not None else "—"
    down_ask = f"{100 - bb}¢" if bb is not None else "—"
    return (
        '<div class="book-meta">'
        f'fair&nbsp;<b>{mkt.fair:.1f}¢</b>'
        f'&nbsp;&nbsp;bid&nbsp;<b>{bb_s}</b>'
        f'&nbsp;&nbsp;ask&nbsp;<b>{ba_s}</b>'
        f'&nbsp;&nbsp;last&nbsp;<b>{last}</b>'
        f'&nbsp;&nbsp;DOWN&nbsp;bid&nbsp;<b>{down_bid}</b>'
        f'&nbsp;&nbsp;DOWN&nbsp;ask&nbsp;<b>{down_ask}</b>'
        '</div>'
    )


# ---- MM state + stats --------------------------------------------------------
def kv(k: str, v: str, cls: str = "") -> str:
    return (f'<div class="kv"><span class="k">{k}</span>'
            f'<span class="v {cls}">{v}</span></div>')


def mm_panel_html(mkt: Market) -> str:
    mm = mkt.market_maker
    pnl = mm.pnl()
    pnl_cls = "pos" if pnl >= 0 else "neg"
    pnl_sign = "+" if pnl >= 0 else ""
    nd = mm.net_delta()
    nd_cls = "pos" if nd >= 0 else "neg"
    sets = min(mkt.mm.up, mkt.mm.down)
    return (
        '<div class="panel">'
        # P&L hero
        '<div class="pnl-hero">'
        '<div class="pnl-hero-label">MM P&amp;L</div>'
        f'<div class="pnl-hero-val {pnl_cls}">{pnl_sign}{pnl:,.2f}</div>'
        f'<div class="pnl-hero-sub">'
        f'equity&nbsp;{mm.equity():,.1f}&nbsp;·&nbsp;'
        f'inv&nbsp;{mm.inventory_value():,.1f}&nbsp;·&nbsp;'
        f'requotes&nbsp;{mm.requotes:,}'
        f'</div>'
        '</div>'
        # details
        '<div class="panel-label">Market-maker state</div>'
        + kv("Cash (USDso)", f"{mkt.mm.cash:,.1f}")
        + kv("UP held", f"{mkt.mm.up:,.1f}")
        + kv("DOWN held", f"{mkt.mm.down:,.1f}")
        + kv("Complete sets", f"{sets:,.1f}")
        + kv("Net Δ (UP−DOWN)", f"{nd:+,.1f}", nd_cls)
        + kv("Fair", f"{mkt.fair:.1f}¢")
        + kv("Hub backing", f"{mkt.backing:,.1f}")
        + '</div>'
    )


def stats_panel_html(mkt: Market) -> str:
    ok = "✓" if mkt.check_invariant() else "✗"
    last_result = mkt.epoch_results[-1] if mkt.epoch_results else None
    last_str = (
        f"{last_result['winner']} (epoch {last_result['epoch']}, "
        f"fair {last_result['fair_at_resolution']}¢)"
        if last_result else "—"
    )
    steps_until = ""
    if mkt.cfg.resolution_step > 0:
        remaining = mkt.cfg.resolution_step - (mkt.step_no % mkt.cfg.resolution_step)
        steps_until = f"{remaining:,} steps"
    return (
        '<div class="panel"><div class="panel-label">Market stats</div>'
        + kv("Step", f"{mkt.step_no:,}")
        + kv("Epoch", f"{mkt.epoch:,}")
        + (kv("Next resolution", steps_until) if steps_until else "")
        + kv("Last resolved", last_str)
        + kv("Epoch trades / vol", f"{mkt.epoch_trades:,} / {mkt.epoch_volume:,.0f}")
        + kv("Total trades / vol", f"{mkt.trades:,} / {mkt.volume:,.0f}")
        + kv("Solvent (backing = supply)", ok)
        + '</div>'
    )


def epoch_history_html(mkt: Market) -> str:
    results = list(reversed(mkt.epoch_results[-10:]))
    if not results:
        inner = '<div style="color:#444;font-size:12px;padding:6px 0">— no resolved epochs yet —</div>'
    else:
        inner = ""
        for r in results:
            wcolor = "#61ea7d" if r["winner"] == "UP" else "#dc0b4a"
            arrow = "↑" if r["winner"] == "UP" else "↓"
            inner += (
                f'<div class="kv">'
                f'<span class="k">Epoch {r["epoch"]}</span>'
                f'<span class="v" style="color:{wcolor}">'
                f'{arrow} {r["winner"]}'
                f'<span style="color:#444">'
                f'&nbsp;·&nbsp;step {r["step"]:,}&nbsp;·&nbsp;fair {r["fair_at_resolution"]}¢'
                f'</span></span></div>'
            )
    return (
        '<div class="panel"><div class="panel-label">Epoch history</div>'
        + inner + '</div>'
    )


# ---- event log ---------------------------------------------------------------
def log_panel_html(mkt: Market) -> str:
    rows = []
    for entry in list(mkt.log)[:40]:
        safe = (entry.replace("&", "&amp;")
                     .replace("<", "&lt;")
                     .replace(">", "&gt;"))
        if "RESOLVED" in entry:
            cls = "log-resolve"
        elif "epoch" in entry and "started" in entry:
            cls = "log-epoch"
        elif "MINT" in entry:
            cls = "log-mint"
        elif "BURN" in entry:
            cls = "log-burn"
        elif "transfer" in entry:
            cls = "log-transfer"
        else:
            cls = "log-default"
        parts = safe.split("] ", 1)
        if len(parts) == 2:
            safe = f'<span class="log-step">{parts[0]}]</span> {parts[1]}'
        rows.append(f'<div class="log-row {cls}">{safe}</div>')

    inner = "\n".join(rows) if rows else '<div class="log-row log-default">(no events yet)</div>'
    return (
        '<div class="panel"><div class="panel-label">Event log</div>'
        f'<div class="log-wrap">{inner}</div>'
        '</div>'
    )


# ---- render ------------------------------------------------------------------
mid_val = m.book.mid() if m.book.mid() is not None else m.fair
atmos_bg = _atmos_bg(mid_val)

st.markdown(prob_bar_html(m), unsafe_allow_html=True)

left, right = st.columns([1.4, 1])

with left:
    show_empty = st.checkbox("Show empty levels", key="show_empty")
    st.markdown(
        f'<div class="panel book-panel" style="background:{atmos_bg};">'
        '<div class="panel-label">UP order book'
        '&nbsp;·&nbsp;asks = buy DOWN / sell UP'
        '&nbsp;·&nbsp;bids = buy UP / sell DOWN</div>'
        + book_meta_html(m)
        + ladder_html(m, view_levels=int(st.session_state.view_levels),
                      show_empty=show_empty)
        + '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="chart-label">Price history (¢) — fair · mid · last</div>',
                unsafe_allow_html=True)
    hist = pd.DataFrame(m.history)
    if not hist.empty:
        st.line_chart(hist.set_index("step")[["fair", "mid", "last"]], height=220)
    else:
        st.caption("Start the flow or step the market to populate the chart.")

with right:
    st.markdown(mm_panel_html(m), unsafe_allow_html=True)
    st.markdown(stats_panel_html(m), unsafe_allow_html=True)
    st.markdown(epoch_history_html(m), unsafe_allow_html=True)

    fc = st.columns(3)
    if fc[0].button("Step ×1", use_container_width=True):
        m.step()
        st.rerun()
    if fc[1].button("Flush traders", use_container_width=True):
        n = m.flush_traders()
        m._log(f"flushed {n} resting trader orders")
        st.rerun()
    if fc[2].button("Resolve now", use_container_width=True):
        m.resolve()
        st.rerun()

    st.markdown(log_panel_html(m), unsafe_allow_html=True)

# ---- auto-run frame loop -----------------------------------------------------
if st.session_state.running:
    time.sleep(0.15)
    st.rerun()
