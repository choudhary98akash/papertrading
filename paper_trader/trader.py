#!/usr/bin/env python3
"""Small Gap Snap — Paper Trader (two-phase: morning picks, evening verdict)."""
import argparse, json, os, sys, io, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MIN_GAP = 0.3
MAX_GAP = 0.8
SL_PCT = 0.005
TARGET_PCT = 0.50

NIFTY_50 = [
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

LEDGER_PATH = "paper_trader/ledger.json"

def load_ledger():
    if os.path.exists(LEDGER_PATH):
        return json.load(open(LEDGER_PATH))
    return {"trades": [], "runs": []}

def save_ledger(ledger):
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2)

def compute_stats(trades):
    resolved = [t for t in trades if t.get("status") != "PENDING"]
    if not resolved:
        return {"total": 0, "wins": 0, "losses": 0, "winrate": 0, "pnl": 0, "avg_pnl": 0}
    wins = sum(1 for t in resolved if t.get("pnl", 0) > 0)
    losses = sum(1 for t in resolved if t.get("pnl", 0) < 0)
    total = len(resolved)
    pnl = sum(t.get("pnl", 0) for t in resolved)
    return {
        "total": total, "wins": wins, "losses": losses,
        "winrate": round(wins / total * 100, 1) if total > 0 else 0,
        "pnl": round(pnl, 2), "avg_pnl": round(pnl / total, 3) if total > 0 else 0
    }

