#!/usr/bin/env python3
"""
Small Gap Snap — Full Backtest Engine
======================================
Strategy: Trade gaps 0.3-0.8%, reverse direction, target 50% fill, SL 0.5%.
Data: Real yfinance daily OHLC (Mar 16 – Jun 15, 2026, 62 trading days, 49 stocks).
"""
import sys, json, os, io, math, webbrowser, warnings
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

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

START_DATE = "2026-03-16"
END_DATE = "2026-06-15"

def clean_sym(s):
    return s.replace(".NS", "")

# ─── Strategy Parameters ───
MIN_GAP = 0.3
MAX_GAP = 0.8
SL_PCT = 0.005
TARGET_PCT = 0.50  

def backtest_stock(symbol):
    """Backtest Small Gap Snap on a single stock. Returns list of trade dicts."""
    name = clean_sym(symbol)
    try:
        df = yf.download(symbol, start=START_DATE, end="2026-06-16", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close"]]
    except:
        return None

    trades = []
    for i in range(1, len(df)):
        prev_close = df["Close"].iloc[i - 1]
        today = df.iloc[i]
        open_p = today["Open"]
        high = today["High"]
        low = today["Low"]
        close = today["Close"]
        date_str = str(today.name.date())

        if date_str > END_DATE:
            break
        if date_str < START_DATE:
            continue

        gap_pct = (open_p - prev_close) / prev_close * 100
        abs_gap = abs(gap_pct)

        if abs_gap < MIN_GAP or abs_gap > MAX_GAP:
            continue

        direction = "SHORT" if gap_pct > 0 else "LONG"
        gap_amount = abs(open_p - prev_close)

        entry = open_p
        if direction == "LONG":
            sl = entry * (1 - SL_PCT)
            target_price = entry + gap_amount * TARGET_PCT
        else:
            sl = entry * (1 + SL_PCT)
            target_price = entry - gap_amount * TARGET_PCT

        sl_hit = low <= sl if direction == "LONG" else high >= sl
        tgt_hit = high >= target_price if direction == "LONG" else low <= target_price

        if tgt_hit:
            exit_price = target_price
            result = "TARGET_HIT"
        elif sl_hit:
            exit_price = sl
            result = "SL_HIT"
        else:
            exit_price = close
            result = "TIME_EXIT"

        pnl_pct = ((exit_price - entry) / entry) * 100
        if direction == "SHORT":
            pnl_pct = -pnl_pct

        trades.append({
            "date": date_str,
            "symbol": name,
            "direction": direction,
            "gap_pct": round(gap_pct, 2),
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "target": round(target_price, 2),
            "exit": round(exit_price, 2),
            "result": result,
            "pnl": round(pnl_pct, 2),
        })

    return trades if trades else None


def backtest_all_parallel():
    all_trades = {}
    stock_stats = {}
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0

    print(f"\n  Backtesting 49 stocks — Small Gap Snap ({START_DATE} to {END_DATE})...\n")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(backtest_stock, sym): sym for sym in NIFTY_50}
        done = 0
        for future in as_completed(futures):
            sym = futures[future]
            name = clean_sym(sym)
            done += 1
            try:
                trades = future.result()
                if trades:
                    all_trades[name] = trades
                    wins = sum(1 for t in trades if t["pnl"] > 0)
                    pnl = sum(t["pnl"] for t in trades)
                    wr = round(wins / len(trades) * 100, 1)
                    stock_stats[name] = {
                        "trades": len(trades),
                        "wins": wins,
                        "losses": len(trades) - wins,
                        "win_rate": wr,
                        "total_pnl": round(pnl, 2),
                        "avg_pnl": round(pnl / len(trades), 2),
                    }
                    total_trades += len(trades)
                    total_wins += wins
                    total_pnl += pnl
                    avg = pnl / len(trades)
                    marker = "★" if wr >= 65 else " "
                    print(f"    [{done:2d}/49] {name:16s} {len(trades):2d} trades  WR:{wr:5.1f}%  PnL:{pnl:+.2f}%  Avg:{avg:+.2f}% {marker}")
                else:
                    print(f"    [{done:2d}/49] {name:16s} no signals")
            except Exception as e:
                print(f"    [{done:2d}/49] {name:16s} ERROR: {e}")

    overall_wr = round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0
    overall = {
        "total_trades": total_trades,
        "total_wins": total_wins,
        "total_losses": total_trades - total_wins,
        "win_rate": overall_wr,
        "total_pnl": round(total_pnl, 2),
        "stocks_with_signals": len(all_trades),
    }
    return all_trades, stock_stats, overall


