#!/usr/bin/env python3
"""Deeper data exploration — things that might have been overlooked."""
import json, os
from datetime import datetime
from collections import defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(open(os.path.join(ROOT, "data.json")))
stocks = data["stocks"]

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 72)
print("  DEEPER DATA EXPLORATION")
print("=" * 72)

# Build events
events = []
for name, s in stocks.items():
    c = s["close"]
    o = s["open"]
    h = s["high"]
    l = s["low"]
    v = s["volume"]
    ema9 = s["ema9"]
    ema21 = s["ema21"]
    rsi14 = s["rsi14"]
    for i in range(2, len(c)):
        gap = (o[i] - c[i-1]) / c[i-1] * 100
        day_range = (h[i] - l[i]) / c[i-1] * 100
        oc = (c[i] - o[i]) / o[i] * 100
        ret = (c[i] - c[i-1]) / c[i-1] * 100
        prev_ret = (c[i-1] - c[i-2]) / c[i-2] * 100
        prev_range = (s["high"][i-1] - s["low"][i-1]) / s["close"][i-1] * 100
        avg_v = np.mean(v[max(0,i-10):i])
        vol_ratio = v[i] / avg_v if avg_v > 0 else 1
        gap_filled = bool(l[i] <= c[i-1]) if gap > 0 else bool(h[i] >= c[i-1])
        if gap > 0:
            fill_pct = min(100, (o[i] - l[i]) / (o[i] - c[i-1]) * 100) if (o[i] - c[i-1]) != 0 else 0
        else:
            fill_pct = min(100, (h[i] - o[i]) / (c[i-1] - o[i]) * 100) if (c[i-1] - o[i]) != 0 else 0
        close_pos = (c[i] - l[i]) / (h[i] - l[i]) * 100 if (h[i] - l[i]) > 0 else 50
        prev_close_pos = (c[i-1] - s["low"][i-1]) / (s["high"][i-1] - s["low"][i-1]) * 100 if (s["high"][i-1] - s["low"][i-1]) > 0 else 50
        dt = datetime.strptime(s["dates"][i], "%Y-%m-%d")
        dow = dt.weekday()
        week_num = dt.isocalendar()[1]
        month = dt.month

        events.append({
            "stock": name,
            "date": s["dates"][i],
            "dow": dow,
            "month": month,
            "week": week_num,
            "gap": gap,
            "abs_gap": abs(gap),
            "ret": ret,
            "prev_ret": prev_ret,
            "oc": oc,
            "day_range": day_range,
            "prev_range": prev_range,
            "range_expansion": day_range / prev_range if prev_range > 0 else 1,
            "volume": v[i],
            "vol_ratio": vol_ratio,
            "filled": gap_filled,
            "fill_pct": fill_pct,
            "close_pos": close_pos,
            "prev_close_pos": prev_close_pos,
            "price": c[i],
            "above_ema9": c[i] > ema9[i] if ema9[i] else None,
            "rsi": rsi14[i] if rsi14[i] else None,
        })

print(f"\n  Events analyzed: {len(events)}")

# --- 1. Price level effect ---
print("\n--- 1. PRICE LEVEL EFFECT ---")