def generate_html(ledger, day_picks, today, day_name, mode, nifty_compare=None):
    all_trades = ledger.get("trades", [])
    stats = compute_stats(all_trades)

    day_breakdown = defaultdict(list)
    for t in all_trades:
        day_breakdown[t.get("date", "unknown")].append(t)

    day_stats = []
    for date, trades in sorted(day_breakdown.items()):
        ds = compute_stats(trades)
        has_pending = any(t.get("status") == "PENDING" for t in trades)
        day_stats.append({"date": date, **ds, "has_pending": has_pending})

    chart_day_stats = sorted(day_stats, key=lambda x: x["date"])
    table_day_stats = sorted(day_stats, key=lambda x: x["date"], reverse=True)

    cum_pnl = []
    running = 0
    for t in all_trades:
        if t.get("status") != "PENDING":
            running += t.get("pnl", 0)
            cum_pnl.append(round(running, 2))

    today_pending = any(p.get("status") == "PENDING" for p in day_picks)

    picks_rows = ""
    for p in day_picks:
        is_pending = p.get("status") == "PENDING"
        cls = "" if is_pending else ("win" if p.get("pnl", 0) > 0 else "loss" if p.get("pnl", 0) < 0 else "")
        dir_cls = "long" if p.get("trade") == "LONG" else "short"
        result_display = p.get("result", "PENDING") if not is_pending else "PENDING"
        pnl_display = f"{p['pnl']:+.2f}%" if not is_pending else "--"
        row_cls = "pending" if is_pending else cls
        picks_rows += f"<tr class='{row_cls}'><td>{p['stock']}</td><td class='{'red' if p['gap']>0 else 'green'}'>{p['gap']:+.2f}%</td><td>{p.get('vol_ratio',0):.1f}x</td><td><span class='badge {'pending-badge' if is_pending else dir_cls}'>{p['trade']}</span></td><td>{p['entry']}</td><td>{p['target']}</td><td>{p['sl']}</td><td>{p['close']}</td><td>{result_display}</td><td>{pnl_display}</td></tr>"

    history_rows = ""
    for ds in table_day_stats:
        date = ds["date"]
        has_pending = ds.get("has_pending", False)
        row_class = "win" if ds["pnl"] > 0 else "loss"
        picks_detail_rows = ""
        verdict_detail_rows = ""
        trades_today = day_breakdown[date]
        for t in trades_today:
            picks_detail_rows += (
                f"<tr><td>{t['stock']}</td>"
                f"<td class='{'red' if t.get('gap',0)>0 else 'green'}'>{t.get('gap',0):+.2f}%</td>"
                f"<td><span class='badge {'long' if t.get('trade')=='LONG' else 'short'}'>{t['trade']}</span></td>"
                f"<td>{t.get('entry','')}</td>"
                f"<td>{t.get('target','')}</td>"
                f"<td>{t.get('sl','')}</td></tr>"
            )
            if t.get("status") != "PENDING" and t.get("result"):
                cls_v = "win" if t.get("pnl",0) > 0 else "loss"
                verdict_detail_rows += (
                    f"<tr class='{cls_v}'><td>{t['stock']}</td>"
                    f"<td><span class='badge {'long' if t.get('trade')=='LONG' else 'short'}'>{t['trade']}</span></td>"
                    f"<td>{t.get('result','')}</td>"
                    f"<td class='{'green' if t.get('pnl',0)>0 else 'red'}'>{t.get('pnl',0):+.2f}%</td>"
                    f"<td>{t.get('close','')}</td></tr>"
                )
        has_verdict = len(verdict_detail_rows) > 0
        picks_section = (
            "<div class='detail-section'>"
            "<h4>Morning Picks</h4>"
            + (f"<table class='sub-table'><tr><th>Stock</th><th>Gap</th><th>Trade</th><th>Entry</th><th>Target</th><th>SL</th></tr>{picks_detail_rows}</table>"
               if picks_detail_rows else "<p class='na'>Not Available</p>")
            + "</div>"
        )
        verdict_section = (
            "<div class='detail-section'>"
            "<h4>Evening Verdict</h4>"
            + (f"<table class='sub-table'><tr><th>Stock</th><th>Trade</th><th>Result</th><th>PnL</th><th>Close</th></tr>{verdict_detail_rows}</table>"
               if has_verdict else "<p class='na'>Not Available" + (" — Verdict pending</p>" if has_pending else "</p>"))
            + "</div>"
        )
        expand_row = f"<tr class='detail-row' data-date='{date}'><td colspan='6'><div class='detail-content'>{picks_section}{verdict_section}</div></td></tr>"
        history_rows += f"<tr class='day-row {row_class}' onclick='toggleDay(this)'><td><span class='arrow'>▶</span> {date}</td><td>{ds['total']}</td><td>{ds['wins']}</td><td>{ds['losses']}</td><td>{ds['winrate']}%</td><td>{ds['pnl']:+.2f}%</td></tr>{expand_row}"

    compare_data = {"dates": [], "strategy": [], "nifty": []}
    if nifty_compare:
        nifty_close_map = dict(zip(nifty_compare.get("dates", []), nifty_compare.get("close", [])))
        nifty_dates_set = set(nifty_compare.get("dates", []))
        if nifty_compare.get("close"):
            first_nifty = nifty_compare["close"][0]
            running_s = 0
            for dstat in chart_day_stats:
                dt = dstat["date"]
                if dt in nifty_dates_set:
                    day_pnl = sum(t.get("pnl", 0) for t in day_breakdown[dt] if t.get("status") != "PENDING")
                    running_s += day_pnl
                    nifty_ret = (nifty_close_map[dt] / first_nifty - 1) * 100
                    compare_data["dates"].append(dt)
                    compare_data["strategy"].append(round(running_s, 2))
                    compare_data["nifty"].append(round(nifty_ret, 2))

    rule = "Gap 0.3-0.8%: reverse direction. Gap UP → SHORT. Gap DOWN → LONG. Target: 50% fill. SL: 0.5%."
    phase_tag = "Morning Picks" if mode == "morning" else "Evening Results"

    html = f'''<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Small Gap Snap - Paper Trader</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0f1117; color:#e1e4e8; padding:20px; }}
h1 {{ font-size:24px; }}
h2 {{ font-size:18px; margin:20px 0 10px; color:#8b949e; }}
h4 {{ font-size:13px; margin:0 0 6px; color:#8b949e; }}
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
tr.pending {{ border-left:3px solid #d29922; }}
tr.day-row {{ cursor:pointer; }}
tr.day-row .arrow {{ display:inline-block; transition:transform .2s; font-size:10px; margin-right:4px; }}
tr.day-row.open .arrow {{ transform:rotate(90deg); }}
tr.detail-row {{ display:none; }}
tr.detail-row.open {{ display:table-row; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.long {{ background:#0d2810; color:#3fb950; }}
.short {{ background:#280d0d; color:#f85149; }}
.pending-badge {{ background:#3d2e00; color:#d29922; }}
.chart-box {{ background:#161b22; border:1px solid #30363d; border-radius:8px; padding:15px; margin:15px 0; }}
.rule {{ background:#1a1d24; padding:10px 15px; border-radius:6px; font-size:13px; color:#8b949e; margin:10px 0; }}
.phase {{ display:inline-block; padding:4px 12px; border-radius:12px; font-size:11px; font-weight:700; font-family:monospace; }}
.phase-morning {{ background:#3d2e00; color:#d29922; border:1px solid #665000; }}
.phase-evening {{ background:#0d2810; color:#3fb950; border:1px solid #005020; }}
.sub-table {{ font-size:12px; margin:0 0 10px; }}
.sub-table th {{ font-size:11px; }}
.detail-content {{ padding:10px 15px; background:#0d1117; border-radius:6px; }}
.detail-section {{ margin-bottom:8px; }}
.detail-section:last-child {{ margin-bottom:0; }}
.na {{ color:#484f58; font-style:italic; font-size:12px; padding:4px 0; }}
.today-section {{ display:flex; gap:20px; flex-wrap:wrap; margin:10px 0; }}
.today-sub {{ flex:1; min-width:300px; }}
</style></head>
<body>
<h1>Small Gap Snap — Paper Trader</h1>
<p class="sub">Running daily via GitHub Actions &middot; {today} &middot; {day_name} &middot; <span class="phase phase-{'morning' if mode == 'morning' else 'evening'}">{phase_tag}</span></p>

<div class="rule">Strategy: <b>{rule}</b></div>

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

<h2>Today's Picks ({len(day_picks)} trades)</h2>
''' + (f'''
<div class="today-section">
<div class="today-sub">
<h4>Morning Picks</h4>
<table><tr><th>Stock</th><th>Gap</th><th>Vol</th><th>Trade</th><th>Entry</th><th>Target</th><th>SL</th></tr>{picks_rows}</table>
</div>
<div class="today-sub">
<h4>Evening{" Verdict (Pending)" if today_pending else " Verdict"}</h4>
<table><tr><th>Stock</th><th>Trade</th><th>Result</th><th>PnL</th><th>Close</th></tr>''' +
''.join(f"<tr class='{'win' if t.get('pnl',0)>0 else 'loss'}'><td>{t['stock']}</td><td><span class='badge {'long' if t.get('trade')=='LONG' else 'short'}'>{t['trade']}</span></td><td>{t.get('result','PENDING')}</td><td class='{'green' if t.get('pnl',0)>0 else 'red'}'>{t['pnl']:+.2f}%</td><td>{t['close']}</td></tr>" for t in day_picks if t.get('status') != 'PENDING')
+ ("<tr><td colspan='5' style='color:#484f58;text-align:center;'>Awaiting evening verdict...</td></tr>" if today_pending else "")
+ '''</table>
</div>
</div>''' if day_picks else "<p class='na'>No data for today yet.</p>") + f'''

<h2>Daily History <span style="font-size:12px;color:#484f58;font-weight:400;">(click a date to expand)</span></h2>
<table><tr><th>Date</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>PnL</th></tr>{history_rows}</table>

''' + (f'''
<h2>Strategy vs Nifty 50</h2>
<div class="chart-box"><canvas id="compareChart" height="80"></canvas></div>
''' if compare_data["dates"] else "") + f'''

<script>
const cumData = {json.dumps(cum_pnl)};
const dayLabels = {json.dumps([ds['date'] for ds in chart_day_stats])};
const dayPnls = {json.dumps([ds['pnl'] for ds in chart_day_stats])};
const dayWrs = {json.dumps([ds['winrate'] for ds in chart_day_stats])};

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

''' + (f'''
const compLabels = {json.dumps(compare_data["dates"])};
const compStrategy = {json.dumps(compare_data["strategy"])};
const compNifty = {json.dumps(compare_data["nifty"])};
new Chart(document.getElementById('compareChart'), {{
    type: 'line',
    data: {{ labels: compLabels, datasets: [
        {{ label:'Strategy PnL %', data:compStrategy, borderColor:'#3fb950', backgroundColor:'rgba(63,185,80,0.1)', fill:true, tension:0.3 }},
        {{ label:'Nifty 50 %', data:compNifty, borderColor:'#58a6ff', backgroundColor:'rgba(88,166,255,0.1)', fill:true, tension:0.3 }}
    ] }},
    options: {{ responsive:true, plugins:{{ title:{{ display:true, text:'Strategy vs Nifty 50 (Cumulative Return %)', color:'#8b949e' }} }}, scales:{{ x:{{ ticks:{{ color:'#8b949e' }} }}, y:{{ ticks:{{ color:'#8b949e' }} }} }} }}
}});
''' if compare_data["dates"] else "") + f'''
</script>
<script>
function toggleDay(el) {{
    var detail = el.nextElementSibling;
    if (detail && detail.classList.contains('detail-row')) {{
        detail.classList.toggle('open');
        el.classList.toggle('open');
    }}
}}
</script>
<p style="color:#484f58;font-size:12px;margin-top:20px">Auto-generated by Small Gap Snap Paper Trader &middot; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
</body></html>'''
    return html


