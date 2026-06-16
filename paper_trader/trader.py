#!/usr/bin/env python3
"""Paper trader — runs daily via GitHub Actions, zero manual steps."""
import json, os, sys
from datetime import datetime, timezone
from collections import defaultdict
import numpy as np

IST = timezone.utc  # GitHub Actions runs UTC; adjust as needed

def get_day_strategy(dow):
    strategies = {
        0: {"name": "Monday — Fake Strength, Real Weakness", "dir": "SHORT", "dir_filter": lambda g: g > 0, "vol_filter": lambda v: v < 0.8, "other_filter": lambda e: True},
        1: {"name": "Tuesday — Every Small Gap Counts", "dir": "BOTH", "dir_filter": lambda g: True, "vol_filter": lambda v: v < 0.8, "other_filter": lambda e: True},
        2: {"name": "Wednesday — Buy the Fake Selloff", "dir": "LONG", "dir_filter": lambda g: g < 0, "vol_filter": lambda v: v < 1.5, "other_filter": lambda e: True},
        3: {"name": "Thursday — Short the Fake Rally", "dir": "SHORT", "dir_filter": lambda g: g > 0, "vol_filter": lambda v: v < 1.5, "other_filter": lambda e: True},
        4: {"name": "Friday — Weekend Prep", "dir": "BOTH", "dir_filter": lambda g: True, "vol_filter": lambda v: v < 1.5, "other_filter": lambda e: True},
    }
    return strategies.get(dow, strategies[1])

def compute_stats(trades):
    if not trades:
        return {"total": 0, "wins": 0, "losses": 0, "winrate": 0, "pnl": 0, "avg_pnl": 0}
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl", 0) < 0)
    total = len(trades)
    pnl = sum(t.get("pnl", 0) for t in trades)
    return {
        "total": total, "wins": wins, "losses": losses,
        "winrate": round(wins / total * 100, 1) if total > 0 else 0,
        "pnl": round(pnl, 2), "avg_pnl": round(pnl / total, 3) if total > 0 else 0
    }

