#!/usr/bin/env python3
"""
Daily Screener — Morning Pick + Evening Result
===============================================
Usage:
    python daily_screener.py morning    # Run at 9:30 AM — picks best stock
    python daily_screener.py evening    # Run at 3:30 PM — checks result
    python daily_screener.py dashboard  # Regenerate dashboard only
    python daily_screener.py auto       # Auto-detect time and run
"""

import sys, json, os, io, csv, warnings, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import math
from collections import Counter
from datetime import datetime, date

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
PICK_FILE = os.path.join(BASE_DIR, "daily_pick.json")
LOG_FILE = os.path.join(BASE_DIR, "daily_log.csv")
REPORT_DIR = os.path.join(BASE_DIR, "report")

NIFTY_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "HINDUNILVR.NS", "ITC.NS", "INFY.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "SBIN.NS", "WIPRO.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ASIANPAINT.NS", "AXISBANK.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "M&M.NS", "TRENT.NS",
    "COALINDIA.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BEL.NS", "BAJAJFINSV.NS",
    "NESTLEIND.NS", "TATACONSUM.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    "HINDALCO.NS", "BPCL.NS", "GRASIM.NS", "EICHERMOT.NS", "BRITANNIA.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "SBILIFE.NS", "APOLLOHOSP.NS",
    "HDFCLIFE.NS", "SHRIRAMFIN.NS", "BAJAJHLDNG.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS",
]


def calc_ema(s, p):
    return s.ewm(span=p, adjust=False).mean()


def calc_atr(df, p=14):
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(p).mean()


def clean_sym(s):
    return s.replace(".NS", "")


def get_github_url():
    try:
        r = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            u = r.stdout.strip().replace(".git", "")
            if u.startswith("git@github.com:"):
                u = "https://github.com/" + u[15:]
            return u
    except Exception:
        pass
    return ""


def fetch_data(symbol, period="2mo"):
    df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
    if df.empty or len(df) < 20:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.name = symbol
    return df


def score_stock(df):
    close, vol = df["Close"], df["Volume"]
    ema9 = calc_ema(close, 9)
    ema21 = calc_ema(close, 21)
    atr = calc_atr(df)
    candidates = []
    for idx in range(len(df) - 2, max(19, len(df) - 5), -1):
        price = close.iloc[idx]
        if price < 500:
            continue
        vol_today = vol.iloc[idx]
        avg_vol = vol.iloc[max(0, idx - 10):idx].mean()
        if vol_today < 1_000_000 or avg_vol == 0:
            continue
        vol_surge = vol_today / avg_vol
        if vol_surge < 1.2:
            continue
        atr_val = atr.iloc[idx]
        if pd.isna(atr_val) or (atr_val / price) < 0.012:
            continue
        e9, e21 = ema9.iloc[idx], ema21.iloc[idx]
        if pd.isna(e9) or pd.isna(e21):
            continue
        if price < e9 or price < e21:
            continue
        score = vol_surge * 2 + (atr_val / price) * 50 + (price / 1000)
        if price > 1000:
            score += 1
        entry = price
        candidates.append({
            "symbol": clean_sym(df.name),
            "date": str(df.index[idx].date()),
            "entry": round(entry, 2),
            "stop_loss": round(entry * 0.99, 2),
            "target": round(entry * 1.02, 2),
            "risk_pct": -1.0,
            "reward_pct": 2.0,
            "rr": 2.0,
            "ltp": round(price, 2),
            "atr_pct": round((atr_val / price) * 100, 2),
            "vol_surge": round(vol_surge, 2),
            "score": round(score, 2),
        })
    return candidates


def morning_pick():
    today_str = str(date.today())
    print(f"\n  [MORNING PICK] {today_str}")
    print(f"  Scanning Nifty 50...\n")
    all_candidates = []
    for i, sym in enumerate(NIFTY_50):
        name = clean_sym(sym)
        print(f"    [{i+1:2d}/50] {name:16s} ... ", end="", flush=True)
        df = fetch_data(sym)
        if df is None:
            print("SKIP")
            continue
        candidates = score_stock(df)
        if candidates:
            print(f"{len(candidates)} signals, best={candidates[0]['score']}")
            all_candidates.append(candidates[0])
        else:
            print("no signal")
    if not all_candidates:
        print("\n  No picks today.")
        return
    all_candidates.sort(key=lambda x: x["score"], reverse=True)
    pick = all_candidates[0]
    print(f"\n  {'='*50}")
    print(f"  TODAY'S PICK")
    print(f"  {'='*50}")
    print(f"  Stock     : {pick['symbol']}")
    print(f"  Entry     : \u20b9{pick['entry']}")
    print(f"  Stop Loss : \u20b9{pick['stop_loss']} (-1%)")
    print(f"  Target    : \u20b9{pick['target']} (+2%)")
    print(f"  R:R       : 1:{pick['rr']}")
    print(f"  ATR       : {pick['atr_pct']}%")
    print(f"  Vol Surge : {pick['vol_surge']}x")
    print(f"  Score     : {pick['score']}")
    print(f"  {'='*50}")
    with open(PICK_FILE, "w") as f:
        json.dump({**pick, "run_date": today_str}, f, indent=2)
    print(f"\n  Saved to: {PICK_FILE}")