def write_dashboard(ledger, day_picks, date_str, day_name, mode):
    nifty_compare = None
    import yfinance as yf
    try:
        df = yf.download("^NSEI", period="6mo", interval="1d", progress=False, auto_adjust=True)
        if not df.empty:
            close_series = df['Close'].squeeze()
            nifty_compare = {
                "dates": [d.strftime('%Y-%m-%d') for d in close_series.index],
                "close": [float(c) for c in close_series.values]
            }
    except:
        pass
    html = generate_html(ledger, day_picks, date_str, day_name, mode, nifty_compare)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Dashboard: index.html")

FORMSPREE_URL = "https://formspree.io/f/mrevdwen"

def send_report(subject, details):
    try:
        data = urllib.parse.urlencode({
            "subject": subject,
            "details": details,
            "_replyto": "",
        }).encode()
        urllib.request.urlopen(FORMSPREE_URL, data=data, timeout=15)
        print(f"Report sent: {subject}")
    except Exception as e:
        print(f"Report failed: {e}")

def format_report(mode, today_str, day_name, day_picks, ledger, all_trades=None):
    if all_trades is None:
        all_trades = ledger.get("trades", [])
    stats = compute_stats(all_trades)
    lines = []
    lines.append(f"Mode: {mode}")
    lines.append(f"Date: {today_str} ({day_name})")
    lines.append(f"Today's picks: {len(day_picks)}")
    for p in day_picks:
        status = p.get("status", p.get("result", "?"))
        pnl = p.get("pnl", 0)
        lines.append(f"  {p['stock']} {p['trade']} gap={p['gap']:+.2f}% → {status} pnl={pnl:+.2f}%")
    lines.append(f"")
    lines.append(f"Overall: {stats['total']} trades, {stats['wins']}W/{stats['losses']}L, WR={stats['winrate']}%, PnL={stats['pnl']:+.2f}%")
    return "\n".join(lines)

