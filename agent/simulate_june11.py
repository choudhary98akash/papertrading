#!/usr/bin/env python3
"""Simulate a June 11th trade entry for demo purposes."""
import json, os, csv
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
PICK_FILE = os.path.join(BASE_DIR, "daily_pick.json")
LOG_FILE = os.path.join(BASE_DIR, "daily_log.csv")
REPORT_DIR = os.path.join(BASE_DIR, "report")

today_str = "2026-06-11"
now_str = "2026-06-11 15:30:00"

# ── 1. Create daily_pick.json ──
pick = {
    "symbol": "RELIANCE",
    "date": today_str,
    "entry": 2850.00,
    "stop_loss": 2821.50,
    "target": 2907.00,
    "risk_pct": -1.0,
    "reward_pct": 2.0,
    "rr": 2.0,
    "ltp": 2850.00,
    "atr_pct": 1.8,
    "vol_surge": 1.5,
    "score": 7.2,
    "run_date": today_str
}
with open(PICK_FILE, "w") as f:
    json.dump(pick, f, indent=2)
print(f"Created: {PICK_FILE}")

# ── 2. Synthetic 1-min intraday data ──
np.random.seed(42)
base = 2850.0
periods = 375
idx = pd.date_range(f"{today_str} 09:15", periods=periods, freq="min")
opens = base + np.cumsum(np.random.normal(0, 2, periods))
highs = opens + abs(np.random.normal(1.5, 1, periods))
lows = opens - abs(np.random.normal(1.5, 1, periods))
closes = opens + np.random.normal(0, 1.5, periods)
volumes = np.random.randint(100000, 500000, periods)
df = pd.DataFrame({"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes}, index=idx)

# Ensure target hit, SL not hit
max_hi = df["High"].max()
min_lo = df["Low"].min()
if max_hi < pick["target"]:
    df.loc[df["High"].idxmax(), "High"] = pick["target"] + 1.5
if min_lo <= pick["stop_loss"]:
    df.loc[df["Low"].idxmin(), "Low"] = pick["stop_loss"] + 1.5

low_val = df["Low"].min()
high_val = df["High"].max()
close_val = df["Close"].iloc[-1]

# ── 3. Generate report HTML ──
result = "TARGET_HIT"
pnl = "+2.00%"
sl_hit = False
tgt_hit = True

def gen_report(pick, today_data, result, pnl, sl_hit, tgt_hit, now_str):
    low_today = today_data["Low"].min()
    high_today = today_data["High"].max()
    last_price = today_data["Close"].iloc[-1]
    open_price = today_data["Open"].iloc[0]
    result_color = "#4ade80" if "TARGET" in result else "#f87171" if "SL" in result else "#eab308"
    result_icon = "✅" if "TARGET" in result else "❌" if "SL" in result else "⏳"
    rows = []
    for ts, row in today_data.iterrows():
        t = ts.strftime("%H:%M")
        cls = "up" if row["Close"] >= row["Open"] else "down"
        rows.append(f"<tr><td>{t}</td><td class=\"{cls}\">{row['Open']:.2f}</td><td class=\"{cls}\">{row['High']:.2f}</td><td class=\"{cls}\">{row['Low']:.2f}</td><td class=\"{cls}\">{row['Close']:.2f}</td><td>{int(row['Volume']):,}</td></tr>")
    rows_html = "\n".join(rows[-90:])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Report - {pick['symbol']} - {pick['run_date']}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0f1e; color:#e2e8f0; font-family:'Segoe UI','Inter',sans-serif; padding:24px; }}
  .container {{ max-width:960px; margin:0 auto; }}
  .header {{ background:linear-gradient(135deg,#1e293b,#0f172a); border:1px solid #334155; border-radius:16px; padding:24px; margin-bottom:20px; }}
  .header h1 {{ font-size:24px; font-weight:800; }}
  .result-badge {{ display:inline-block; padding:6px 16px; border-radius:8px; font-weight:700; font-size:14px; margin-top:8px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:20px; }}
  .card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:16px; }}
  .card .label {{ color:#64748b; font-size:11px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }}
  .card .value {{ font-size:20px; font-weight:700; font-family:monospace; }}
  .card .sub {{ color:#475569; font-size:12px; margin-top:4px; }}
  .full-card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:16px; margin-bottom:20px; }}
  .full-card h2 {{ font-size:14px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; color:#64748b; margin-bottom:12px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12px; font-family:monospace; }}
  th {{ color:#64748b; text-align:left; padding:8px 6px; border-bottom:1px solid #1e293b; }}
  td {{ padding:4px 6px; border-bottom:1px solid #0f172a; }}
  tr:hover td {{ background:#1e293b44; }}
  .up {{ color:#4ade80; }}
  .down {{ color:#f87171; }}
  .stats {{ display:flex; gap:12px; flex-wrap:wrap; }}
  .stat {{ background:#1e293b; padding:8px 14px; border-radius:8px; font-size:12px; }}
  .stat span {{ color:#94a3b8; }}
  .stat strong {{ color:#e2e8f0; font-family:monospace; }}
  .footer {{ text-align:center; color:#334155; font-size:11px; font-family:monospace; margin-top:20px; padding:16px; border-top:1px solid #1e293b; }}
</style>
</head>
<body>
<div class="container">
  <div class="header" style="text-align:center;">
    <div style="color:#64748b;font-size:11px;font-family:monospace;letter-spacing:2px;margin-bottom:8px;">NIFTY 50 INTRADAY SCREENER</div>
    <h1>{pick['run_date']}</h1>
    <div style="margin-top:12px;">
      <span class="result-badge" style="background:{result_color}22;color:{result_color};border:1px solid {result_color}44;">
        {result_icon} {result} &mdash; {pnl}
      </span>
    </div>
  </div>
  <div class="grid">
    <div class="card"><div class="label">Stock</div><div class="value" style="font-size:28px;">{pick['symbol']}</div><div class="sub">NSE &middot; CASH</div></div>
    <div class="card"><div class="label">Score</div><div class="value" style="color:#a78bfa;">{pick['score']}</div><div class="sub">ATR {pick['atr_pct']}% &middot; Vol Surge {pick['vol_surge']}x</div></div>
    <div class="card"><div class="label">Entry Zone</div><div class="value" style="color:#60a5fa;">\u20b9{pick['entry']}</div><div class="sub">Close at signal time</div></div>
    <div class="card"><div class="label">Stop Loss</div><div class="value" style="color:#f87171;">\u20b9{pick['stop_loss']}</div><div class="sub">-1% &middot; {'SL HIT' if sl_hit else 'OK'}</div></div>
    <div class="card"><div class="label">Target</div><div class="value" style="color:#4ade80;">\u20b9{pick['target']}</div><div class="sub">+2% &middot; {'HIT' if tgt_hit else 'Missed'}</div></div>
    <div class="card"><div class="label">Risk:Reward</div><div class="value" style="color:#fbbf24;">1:{pick['rr']}</div><div class="sub">Min 1:2 required</div></div>
  </div>
  <div class="full-card">
    <h2>Day Summary</h2>
    <div class="stats">
      <div class="stat"><span>Open</span> <strong>\u20b9{open_price:.2f}</strong></div>
      <div class="stat"><span>High</span> <strong style="color:#4ade80;">\u20b9{high_today:.2f}</strong></div>
      <div class="stat"><span>Low</span> <strong style="color:#f87171;">\u20b9{low_today:.2f}</strong></div>
      <div class="stat"><span>Close</span> <strong>\u20b9{last_price:.2f}</strong></div>
      <div class="stat"><span>Range</span> <strong>\u20b9{high_today - low_today:.2f}</strong></div>
      <div class="stat"><span>Candles</span> <strong>{len(today_data)}</strong></div>
    </div>
  </div>
  <div class="full-card">
    <h2>Intraday Price Action (1-min candles)</h2>
    <div style="max-height:400px;overflow-y:auto;">
      <table><thead><tr><th>Time</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Vol</th></tr></thead>
      <tbody>{rows_html}</tbody></table>
    </div>
  </div>
  <div class="footer">
    Generated by Nifty 50 Intraday Screener &middot; {now_str}<br>
    <span style="color:#1e293b;">This is AI-generated research for educational purposes only. Not SEBI registered advice.</span>
  </div>
</div>
</body>
</html>"""

os.makedirs(REPORT_DIR, exist_ok=True)
report_path = os.path.join(REPORT_DIR, f"{today_str}_15-30.html")
html = gen_report(pick, df, result, pnl, sl_hit, tgt_hit, now_str)
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Report: {report_path}")

# ── 4. Log entry ──
log_exists = os.path.exists(LOG_FILE)
with open(LOG_FILE, "a", encoding="utf-8") as f:
    if not log_exists:
        f.write("date,symbol,entry,sl,target,low,high,close,result,pnl\n")
    f.write(f"{today_str},{pick['symbol']},{pick['entry']},{pick['stop_loss']},"
            f"{pick['target']},{low_val:.2f},{high_val:.2f},{close_val:.2f},"
            f"{result},{pnl}\n")
print(f"Logged: {LOG_FILE}")

print("\nDone. Run 'python daily_screener.py dashboard' to regenerate dashboard.")