# ─── HTML Templates ───

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nifty 50 Intraday Screener — Dashboard</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0a0f1e; color:#e2e8f0; font-family:'Inter','Segoe UI',sans-serif; }
  .hero {
    background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#0f172a 100%);
    border-bottom:1px solid #1e293b; padding:48px 24px 32px; text-align:center;
    position:relative; overflow:hidden;
  }
  .hero::before {
    content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%;
    background:radial-gradient(circle at 30% 50%,rgba(99,102,241,0.06) 0%,transparent 60%);
  }
  .hero h1 { font-size:32px; font-weight:900; letter-spacing:-1px; position:relative; }
  .hero h1 span { background:linear-gradient(135deg,#818cf8,#6366f1,#4ade80); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
  .hero p { color:#64748b; font-size:13px; margin-top:8px; font-family:monospace; position:relative; }
  .hero .badge {
    display:inline-block; margin-top:12px; padding:4px 14px; border-radius:20px;
    font-size:11px; font-family:monospace; letter-spacing:1px;
    border:1px solid #334155; color:#94a3b8; background:#0f172a;
  }
  .container { max-width:1100px; margin:0 auto; padding:24px; }
  .stats-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:12px; margin-bottom:28px; }
  .stat-card {
    background:linear-gradient(135deg,#0f172a,#1e293b); border:1px solid #1e293b;
    border-radius:12px; padding:16px; text-align:center; transition:border-color .2s;
  }
  .stat-card:hover { border-color:#334155; }
  .stat-card .num { font-size:24px; font-weight:800; font-family:monospace; }
  .stat-card .lbl { color:#64748b; font-size:10px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; margin-top:4px; }
  .section-title {
    font-size:13px; font-family:monospace; text-transform:uppercase; letter-spacing:2px;
    color:#64748b; margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid #1e293b;
  }
  .latest-card {
    background:linear-gradient(135deg,#0f172a,#1e1b4b); border:1px solid #312e81;
    border-radius:14px; padding:20px; margin-bottom:28px;
    display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;
  }
  .latest-card .info { flex:1; min-width:200px; }
  .latest-card .date { color:#64748b; font-size:11px; font-family:monospace; }
  .latest-card .stock { font-size:28px; font-weight:800; margin:4px 0; }
  .latest-card .detail { color:#94a3b8; font-size:13px; }
  .latest-card .levels { display:flex; gap:16px; font-family:monospace; font-size:13px; }
  .levels span { padding:6px 12px; border-radius:8px; }
  .level-entry { background:#1e3a5f44; color:#60a5fa; border:1px solid #1e3a5f; }
  .level-sl { background:#450a0a44; color:#f87171; border:1px solid #450a0a; }
  .level-tgt { background:#052e1644; color:#4ade80; border:1px solid #052e16; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { color:#64748b; font-family:monospace; font-size:11px; text-transform:uppercase; letter-spacing:1px; text-align:left; padding:10px 8px; border-bottom:1px solid #1e293b; }
  td { padding:10px 8px; border-bottom:1px solid #0f172a; }
  tr:hover td { background:#0f172a88; }
  .result-hit { color:#4ade80; font-weight:700; }
  .result-sl { color:#f87171; font-weight:700; }
  .result-hold { color:#eab308; font-weight:700; }
  .report-link { color:#60a5fa; text-decoration:none; font-family:monospace; font-size:12px; }
  .report-link:hover { text-decoration:underline; color:#93c5fd; }
  .empty { color:#475569; text-align:center; padding:40px; font-size:14px; }
  .footer { text-align:center; color:#1e293b; font-size:11px; font-family:monospace; padding:24px; border-top:1px solid #0f172a; margin-top:28px; }
  @media(max-width:640px) {
    .hero h1 { font-size:22px; }
    .stats-row { grid-template-columns:repeat(2,1fr); }
    .latest-card { flex-direction:column; text-align:center; }
    .latest-card .levels { justify-content:center; }
  }
  .charts-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:28px; }
  .chart-card { background:#0f172a; border:1px solid #1e293b; border-radius:14px; overflow:hidden; padding:16px; }
  .chart-card h3 { font-size:12px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; color:#64748b; margin-bottom:12px; padding-left:4px; }
  .analysis-grid { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:28px; }
  .analysis-card { background:#0f172a; border:1px solid #1e293b; border-radius:14px; padding:16px; }
  .analysis-card h3 { font-size:12px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; color:#64748b; margin-bottom:12px; }
  .mini-table { width:100%; font-size:12px; border-collapse:collapse; }
  .mini-table th { color:#64748b; font-family:monospace; font-size:10px; text-transform:uppercase; letter-spacing:1px; padding:6px 4px; border-bottom:1px solid #1e293b; }
  .mini-table td { padding:6px 4px; border-bottom:1px solid #0f172a; }
  .mini-table tr:last-child td { border-bottom:none; }
  .mini-table .num { font-family:monospace; text-align:right; font-weight:600; }
  @media(max-width:768px) {
    .charts-grid { grid-template-columns:1fr; }
    .analysis-grid { grid-template-columns:1fr; }
  }
</style>
</head>
<body>
<div class="hero">
  <h1><span>Nifty 50</span> Intraday Screener</h1>
  <p>Automated daily picks · 1% SL · 2% Target</p>
  {badge_html}
</div>
<div class="container">
  {stats_html}
  {stats2_html}
  {latest_html}
  <div class="section-title">Trade Log</div>
  {table_html}
  {charts_html}
  {analysis_html}
</div>
<div class="footer">Last updated: {timestamp} &middot; {github_html}</div>
</body>
</html>"""


def generate_dashboard():
    """Generate the main dashboard at repo root (index.html)."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    github_url = get_github_url()

    trades = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                trades.append(row)

    total = len(trades)
    wins = sum(1 for t in trades if "TARGET" in t.get("result", ""))
    losses = sum(1 for t in trades if "SL" in t.get("result", ""))
    win_rate = round(wins / total * 100, 1) if total > 0 else 0

    win_pnl = sum(float(t.get("pnl", "0").replace("+", "").replace("%", "")) for t in trades if "TARGET" in t.get("result", ""))
    loss_pnl = sum(float(t.get("pnl", "0").replace("+", "").replace("%", "")) for t in trades if "SL" in t.get("result", ""))
    total_pnl = round(win_pnl + loss_pnl, 2)
    avg_entry = round(sum(float(t.get("entry", 0)) for t in trades) / max(total, 1))

    # ─── Advanced Stats ───
    profit_factor = 0.0
    avg_win = 0.0
    avg_loss = 0.0
    max_consec_losses = 0
    best_trade_pnl = 0.0
    best_trade = ""
    worst_trade_pnl = 0.0
    worst_trade = ""

    if total > 0:
        gw = sum(float(t.get("pnl", "0").replace("+", "").replace("%", "")) for t in trades if "TARGET" in t.get("result", ""))
        gl = abs(sum(float(t.get("pnl", "0").replace("+", "").replace("%", "")) for t in trades if "SL" in t.get("result", "")))
        profit_factor = round(gw / gl, 2) if gl > 0 else round(gw, 2) if wins > 0 else 0

        wins_list = [float(t.get("pnl", "0").replace("+", "").replace("%", "")) for t in trades if "TARGET" in t.get("result", "")]
        losses_list = [float(t.get("pnl", "0").replace("+", "").replace("%", "")) for t in trades if "SL" in t.get("result", "")]
        avg_win = round(sum(wins_list) / len(wins_list), 2) if wins_list else 0
        avg_loss = round(sum(losses_list) / len(losses_list), 2) if losses_list else 0

        cur_consec = 0
        for t in trades:
            if "SL" in t.get("result", ""):
                cur_consec += 1
                max_consec_losses = max(max_consec_losses, cur_consec)
            else:
                cur_consec = 0

        for t in trades:
            pnl_val = float(t.get("pnl", "0").replace("+", "").replace("%", ""))
            if pnl_val > best_trade_pnl:
                best_trade_pnl = pnl_val
                best_trade = t.get("symbol", "")
            if pnl_val < worst_trade_pnl:
                worst_trade_pnl = pnl_val
                worst_trade = t.get("symbol", "")

    # ─── Cumulative PnL + Drawdown ───
    pnl_cumulative = []
    running = 0.0
    for t in trades:
        pnl_val = float(t.get("pnl", "0").replace("+", "").replace("%", ""))
        running += pnl_val
        pnl_cumulative.append(round(running, 2))

    max_dd = 0.0
    peak = -999.0
    for v in pnl_cumulative:
        peak = max(peak, v)
        dd = v - peak
        max_dd = min(max_dd, dd)

    # ─── Stock Frequency ───
    stock_freq = Counter(t.get("symbol", "") for t in trades)

    # ─── Day of Week ───
    dow_data = {}
    for t in trades:
        try:
            dt = datetime.strptime(t.get("date", ""), "%Y-%m-%d")
            dow = dt.strftime("%A")
            if dow not in dow_data:
                dow_data[dow] = {"count": 0, "wins": 0, "pnl": 0.0}
            pnl_val = float(t.get("pnl", "0").replace("+", "").replace("%", ""))
            dow_data[dow]["count"] += 1
            dow_data[dow]["pnl"] += pnl_val
            if "TARGET" in t.get("result", ""):
                dow_data[dow]["wins"] += 1
        except ValueError:
            pass

    # ─── Badge ───
    badge_html = f'<div class="badge">{total} trades &middot; {win_rate}% win rate &middot; {now_str[:10]}</div>'
    wr_color = "#4ade80" if win_rate >= 40 else "#eab308" if win_rate >= 25 else "#f87171"
    pnl_color = "#4ade80" if total_pnl >= 0 else "#f87171"

    # ─── Stats Row 1 ───
    stats_html = f"""<div class="stats-row">
<div class="stat-card"><div class="num" style="color:#94a3b8;">{total}</div><div class="lbl">Total Trades</div></div>
<div class="stat-card"><div class="num" style="color:#4ade80;">{wins}</div><div class="lbl">Wins</div></div>
<div class="stat-card"><div class="num" style="color:#f87171;">{losses}</div><div class="lbl">Losses</div></div>
<div class="stat-card"><div class="num" style="color:{wr_color};">{win_rate}%</div><div class="lbl">Win Rate</div></div>
<div class="stat-card"><div class="num" style="color:{pnl_color};">{total_pnl:+.1f}%</div><div class="lbl">Total PnL</div></div>
<div class="stat-card"><div class="num" style="color:#a78bfa;">{avg_entry:,}</div><div class="lbl">Avg Entry</div></div>
</div>"""

    # ─── Stats Row 2 ───
    pf_color = "#4ade80" if profit_factor >= 1.5 else "#eab308" if profit_factor >= 1.0 else "#f87171"
    best_label = f"{best_trade} {best_trade_pnl:+.2f}%" if best_trade else "-"
    worst_label = f"{worst_trade} {worst_trade_pnl:+.2f}%" if worst_trade else "-"
    stats2_html = f"""<div class="stats-row">
<div class="stat-card"><div class="num" style="color:{pf_color};">{profit_factor}</div><div class="lbl">Profit Factor</div></div>
<div class="stat-card"><div class="num" style="color:#4ade80;">{avg_win:+.2f}%</div><div class="lbl">Avg Win</div></div>
<div class="stat-card"><div class="num" style="color:#f87171;">{avg_loss:+.2f}%</div><div class="lbl">Avg Loss</div></div>
<div class="stat-card"><div class="num" style="color:#f87171;">{max_consec_losses}</div><div class="lbl">Max Consec Losses</div></div>
<div class="stat-card"><div class="num" style="color:#f87171;">{max_dd:+.2f}%</div><div class="lbl">Max Drawdown</div></div>
<div class="stat-card"><div class="num" style="color:#4ade80;">{best_trade_pnl:+.2f}%</div><div class="lbl">Best Trade</div></div>
</div>"""

    # ─── Latest Trade ───
    from os.path import relpath
    report_rel = relpath(REPORT_DIR, ROOT_DIR).replace("\\", "/")

    latest_html = ""
    if trades:
        t = trades[-1]
        res = t.get("result", "")
        res_cls = "result-hit" if "TARGET" in res else "result-sl" if "SL" in res else "result-hold"
        icon = "✅" if "TARGET" in res else "❌" if "SL" in res else "⏳"
        date_str = t.get("date", "")
        entry = t.get("entry", "")
        sl = t.get("sl", "")
        target = t.get("target", "")
        pnl_val = t.get("pnl", "")

        report_link = ""
        if os.path.exists(REPORT_DIR):
            for f in sorted(os.listdir(REPORT_DIR), reverse=True):
                if f.endswith(".html") and f != "index.html" and date_str in f:
                    report_link = f'{report_rel}/{f}'
                    break

        link_html = f'<a href="{report_link}" style="color:#60a5fa;font-size:13px;font-family:monospace;">View Report &rarr;</a>' if report_link else ""

        latest_html = f"""<div class="section-title" style="margin-top:8px;">Latest Trade</div>
<div class="latest-card">
<div class="info"><div class="date">{date_str} &middot; {t['symbol']}</div>
<div class="stock">{icon} <span class="{res_cls}">{res}</span> &middot; {pnl_val}</div>
<div class="detail">{link_html}</div></div>
<div class="levels">
<span class="level-entry">E: ₹{entry}</span>
<span class="level-sl">SL: ₹{sl}</span>
<span class="level-tgt">T: ₹{target}</span>
</div></div>"""

    # ─── Trade Log ───
    if trades:
        rows = []
        for t in reversed(trades):
            res = t.get("result", "")
            res_cls = "result-hit" if "TARGET" in res else "result-sl" if "SL" in res else "result-hold"
            icon = "✅" if "TARGET" in res else "❌" if "SL" in res else "⏳"
            date_str = t.get("date", "")
            report_link = ""
            if os.path.exists(REPORT_DIR):
                for f in sorted(os.listdir(REPORT_DIR), reverse=True):
                    if f.endswith(".html") and f != "index.html" and date_str in f:
                        report_link = f'<a class="report-link" href="{report_rel}/{f}">View</a>'
                        break
            rows.append(f"<tr><td>{t['date']}</td><td style=\"font-weight:700;\">{t['symbol']}</td><td>₹{t['entry']}</td><td style=\"color:#f87171;\">₹{t['sl']}</td><td style=\"color:#4ade80;\">₹{t['target']}</td><td class=\"{res_cls}\">{icon} {res}</td><td style=\"font-weight:700;\">{t['pnl']}</td><td>{report_link}</td></tr>")
        table_html = "<div style=\"overflow-x:auto;\"><table><thead><tr><th>Date</th><th>Stock</th><th>Entry</th><th>SL</th><th>Target</th><th>Result</th><th>PnL</th><th></th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    else:
        table_html = "<div class=\"empty\">No trades yet. The screener runs Mon-Fri at 9:30 AM IST.</div>"

    # ─── Charts ───
    charts_html = ""
    if total > 0:
        eq_svg = svg_equity_curve(pnl_cumulative)
        pnl_svg = svg_pnl_bars(trades)
        charts_html = f"""<div class="section-title">Charts</div>
<div class="charts-grid">
<div class="chart-card"><h3>Equity Curve</h3>{eq_svg}</div>
<div class="chart-card"><h3>Trade PnL Distribution</h3>{pnl_svg}</div>
</div>"""

    # ─── Analysis Tables ───
    analysis_html = ""
    if total > 0:
        sf_rows = ""
        for sym, cnt in stock_freq.most_common(10):
            pct = round(cnt / total * 100, 1) if total > 0 else 0
            sf_rows += f"<tr><td>{sym}</td><td class=\"num\">{cnt}</td><td class=\"num\" style=\"color:#64748b;\">{pct}%</td></tr>"

        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        dow_rows = ""
        for d in dow_order:
            if d in dow_data:
                dd = dow_data[d]
                wr = round(dd["wins"] / dd["count"] * 100, 1) if dd["count"] > 0 else 0
                pnl_c = "#4ade80" if dd["pnl"] >= 0 else "#f87171"
                dow_rows += f"<tr><td>{d[:3]}</td><td class=\"num\">{dd['count']}</td><td class=\"num\">{dd['wins']}</td><td class=\"num\" style=\"color:{pnl_c};\">{dd['pnl']:+.2f}%</td></tr>"

        analysis_html = f"""<div class="section-title">Analysis</div>
<div class="analysis-grid">
<div class="analysis-card">
<h3>Stock Frequency</h3>
<table class="mini-table"><thead><tr><th>Stock</th><th class="num">Trades</th><th class="num">%</th></tr></thead><tbody>{sf_rows}</tbody></table>
</div>
<div class="analysis-card">
<h3>Day of Week</h3>
<table class="mini-table"><thead><tr><th>Day</th><th class="num">Trades</th><th class="num">Wins</th><th class="num">PnL</th></tr></thead><tbody>{dow_rows}</tbody></table>
</div>
</div>"""

    # ─── Footer ───
    github_html = f'<a href="{github_url}" style="color:#334155;text-decoration:none;">GitHub</a>' if github_url else ""

    update_report_index()

    # ─── Assemble ───
    html = (DASHBOARD_HTML
        .replace("{badge_html}", badge_html)
        .replace("{stats_html}", stats_html)
        .replace("{stats2_html}", stats2_html)
        .replace("{latest_html}", latest_html)
        .replace("{table_html}", table_html)
        .replace("{charts_html}", charts_html)
        .replace("{analysis_html}", analysis_html)
        .replace("{timestamp}", now_str)
        .replace("{github_html}", github_html)
    )

    idx_path = os.path.join(ROOT_DIR, "index.html")
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Dashboard: {idx_path}")


# ─── Report Generation ───

def svg_chart(closes, times, entry, sl, target, sl_label, tgt_label):
    W, H = 800, 360
    ML, MR, MT, MB = 70, 16, 24, 44
    PW = W - ML - MR
    PH = H - MT - MB

    cmin = min(closes)
    cmax = max(closes)
    pad = max((cmax - cmin) * 0.12, (cmax - cmin) * 0.12 or 2)
    ylo = min(cmin - pad, sl - 2)
    yhi = max(cmax + pad, target + 2)

    def sx(i): return ML + PW * i / max(len(closes) - 1, 1)
    def sy(v): return MT + PH * (yhi - v) / (yhi - ylo)

    pts = " ".join(f"{sx(i)},{sy(v)}" for i, v in enumerate(closes))
    fill_pts = f"{sx(0)},{H} {pts} {sx(len(closes)-1)},{H}"

    tick_step = max(1, len(times) // 14)
    x_ticks = [(i, times[i]) for i in range(0, len(times), tick_step)]
    y_range = yhi - ylo
    y_step = 10 ** round(__import__("math").log10(y_range)) / 4
    y_ticks = []
    v = round(ylo / y_step) * y_step
    while v <= yhi:
        y_ticks.append(v)
        v += y_step

    svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">'
    svg += f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0f172a" rx="12"/>'
    svg += f'<clipPath id="cp"><rect x="{ML}" y="{MT}" width="{PW}" height="{PH}"/></clipPath>'
    svg += f'<g clip-path="url(#cp)">'
    svg += f'<polygon points="{fill_pts}" fill="rgba(129,140,248,0.1)"/>'
    svg += f'<polyline points="{pts}" fill="none" stroke="#818cf8" stroke-width="2" stroke-linejoin="round"/>'
    svg += f'</g>'

    for v in y_ticks:
        y = sy(v)
        svg += f'<line x1="{ML}" y1="{y}" x2="{W-MR}" y2="{y}" stroke="#1e293b" stroke-width="1"/>'
        svg += f'<text x="{ML-6}" y="{y+4}" fill="#64748b" font-family="monospace" font-size="11" text-anchor="end">₹{v:,.0f}</text>'

    for i, t in x_ticks:
        x = sx(i)
        svg += f'<line x1="{x}" y1="{MT}" x2="{x}" y2="{H-MB}" stroke="#1e293b" stroke-width="1"/>'
        svg += f'<text x="{x}" y="{H-MB+16}" fill="#64748b" font-family="monospace" font-size="10" text-anchor="middle">{t}</text>'

    lines = [
        (entry, "#60a5fa", f"Entry ₹{entry}", "bottom"),
        (sl, "#f87171", f"{sl_label} ₹{sl}", "top"),
        (target, "#4ade80", f"{tgt_label} ₹{target}", "bottom"),
    ]
    for v, color, label, anchor in lines:
        y = sy(v)
        svg += f'<line x1="{ML}" y1="{y}" x2="{W-MR}" y2="{y}" stroke="{color}" stroke-width="1.5" stroke-dasharray="6,4"/>'
        dy = 4 if anchor == "top" else -4
        svg += f'<text x="{ML+4}" y="{y+dy}" fill="{color}" font-family="monospace" font-size="11" font-weight="600" dominant-baseline="{anchor}">{label}</text>'

    close_val = closes[-1]
    yc = sy(close_val)
    svg += f'<text x="{W-MR-4}" y="{yc-4}" fill="#e2e8f0" font-family="monospace" font-size="11" font-weight="600" text-anchor="end">Close ₹{close_val:,.2f}</text>'

    svg += '</svg>'
    return svg


def svg_equity_curve(values):
    W, H = 800, 300
    ML, MR, MT, MB = 70, 16, 24, 44
    PW = W - ML - MR
    PH = H - MT - MB
    if not values:
        return ""
    cmin = min(values)
    cmax = max(values)
    rng = max(cmax - cmin, 0.5)
    pad = rng * 0.15
    ylo = min(cmin - pad, -0.5)
    yhi = max(cmax + pad, 0.5)
    def sx(i): return ML + PW * i / max(len(values) - 1, 1)
    def sy(v): return MT + PH * (yhi - v) / (yhi - ylo)
    pts = " ".join(f"{sx(i)},{sy(v)}" for i, v in enumerate(values))
    zero_y = sy(0)
    y_range = yhi - ylo
    y_step = 10 ** round(math.log10(y_range)) / 4
    y_ticks = []
    v = round(ylo / y_step) * y_step
    while v <= yhi:
        y_ticks.append(round(v, 2))
        v += y_step
    final_color = "#4ade80" if values[-1] >= 0 else "#f87171"
    svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">'
    svg += f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0f172a" rx="12"/>'
    svg += f'<clipPath id="cp-eq"><rect x="{ML}" y="{MT}" width="{PW}" height="{PH}"/></clipPath>'
    for vv in y_ticks:
        y = sy(vv)
        svg += f'<line x1="{ML}" y1="{y}" x2="{W-MR}" y2="{y}" stroke="#1e293b" stroke-width="1"/>'
        svg += f'<text x="{ML-6}" y="{y+4}" fill="#64748b" font-family="monospace" font-size="11" text-anchor="end">{vv:+.1f}%</text>'
    svg += f'<line x1="{ML}" y1="{zero_y}" x2="{W-MR}" y2="{zero_y}" stroke="#334155" stroke-width="1.5"/>'
    svg += f'<g clip-path="url(#cp-eq)">'
    if len(values) > 1:
        fill_pts = f"{sx(0)},{zero_y} {pts} {sx(len(values)-1)},{zero_y}"
        svg += f'<polygon points="{fill_pts}" fill="rgba(129,140,248,0.08)"/>'
    svg += f'<polyline points="{pts}" fill="none" stroke="{final_color}" stroke-width="2.5" stroke-linejoin="round"/>'
    svg += f'<circle cx="{sx(0)}" cy="{sy(values[0])}" r="4" fill="{final_color}"/>'
    svg += f'<circle cx="{sx(len(values)-1)}" cy="{sy(values[-1])}" r="5" fill="{final_color}" stroke="#0f172a" stroke-width="2"/>'
    svg += f'<text x="{W-MR-4}" y="{sy(values[-1])-8}" fill="{final_color}" font-family="monospace" font-size="12" font-weight="700" text-anchor="end">{values[-1]:+.2f}%</text>'
    svg += f'</g>'
    n = len(values)
    step = max(1, n // 10)
    for i in range(0, n, step):
        x = sx(i)
        svg += f'<text x="{x}" y="{H-MB+16}" fill="#64748b" font-family="monospace" font-size="10" text-anchor="middle">{i+1}</text>'
    svg += '</svg>'
    return svg


def svg_pnl_bars(trades):
    W, H = 800, 300
    ML, MR, MT, MB = 70, 16, 24, 44
    PW = W - ML - MR
    PH = H - MT - MB
    values = [float(t.get("pnl", "0").replace("+", "").replace("%", "")) for t in trades]
    if not values:
        return ""
    cmin = min(values)
    cmax = max(values)
    rng = max(cmax - cmin, 0.5)
    pad = rng * 0.2
    ylo = min(cmin - pad, -0.5)
    yhi = max(cmax + pad, 0.5)
    def sx(i): return ML + PW * (i + 0.5) / len(values)
    def sy(v): return MT + PH * (yhi - v) / (yhi - ylo)
    zero_y = sy(0)
    bar_w = max(8, min(40, PW / len(values) * 0.6))
    y_range = yhi - ylo
    y_step = 10 ** round(math.log10(y_range)) / 4
    y_ticks = []
    v = round(ylo / y_step) * y_step
    while v <= yhi:
        y_ticks.append(round(v, 2))
        v += y_step
    svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">'
    svg += f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0f172a" rx="12"/>'
    for vv in y_ticks:
        y = sy(vv)
        svg += f'<line x1="{ML}" y1="{y}" x2="{W-MR}" y2="{y}" stroke="#1e293b" stroke-width="1"/>'
        svg += f'<text x="{ML-6}" y="{y+4}" fill="#64748b" font-family="monospace" font-size="11" text-anchor="end">{vv:+.1f}%</text>'
    svg += f'<line x1="{ML}" y1="{zero_y}" x2="{W-MR}" y2="{zero_y}" stroke="#334155" stroke-width="1.5"/>'
    for i, v in enumerate(values):
        x = sx(i) - bar_w / 2
        y_top = sy(v) if v >= 0 else zero_y
        bar_h = abs(sy(v) - zero_y)
        color = "#4ade80" if v >= 0 else "#f87171"
        svg += f'<rect x="{x:.1f}" y="{y_top:.1f}" width="{bar_w:.1f}" height="{max(bar_h, 1):.1f}" rx="3" fill="{color}" opacity="0.8"/>'
    step = max(1, len(values) // 10)
    for i in range(0, len(values), step):
        x = sx(i)
        svg += f'<text x="{x}" y="{H-MB+16}" fill="#64748b" font-family="monospace" font-size="10" text-anchor="middle">{i+1}</text>'
    svg += '</svg>'
    return svg


def generate_report_html(pick, today_data, result, pnl, sl_hit, tgt_hit, now_str):
    low_today = today_data["Low"].min()
    high_today = today_data["High"].max()
    last_price = today_data["Close"].iloc[-1]
    open_price = today_data["Open"].iloc[0]
    entry = pick["entry"]
    sl = pick["stop_loss"]
    target = pick["target"]

    result_color = "#4ade80" if "TARGET" in result else "#f87171" if "SL" in result else "#eab308"
    result_icon = "✅" if "TARGET" in result else "❌" if "SL" in result else "⏳"

    times = [ts.strftime("%H:%M") for ts in today_data.index]
    closes = [round(c, 2) for c in today_data["Close"].tolist()]

    sl_label = "SL HIT" if sl_hit else "SL"
    tgt_label = "TARGET HIT" if tgt_hit else "TARGET"

    chart_svg = svg_chart(closes, times, entry, sl, target, sl_label, tgt_label)

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
  .chart-card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; margin-bottom:20px; overflow:hidden; }}
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
    <h1>{pick['run_date']} &middot; {pick['symbol']}</h1>
    <div style="margin-top:12px;">
      <span class="result-badge" style="background:{result_color}22;color:{result_color};border:1px solid {result_color}44;">
        {result_icon} {result} &mdash; {pnl}
      </span>
    </div>
  </div>
  <div class="grid">
    <div class="card"><div class="label">Stock</div><div class="value" style="font-size:28px;">{pick['symbol']}</div><div class="sub">NSE &middot; CASH</div></div>
    <div class="card"><div class="label">Score</div><div class="value" style="color:#a78bfa;">{pick['score']}</div><div class="sub">ATR {pick['atr_pct']}% &middot; Vol Surge {pick['vol_surge']}x</div></div>
    <div class="card"><div class="label">Entry Zone</div><div class="value" style="color:#60a5fa;">\u20b9{entry}</div><div class="sub">Close at signal time</div></div>
    <div class="card"><div class="label">Stop Loss</div><div class="value" style="color:#f87171;">\u20b9{sl}</div><div class="sub">-1% &middot; {'SL HIT' if sl_hit else 'OK'}</div></div>
    <div class="card"><div class="label">Target</div><div class="value" style="color:#4ade80;">\u20b9{target}</div><div class="sub">+2% &middot; {'HIT' if tgt_hit else 'Missed'}</div></div>
    <div class="card"><div class="label">Risk:Reward</div><div class="value" style="color:#fbbf24;">1:{pick['rr']}</div><div class="sub">Min 1:2 required</div></div>
  </div>
  <div class="chart-card">{chart_svg}</div>
  <div class="full-card" style="background:#0f172a;border:1px solid #1e293b;border-radius:12px;padding:16px;margin-bottom:20px;">
    <h2 style="font-size:14px;font-family:monospace;text-transform:uppercase;letter-spacing:1px;color:#64748b;margin-bottom:12px;">Day Summary</h2>
    <div class="stats">
      <div class="stat"><span>Open</span> <strong>\u20b9{open_price:.2f}</strong></div>
      <div class="stat"><span>High</span> <strong style="color:#4ade80;">\u20b9{high_today:.2f}</strong></div>
      <div class="stat"><span>Low</span> <strong style="color:#f87171;">\u20b9{low_today:.2f}</strong></div>
      <div class="stat"><span>Close</span> <strong>\u20b9{last_price:.2f}</strong></div>
      <div class="stat"><span>Range</span> <strong>\u20b9{high_today - low_today:.2f}</strong></div>
      <div class="stat"><span>Candles</span> <strong>{len(today_data)}</strong></div>
    </div>
  </div>
  <div class="footer">
    Generated by Nifty 50 Intraday Screener &middot; {now_str}<br>
    <span style="color:#1e293b;">This is AI-generated research for educational purposes only. Not SEBI registered advice.</span>
  </div>
</div>
</body>
</html>"""


def evening_check():
    today_str = str(date.today())
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n  [EVENING CHECK] {today_str}")

    if not os.path.exists(PICK_FILE):
        print("  No pick file found. Run 'morning' first.")
        return

    with open(PICK_FILE) as f:
        pick = json.load(f)

    print(f"  Checking: {pick['symbol']}")
    print(f"  Entry: \u20b9{pick['entry']}, SL: \u20b9{pick['stop_loss']}, TGT: \u20b9{pick['target']}")

    df = yf.download(
        pick["symbol"] + ".NS",
        period="2d", interval="1m",
        progress=False, auto_adjust=True
    )
    if df.empty:
        print("  No intraday data available.")
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    today_data = df[df.index.date == date.today()]
    if today_data.empty:
        print("  No data for today yet (market may be closed).")
        return

    low_today = today_data["Low"].min()
    high_today = today_data["High"].max()
    last_price = today_data["Close"].iloc[-1]

    sl_hit = low_today <= pick["stop_loss"]
    tgt_hit = high_today >= pick["target"]

    if tgt_hit:
        result = "TARGET_HIT"
        pnl = "+2.00%"
    elif sl_hit:
        result = "SL_HIT"
        pnl = "-1.00%"
    else:
        result = "NO_TRIGGER"
        pnl_pct = round(((last_price - pick["entry"]) / pick["entry"]) * 100, 2)
        pnl = f"{pnl_pct:+.2f}%"

    print(f"\n  {'='*50}")
    print(f"  RESULT")
    print(f"  {'='*50}")
    print(f"  Day Low   : \u20b9{low_today:.2f}  {'SL HIT' if sl_hit else 'OK'}")
    print(f"  Day High  : \u20b9{high_today:.2f}  {'TARGET HIT' if tgt_hit else 'OK'}")
    print(f"  Close     : \u20b9{last_price:.2f}")
    print(f"  Result    : {result}  ({pnl})")
    print(f"  {'='*50}")

    # CSV log
    log_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a") as f:
        if not log_exists:
            f.write("date,symbol,entry,sl,target,low,high,close,result,pnl\n")
        f.write(f"{today_str},{pick['symbol']},{pick['entry']},{pick['stop_loss']},"
                f"{pick['target']},{low_today:.2f},{high_today:.2f},{last_price:.2f},"
                f"{result},{pnl}\n")
    print(f"  Logged to: {LOG_FILE}")

    # Detailed report
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_filename = f"{today_str}_{datetime.now().strftime('%H-%M')}.html"
    report_path = os.path.join(REPORT_DIR, report_filename)
    html = generate_report_html(pick, today_data, result, pnl, sl_hit, tgt_hit, now_str)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Report: {report_path}")

    # Index + Dashboard
    update_report_index()
    generate_dashboard()


def update_report_index():
    os.makedirs(REPORT_DIR, exist_ok=True)
    reports = sorted([f for f in os.listdir(REPORT_DIR) if f.endswith(".html") and f != "index.html"], reverse=True)
    if not reports:
        return
    links = "".join(f"<tr><td><a href=\"{r}\">{r.replace('.html','')}</a></td></tr>\n" for r in reports[:30])
    idx_path = os.path.join(REPORT_DIR, "index.html")
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Daily Reports</title>
<style>
  body{{background:#0a0f1e;color:#e2e8f0;font-family:'Segoe UI',sans-serif;padding:24px;max-width:800px;margin:0 auto;}}
  h1{{font-size:24px;}} p{{color:#64748b;font-size:13px;margin-bottom:24px;}}
  a{{color:#60a5fa;text-decoration:none;font-family:monospace;}}
  a:hover{{color:#93c5fd;text-decoration:underline;}}
  td{{padding:8px 6px;border-bottom:1px solid #1e293b;font-size:13px;}}
</style></head><body>
<h1>Daily Reports</h1>
<p><a href="../">Dashboard</a></p>
<table><tbody>{links}</tbody></table>
</body></html>""")
    print(f"  Report index: {idx_path}")


def auto_mode():
    now = datetime.now()
    total_min = now.hour * 60 + now.minute
    if 420 <= total_min <= 780:
        print("[AUTO] Morning → running morning pick")
        morning_pick()
    elif 810 <= total_min <= 1080:
        print("[AUTO] Evening → running evening check")
        evening_check()
    else:
        print(f"[AUTO] {now.strftime('%H:%M')} outside trading hours.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python daily_screener.py morning|evening|dashboard|auto")
        return
    mode = sys.argv[1].lower()
    if mode == "morning":
        morning_pick()
    elif mode == "evening":
        evening_check()
    elif mode == "dashboard":
        generate_dashboard()
    elif mode == "auto":
        auto_mode()
    else:
        print(f"Unknown: {mode}. Use: morning, evening, dashboard, auto")


if __name__ == "__main__":
    main()