def mode_morning():
    import yfinance as yf
    today = datetime.now()
    dow = today.weekday()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if dow >= 5:
        print(f"Weekend ({day_names[dow]}) - no trading")
        return

    today_str = today.strftime('%Y-%m-%d')
    print(f"Morning picks - {today_str} ({day_names[dow]})")

    stock_names = {s: s.replace('.NS','') for s in NIFTY_50}

    print("Fetching daily data for yesterday close...")
    df_day = yf.download(NIFTY_50, start=(today - timedelta(days=5)).strftime('%Y-%m-%d'),
                         end=today_str, interval='1d', progress=False, auto_adjust=True)
    dates = [d.strftime('%Y-%m-%d') for d in df_day.index]

    if len(dates) < 2:
        print("Not enough daily data")
        return

    prev_date = dates[-2]
    print(f"  Prev close date: {prev_date}")

    print("Fetching 5m data for today's open...")
    df_5m = yf.download(NIFTY_50, period="2d", interval="5m", progress=False, auto_adjust=True)

    idx_5m = [d.strftime('%Y-%m-%d') for d in df_5m.index]
    today_5m_mask = [d == today_str for d in idx_5m]
    today_5m = df_5m[today_5m_mask]
    if today_5m.empty:
        print("No 5m data for today yet - market may not have opened")
        return

    first_candle = today_5m.iloc[0]
    today_open = first_candle['Open']
    yesterday_close = df_day['Close'].loc[prev_date]

    print(f"First 5m candle time: {today_5m.index[0]}")
    print(f"Today's open: {float(today_open[NIFTY_50[0]]):.2f} (sample)")

    ledger = load_ledger()
    existing_pending = {t['stock'] for t in ledger['trades']
                        if t.get('date') == today_str and t.get('status') == 'PENDING'}
    existing_today = {t['stock'] for t in ledger['trades'] if t.get('date') == today_str}
    if existing_pending:
        print(f"Already have {len(existing_pending)} pending picks for today - skipping")
        todays_picks = [t for t in ledger["trades"] if t.get("date") == today_str]
        write_dashboard(ledger, todays_picks, today_str, day_names[dow], "morning")
        return
    if existing_today:
        print(f"Already have {len(existing_today)} resolved trades for today - skipping")
        todays_picks = [t for t in ledger["trades"] if t.get("date") == today_str]
        write_dashboard(ledger, todays_picks, today_str, day_names[dow], "morning")
        return

    day_picks = []
    for sym in NIFTY_50:
            name = stock_names[sym]
            try:
                pc = float(yesterday_close[sym])
                op = float(today_open[sym])
            except:
                continue
            if pc == 0 or np.isnan(pc) or np.isnan(op):
                continue

            gap = (op - pc) / pc * 100
            if np.isnan(gap) or abs(gap) < MIN_GAP or abs(gap) > MAX_GAP:
                continue

            abs_gap = abs(gap)
            gap_amount = abs(op - pc)
            trade = "SHORT" if gap > 0 else "LONG"

            if trade == "LONG":
                sl_price = op * (1 - SL_PCT)
                target_price = op + gap_amount * TARGET_PCT
            else:
                sl_price = op * (1 + SL_PCT)
                target_price = op - gap_amount * TARGET_PCT

            day_picks.append({
                "stock": name, "gap": round(gap, 2), "abs_gap": round(abs_gap, 2),
                "vol_ratio": 0, "trade": trade,
                "entry": round(op, 2), "target": round(target_price, 2),
                "sl": round(sl_price, 2), "close": round(op, 2),
                "result": "PENDING", "pnl": 0,
                "status": "PENDING",
                "date": today_str, "day": day_names[dow],
                "market_tide": ""
            })

    for p in day_picks:
        ledger["trades"].append(p)
    ledger["runs"].append({"date": today_str, "mode": "morning", "trades": len(day_picks)})
    save_ledger(ledger)
    print(f"Recorded {len(day_picks)} pending trades")

    todays_picks = [t for t in ledger["trades"] if t.get("date") == today_str]
    write_dashboard(ledger, todays_picks, today_str, day_names[dow], "morning")

    all_trades = ledger["trades"]
    pending = [t for t in all_trades if t.get("status") == "PENDING"]
    print(f"\nPending: {len(pending)} trades waiting for evening verdict")
    report = format_report("morning", today_str, day_names[dow], todays_picks, ledger, all_trades)
    send_report(f"Morning Picks — {today_str}", report)