def generate_html(ledger, day_picks, today, day_name):
    all_trades = ledger.get("trades", [])
    stats = compute_stats(all_trades)

    # Day-by-day breakdown
    day_breakdown = defaultdict(list)
    for t in all_trades:
        day_breakdown[t.get("date", "unknown")].append(t)

    day_stats = []
    for date, trades in sorted(day_breakdown.items()):
        ds = compute_stats(trades)
        day_stats.append({"date": date, **ds})

    # Cumulative PnL
    cum_pnl = []
    running = 0
    for t in all_trades:
        running += t.get("pnl", 0)
        cum_pnl.append(round(running, 2))

    # Picks table
    picks_rows = ""
    for p in day_picks:
        cls = "win" if p.get("pnl", 0) > 0 else ("loss" if p.get("pnl", 0) < 0 else "")
        dir_cls = "long" if p.get("trade") == "LONG" else "short"
        picks_rows += f"<tr class='{cls}'><td>{p['stock']}</td><td class='{'red' if p['gap']>0 else 'green'}'>{p['gap']:+.2f}%</td><td>{p['vol_ratio']:.1f}x</td><td><span class='badge {dir_cls}'>{p['trade']}</span></td><td>{p['entry']}</td><td>{p['target']}</td><td>{p['sl']}</td><td>{p['close']}</td><td>{p['result']}</td><td>{p['pnl']:+.2f}%</td></tr>"

    # Day history table
    history_rows = ""
    for ds in sorted(day_stats, key=lambda x: x["date"]):
        cls = "win" if ds["pnl"] > 0 else "loss"
        history_rows += f"<tr class='{cls}'><td>{ds['date']}</td><td>{ds['total']}</td><td>{ds['wins']}</td><td>{ds['losses']}</td><td>{ds['winrate']}%</td><td>{ds['pnl']:+.2f}%</td></tr>"

    # Strategy for the trade date
    strategy_rules = {
        0: "Short gap-ups 0.3-0.8% with vol<0.8x. Skip gap-downs. 62.6% fill rate.",
        1: "Trade BOTH directions. Gap-downs (82.1%) prefer LONG. Gap-ups (73.2%) SHORT. Vol<0.8x.",
        2: "LONG all gap-downs 0.3-0.8%. Best setup 84.7% fill. NEVER short gap-ups.",
        3: "SHORT all gap-ups 0.3-0.8%. 79.2% fill (low vol). NEVER buy gap-downs.",
        4: "Gap-down + low vol → LONG (80.6%). Gap-up + high vol → SHORT (78.1%). Close by 3:10 PM.",
    }
    # Derive day from the picks data if available
    today_dow = 1  # default Tue
    if day_picks:
        first = day_picks[0] if isinstance(day_picks, list) and len(day_picks) > 0 else None
    else:
        first = None
    if first and "day" in first:
        day_map = {"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4}
        today_dow = day_map.get(first["day"], 1)
    rule = strategy_rules.get(today_dow, "")

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Trader — Live</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f1117; color:#e1e4e8; padding:20px; }}
h1 {{ font-size:24px; }}
h2 {{ font-size:18px; margin:20px 0 10px; color:#8b949e; }}
.sub {{ color:#8b949e; font-size:14px; }}
.stats {{ display:flex; gap:12px; flex-wrap:wrap; margin:16px 0; }}
.stat {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:12px 20px; flex:1; min-width:100px; }}
.stat .num {{ font-size:28px; font-weight:700; }}
.stat .lbl {{ font-size:12px; color:#8b949e; }}
.green {{ color:#3fb950; }} .red {{ color:#f85149; }} .yellow {{ color:#d29922; }}
table {{ width:100%; border-collapse:collapse; margin:10px 0; font-size:13px; }}
th, td {{ padding:6px 8px; text-align:left; border-bottom:1px solid #21262d; }}
th {{ background:#161b22; color:#8b949e; font-weight:600; position:sticky; top:0; }}
tr:hover {{ background:#1c2128; }}
tr.win {{ border-left:3px solid #3fb950; }}
tr.loss {{ border-left:3px solid #f85149; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.long {{ background:#0d2810; color:#3fb950; }}
.short {{ background:#280d0d; color:#f85149; }}
.chart-box {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:15px; margin:15px 0; }}
.rule {{ background:#1a1d24; padding:10px 15px; border-radius:6px; font-size:13px; color:#8b949e; margin:10px 0; }}
</style></head>
<body>
<h1>📈 Paper Trader — Live Results</h1>
<p class="sub">Running daily via GitHub Actions · {today} · {day_name}</p>

<div class="rule">📋 Today's strategy: <b>{day_name}</b> — {rule}</div>

<div class="stats">
<div class="stat"><div class="num">{stats['total']}</div><div class="lbl">Total Trades</div></div>
<div class="stat"><div class="num green">{stats['wins']}</div><div class="lbl">Wins</div></div>
<div class="stat"><div class="num red">{stats['losses']}</div><div class="lbl">Losses</div></div>
<div class="stat"><div class="num {'green' if stats['winrate']>=70 else 'yellow'}">{stats['winrate']}%</div><div class="lbl">Win Rate</div></div>
<div class="stat"><div class="num {'green' if stats['pnl']>=0 else 'red'}">{stats['pnl']:+.2f}%</div><div class="lbl">Total PnL</div></div>
<div class="stat"><div class="num {('green' if stats['avg_pnl']>=0 else 'red')}">{stats['avg_pnl']:+.3f}%</div><div class="lbl">Avg PnL/Trade</div></div>
</div>

<div class="chart-box"><canvas id="cumChart" height="80"></canvas></div>
<div class="chart-box"><canvas id="dayChart" height="80"></canvas></div>

<h2>📊 Today's Picks ({len(day_picks)} trades)</h2>
<table><tr><th>Stock</th><th>Gap</th><th>Vol</th><th>Trade</th><th>Entry</th><th>Target</th><th>SL</th><th>Close</th><th>Result</th><th>PnL</th></tr>{picks_rows}</table>

<h2>📅 Daily History</h2>
<table><tr><th>Date</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>PnL</th></tr>{history_rows}</table>

<script>
const cumData = {json.dumps(cum_pnl)};
const dayLabels = {json.dumps([ds['date'] for ds in sorted(day_stats, key=lambda x: x['date'])])};
const dayPnls = {json.dumps([ds['pnl'] for ds in sorted(day_stats, key=lambda x: x['date'])])};
const dayWrs = {json.dumps([ds['winrate'] for ds in sorted(day_stats, key=lambda x: x['date'])])};

new Chart(document.getElementById('cumChart'), {{
    type: 'line',
    data: {{ labels: cumData.map((_,i)=>i+1), datasets: [{{ label:'Cumulative PnL %', data:cumData, borderColor:'#3fb950', backgroundColor:'rgba(63,185,80,0.1)', fill:true, tension:0.3 }}] }},
    options: {{ responsive:true, plugins:{{ legend:{{ display:false }}, title:{{ display:true, text:'Cumulative PnL Over Time', color:'#8b949e' }} }}, scales:{{ x:{{ ticks:{{ color:'#8b949e' }} }}, y:{{ ticks:{{ color:'#8b949e' }} }} }} }}
}});

new Chart(document.getElementById('dayChart'), {{
    type: 'bar',
    data: {{ labels: dayLabels, datasets: [
        {{ label:'Daily PnL %', data:dayPnls, backgroundColor:dayPnls.map(v=>v>=0?'rgba(63,185,80,0.7)':'rgba(248,81,73,0.7)'), borderColor:dayPnls.map(v=>v>=0?'#3fb950':'#f85149'), borderWidth:1 }},
        {{ label:'Win Rate %', data:dayWrs, type:'line', borderColor:'#d29922', backgroundColor:'rgba(210,153,34,0.1)', fill:false, tension:0.3, yAxisID:'y1' }}
    ] }},
    options: {{ responsive:true, plugins:{{ title:{{ display:true, text:'Daily Performance', color:'#8b949e' }} }}, scales:{{ x:{{ ticks:{{ color:'#8b949e' }} }}, y:{{ ticks:{{ color:'#8b949e' }}, position:'left' }}, y1:{{ ticks:{{ color:'#d29922' }}, position:'right', max:100, grid:{{ drawOnChartArea:false }} }} }} }}
}});
</script>
<p style="color:#484f58;font-size:12px;margin-top:20px">Auto-generated by Paper Trader · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
</body></html>'''

    return html

def run_paper_trade():
    # Import yfinance inside to avoid import errors if missing
    import yfinance as yf

    today = datetime.now()
    dow = today.weekday()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_name = day_names[dow]

    if dow >= 5:
        print(f"Weekend ({day_name}) — no trading")
        return

    print(f"Running paper trade for {day_name} ({today.strftime('%Y-%m-%d')})")

    strategy = get_day_strategy(dow)
    print(f"Strategy: {strategy['name']}")

    # Nifty 50 symbols
    symbols = [
        'RELIANCE.NS','TCS.NS','HDFCBANK.NS','INFY.NS','ICICIBANK.NS',
        'HINDUNILVR.NS','ITC.NS','SBIN.NS','BHARTIARTL.NS','KOTAKBANK.NS',
        'LT.NS','WIPRO.NS','AXISBANK.NS','BAJFINANCE.NS','MARUTI.NS',
        'TITAN.NS','SUNPHARMA.NS','ONGC.NS','NTPC.NS','POWERGRID.NS',
        'M&M.NS','HCLTECH.NS','ULTRACEMCO.NS','NESTLEIND.NS','ASIANPAINT.NS',
        'JSWSTEEL.NS','ADANIPORTS.NS','HINDALCO.NS','TATASTEEL.NS',
        'BAJAJFINSV.NS','DRREDDY.NS','ADANIENT.NS','BRITANNIA.NS','CIPLA.NS',
        'COALINDIA.NS','DIVISLAB.NS','EICHERMOT.NS','GRASIM.NS','HEROMOTOCO.NS',
        'HDFCLIFE.NS','SBILIFE.NS','APOLLOHOSP.NS','BPCL.NS','BEL.NS',
        'BAJAJHLDNG.NS','INDUSINDBK.NS','SHRIRAMFIN.NS','TATACONSUM.NS','TRENT.NS'
    ]
    stock_names = {s: s.replace('.NS','') for s in symbols}

    today_str = today.strftime('%Y-%m-%d')
    from datetime import timedelta
    # Fetch extra days ahead to ensure today's completed candle is available
    end_str = (today + timedelta(days=2)).strftime('%Y-%m-%d')
    start_str = (today - timedelta(days=20)).strftime('%Y-%m-%d')

    print("Fetching data...")
    try:
        df = yf.download(symbols, start=start_str, end=end_str, interval='1d', progress=False, auto_adjust=True)
    except Exception as e:
        print(f"Fetch error: {e}")
        return

    available_dates = [d.strftime('%Y-%m-%d') for d in df.index]
    print(f"Available dates: {available_dates}")

    # Find the most recent trading day that has complete data
    # If today (weekday) has data, use it (market closed)
    if today_str in available_dates and dow < 5:
        trade_date = today_str
    else:
        # Otherwise use last completed day
        completed_dates = [d for d in available_dates if d < today_str]
        if not completed_dates:
            completed_dates = available_dates
        trade_date = completed_dates[-1]
    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    trade_dow = trade_dt.weekday()

    # Override DOW with actual trade date's day
    trade_dt = datetime.strptime(trade_date, '%Y-%m-%d')
    trade_dow = trade_dt.weekday()
    print(f"Trade date: {trade_date} ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][trade_dow]})")
    print(f"System says today is {today_str} ({day_name}) — trading on {trade_date}")

    # Get previous trading day
    idx = available_dates.index(trade_date)
    prev_date = available_dates[idx - 1] if idx > 0 else available_dates[0]

    print(f"Trading date: {trade_date}, Prev date: {prev_date}")

    # Check if already have picks for this date in ledger
    ledger_path = "paper_trader/ledger.json"
    if os.path.exists(ledger_path):
        ledger = json.load(open(ledger_path))
    else:
        ledger = {"trades": [], "runs": []}

    # Use trade date's day of week for strategy
    actual_day_name = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"][trade_dow]

    existing_dates = {t.get("date") for t in ledger["trades"]}
    if trade_date in existing_dates:
        print(f"Already processed {trade_date} — skipping")
        # Still regenerate HTML below
    else:
        # Use trade date's day of week for strategy
        strategy = get_day_strategy(trade_dow)
        print(f"Using strategy: {strategy['name']}")
        # Process
        try:
            yclose = df['Close'].loc[prev_date]
            topen = df['Open'].loc[trade_date]
            thigh = df['High'].loc[trade_date]
            tlow = df['Low'].loc[trade_date]
            tclose = df['Close'].loc[trade_date]
            tvol = df['Volume'].loc[trade_date]
        except Exception as e:
            print(f"Data error: {e}")
            return

        # Compute market context — what % of stocks gap in each direction?
        gap_directions = []
        for sym in symbols:
            try:
                pc2 = float(yclose[sym])
                op2 = float(topen[sym])
                if pc2 != 0 and not np.isnan(pc2) and not np.isnan(op2):
                    g2 = (op2 - pc2) / pc2 * 100
                    if abs(g2) >= 0.15:
                        gap_directions.append(g2)
            except:
                continue
        pct_up = sum(1 for g in gap_directions if g > 0) / len(gap_directions) * 100 if gap_directions else 50
        print(f"Market context: {len(gap_directions)} stocks with gaps, {pct_up:.0f}% gap-up, {100-pct_up:.0f}% gap-down")

        # Volume history
        vol_hist = df['Volume'].loc[:prev_date]

        day_picks = []
        for sym in symbols:
            name = stock_names[sym]
            try:
                pc = float(yclose[sym])
                op = float(topen[sym])
                hp = float(thigh[sym])
                lp = float(tlow[sym])
                cp = float(tclose[sym])
                vt = float(tvol[sym])
            except:
                continue
            if pc == 0 or np.isnan(pc):
                continue

            gap = (op - pc) / pc * 100
            oc = (cp - op) / op * 100 if op != 0 else 0
            day_range = (hp - lp) / pc * 100

            vols = [float(v) for v in vol_hist[sym].dropna() if not np.isnan(float(v))]
            avg_vol = np.mean(vols[-10:]) if len(vols) >= 10 else np.mean(vols) if len(vols) > 0 else vt
            vol_ratio = vt / avg_vol if avg_vol > 0 else 1

            gap_filled = (lp <= pc) if gap > 0 else (hp >= pc)
            if gap > 0:
                fill_pct = min(100, (op - lp) / (op - pc) * 100) if (op - pc) != 0 else 0
            else:
                fill_pct = min(100, (hp - op) / (pc - op) * 100) if (pc - op) != 0 else 0

            # Apply strategy
            abs_gap = abs(gap)
            trade = "NONE"
            direction = ""
            target_price = 0
            sl_price = 0

            # Market tide filter: if >70% stocks gap same direction, don't trade against it
            # When 91% gap up, don't SHORT (which bets on gap filling = going down)
            # When 91% gap down, don't LONG (which bets on gap filling = going up)
            strong_tide_up = pct_up > 70
            strong_tide_dn = pct_up < 30
            fading_tide = (gap > 0 and strong_tide_up) or (gap < 0 and strong_tide_dn)

            if 0.3 <= abs_gap <= 0.8 and not fading_tide:
                # Tuesday: golden day, trade low-vol gaps in both directions
                if trade_dow == 1:
                    if gap < 0 and vol_ratio < 0.8:
                        trade = "LONG"; direction = "gap-down reversal"
                        target_price = op * (1 + abs_gap * 0.5 / 100)
                        sl_price = op * (1 - 0.5 / 100)
                    elif gap > 0 and vol_ratio < 0.8:
                        trade = "SHORT"; direction = "gap-up fade"
                        target_price = op * (1 - abs_gap * 0.5 / 100)
                        sl_price = op * (1 + 0.5 / 100)
                    elif gap < 0 and vol_ratio < 1.5:
                        trade = "LONG"; direction = "moderate vol gap-down"
                        target_price = op * (1 + abs_gap * 0.5 / 100)
                        sl_price = op * (1 - 0.5 / 100)
                # Wednesday: long gap-downs only
                elif trade_dow == 2 and gap < 0:
                    trade = "LONG"; direction = "gap-down buy"
                    target_price = op * (1 + abs_gap * 0.5 / 100)
                    sl_price = op * (1 - 0.5 / 100)
                # Thursday: short gap-ups only
                elif trade_dow == 3 and gap > 0:
                    trade = "SHORT"; direction = "gap-up short"
                    target_price = op * (1 - abs_gap * 0.5 / 100)
                    sl_price = op * (1 + 0.5 / 100)
                # Monday: short gap-ups only
                elif trade_dow == 0 and gap > 0 and vol_ratio < 0.8:
                    trade = "SHORT"; direction = "gap-up fade"
                    target_price = op * (1 - abs_gap * 0.5 / 100)
                    sl_price = op * (1 + 0.5 / 100)
                # Friday: depends on volume
                elif trade_dow == 4:
                    if gap < 0 and vol_ratio < 0.8:
                        trade = "LONG"; direction = "gap-down bargain"
                        target_price = op * (1 + abs_gap * 0.5 / 100)
                        sl_price = op * (1 - 0.5 / 100)
                    elif gap > 0 and vol_ratio > 1.5:
                        trade = "SHORT"; direction = "gap-up short covering"
                        target_price = op * (1 - abs_gap * 0.5 / 100)
                        sl_price = op * (1 + 0.5 / 100)

            # Compute PnL
            pnl = 0
            result = "SKIP"
            if trade != "NONE":
                # For SHORT trades (gap-up): gap fills when low <= prev_close
                # For LONG trades (gap-down):  gap fills when high >= prev_close
                if trade == "LONG":
                    gap_filled_check = hp >= pc
                    sl_hit = lp <= sl_price
                else:
                    gap_filled_check = lp <= pc
                    sl_hit = hp >= sl_price

                if gap_filled_check:
                    result = "✅ FILLED"
                    if trade == "LONG":
                        achieved = min(hp, target_price)
                        pnl = round(max(0, (achieved - op) / op * 100), 2)
                    else:
                        achieved = max(lp, target_price)
                        pnl = round(max(0, (op - achieved) / op * 100), 2)
                elif sl_hit:
                    pnl = -0.5
                    result = "❌ STOPPED"
                else:
                    if trade == "LONG":
                        pnl = round((cp - op) / op * 100, 2)
                    else:
                        pnl = round((op - cp) / op * 100, 2)
                    result = "⏳ OPEN"

                day_picks.append({
                    "stock": name, "gap": round(gap, 2), "abs_gap": round(abs_gap, 2),
                    "vol_ratio": round(vol_ratio, 2), "trade": trade,
                    "entry": round(op, 2), "target": round(target_price, 2),
                    "sl": round(sl_price, 2), "close": round(cp, 2),
                    "result": result, "pnl": pnl, "direction": direction,
                    "gap_filled": gap_filled, "fill_pct": round(fill_pct, 1),
                    "date": trade_date, "day": actual_day_name,
                    "market_tide": f"{pct_up:.0f}% up"
                })

        # Save to ledger
        for p in day_picks:
            ledger["trades"].append(p)
        ledger["runs"].append({"date": trade_date, "day": day_name, "trades": len(day_picks)})

        with open(ledger_path, "w") as f:
            json.dump(ledger, f, indent=2)

        print(f"Recorded {len(day_picks)} trades for {trade_date}")

    # Generate HTML
    # Get picks for today
    todays_picks = [t for t in ledger["trades"] if t.get("date") == trade_date]

    html = generate_html(ledger, todays_picks, trade_date, actual_day_name)
    html_path = "paper_trader/index.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Copy to root for easy access
    with open("paper-trading.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard: {html_path}")
    print(f"Root copy: paper-trading.html")

    # Summary
    all_trades = ledger["trades"]
    wins = sum(1 for t in all_trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in all_trades if t.get("pnl", 0) < 0)
    total_pnl = sum(t.get("pnl", 0) for t in all_trades)
    print(f"\n{'='*50}")
    print(f"  PAPER TRADING SUMMARY")
    print(f"{'='*50}")
    print(f"  Total runs: {len(ledger['runs'])}")
    print(f"  Total trades: {len(all_trades)}")
    print(f"  Wins: {wins}, Losses: {losses}")
    wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    print(f"  Win rate: {wr:.1f}%")
    print(f"  Total PnL: {total_pnl:+.2f}%")
    print(f"  Today: {len(todays_picks)} trades")
    print(f"{'='*50}")

if __name__ == "__main__":
    run_paper_trade()