def generate_html_report(all_trades, stock_stats, overall):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sorted_stocks = sorted(stock_stats.items(), key=lambda x: (-x[1]["win_rate"], -x[1]["total_pnl"]))

    symbols_json = json.dumps([s[0] for s in sorted_stocks])
    wr_json = json.dumps([s[1]["win_rate"] for s in sorted_stocks])
    pnl_json = json.dumps([s[1]["total_pnl"] for s in sorted_stocks])
    tc_json = json.dumps([s[1]["trades"] for s in sorted_stocks])

    wr_color = "#4ade80" if overall["win_rate"] >= 65 else "#eab308" if overall["win_rate"] >= 50 else "#f87171"
    pnl_color = "#4ade80" if overall["total_pnl"] >= 0 else "#f87171"

    equity_curve = []
    cumulative = 0
    all_flat = []
    for name, _ in sorted_stocks:
        for t in all_trades.get(name, []):
            all_flat.append(t)
    all_flat.sort(key=lambda x: x["date"])
    eq_points = []
    for t in all_flat:
        cumulative += t["pnl"]
        eq_points.append({"date": t["date"], "pnl": cumulative})
    eq_dates = json.dumps([p["date"] for p in eq_points])
    eq_pnl = json.dumps([round(p["pnl"], 2) for p in eq_points])

    stats_row = f"""
  <div class="stats-grid">
    <div class="stat-card"><div class="num" style="color:#94a3b8;">{overall['total_trades']}</div><div class="lbl">Total Trades</div></div>
    <div class="stat-card"><div class="num" style="color:#4ade80;">{overall['total_wins']}</div><div class="lbl">Wins</div></div>
    <div class="stat-card"><div class="num" style="color:#f87171;">{overall['total_losses']}</div><div class="lbl">Losses</div></div>
    <div class="stat-card"><div class="num" style="color:{wr_color};">{overall['win_rate']}%</div><div class="lbl">Win Rate</div></div>
    <div class="stat-card"><div class="num" style="color:{pnl_color};">{overall['total_pnl']:+.2f}%</div><div class="lbl">Total PnL</div></div>
    <div class="stat-card"><div class="num" style="color:#818cf8;">{overall['stocks_with_signals']}</div><div class="lbl">Active Stocks</div></div>
  </div>"""

    summary_rows = ""
    for rank, (name, stats) in enumerate(sorted_stocks, 1):
        rank_cls = f"rank-{rank}" if rank <= 3 else ""
        wr_c = "green" if stats["win_rate"] >= 65 else "yellow" if stats["win_rate"] >= 50 else "red"
        pnl_c = "green" if stats["total_pnl"] >= 0 else "red"
        summary_rows += f"""
    <tr class=\"{rank_cls}\">
      <td style=\"color:#64748b;\">#{rank}</td>
      <td style=\"font-weight:700;\">{name}</td>
      <td class=\"num-cell\">{stats['trades']}</td>
      <td class=\"num-cell\" style=\"color:#4ade80;\">{stats['wins']}</td>
      <td class=\"num-cell\" style=\"color:#f87171;\">{stats['losses']}</td>
      <td class=\"num-cell {wr_c}\">{stats['win_rate']}%</td>
      <td class=\"num-cell {pnl_c}\">{stats['total_pnl']:+.2f}%</td>
      <td class=\"num-cell\">{stats['avg_pnl']:+.2f}%</td>
    </tr>"""

    daily_map = defaultdict(list)
    for name, trades in all_trades.items():
        for t in trades:
            daily_map[t["date"]].append({**t, "symbol": name})

    sorted_dates = sorted(daily_map.keys())
    daily_logs = ""
    daily_chart_dates = []
    daily_chart_pnl = []
    daily_chart_trades = []
    daily_chart_wins = []

    for date in sorted_dates:
        day_trades = daily_map[date]
        day_total = len(day_trades)
        day_wins = sum(1 for t in day_trades if t["pnl"] > 0)
        day_pnl = sum(t["pnl"] for t in day_trades)
        day_wr = round(day_wins / day_total * 100, 1) if day_total else 0
        daily_chart_dates.append(date)
        daily_chart_pnl.append(round(day_pnl, 2))
        daily_chart_trades.append(day_total)
        daily_chart_wins.append(day_wins)

        pnl_c = "green" if day_pnl >= 0 else "red"
        wr_c = "green" if day_wr >= 60 else "yellow" if day_wr >= 40 else "red"

        day_stock_rows = ""
        for t in day_trades:
            res_c = "green" if t["result"] == "TARGET_HIT" else "red" if t["result"] == "SL_HIT" else "yellow"
            dir_c = "SHORT" if t["direction"] == "SHORT" else "LONG"
            day_stock_rows += f"""
          <tr>
            <td>{t['symbol']}</td>
            <td>{dir_c}</td>
            <td>{t['gap_pct']:+.2f}%</td>
            <td class=\"num-cell\">{t['entry']}</td>
            <td class=\"num-cell\">{t['sl']}</td>
            <td class=\"num-cell\">{t['target']}</td>
            <td class=\"num-cell {res_c}\">{t['result']}</td>
            <td class=\"num-cell {res_c}\">{t['pnl']:+.2f}%</td>
          </tr>"""

        daily_logs += f"""
  <div class="stock-card">
    <div class="stock-header" onclick="toggle(this)">
      <div>
        <span class="stock-name">{date}</span>
        <span class="stock-stats">
          <span>{day_total} trades</span>
          <span class="{wr_c}">WR: {day_wr}%</span>
          <span class="{pnl_c}">PnL: {day_pnl:+.2f}%</span>
        </span>
      </div>
      <button class="toggle-btn" onclick="event.stopPropagation();toggle(this.parentElement)">{'Show Trades ▼' if day_stock_rows else 'No Trades'}</button>
    </div>
    <div class="trade-table">
      <table>
        <thead><tr><th>Stock</th><th>Dir</th><th>Gap</th><th>Entry</th><th>SL</th><th>Target</th><th>Result</th><th>PnL</th></tr></thead>
        <tbody>{day_stock_rows}</tbody>
      </table>
    </div>
  </div>"""

    daily_pnl_json = json.dumps(daily_chart_pnl)
    daily_trades_json = json.dumps(daily_chart_trades)
    daily_wins_json = json.dumps(daily_chart_wins)
    daily_labels_json = json.dumps(daily_chart_dates)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Small Gap Snap — Full Backtest</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0f1e; color:#e2e8f0; font-family:'Inter','Segoe UI',sans-serif; }}
  .hero {{
    background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 50%,#0f172a 100%);
    border-bottom:1px solid #1e293b; padding:48px 24px 32px; text-align:center;
    position:relative; overflow:hidden;
  }}
  .hero::before {{
    content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%;
    background:radial-gradient(circle at 30% 50%,rgba(99,102,241,0.06) 0%,transparent 60%);
  }}
  .hero h1 {{ font-size:32px; font-weight:900; letter-spacing:-1px; position:relative; }}
  .hero h1 span {{ background:linear-gradient(135deg,#818cf8,#6366f1,#4ade80); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
  .hero p {{ color:#64748b; font-size:13px; margin-top:8px; font-family:monospace; position:relative; }}
  .hero .badge {{
    display:inline-block; margin-top:12px; padding:4px 14px; border-radius:20px;
    font-size:11px; font-family:monospace; letter-spacing:1px;
    border:1px solid #334155; color:#94a3b8; background:#0f172a;
  }}
  .container {{ max-width:1200px; margin:0 auto; padding:24px; }}
  .stats-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin-bottom:28px; }}
  .stat-card {{ background:linear-gradient(135deg,#0f172a,#1e293b); border:1px solid #1e293b; border-radius:12px; padding:20px; text-align:center; }}
  .stat-card .num {{ font-size:28px; font-weight:800; font-family:monospace; }}
  .stat-card .lbl {{ color:#64748b; font-size:10px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; margin-top:4px; }}
  .section-title {{ font-size:13px; font-family:monospace; text-transform:uppercase; letter-spacing:2px; color:#64748b; margin-bottom:14px; padding-bottom:8px; border-bottom:1px solid #1e293b; margin-top:28px; }}
  .chart-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:28px; }}
  .chart-card {{ background:#0f172a; border:1px solid #1e293b; border-radius:14px; padding:20px; }}
  .chart-card h3 {{ font-size:12px; font-family:monospace; text-transform:uppercase; letter-spacing:1px; color:#64748b; margin-bottom:12px; }}
  .chart-card canvas {{ width:100% !important; height:auto !important; max-height:300px; }}
  @media(max-width:768px) {{ .chart-grid {{ grid-template-columns:1fr; }} }}
  .table-wrap {{ overflow-x:auto; margin-bottom:28px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ color:#64748b; font-family:monospace; font-size:11px; text-transform:uppercase; letter-spacing:1px; text-align:left; padding:10px 10px; border-bottom:1px solid #1e293b; white-space:nowrap; }}
  td {{ padding:10px 10px; border-bottom:1px solid #0f172a; white-space:nowrap; }}
  tr:hover td {{ background:#0f172a88; }}
  tr.rank-1 td {{ background:#312e8144; }}
  tr.rank-2 td {{ background:#312e8122; }}
  tr.rank-3 td {{ background:#312e8111; }}
  .num-cell {{ font-family:monospace; text-align:right; font-weight:600; }}
  .green {{ color:#4ade80; }}
  .red {{ color:#f87171; }}
  .yellow {{ color:#eab308; }}
  .stock-card {{ background:#0f172a; border:1px solid #1e293b; border-radius:12px; padding:16px; margin-bottom:12px; }}
  .stock-card .stock-header {{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; cursor:pointer; }}
  .stock-card .stock-name {{ font-size:16px; font-weight:700; }}
  .stock-card .stock-stats {{ display:flex; gap:16px; font-family:monospace; font-size:13px; }}
  .stock-card .trade-table {{ margin-top:12px; display:none; }}
  .stock-card .trade-table.show {{ display:block; }}
  .stock-card .toggle-btn {{ color:#60a5fa; font-size:11px; cursor:pointer; background:none; border:1px solid #334155; border-radius:6px; padding:4px 10px; font-family:monospace; }}
  .callout {{
    background:linear-gradient(135deg,#1e1b4b,#0f172a); border:1px solid #312e81; border-radius:14px;
    padding:20px; margin-bottom:28px; display:flex; align-items:center; gap:16px; flex-wrap:wrap;
  }}
  .callout .big {{ font-size:48px; font-weight:900; font-family:monospace; }}
  .callout .text {{ font-size:14px; color:#94a3b8; }}
  .footer {{ text-align:center; color:#334155; font-size:11px; font-family:monospace; padding:24px; border-top:1px solid #0f172a; margin-top:28px; }}
</style>
</head>
<body>
<div class="hero">
  <h1><span>Small Gap Snap</span> — Full Backtest</h1>
  <p>Gap 0.3-0.8% · Reverse direction · Target 50% fill · SL 0.5% · Daily OHLC via yfinance</p>
  <div class="badge">62 trading days · {overall['total_trades']} trades · {overall['win_rate']}% win rate · {START_DATE} → {END_DATE}</div>
</div>
<div class="container">
  <div class="callout">
    <div class="big" style="color:#4ade80;">{overall['win_rate']}%</div>
    <div class="text">
      <strong style="color:#e2e8f0;font-size:18px;">Win Rate Across {overall['total_trades']} Trades</strong><br>
      Total PnL: <span style="color:#4ade80;font-weight:700;">{overall['total_pnl']:+.2f}%</span> ·
      Stocks: {overall['stocks_with_signals']}/49 active ·
      Period: {START_DATE} to {END_DATE}
    </div>
  </div>
{stats_row}
  <div class="section-title">Stock Performance Summary</div>
  <div class="table-wrap">
  <table>
    <thead><tr>
      <th>Rank</th><th>Stock</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win Rate</th>
      <th>Total PnL</th><th>Avg PnL</th>
    </tr></thead>
    <tbody>
{summary_rows}
    </tbody></table></div>

  <div class="section-title">Charts</div>
  <div class="chart-grid">
    <div class="chart-card" style="grid-column:1/-1;"><h3>Equity Curve</h3><canvas id="chartEquity"></canvas></div>
    <div class="chart-card"><h3>Win Rate by Stock</h3><canvas id="chartWinRate"></canvas></div>
    <div class="chart-card"><h3>Total PnL by Stock</h3><canvas id="chartPnL"></canvas></div>
    <div class="chart-card"><h3>Trade Count by Stock</h3><canvas id="chartTrades"></canvas></div>
    <div class="chart-card"><h3>Win Rate vs Trade Count</h3><canvas id="chartScatter"></canvas></div>
    <div class="chart-card" style="grid-column:1/-1;"><h3>Daily PnL</h3><canvas id="chartDailyPnL"></canvas></div>
    <div class="chart-card" style="grid-column:1/-1;"><h3>Daily Trade Count</h3><canvas id="chartDailyTrades"></canvas></div>
  </div>

  <script>
    const labels = {symbols_json};
    const winRates = {wr_json};
    const pnls = {pnl_json};
    const tradeCounts = {tc_json};
    const colors = winRates.map(w => w >= 65 ? '#4ade80' : w >= 50 ? '#eab308' : '#f87171');
    const pnlColors = pnls.map(p => p >= 0 ? '#4ade80' : '#f87171');

    const dailyLabels = {daily_labels_json};
    const dailyPnl = {daily_pnl_json};
    const dailyTrades = {daily_trades_json};
    const dailyWins = {daily_wins_json};
    const dailyPnlColors = dailyPnl.map(p => p >= 0 ? '#4ade80' : '#f87171');

    const eqDates = {eq_dates};
    const eqPnl = {eq_pnl};

    new Chart(document.getElementById('chartEquity'), {{
      type: 'line', data: {{
        labels: eqDates,
        datasets: [{{
          label: 'Cumulative PnL %',
          data: eqPnl,
          borderColor: '#818cf8',
          backgroundColor: 'rgba(129,140,248,0.1)',
          fill: true,
          tension: 0.2,
          pointRadius: 2,
          pointBackgroundColor: '#818cf8',
        }}]
      }},
      options: {{
        responsive: true,
        plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 10 }} }} }} }},
        scales: {{
          x: {{ ticks: {{ maxTicksLimit: 15, color: '#64748b' }}, grid: {{ color: '#1e293b' }} }},
          y: {{ grid: {{ color: '#1e293b' }} }}
        }}
      }}
    }});

    new Chart(document.getElementById('chartWinRate'), {{
      type: 'bar', data: {{ labels, datasets: [{{ label:'Win Rate %', data: winRates, backgroundColor: colors, borderRadius:4 }}] }},
      options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }}, scales: {{ y:{{ beginAtZero:true, max:100, grid:{{ color:'#1e293b' }} }}, x:{{ grid:{{ display:false }} }} }} }}
    }});
    new Chart(document.getElementById('chartPnL'), {{
      type: 'bar', data: {{ labels, datasets: [{{ label:'Total PnL %', data: pnls, backgroundColor: pnlColors, borderRadius:4 }}] }},
      options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }}, scales: {{ y:{{ grid:{{ color:'#1e293b' }} }}, x:{{ grid:{{ display:false }} }} }} }}
    }});
    new Chart(document.getElementById('chartTrades'), {{
      type: 'bar', data: {{ labels, datasets: [{{ label:'Trade Count', data: tradeCounts, backgroundColor:'#818cf8', borderRadius:4 }}] }},
      options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }}, scales: {{ y:{{ beginAtZero:true, grid:{{ color:'#1e293b' }} }}, x:{{ grid:{{ display:false }} }} }} }}
    }});
    new Chart(document.getElementById('chartScatter'), {{
      type: 'scatter', data: {{
        datasets: [{{
          label: 'Stocks',
          data: winRates.map((w, i) => ({{ x: tradeCounts[i], y: w }})),
          backgroundColor: colors,
          pointRadius: 6,
        }}]
      }},
      options: {{
        responsive:true, plugins:{{ legend:{{ display:false }} }},
        scales: {{
          x: {{ title:{{ display:true, text:'Trade Count', color:'#64748b' }}, beginAtZero:true, grid:{{ color:'#1e293b' }} }},
          y: {{ title:{{ display:true, text:'Win Rate %', color:'#64748b' }}, beginAtZero:true, max:100, grid:{{ color:'#1e293b' }} }}
        }}
      }}
    }});
    new Chart(document.getElementById('chartDailyPnL'), {{
      type: 'bar', data: {{ labels: dailyLabels, datasets: [{{ label:'Daily PnL %', data: dailyPnl, backgroundColor: dailyPnlColors, borderRadius:3 }}] }},
      options: {{ responsive:true, plugins:{{ legend:{{ display:false }} }}, scales: {{ x:{{ ticks:{{ maxTicksLimit:20, color:'#64748b' }}, grid:{{ display:false }} }}, y:{{ grid:{{ color:'#1e293b' }} }} }} }}
    }});
    new Chart(document.getElementById('chartDailyTrades'), {{
      type: 'bar', data: {{ labels: dailyLabels, datasets: [{{ label:'Trades', data: dailyTrades, backgroundColor:'#818cf8', borderRadius:3 }}, {{ label:'Wins', data: dailyWins, backgroundColor:'#4ade80', borderRadius:3 }}] }},
      options: {{ responsive:true, plugins:{{ legend:{{ labels:{{ color:'#94a3b8', font:{{ size:10 }} }} }} }}, scales: {{ x:{{ ticks:{{ maxTicksLimit:20, color:'#64748b' }}, grid:{{ display:false }} }}, y:{{ beginAtZero:true, grid:{{ color:'#1e293b' }} }} }} }}
    }});
  </script>

  <div class="section-title">Daily Breakdown</div>
  <p style="color:#64748b;font-size:12px;font-family:monospace;margin-bottom:12px;">Each day shows gap (%), direction, entry, SL (0.5%), target (50% fill), result, and PnL.</p>
{daily_logs}

  <div class="footer">
    Generated by Small Gap Snap Backtest Engine &middot; {now} &middot; Data: yfinance<br>
    <span style="color:#1e293b;">Strategy: Trade gaps 0.3-0.8% · Reverse direction · Target 50% fill · SL 0.5% · Time exit EOD</span>
  </div>
</div>
<script>
  function toggle(el) {{
    const table = el.parentElement.querySelector('.trade-table');
    const btn = el.querySelector('.toggle-btn');
    if (table) {{
      table.classList.toggle('show');
      btn.textContent = table.classList.contains('show') ? 'Hide Trades ▲' : 'Show Trades ▼';
    }}
  }}
</script>
</body>
</html>'''

    return html


def main():
    print("=" * 70)
    print("  SMALL GAP SNAP — FULL BACKTEST")
    print(f"  Period: {START_DATE} to {END_DATE}")
    print("  Strategy: Gap 0.3-0.8%, reverse direction, target 50% fill, SL 0.5%")
    print("=" * 70)

    all_trades, stock_stats, overall = backtest_all_parallel()

    if not all_trades:
        print("  No trades found.")
        return

    gross_w = sum(max(0, s["total_pnl"]) for s in stock_stats.values())
    gross_l = sum(abs(min(0, s["total_pnl"])) for s in stock_stats.values())
    pf = round(gross_w / gross_l, 2) if gross_l > 0 else float("inf")

    print(f"\n  {'=' * 70}")
    print(f"  OVERALL RESULTS")
    print(f"  {'=' * 70}")
    print(f"  Stocks with signals: {overall['stocks_with_signals']}/{len(NIFTY_50)}")
    print(f"  Total trades:        {overall['total_trades']}")
    print(f"  Win rate:            {overall['win_rate']}%")
    print(f"  Total PnL:           {overall['total_pnl']:+.2f}%")
    print(f"  Profit factor:       {pf}")

    sorted_s = sorted(stock_stats.items(), key=lambda x: -x[1]["win_rate"])
    print(f"\n  Top 10 stocks by win rate:")
    for name, s in sorted_s[:10]:
        print(f"    {name:18s} WR: {s['win_rate']:5.1f}%  PnL: {s['total_pnl']:+7.2f}%  Trades: {s['trades']}")

    print(f"\n  Generating HTML report...")
    html = generate_html_report(all_trades, stock_stats, overall)

    report_path = os.path.join(ROOT_DIR, "small-gap-snap-backtest.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Report: {report_path}")
    print(f"\n  {'=' * 70}")
    print(f"  DONE")
    print(f"  {'=' * 70}")


if __name__ == "__main__":
    main()