def mode_evening():
    import yfinance as yf
    today = datetime.now()
    dow = today.weekday()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if dow >= 5:
        print(f"Weekend ({day_names[dow]}) - no trading")
        return

    today_str = today.strftime('%Y-%m-%d')
    print(f"Evening verdict - {today_str} ({day_names[dow]})")

    ledger = load_ledger()
    pending_trades = [t for t in ledger['trades']
                      if t.get('date') == today_str and t.get('status') == 'PENDING']

    if not pending_trades:
        print("No pending trades for today - morning may not have run")
        write_dashboard(ledger, [], today_str, day_names[dow], "evening")
        return

    print(f"Resolving {len(pending_trades)} pending trades...")

    stock_names = {s: s.replace('.NS','') for s in NIFTY_50}
    rev_names = {v: k for k, v in stock_names.items()}

    print("Fetching today's daily data for verdict...")
    end_str = (today + timedelta(days=2)).strftime('%Y-%m-%d')
    start_str = (today - timedelta(days=5)).strftime('%Y-%m-%d')
    df_day = yf.download(NIFTY_50, start=start_str, end=end_str,
                         interval='1d', progress=False, auto_adjust=True)
    dates = [d.strftime('%Y-%m-%d') for d in df_day.index]

    if today_str not in dates:
        print(f"Today {today_str} not in daily data yet - trying 5m data")
        df_5m = yf.download(NIFTY_50, period="2d", interval="5m", progress=False, auto_adjust=True)
        idx_5m = [d.strftime('%Y-%m-%d') for d in df_5m.index]
        today_mask = [d == today_str for d in idx_5m]
        today_5m = df_5m[today_mask]
        if today_5m.empty:
            print("No intraday data available yet")
            write_dashboard(ledger, pending_trades, today_str, day_names[dow], "evening")
            return

        day_high = {}
        day_low = {}
        day_close = {}
        for sym in NIFTY_50:
            try:
                day_high[sym] = float(today_5m['High'][sym].max())
                day_low[sym] = float(today_5m['Low'][sym].min())
                day_close[sym] = float(today_5m['Close'][sym].iloc[-1])
            except:
                continue
    else:
        try:
            thigh = df_day['High'].loc[today_str]
            tlow = df_day['Low'].loc[today_str]
            tclose = df_day['Close'].loc[today_str]
            day_high = {sym: float(thigh[sym]) for sym in NIFTY_50}
            day_low = {sym: float(tlow[sym]) for sym in NIFTY_50}
            day_close = {sym: float(tclose[sym]) for sym in NIFTY_50}
        except Exception as e:
            print(f"Data error: {e}")
            write_dashboard(ledger, pending_trades, today_str, day_names[dow], "evening")
            return

    updated = 0
    for t in ledger['trades']:
        if t.get('status') != 'PENDING' or t.get('date') != today_str:
            continue

        sym = rev_names.get(t['stock'])
        if not sym:
            continue

        hp = day_high.get(sym)
        lp = day_low.get(sym)
        cp = day_close.get(sym)
        op = t['entry']

        if hp is None or lp is None or cp is None:
            continue

        tgt_hit = (hp >= t['target']) if t['trade'] == 'LONG' else (lp <= t['target'])
        sl_hit = (lp <= t['sl']) if t['trade'] == 'LONG' else (hp >= t['sl'])

        if tgt_hit:
            exit_price = t['target']
            result = "TARGET_HIT"
        elif sl_hit:
            exit_price = t['sl']
            result = "STOPPED"
        else:
            exit_price = cp
            result = "TIME_EXIT"

        raw = (exit_price - op) / op * 100
        pnl = round(-raw if t['trade'] == 'SHORT' else raw, 2)

        t['close'] = round(cp, 2)
        t['result'] = result
        t['pnl'] = pnl
        t['status'] = "RESOLVED"
        del t['status']
        updated += 1

    ledger['runs'].append({"date": today_str, "mode": "evening", "resolved": updated})
    save_ledger(ledger)
    print(f"Resolved {updated} trades")

    todays_picks = [t for t in ledger["trades"] if t.get("date") == today_str]
    write_dashboard(ledger, todays_picks, today_str, day_names[dow], "evening")

    all_trades = ledger["trades"]
    wins = sum(1 for t in all_trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in all_trades if t.get("pnl", 0) < 0)
    total_pnl = sum(t.get("pnl", 0) for t in all_trades)
    wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    print(f"\n{'='*50}")
    print(f"  SMALL GAP SNAP - EVENING SUMMARY")
    print(f"{'='*50}")
    print(f"  Total trades:   {len(all_trades)}")
    print(f"  Wins: {wins}, Losses: {losses}")
    print(f"  Win rate: {wr:.1f}%")
    print(f"  Total PnL: {total_pnl:+.2f}%")
    print(f"{'='*50}")
    report = format_report("evening", today_str, day_names[dow], todays_picks, ledger, all_trades)
    send_report(f"Evening Verdict — {today_str}", report)

