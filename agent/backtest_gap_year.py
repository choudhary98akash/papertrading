#!/usr/bin/env python3
"""
Gap Mean Reversion — Full Year Backtest + HTML Report Generator
Entry: 9:25 AM (daily open)
Exit:  3:45 PM (daily close) or SL/Target hit intraday
Data:  Daily OHLC via yfinance (Jan 2026 – present)
"""

import sys, json, os, io, warnings, math
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
OUTPUT_DIR = os.path.join(BASE_DIR, "backtest_report")
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

START_DATE = "2026-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")


def clean_sym(s):
    return s.replace(".NS", "")


def backtest_stock(symbol):
    """Backtest gap mean reversion on a single stock. Returns dict of results."""
    name = clean_sym(symbol)
    try:
        df = yf.download(symbol, start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
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

        # Gap calculation
        gap_pct = (open_p - prev_close) / prev_close * 100

        # Check minimum gap threshold
        if abs(gap_pct) < 0.5:
            continue

        direction = "SHORT" if gap_pct > 0 else "LONG"
        entry = open_p
        sl = entry * 0.99 if direction == "LONG" else entry * 1.01
        target = entry * 1.012 if direction == "LONG" else entry * 0.988

        # Simulate intraday exit using daily OHLC
        sl_hit = low <= sl if direction == "LONG" else high >= sl
        tgt_hit = high >= target if direction == "LONG" else low <= target

        if tgt_hit:
            exit_price = target
            result = "TARGET_HIT"
            pnl = 1.2
        elif sl_hit:
            exit_price = sl
            result = "SL_HIT"
            pnl = -1.0
        else:
            exit_price = close
            pnl_pct = ((close - entry) / entry) * 100
            if direction == "SHORT":
                pnl_pct = -pnl_pct
            pnl = round(pnl_pct, 2)
            result = "TIME_EXIT"

        trades.append({
            "date": date_str,
            "symbol": name,
            "direction": direction,
            "gap_pct": round(gap_pct, 2),
            "entry": round(entry, 2),
            "sl": round(sl, 2),
            "target": round(target, 2),
            "exit_price": round(exit_price, 2),
            "result": result,
            "pnl": pnl,
        })

    return trades if trades else None


def backtest_all_parallel():
    """Run backtest on all stocks in parallel."""
    all_trades = {}
    stock_stats = {}
    total_trades = 0
    total_wins = 0
    total_pnl = 0.0

    print(f"\n  Backtesting 49 stocks (parallel) from {START_DATE} to {END_DATE}...\n")

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
                    print(f"    [{done:2d}/49] {name:16s} {len(trades):3d} trades  WR:{wr:5.1f}%  PnL:{pnl:+.2f}%")
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


def generate_html_backtest(all_trades, stock_stats, overall):
    """Generate comprehensive HTML backtest report using string replace template."""
    sorted_stocks = sorted(stock_stats.items(), key=lambda x: (-x[1]["win_rate"], -x[1]["total_pnl"]))

    symbols_json = json.dumps([s[0] for s in sorted_stocks])
    wr_json = json.dumps([s[1]["win_rate"] for s in sorted_stocks])
    pnl_json = json.dumps([s[1]["total_pnl"] for s in sorted_stocks])
    tc_json = json.dumps([s[1]["trades"] for s in sorted_stocks])

    wr_color = "#4ade80" if overall["win_rate"] >= 70 else "#eab308" if overall["win_rate"] >= 50 else "#f87171"
    pnl_color = "#4ade80" if overall["total_pnl"] >= 0 else "#f87171"

    # Build stats row
    stats_row = f"""
  <div class="stats-grid">
    <div class="stat-card"><div class="num" style="color:#94a3b8;">{overall['total_trades']}</div><div class="lbl">Total Trades</div></div>
    <div class="stat-card"><div class="num" style="color:#4ade80;">{overall['total_wins']}</div><div class="lbl">Wins</div></div>
    <div class="stat-card"><div class="num" style="color:#f87171;">{overall['total_losses']}</div><div class="lbl">Losses</div></div>
    <div class="stat-card"><div class="num" style="color:{wr_color};">{overall['win_rate']}%</div><div class="lbl">Win Rate</div></div>
    <div class="stat-card"><div class="num" style="color:{pnl_color};">{overall['total_pnl']:+.2f}%</div><div class="lbl">Total PnL</div></div>
    <div class="stat-card"><div class="num" style="color:#818cf8;">{overall['stocks_with_signals']}</div><div class="lbl">Active Stocks</div></div>
  </div>"""

    # Build summary table rows
    summary_rows = ""
    for rank, (name, stats) in enumerate(sorted_stocks, 1):
        rank_cls = f"rank-{rank}" if rank <= 3 else ""
        wr_c = "green" if stats["win_rate"] >= 70 else "yellow" if stats["win_rate"] >= 50 else "red"
        pnl_c = "green" if stats["total_pnl"] >= 0 else "red"
        summary_rows += f"""
    <tr class="{rank_cls}">
      <td style="color:#64748b;">#{rank}</td>
      <td style="font-weight:700;">{name}</td>
      <td class="num-cell">{stats['trades']}</td>
      <td class="num-cell" style="color:#4ade80;">{stats['wins']}</td>
      <td class="num-cell" style="color:#f87171;">{stats['losses']}</td>
      <td class="num-cell {wr_c}">{stats['win_rate']}%</td>
      <td class="num-cell {pnl_c}">{stats['total_pnl']:+.2f}%</td>
      <td class="num-cell">{stats['avg_pnl']:+.2f}%</td>
    </tr>"""

    # Build per-stock trade logs
    stock_logs = ""
    for rank, (name, stats) in enumerate(sorted_stocks, 1):
        trades = all_trades.get(name, [])
        wr_c = "green" if stats["win_rate"] >= 70 else "yellow" if stats["win_rate"] >= 50 else "red"
        pnl_c = "green" if stats["total_pnl"] >= 0 else "red"
        trade_rows = ""
        for t in trades:
            res_c = "green" if t["result"] == "TARGET_HIT" else "red" if t["result"] == "SL_HIT" else "yellow"
            dir_icon = "SHORT" if t["direction"] == "SHORT" else "LONG"
            trade_rows += f"""
      <tr>
        <td>{t['date']}</td>
        <td>{dir_icon}</td>
        <td>{t['gap_pct']:+.2f}%</td>
        <td class="num-cell">{t['entry']}</td>
        <td class="num-cell red">{t['sl']}</td>
        <td class="num-cell green">{t['target']}</td>
        <td class="num-cell {res_c}">{t['result']}</td>
        <td class="num-cell {res_c}">{t['pnl']:+.2f}%</td>
      </tr>"""

        stock_logs += f"""
  <div class="stock-card">
    <div class="stock-header" onclick="toggle(this)">
      <div>
        <span class="stock-name">#{rank} {name}</span>
        <span class="stock-stats">
          <span>{stats['trades']} trades</span>
          <span class="{wr_c}">WR: {stats['win_rate']}%</span>
          <span class="{pnl_c}">PnL: {stats['total_pnl']:+.2f}%</span>
        </span>
      </div>
      <button class="toggle-btn" onclick="event.stopPropagation();toggle(this.parentElement)">Show Trades ▼</button>
    </div>
    <div class="trade-table">
      <table>
        <thead><tr>
          <th>Date</th><th>Dir</th><th>Gap</th><th>Entry</th><th>SL</th><th>Target</th><th>Result</th><th>PnL</th>
        </tr></thead>
        <tbody>{trade_rows}</tbody>
      </table>
    </div>
  </div>"""

    # ── Daily Breakdown ──
    daily_map = defaultdict(list)
    for name, trades in all_trades.items():
        for t in trades:
            daily_map[t["date"]].append({**t, "symbol": name})

    sorted_dates = sorted(daily_map.keys())
    daily_rows = ""
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

        # Per-stock rows inside this day
        day_stock_rows = ""
        for t in day_trades:
            res_c = "green" if t["result"] == "TARGET_HIT" else "red" if t["result"] == "SL_HIT" else "yellow"
            dir_c = "SHORT" if t["direction"] == "SHORT" else "LONG"
            day_stock_rows += f"""
          <tr>
            <td>{t['symbol']}</td>
            <td>{dir_c}</td>
            <td>{t['gap_pct']:+.2f}%</td>
            <td class="num-cell">{t['entry']}</td>
            <td class="num-cell {res_c}">{t['result']}</td>
            <td class="num-cell {res_c}">{t['pnl']:+.2f}%</td>
          </tr>"""

        daily_rows += f"""
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
        <thead><tr><th>Stock</th><th>Dir</th><th>Gap</th><th>Entry</th><th>Result</th><th>PnL</th></tr></thead>
        <tbody>{day_stock_rows}</tbody>
      </table>
    </div>
  </div>"""

    daily_pnl_json = json.dumps(daily_chart_pnl)
    daily_trades_json = json.dumps(daily_chart_trades)
    daily_wins_json = json.dumps(daily_chart_wins)
    daily_labels_json = json.dumps(daily_chart_dates)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    period_str = f"{START_DATE} → {END_DATE}"

    # Read template and substitute
    with open(os.path.join(os.path.dirname(__file__), "backtest_report_template.html"), "r", encoding="utf-8") as f:
        template = f.read()

    html = template.replace("{{STATS_ROW}}", stats_row)
    html = html.replace("{{SUMMARY_ROWS}}", summary_rows)
    html = html.replace("{{STOCK_LOGS}}", stock_logs)
    html = html.replace("{{DAILY_LOGS}}", daily_rows)
    html = html.replace("{{SYMBOLS_JSON}}", symbols_json)
    html = html.replace("{{WR_JSON}}", wr_json)
    html = html.replace("{{PNL_JSON}}", pnl_json)
    html = html.replace("{{TC_JSON}}", tc_json)
    html = html.replace("{{DAILY_PNL_JSON}}", daily_pnl_json)
    html = html.replace("{{DAILY_TRADES_JSON}}", daily_trades_json)
    html = html.replace("{{DAILY_WINS_JSON}}", daily_wins_json)
    html = html.replace("{{DAILY_LABELS_JSON}}", daily_labels_json)
    html = html.replace("{{TOTAL_TRADES}}", str(overall["total_trades"]))
    html = html.replace("{{WIN_RATE}}", str(overall["win_rate"]))
    html = html.replace("{{PERIOD_STR}}", period_str)
    html = html.replace("{{TIMESTAMP}}", now)

    return html

def main():
    print(f"{'='*70}")
    print(f"  GAP MEAN REVERSION — FULL YEAR BACKTEST")
    print(f"  Period: {START_DATE} to {END_DATE}")
    print(f"  Strategy: Gap >0.5% → reverse at open, SL 1%, Target 1.2%")
    print(f"{'='*70}\n")

    # Run parallel backtest
    all_trades, stock_stats, overall = backtest_all_parallel()

    if not all_trades:
        print("  No trades found.")
        return

    # Print overall summary
    print(f"\n  {'='*70}")
    print(f"  OVERALL RESULTS")
    print(f"  {'='*70}")
    print(f"  Stocks with signals: {overall['stocks_with_signals']}/{len(NIFTY_50)}")
    print(f"  Total trades:        {overall['total_trades']}")
    print(f"  Win rate:            {overall['win_rate']}%")
    print(f"  Total PnL:           {overall['total_pnl']:+.2f}%")

    gross_w = sum(max(0, s["total_pnl"]) for s in stock_stats.values())
    gross_l = sum(abs(min(0, s["total_pnl"])) for s in stock_stats.values())
    pf = round(gross_w / gross_l, 2) if gross_l > 0 else float("inf")
    print(f"  Profit factor:       {pf}")

    # Top/bottom stocks
    sorted_s = sorted(stock_stats.items(), key=lambda x: -x[1]["win_rate"])
    print(f"\n  Top 5 stocks by win rate:")
    for name, s in sorted_s[:5]:
        print(f"    {name:18s} WR: {s['win_rate']:5.1f}%  PnL: {s['total_pnl']:+7.2f}%  Trades: {s['trades']}")

    print(f"\n  Bottom 5 stocks by win rate:")
    for name, s in sorted_s[-5:]:
        print(f"    {name:18s} WR: {s['win_rate']:5.1f}%  PnL: {s['total_pnl']:+7.2f}%  Trades: {s['trades']}")

    # Generate HTML
    print(f"\n  Generating HTML report...")
    html = generate_html_backtest(all_trades, stock_stats, overall)

    report_path = os.path.join(OUTPUT_DIR, "gap_backtest_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Report: {report_path}")

    # Also copy to root
    root_report = os.path.join(ROOT_DIR, "gap-backtest-report.html")
    with open(root_report, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Report: {root_report}")

    # Save JSON
    json_path = os.path.join(BASE_DIR, "backtest_report", "gap_backtest_data.json")
    with open(json_path, "w") as f:
        json.dump({
            "overall": overall,
            "stocks": {k: v for k, v in sorted_s},
        }, f, indent=2)
    print(f"  Data:   {json_path}")

    print(f"\n  {'='*70}")
    print(f"  DONE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
