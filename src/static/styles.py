_CSS = """
<style>
  /* === base === */
  .stApp { background: #000 !important; }
  .block-container {
    padding-top: 0 !important;
    padding-bottom: 2rem !important;
    max-width: 1580px !important;
  }
  * { -webkit-font-smoothing: antialiased; }

  /* === header === */
  .site-header {
    display: flex; align-items: baseline; justify-content: space-between;
    padding: 18px 0 14px;
    border-bottom: 1px solid #1c1c1c;
    margin-bottom: 14px;
  }
  .site-title {
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 14px; font-weight: 700;
    color: #f5f5f5; letter-spacing: 0.14em; text-transform: uppercase;
  }
  .site-title .dot { color: #711aff; margin: 0 7px; }
  .site-sub {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px; color: #444; letter-spacing: 0.03em;
  }

  /* === panels === */
  .panel {
    background: #141414; border: 1px solid #1c1c1c;
    border-radius: 12px; padding: 20px 24px; margin-bottom: 12px;
    position: relative; overflow: hidden;
  }
  .panel-label {
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 10px; font-weight: 600;
    letter-spacing: 0.1em; color: #666;
    text-transform: uppercase; margin-bottom: 14px;
  }

  /* === probability bar (the risk: full-spectrum + glowing needle) === */
  .prob-section { margin: 4px 0 18px; }
  .prob-header {
    display: flex; justify-content: space-between; align-items: baseline;
    margin-bottom: 9px;
  }
  .prob-side-label {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px; letter-spacing: 0.04em;
  }
  .prob-side-label.down { color: #dc0b4a; }
  .prob-side-label.up   { color: #61ea7d; }
  .prob-center {
    text-align: center; line-height: 1.1;
  }
  .prob-mid-val {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 26px; font-weight: 700;
    color: #f5f5f5; letter-spacing: -0.025em;
    font-variant-numeric: tabular-nums;
  }
  .prob-mid-unit { font-size: 13px; color: #666; font-weight: 400; margin-left: 1px; }
  .prob-meta-line {
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 10px; color: #444; letter-spacing: 0.06em;
    text-transform: uppercase; margin-top: 3px;
  }
  .prob-track {
    height: 3px; border-radius: 2px;
    position: relative; /* needle uses absolute positioning */
  }
  .prob-spectrum {
    width: 100%; height: 100%; border-radius: 2px;
    background: linear-gradient(90deg,
      #dc0b4a 0%,
      #8e47ff 28%,
      #711aff 50%,
      #20ccff 72%,
      #61ea7d 100%
    );
  }
  .prob-needle {
    position: absolute; top: -5px;
    width: 2px; height: 13px; border-radius: 1px;
    background: #f5f5f5;
    transform: translateX(-50%);
    box-shadow: 0 0 8px 2px rgba(245,245,245,.55);
  }

  /* === book panel atmosphere (dynamic bg injected per frame) === */
  .book-panel { transition: background 0.8s ease; }

  /* === order book === */
  .book-meta {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px; color: #666;
    display: flex; gap: 18px; flex-wrap: wrap;
    margin-bottom: 14px;
  }
  .book-meta b { color: #d3d3d3; font-weight: 500; }

  .book-row {
    display: flex; align-items: center; gap: 10px;
    padding: 2px 0;
  }
  .book-price {
    width: 44px; text-align: right;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px; font-weight: 600;
    font-variant-numeric: tabular-nums; letter-spacing: -0.01em;
  }
  .book-size {
    width: 72px; text-align: right;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px; color: #666; font-variant-numeric: tabular-nums;
  }
  .book-bar-track { flex: 1; height: 7px; border-radius: 2px; background: #1c1c1c; }
  .book-bar-fill  { height: 100%; border-radius: 2px; }

  .ask .book-price { color: #dc0b4a; }
  .ask .book-bar-fill {
    background: linear-gradient(90deg, rgba(220,11,74,.08), rgba(220,11,74,.32));
  }
  .bid .book-price { color: #61ea7d; }
  .bid .book-bar-fill {
    background: linear-gradient(90deg, rgba(97,234,125,.08), rgba(97,234,125,.32));
  }

  .spread-divider {
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 11px; text-align: center;
    padding: 9px 0 7px;
    border-top: 1px solid #1c1c1c; border-bottom: 1px solid #1c1c1c;
    margin: 4px 0;
  }
  .spread-mid-num {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 17px; font-weight: 700;
    color: #711aff; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
  }
  .spread-prob { color: #666; font-size: 12px; }

  /* === key-value rows === */
  .kv {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px;
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 5px 0; border-bottom: 1px solid #1c1c1c;
  }
  .kv:last-child { border-bottom: none; }
  .kv .k { color: #666; font-size: 12px; }
  .kv .v { color: #f5f5f5; font-weight: 500; font-variant-numeric: tabular-nums; }
  .pos { color: #61ea7d; }
  .neg { color: #dc0b4a; }

  /* === MM P&L hero === */
  .pnl-hero { margin-bottom: 18px; padding-bottom: 16px; border-bottom: 1px solid #1c1c1c; }
  .pnl-hero-label {
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 10px; font-weight: 600;
    letter-spacing: 0.1em; color: #666;
    text-transform: uppercase; margin-bottom: 3px;
  }
  .pnl-hero-val {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 38px; font-weight: 700;
    letter-spacing: -0.03em; line-height: 1.05;
    font-variant-numeric: tabular-nums;
  }
  .pnl-hero-sub {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px; color: #666; margin-top: 4px;
    font-variant-numeric: tabular-nums;
  }

  /* === event log === */
  .log-wrap {
    max-height: 256px; overflow-y: auto;
    scrollbar-width: thin; scrollbar-color: #2f2f2f transparent;
  }
  .log-row {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11.5px; line-height: 1.7;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .log-step { color: #2f2f2f; }
  .log-default  { color: #666; }
  .log-mint     { color: #61ea7d; }
  .log-burn     { color: #dc0b4a; }
  .log-transfer { color: #20ccff; }
  .log-resolve  { color: #711aff; font-weight: 600; }
  .log-epoch    { color: #444; }

  /* === chart section === */
  .chart-label {
    font-family: ui-sans-serif, system-ui, sans-serif;
    font-size: 10px; font-weight: 600;
    letter-spacing: 0.1em; color: #666;
    text-transform: uppercase; margin-bottom: 6px;
  }

  /* === widget overrides === */
  label[data-testid="stWidgetLabel"] p {
    color: #666 !important; font-size: 10px !important;
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important;
    font-weight: 600 !important;
  }
  input[data-testid="stNumberInputField"],
  div[data-testid="stNumberInput"] input {
    background: #141414 !important; color: #f5f5f5 !important;
    border: 1px solid #1c1c1c !important; border-radius: 6px !important;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace !important;
    font-size: 13px !important;
  }
  input[data-testid="stNumberInputField"]:focus,
  div[data-testid="stNumberInput"] input:focus {
    border-color: #711aff !important; box-shadow: 0 0 0 1px #711aff !important;
  }
  div[data-testid="stNumberInput"] button {
    background: #1c1c1c !important; border-color: #1c1c1c !important; color: #666 !important;
  }
  .stButton > button {
    background: #141414 !important; color: #d3d3d3 !important;
    border: 1px solid #1c1c1c !important; border-radius: 8px !important;
    font-family: ui-sans-serif, system-ui, sans-serif !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important;
    transition: all .15s !important;
  }
  .stButton > button:hover {
    background: #1c1c1c !important; border-color: #711aff !important; color: #f5f5f5 !important;
  }
  .stButton > button:active {
    background: #5c16cc !important; border-color: #5c16cc !important; color: #fff !important;
  }
  .stCaption { color: #555 !important; }
  [data-testid="stVegaLiteChart"] { background: transparent !important; }
  .stMarkdown p { color: #d3d3d3; }
  hr { border-color: #1c1c1c !important; }
  *:focus-visible { outline-color: #711aff !important; }
</style>
"""