def mode_backfill():
    import yfinance as yf
    today = datetime.now()
    dow = today.weekday()
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    if dow >= 5:
        print(f"Weekend ({day_names[dow]}) - no trading")
        return

    print(f"Backfill mode - {today.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    stock_names = {s: s.replace('.NS','') for s in NIFTY_50}
    end_str = (today + timedelta(days=2)).strftime('%Y-%m-%d')
    start_str = (today - timedelta(days=70)).strftime('%Y-%m-%d')

    print("Fetching data...")
    try:
        df = yf.download(NIFTY_50, start=start_str, end=end_str, interval='1d', progress=False, auto_adjust=True)
    except Exception as e:
        print(f"Fetch error: {e}")
        sys.exit(1)

    available_dates = [d.strftime('%Y-%m-%d') for d in df.index]
    print(f"Data range: {available_dates[0]} -> {available_dates[-1]} ({len(available_dates)} days)")

    ledger = load_ledger()
    existing_dates = {t.get("date") for t in ledger["trades"]}
    print(f"Already processed: {len(existing_dates)} days")

    new_count = 0
    for i in range(1, len(available_dates)):
        d = available_dates[i]
        dt = datetime.strptime(d, '%Y-%m-%d')
        if dt.weekday() >= 5:
            continue
        if d in existing_dates:
            continue
        print(f"\nProcessing {d}...")

        idx = available_dates.index(d)
        prev_date = available_dates[idx - 1]

        try:
            yclose = df['Close'].loc[prev_date]
            topen = df['Open'].loc[d]
            thigh = df['High'].loc[d]
            tlow = df['Low'].loc[d]
            tclose = df['Close'].loc[d]
            tvol = df['Volume'].loc[d]
        except Exception as e:
            print(f"  Data error: {e}")
            continue

        gap_directions = []
        for sym in NIFTY_50:
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
        print(f"  Market: {len(gap_directions)} stocks with gaps, {pct_up:.0f}% gap-up")

        vol_hist = df['Volume'].loc[:prev_date]
        day_picks = []

        for sym in NIFTY_50:
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
            if np.isnan(gap):
                continue
            abs_gap = abs(gap)

            vols = [float(v) for v in vol_hist[sym].dropna() if not np.isnan(float(v))]
            avg_vol = np.mean(vols[-10:]) if len(vols) >= 10 else np.mean(vols) if len(vols) > 0 else vt
            vol_ratio = vt / avg_vol if avg_vol > 0 else 1

            if abs_gap < MIN_GAP or abs_gap > MAX_GAP:
                continue

            gap_amount = abs(op - pc)
            trade = "SHORT" if gap > 0 else "LONG"

            if trade == "LONG":
                sl_price = op * (1 - SL_PCT)
                target_price = op + gap_amount * TARGET_PCT
            else:
                sl_price = op * (1 + SL_PCT)
                target_price = op - gap_amount * TARGET_PCT

            tgt_hit = (hp >= target_price) if trade == "LONG" else (lp <= target_price)
            sl_hit = (lp <= sl_price) if trade == "LONG" else (hp >= sl_price)

            if tgt_hit:
                exit_price = target_price
                result = "TARGET_HIT"
            elif sl_hit:
                exit_price = sl_price
                result = "STOPPED"
            else:
                exit_price = cp
                result = "TIME_EXIT"

            raw_pnl = (exit_price - op) / op * 100
            pnl = round(-raw_pnl if trade == "SHORT" else raw_pnl, 2)

            day_picks.append({
                "stock": name, "gap": round(gap, 2), "abs_gap": round(abs_gap, 2),
                "vol_ratio": round(vol_ratio, 2), "trade": trade,
                "entry": round(op, 2), "target": round(target_price, 2),
                "sl": round(sl_price, 2), "close": round(cp, 2),
                "result": result, "pnl": pnl,
                "date": d, "day": datetime.strptime(d, '%Y-%m-%d').strftime('%A'),
                "market_tide": f"{pct_up:.0f}% up"
            })

        for p in day_picks:
            ledger["trades"].append(p)
        ledger["runs"].append({"date": d, "mode": "backfill", "trades": len(day_picks)})
        print(f"  Recorded {len(day_picks)} trades")
        new_count += 1

    if new_count > 0:
        save_ledger(ledger)
        print(f"\nSaved {new_count} new days to ledger")

    last_date = available_dates[-1]
    last_dt = datetime.strptime(last_date, '%Y-%m-%d')
    last_day = day_names[last_dt.weekday()]
    todays_picks = [t for t in ledger["trades"] if t.get("date") == last_date]
    write_dashboard(ledger, todays_picks, last_date, last_day, "backfill")

    all_trades = ledger["trades"]
    wins = sum(1 for t in all_trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in all_trades if t.get("pnl", 0) < 0)
    total_pnl = sum(t.get("pnl", 0) for t in all_trades)
    wr = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
    print(f"\n{'='*50}")
    print(f"  SMALL GAP SNAP - SUMMARY")
    print(f"{'='*50}")
    print(f"  Processed days: {len(ledger['runs'])}")
    print(f"  Total trades:   {len(all_trades)}")
    print(f"  Wins: {wins}, Losses: {losses}")
    print(f"  Win rate: {wr:.1f}%")
    print(f"  Total PnL: {total_pnl:+.2f}%")
    print(f"{'='*50}")
    report = format_report("backfill", last_date, last_day, todays_picks, ledger, all_trades)
    send_report(f"Backfill — {last_date}", report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Small Gap Snap Paper Trader")
    parser.add_argument('--mode', choices=['morning', 'evening', 'backfill'], default='backfill',
                        help='morning: scan gaps at open, evening: resolve pending trades, backfill: process history')
    args = parser.parse_args()
    if args.mode == 'morning':
        mode_morning()
    elif args.mode == 'evening':
        mode_evening()
    else:
        mode_backfill()