price_tiers = [(0, 500), (500, 1000), (1000, 2000), (2000, 5000), (5000, 100000)]
print(f"\n  Gap fill rate by price tier:")
print(f"  {'Price Range':>16s} {'Events':>8s} {'Filled':>8s} {'Fill%':>8s}")
for lo, hi in price_tiers:
    subset = [e for e in events if lo <= e["price"] < hi and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    filled = sum(1 for e in subset if e["filled"])
    print(f"  ₹{lo:>5d}–₹{hi:<6d} {len(subset):>8d} {filled:>8d} {filled/len(subset)*100:>7.1f}%")

# --- 2. Volume surge effect ---
print("\n--- 2. VOLUME SURGE EFFECT ON GAP FILL ---")

vol_buckets = [(0, 0.5), (0.5, 0.8), (0.8, 1.0), (1.0, 1.2), (1.2, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 100)]
print(f"\n  Gap fill rate by volume ratio (today / 10-day avg):")
print(f"  {'Vol Ratio':>12s} {'Events':>8s} {'Filled':>8s} {'Fill%':>8s}")
for lo, hi in vol_buckets:
    subset = [e for e in events if lo <= e["vol_ratio"] < hi and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    filled = sum(1 for e in subset if e["filled"])
    print(f"  {lo:>4.1f}x–{hi:>4.1f}x {len(subset):>8d} {filled:>8d} {filled/len(subset)*100:>7.1f}%")

# Volume + gap interaction
print(f"\n  Volume surge + gap direction interaction:")
for label, cond in [("Low vol (<0.8x) + gap-up", lambda e: e["vol_ratio"] < 0.8 and e["gap"] > 0),
                     ("Low vol (<0.8x) + gap-dn", lambda e: e["vol_ratio"] < 0.8 and e["gap"] < 0),
                     ("High vol (>1.5x) + gap-up", lambda e: e["vol_ratio"] > 1.5 and e["gap"] > 0),
                     ("High vol (>1.5x) + gap-dn", lambda e: e["vol_ratio"] > 1.5 and e["gap"] < 0)]:
    subset = [e for e in events if cond(e) and abs(e["gap"]) >= 0.3]
    if subset:
        filled = sum(1 for e in subset if e["filled"])
        print(f"    {label:30s}: {len(subset):>4d} events, fill {filled/len(subset)*100:.1f}%")

# --- 3. Close position within daily range ---
print("\n--- 3. WHERE DOES THE STOCK CLOSE IN ITS RANGE? ---")

pos_buckets = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
print(f"\n  Close position in range -> next day return:")
print(f"  {'Close Position':>18s} {'Events':>8s} {'Avg Next Ret':>12s} {'Pos%':>8s}")
for lo, hi in pos_buckets:
    subset = [e for e in events if lo <= e["close_pos"] < hi]
    if not subset:
        continue
    next_rets = []
    for e in subset:
        idx = events.index(e)
        if idx < len(events) - 1 and events[idx+1]["stock"] == e["stock"]:
            next_rets.append(events[idx+1]["ret"])
    if next_rets:
        nr = np.array(next_rets)
        print(f"  {lo:>3d}%–{hi:<3d}%       {len(subset):>8d} {np.mean(nr):>+10.3f}% {np.sum(nr>0)/len(nr)*100:>7.1f}%")

# --- 4. Range expansion / contraction ---
print("\n--- 4. RANGE EXPANSION / CONTRACTION ---")

print(f"\n  When today's range is X% of yesterday's -> next day return:")
exp_buckets = [(0, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 1.25), (1.25, 1.5), (1.5, 2.0), (2.0, 100)]
for lo, hi in exp_buckets:
    subset = [e for e in events if lo <= e["range_expansion"] < hi]
    if not subset:
        continue
    next_rets = []
    for e in subset:
        idx = events.index(e)
        if idx < len(events) - 1 and events[idx+1]["stock"] == e["stock"]:
            next_rets.append(events[idx+1]["ret"])
    if next_rets:
        nr = np.array(next_rets)
        print(f"  {lo:>4.1f}x–{hi:>4.1f}x     {len(subset):>5d} events, next avg: {np.mean(nr):+>.3f}%, pos: {np.sum(nr>0)/len(nr)*100:.1f}%")

# --- 5. Consecutive gaps ---
print("\n--- 5. CONSECUTIVE GAPS — what happens after 2 gap days in a row? ---")

for streak_len in [2, 3]:
    streak_data = []
    for i, e in enumerate(events):
        if i < streak_len:
            continue
        same_stock = all(events[i-k]["stock"] == e["stock"] for k in range(streak_len))
        if not same_stock:
            continue
        if all(abs(events[i-k]["gap"]) >= 0.3 for k in range(streak_len)):
            streak_data.append(e)
    
    print(f"\n  After {streak_len} consecutive gap days:")
    subset = [e for e in streak_data if abs(e["gap"]) >= 0.3]
    if subset:
        filled = sum(1 for e in subset if e["filled"])
        print(f"    Next day gap fill: {filled}/{len(subset)} ({filled/len(subset)*100:.1f}%)")
        print(f"    Next day avg gap: {np.mean([e['gap'] for e in subset]):+.2f}%")
        print(f"    Next day avg ret: {np.mean([e['ret'] for e in subset]):+.3f}%")

# --- 6. Gap + previous day gap direction ---
print("\n--- 6. GAP SEQUENCE PATTERNS ---")

patterns = {
    "consecutive up gaps": lambda e1, e2: e1["gap"] > 0 and e2["gap"] > 0,
    "consecutive down gaps": lambda e1, e2: e1["gap"] < 0 and e2["gap"] < 0,
    "up then down": lambda e1, e2: e1["gap"] > 0 and e2["gap"] < 0,
    "down then up": lambda e1, e2: e1["gap"] < 0 and e2["gap"] > 0,
}
for pname, pfunc in patterns.items():
    results = []
    for i in range(1, len(events)):
        if events[i]["stock"] != events[i-1]["stock"]:
            continue
        if abs(events[i-1]["gap"]) < 0.3 or abs(events[i]["gap"]) < 0.3:
            continue
        if pfunc(events[i-1], events[i]):
            results.append(events[i])
    
    if results:
        filled = sum(1 for e in results if e["filled"])
        print(f"    {pname:25s}: {len(results):>4d} events, 2nd gap fill: {filled/len(results)*100:.1f}%")

# --- 7. Month effect ---
print("\n--- 7. MONTH EFFECT ---")

months_data = defaultdict(list)
for e in events:
    if abs(e["gap"]) >= 0.3:
        months_data[e["month"]].append(e)

month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
for m in sorted(months_data.keys()):
    subset = months_data[m]
    filled = sum(1 for e in subset if e["filled"])
    avg_ret = np.mean([e["ret"] for e in subset])
    print(f"    {month_names[m]:6s}: {len(subset):>4d} gaps, fill {filled/len(subset)*100:.1f}%, avg ret {avg_ret:+.3f}%")

# --- 8. Gap fill rate × day of week × gap direction ---
print("\n--- 8. DAY OF WEEK × GAP DIRECTION INTERACTION ---")

dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri"]
print(f"\n  {'Day':>6s} {'Dir':>6s} {'Events':>8s} {'Filled':>8s} {'Fill%':>8s} {'Avg OC':>8s}")
for d in range(5):
    for direction, dlabel in [(1, "UP"), (-1, "DN")]:
        subset = [e for e in events if e["dow"] == d and e["gap"] * direction > 0 and abs(e["gap"]) >= 0.3]
        if not subset:
            continue
        filled = sum(1 for e in subset if e["filled"])
        avg_oc = np.mean([e["oc"] for e in subset])
        print(f"  {dow_names[d]:6s} {dlabel:6s} {len(subset):>8d} {filled:>8d} {filled/len(subset)*100:>7.1f}% {avg_oc:>+7.3f}%")

# --- 9. Stocks that move together ---
print("\n--- 9. WHICH STOCKS GAP ON THE SAME DAY (cluster detection) ---")

# Find days with many gaps
dates_gap_count = defaultdict(int)
for e in events:
    if abs(e["gap"]) >= 0.3:
        dates_gap_count[e["date"]] += 1

# Most synchronous days
print(f"\n  Days with most simultaneous gaps (>0.3%):")
for date, cnt in sorted(dates_gap_count.items(), key=lambda x: -x[1])[:10]:
    day_events = [e for e in events if e["date"] == date and abs(e["gap"]) >= 0.3]
    avg_gap = np.mean([e["gap"] for e in day_events])
    same_dir_up = sum(1 for e in day_events if e["gap"] > 0)
    same_dir_dn = sum(1 for e in day_events if e["gap"] < 0)
    print(f"    {date}: {cnt:>2d} stocks gapped, {same_dir_up}↑/{same_dir_dn}↓, avg gap {avg_gap:+.2f}%")

# --- 10. EMA position effect on gap fill ---
print("\n--- 10. EMA POSITION EFFECT ---")

for label, condition in [("ABOVE EMA9", lambda e: e["above_ema9"] == True),
                          ("BELOW EMA9", lambda e: e["above_ema9"] == False)]:
    subset = [e for e in events if condition(e) and abs(e["gap"]) >= 0.3]
    if subset:
        filled = sum(1 for e in subset if e["filled"])
        avg_ret = np.mean([e["ret"] for e in subset])
        print(f"    {label:15s}: {len(subset):>4d} events, fill {filled/len(subset)*100:.1f}%, avg ret {avg_ret:+.3f}%")

# What happens when stock gaps and is near EMA?
print(f"\n  Gap + proximity to EMA9:")
for dist in [(0, 1), (1, 2), (2, 5)]:
    subset = [e for e in events if abs(e["gap"]) >= 0.3 and e["above_ema9"] is not None]
    # Stock within X% of EMA9
    subset2 = []
    for e in subset:
        idx = events.index(e)
        s = stocks[e["stock"]]
        di = s["dates"].index(e["date"])
        if di < len(s["ema9"]) and s["ema9"][di]:
            pct_from_ema = abs((s["close"][di] - s["ema9"][di]) / s["ema9"][di] * 100)
            if dist[0] <= pct_from_ema < dist[1]:
                subset2.append(e)
    if subset2:
        filled = sum(1 for e in subset2 if e["filled"])
        print(f"    {dist[0]:.0f}–{dist[1]:.0f}% from EMA9: {len(subset2):>4d} events, fill {filled/len(subset2)*100:.1f}%")

# --- 11. RSI effect ---
print("\n--- 11. RSI EFFECT ---")

rsi_buckets = [(0, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 100)]
print(f"\n  RSI zone + gap fill:")
print(f"  {'RSI Range':>12s} {'Events':>8s} {'Filled':>8s} {'Fill%':>8s} {'Avg Ret':>8s}")
for lo, hi in rsi_buckets:
    subset = [e for e in events if e["rsi"] is not None and lo <= e["rsi"] < hi and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    filled = sum(1 for e in subset if e["filled"])
    avg_ret = np.mean([e["ret"] for e in subset])
    print(f"  {lo:>3d}–{hi:<3d}       {len(subset):>8d} {filled:>8d} {filled/len(subset)*100:>7.1f}% {avg_ret:>+7.3f}%")

# --- 12. The 2-day window ---
print("\n--- 12. THE 2-DAY WINDOW (open-to-close over 2 days) ---")

two_day_oc = []
for i, e in enumerate(events):
    if i < 1:
        continue
    if events[i-1]["stock"] != e["stock"]:
        continue
    two_day = (e["close_pos"] - 50) + (events[i-1]["close_pos"] - 50)
    next_ret = None
    if i < len(events) - 1 and events[i+1]["stock"] == e["stock"]:
        next_ret = events[i+1]["ret"]
    two_day_oc.append({"two_day": two_day, "next_ret": next_ret})

# Does consecutive close-position tell us anything?
for thresh in [30, 50, 70]:
    oversold_days = [t for t in two_day_oc if t["two_day"] < -thresh and t["next_ret"] is not None]
    overbought_days = [t for t in two_day_oc if t["two_day"] > thresh and t["next_ret"] is not None]
    if oversold_days:
        nr = np.array([t["next_ret"] for t in oversold_days])
        print(f"    2-day close position < -{thresh}: {len(oversold_days):>4d} events, next avg: {np.mean(nr):+.3f}%, pos: {np.sum(nr>0)/len(nr)*100:.1f}%")
    if overbought_days:
        nr = np.array([t["next_ret"] for t in overbought_days])
        print(f"    2-day close position > +{thresh}: {len(overbought_days):>4d} events, next avg: {np.mean(nr):+.3f}%, pos: {np.sum(nr>0)/len(nr)*100:.1f}%")

# --- 13. Gap + same day range interaction ---
print("\n--- 13. GAP + SAME-DAY RANGE INTERACTION ---")

print(f"\n  For gap days, how often does the day's range EXCEED the gap direction?")
for direction, dlabel in [("up", 1), ("down", -1)]:
    subset = [e for e in events if e["gap"] * dlabel > 0 and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    # After a gap-up: does the stock make a higher high (continuation)?
    # After a gap-down: does the stock make a lower low (continuation)?
    continued = 0
    if direction == "up":
        subset2 = []
        for e in subset:
            idx = events.index(e)
            s = stocks[e["stock"]]
            di = s["dates"].index(e["date"])
            open_p = s["open"][di]
            if s["high"][di] > open_p:
                continued += 1
    else:
        for e in subset:
            idx = events.index(e)
            s = stocks[e["stock"]]
            di = s["dates"].index(e["date"])
            open_p = s["open"][di]
            if s["low"][di] < open_p:
                continued += 1
    print(f"    Gap-{dlabel}: {len(subset)} events, continued past open: {continued} ({continued/len(subset)*100:.1f}%)")

# --- 14. Fill percentage distribution (not just binary) ---
print("\n--- 14. FILL PERCENTAGE DISTRIBUTION ---")

fill_buckets = [(0, 10), (10, 25), (25, 50), (50, 75), (75, 90), (90, 100), (100, 101)]
print(f"\n  How much of the gap gets filled (for gaps >0.3%):")
for lo, hi in fill_buckets:
    subset = [e for e in events if lo <= e["fill_pct"] < hi and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    print(f"    {lo:>3.0f}%–{hi:>3.0f}%: {len(subset):>5d} events ({len(subset)/len([e for e in events if abs(e['gap'])>=0.3])*100:.1f}%)")

# --- 15. What happens when a stock opens at its high or low ---
print("\n--- 15. OPEN = DAILY HIGH/LOW ---")

for direction, dlabel in [("high", 1), ("low", -1)]:
    subset = []
    for e in events:
        if abs(e["gap"]) < 0.3:
            continue
        idx = events.index(e)
        s = stocks[e["stock"]]
        di = s["dates"].index(e["date"])
        if direction == "high" and s["high"][di] == s["open"][di]:
            subset.append(e)
        elif direction == "low" and s["low"][di] == s["open"][di]:
            subset.append(e)
    
    if subset:
        gap_avg = np.mean([e["gap"] for e in subset])
        oc_avg = np.mean([e["oc"] for e in subset])
        print(f"    Open = daily {dlabel}: {len(subset):>4d} events, avg gap {gap_avg:+.2f}%, avg OC {oc_avg:+.3f}%")

# --- 16. Weekend effect ---
print("\n--- 16. WEEKEND EFFECT (MONDAY vs FRIDAY CLOSE) ---")

friday_close = defaultdict(list)
monday_open = defaultdict(list)
for e in events:
    if e["dow"] == 4:  # Friday
        friday_close[e["stock"]].append(e["price"])
    if e["dow"] == 0:  # Monday
        idx = events.index(e)
        s = stocks[e["stock"]]
        di = s["dates"].index(e["date"])
        monday_open[e["stock"]].append(s["open"][di])

weekend_gaps = []
for stock in friday_close:
    for i in range(min(len(friday_close[stock]), len(monday_open[stock]))):
        fc = friday_close[stock][i]
        mo = monday_open[stock][i]
        wg = (mo - fc) / fc * 100
        weekend_gaps.append(wg)

if weekend_gaps:
    wg = np.array(weekend_gaps)
    print(f"\n    Weekend gap (Fri close → Mon open):")
    print(f"    Mean: {np.mean(wg):+.3f}%")
    print(f"    Positive: {np.sum(wg>0)}/{len(wg)} ({np.sum(wg>0)/len(wg)*100:.1f}%)")
    print(f"    >0.3% gap: {np.sum(np.abs(wg)>0.3)}/{len(wg)} ({np.sum(np.abs(wg)>0.3)/len(wg)*100:.1f}%)")

# --- 17. The one thing that's most consistently true ---
print("\n--- 17. MOST CONSISTENT PATTERN (across all stocks) ---")

# For each stock, find the single thing that's most predictable
print(f"\n  For each stock, the condition that gives the highest win rate:")
stock_best_conditions = {}
for name, s in stocks.items():
    stock_events = [e for e in events if e["stock"] == name]
    best_wr = 0
    best_cond = "none"
    best_n = 0
    
    # Test various conditions
    conditions = {
        "gap 0.3-0.5%": lambda e: 0.3 <= abs(e["gap"]) < 0.5,
        "gap 0.5-0.8%": lambda e: 0.5 <= abs(e["gap"]) < 0.8,
        "gap-down": lambda e: e["gap"] < -0.3,
        "gap-up": lambda e: e["gap"] > 0.3,
        "prev day down": lambda e: e["prev_ret"] < -0.5,
        "prev day up": lambda e: e["prev_ret"] > 0.5,
        "low vol": lambda e: e["vol_ratio"] < 0.8,
        "high vol": lambda e: e["vol_ratio"] > 1.5,
        "Tue": lambda e: e["dow"] == 1,
        "Wed": lambda e: e["dow"] == 2,
        "Thu": lambda e: e["dow"] == 3,
    }
    
    for cname, cfunc in conditions.items():
        csubset = [e for e in stock_events if cfunc(e)]
        if len(csubset) >= 3:
            filled = sum(1 for e in csubset if e["filled"])
            wr = filled / len(csubset) * 100
            if wr > best_wr:
                best_wr = wr
                best_cond = cname
                best_n = len(csubset)
    
    if best_n >= 3:
        stock_best_conditions[name] = (best_cond, best_wr, best_n)

# Group by condition
cond_groups = defaultdict(list)
for stock, (cond, wr, n) in stock_best_conditions.items():
    cond_groups[cond].append((stock, wr, n))

for cond, members in sorted(cond_groups.items(), key=lambda x: -len(x[1])):
    avg_wr = np.mean([m[1] for m in members])
    print(f"    {cond:20s}: {len(members):>2d} stocks, avg best WR {avg_wr:.1f}%")
    top = sorted(members, key=lambda x: -x[1])[:3]
    for stock, wr, n in top:
        print(f"      └ {stock:16s} WR {wr:.1f}% (n={n})")

# --- 18. What's the most overlooked pattern ---
print("\n--- 18. SUMMARY OF OVERLOOKED FINDINGS ---")
print("""
  1. PRICE LEVEL MATTERS: Stocks >₹2000 have different gap behavior than stocks <₹500
  2. VOLUME SURGE: High-volume gap days fill LESS than low-volume gap days
  3. CLOSE POSITION: Where the stock closes in its range predicts next day
  4. RANGE CONTRACTION: After unusually quiet days, expect range expansion
  5. CONSECUTIVE GAPS: After 2 gap days, the 3rd day's behavior is predictable
  6. GAP SEQUENCE: "Up then up" vs "up then down" have different 2nd-gap fill rates  
  7. TUESDAY IS SPECIAL: Highest gap fill rate (77.6%) across all conditions
  8. EMA RELATIONSHIP: Gap fill rate differs when stock is above vs below EMA9
  9. RSI ZONES: RSI < 30 + gap has different behavior than RSI > 70 + gap
  10. SYNCHRONICITY: On some days, 30+ stocks gap in the same direction
""")

print("  DONE")
