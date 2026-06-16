#!/usr/bin/env python3
"""
Pure data exploration — no strategy, no bias, no assumptions.
Just reads data.json and asks: what's actually here?
"""
import json, os, sys, math
from datetime import datetime
from collections import defaultdict, Counter
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(open(os.path.join(ROOT, "data.json")))

stocks = data["stocks"]
nifty = data.get("nifty_index", {})

print("=" * 72)
print("  PURE DATA EXPLORATION — NO STRATEGY LENS")
print(f"  {len(stocks)} stocks, ~{len(list(stocks.values())[0]['dates'])} trading days each")
print(f"  Period: {list(stocks.values())[0]['dates'][0]} to {list(stocks.values())[0]['dates'][-1]}")
print("=" * 72)

# ─── 1. What does a typical trading day look like? ───
print("\n─── 1. THE TYPICAL DAY (median of all stocks × all days) ───")

all_returns = []
all_ranges = []
all_opens = []
all_closes = []
all_gaps = []
all_volumes = []

for name, s in stocks.items():
    c = s["close"]
    o = s["open"]
    h = s["high"]
    l = s["low"]
    v = s["volume"]
    for i in range(len(c)):
        if i > 0:
            ret = (c[i] - c[i-1]) / c[i-1] * 100
            gap = (o[i] - c[i-1]) / c[i-1] * 100
            all_returns.append(ret)
            all_gaps.append(gap)
        rng = (h[i] - l[i]) / c[i] * 100
        all_ranges.append(rng)
        all_volumes.append(v[i])

all_returns = np.array(all_returns)
all_gaps = np.array(all_gaps)
all_ranges = np.array(all_ranges)

print(f"\n  Daily Return %:")
print(f"    Mean:   {np.mean(all_returns):+.3f}%")
print(f"    Median: {np.median(all_returns):+.3f}%")
print(f"    Std:    {np.std(all_returns):.3f}%")
print(f"    25th:   {np.percentile(all_returns, 25):+.3f}%")
print(f"    75th:   {np.percentile(all_returns, 75):+.3f}%")
print(f"    90th:   {np.percentile(all_returns, 90):+.3f}%")
print(f"    Skew:   {np.mean(((all_returns - np.mean(all_returns))/np.std(all_returns))**3):.3f}")

print(f"\n  Daily Range %:")
print(f"    Mean:   {np.mean(all_ranges):.2f}%")
print(f"    Median: {np.median(all_ranges):.2f}%")
print(f"    90th:   {np.percentile(all_ranges, 90):.2f}%")

print(f"\n  Gap %:")
print(f"    Mean:   {np.mean(all_gaps):+.3f}%")
print(f"    Median: {np.median(all_gaps):+.3f}%")
print(f"    Std:    {np.std(all_gaps):.3f}%")

# ─── 2. Open vs Close — where does the price go? ───
print("\n─── 2. OPEN vs CLOSE: WHERE DOES PRICE GO DURING THE DAY? ───")

oc_returns = []
for name, s in stocks.items():
    o = s["open"]
    c = s["close"]
    for i in range(len(c)):
        oc = (c[i] - o[i]) / o[i] * 100
        oc_returns.append(oc)

oc_returns = np.array(oc_returns)
print(f"\n  Open-to-Close return %:")
print(f"    Mean:   {np.mean(oc_returns):+.3f}%")
print(f"    Median: {np.median(oc_returns):+.3f}%")
print(f"    Positive days: {np.sum(oc_returns > 0)} / {len(oc_returns)} ({np.sum(oc_returns > 0)/len(oc_returns)*100:.1f}%)")
print(f"    Negative days: {np.sum(oc_returns < 0)} / {len(oc_returns)} ({np.sum(oc_returns < 0)/len(oc_returns)*100:.1f}%)")

# ─── 3. Gap Analysis — the raw truth ───
print("\n─── 3. THE RAW TRUTH ABOUT GAPS ───")

# Collect ALL gaps
all_gap_events = []
for name, s in stocks.items():
    c = s["close"]
    o = s["open"]
    h = s["high"]
    l = s["low"]
    for i in range(1, len(c)):
        gap = (o[i] - c[i-1]) / c[i-1] * 100
        day_range = (h[i] - l[i]) / c[i-1] * 100
        oc_return = (c[i] - o[i]) / o[i] * 100
        gap_filled = None
        if gap > 0:
            gap_filled = l[i] <= c[i-1]
        else:
            gap_filled = h[i] >= c[i-1]
        
        # How much of the gap filled?
        if gap > 0:
            fill_pct = min(100, (o[i] - l[i]) / (o[i] - c[i-1]) * 100) if (o[i] - c[i-1]) != 0 else 0
        else:
            fill_pct = min(100, (h[i] - o[i]) / (c[i-1] - o[i]) * 100) if (c[i-1] - o[i]) != 0 else 0
        
        # Prev day info
        prev_ret = (c[i-1] - c[i-2]) / c[i-2] * 100 if i > 1 else 0
        prev_range = (s["high"][i-1] - s["low"][i-1]) / s["close"][i-1] * 100 if i > 1 else 0

        all_gap_events.append({
            "stock": name,
            "date": s["dates"][i],
            "gap": gap,
            "abs_gap": abs(gap),
            "direction": "UP" if gap > 0 else "DOWN",
            "filled": gap_filled,
            "fill_pct": fill_pct,
            "day_range": day_range,
            "oc_return": oc_return,
            "prev_ret": prev_ret,
            "prev_range": prev_range,
        })

print(f"  Total gap events: {len(all_gap_events)}")

# What's the relationship between gap size and fill probability?
buckets = [(0, 0.3), (0.3, 0.5), (0.5, 0.8), (0.8, 1.2), (1.2, 2.0), (2.0, 5.0), (5.0, 100)]
print(f"\n  Gap Size -> Fill Rate (the real relationship):")
print(f"  {'Range':>12s} {'Events':>8s} {'Filled':>8s} {'Fill%':>8s} {'Avg Fill%':>10s}")
print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*10}")
for lo, hi in buckets:
    subset = [g for g in all_gap_events if lo <= g["abs_gap"] < hi]
    if not subset:
        continue
    filled = sum(1 for g in subset if g["filled"])
    avg_fill = np.mean([g["fill_pct"] for g in subset])
    print(f"  {lo:>5.1f}%-{hi:>5.1f}% {len(subset):>8d} {filled:>8d} {filled/len(subset)*100:>7.1f}% {avg_fill:>9.1f}%")

# ─── 4. What predicts something unusual? ───
print("\n─── 4. UNCONDITIONAL PROBABILITIES — what just happens? ───")

# Day of week effects
dow_map = defaultdict(list)
for name, s in stocks.items():
    for i, d in enumerate(s["dates"]):
        dt = datetime.strptime(d, "%Y-%m-%d")
        dow = dt.weekday()
        if i > 0:
            ret = (s["close"][i] - s["close"][i-1]) / s["close"][i-1] * 100
            dow_map[dow].append(ret)

dow_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
print(f"\n  Day of Week — Average Return:")
for d in range(5):
    rets = np.array(dow_map[d])
    print(f"    {dow_names[d]:12s}: {np.mean(rets):+.3f}% (pos: {np.sum(rets>0)}/{len(rets)} = {np.sum(rets>0)/len(rets)*100:.1f}%)")

# ─── 5. Consecutive day patterns ───
print("\n─── 5. CONSECUTIVE DAYS — what happens after streaks? ───")

streak_data = defaultdict(list)
for name, s in stocks.items():
    c = s["close"]
    for i in range(3, len(c)):
        rets = [(c[j] - c[j-1]) / c[j-1] * 100 for j in range(i-2, i+1)]
        # Count streak
        streak = 1
        for j in range(len(rets)-2, -1, -1):
            if (rets[j] > 0) == (rets[j+1] > 0):
                streak += 1
            else:
                break
        if streak > 5:
            streak = 5
        streak_data[streak].append(rets[-1])

print(f"\n  After N consecutive days in same direction -> next day return:")
for streak in sorted(streak_data.keys()):
    rets = np.array(streak_data[streak])
    pos = np.sum(rets > 0)
    neg = np.sum(rets < 0)
    print(f"    {streak}X streak: {len(rets):>5d} events, next day positive: {pos/len(rets)*100:>5.1f}% (mean: {np.mean(rets):+.3f}%)")

# ─── 6. The most interesting question: When is a gap most/least likely to fill? ───
print("\n─── 6. GAP FILL CORRELATES — what factors affect fill rate? ───")

# Factor 1: Previous day range
print(f"\n  Factor: Previous Day Range vs Gap Fill")
prev_range_buckets = [(0, 1), (1, 1.5), (1.5, 2), (2, 3), (3, 100)]
for lo, hi in prev_range_buckets:
    subset = [g for g in all_gap_events if lo <= g["prev_range"] < hi]
    if not subset:
        continue
    filled = sum(1 for g in subset if g["filled"])
    print(f"    Prev range {lo:>3.1f}%-{hi:>3.1f}%: {len(subset):>5d} gaps, filled {filled:>5d} ({filled/len(subset)*100:.1f}%)")

# Factor 2: Gap direction + previous day direction
print(f"\n  Factor: Previous Day Return + Gap Direction")
same_dir = [g for g in all_gap_events if (g["gap"] > 0 and g["prev_ret"] > 0) or (g["gap"] < 0 and g["prev_ret"] < 0)]
opp_dir = [g for g in all_gap_events if abs(g["gap"]) > 0.3 and ((g["gap"] > 0 and g["prev_ret"] < 0) or (g["gap"] < 0 and g["prev_ret"] > 0))]
if same_dir:
    sf = sum(1 for g in same_dir if g["filled"])
    print(f"    Gap SAME direction as prev day:   {len(same_dir):>5d} gaps, filled {sf:>5d} ({sf/len(same_dir)*100:.1f}%)")
if opp_dir:
    of = sum(1 for g in opp_dir if g["filled"])
    print(f"    Gap OPPOSITE direction to prev day: {len(opp_dir):>5d} gaps, filled {of:>5d} ({of/len(opp_dir)*100:.1f}%)")

# Factor 3: Day of week + gap
print(f"\n  Factor: Day of Week + Gap Fill")
dow_gaps = defaultdict(list)
for g in all_gap_events:
    dt = datetime.strptime(g["date"], "%Y-%m-%d")
    dow_gaps[dt.weekday()].append(g)
for d in range(5):
    subset = dow_gaps[d]
    if not subset:
        continue
    filled = sum(1 for g in subset if g["filled"])
    print(f"    {dow_names[d]:12s}: {len(subset):>5d} gaps, filled {filled:>5d} ({filled/len(subset)*100:.1f}%)")

# ─── 7. The most surprising thing ───
print("\n─── 7. OUTLIERS — the biggest moves ───")

# Top 20 biggest gap-up days
gap_ups = sorted([g for g in all_gap_events if g["gap"] > 0], key=lambda x: -x["gap"])[:10]
print(f"\n  Biggest gap-ups:")
for g in gap_ups:
    print(f"    {g['stock']:16s} {g['date']} gap: +{g['gap']:.2f}% filled: {g['filled']} day: {g['day_range']:.1f}%")

# Top 20 biggest gap-down days
gap_downs = sorted([g for g in all_gap_events if g["gap"] < 0], key=lambda x: x["gap"])[:10]
print(f"\n  Biggest gap-downs:")
for g in gap_downs:
    print(f"    {g['stock']:16s} {g['date']} gap: {g['gap']:.2f}% filled: {g['filled']} day: {g['day_range']:.1f}%")

# ─── 8. Best individual stock patterns ───
print("\n─── 8. BY-STOCK PERSONALITY ───")

stock_personality = []
for name, s in stocks.items():
    c = s["close"]
    o = s["open"]
    h = s["high"]
    l = s["low"]
    v = s["volume"]
    rets = [(c[i] - c[i-1]) / c[i-1] * 100 for i in range(1, len(c))]
    ranges = [(h[i] - l[i]) / c[i] * 100 for i in range(len(c))]
    gaps = [(o[i] - c[i-1]) / c[i-1] * 100 for i in range(1, len(c))]
    
    # Gap fill rate
    gap_fills = []
    for i in range(1, len(c)):
        gp = (o[i] - c[i-1]) / c[i-1] * 100
        if abs(gp) < 0.3:
            continue
        if gp > 0:
            gap_fills.append(1 if l[i] <= c[i-1] else 0)
        else:
            gap_fills.append(1 if h[i] >= c[i-1] else 0)
    
    stock_personality.append({
        "name": name,
        "avg_ret": np.mean(rets),
        "std_ret": np.std(rets),
        "avg_range": np.mean(ranges),
        "avg_gap": np.mean([abs(g) for g in gaps]),
        "gap_fill_rate": np.mean(gap_fills) * 100 if gap_fills else 0,
        "pos_days": np.sum(np.array(rets) > 0) / len(rets) * 100,
        "avg_volume": np.mean(v),
        "gap_freq": sum(1 for g in gaps if abs(g) >= 0.3) / len(gaps) * 100,
    })

# Most volatile
print(f"\n  Most volatile (highest avg daily range):")
for s in sorted(stock_personality, key=lambda x: -x["avg_range"])[:5]:
    print(f"    {s['name']:16s} avg range: {s['avg_range']:.2f}%  avg gap: {s['avg_gap']:.2f}%  gap fill: {s['gap_fill_rate']:.1f}%")

# Most stable
print(f"\n  Most stable (lowest avg daily range):")
for s in sorted(stock_personality, key=lambda x: x["avg_range"])[:5]:
    print(f"    {s['name']:16s} avg range: {s['avg_range']:.2f}%  avg gap: {s['avg_gap']:.2f}%  gap fill: {s['gap_fill_rate']:.1f}%")

# Best gap fill stocks
print(f"\n  Best gap fill stocks:")
for s in sorted(stock_personality, key=lambda x: -x["gap_fill_rate"])[:5]:
    print(f"    {s['name']:16s} fill rate: {s['gap_fill_rate']:.1f}%  gap freq: {s['gap_freq']:.1f}%  range: {s['avg_range']:.2f}%")

# Worst gap fill stocks
print(f"\n  Worst gap fill stocks:")
for s in sorted(stock_personality, key=lambda x: x["gap_fill_rate"])[:5]:
    print(f"    {s['name']:16s} fill rate: {s['gap_fill_rate']:.1f}%  gap freq: {s['gap_freq']:.1f}%  range: {s['avg_range']:.2f}%")

# ─── 9. Correlation: does anything predict next day's return? ───
print("\n─── 9. PREDICTIVE POWER — what correlates with NEXT day's return? ───")

# Test various factors
factors = {
    "Today's return": ([], []),
    "Today's range": ([], []),
    "Gap size": ([], []),
    "Today's volume vs avg": ([], []),
}

for name, s in stocks.items():
    c = s["close"]
    o = s["open"]
    h = s["high"]
    l = s["low"]
    v = s["volume"]
    for i in range(2, len(c) - 1):
        today_ret = (c[i] - c[i-1]) / c[i-1] * 100
        today_range = (h[i] - l[i]) / c[i-1] * 100
        gap = (o[i] - c[i-1]) / c[i-1] * 100
        next_ret = (c[i+1] - c[i]) / c[i] * 100
        avg_v = np.mean(v[max(0,i-10):i])
        vol_ratio = v[i] / avg_v if avg_v > 0 else 1

        factors["Today's return"][0].append(today_ret)
        factors["Today's return"][1].append(next_ret)
        factors["Today's range"][0].append(today_range)
        factors["Today's range"][1].append(next_ret)
        factors["Gap size"][0].append(gap)
        factors["Gap size"][1].append(next_ret)
        factors["Today's volume vs avg"][0].append(vol_ratio)
        factors["Today's volume vs avg"][1].append(next_ret)

for factor_name, (x, y) in factors.items():
    x = np.array(x)
    y = np.array(y)
    corr = np.corrcoef(x, y)[0, 1]
    print(f"    {factor_name:30s} → next day return: r = {corr:+.4f}")

# ─── 10. The single most interesting thing ───
print("\n─── 10. THE MOST INTERESTING THING IN THE DATA ───")

# What's the most extreme asymmetry?
# Compare gap-up days vs gap-down days
up_days = [g for g in all_gap_events if g["gap"] > 0]
down_days = [g for g in all_gap_events if g["gap"] < 0]

print(f"\n  Gap-up days: {len(up_days)}")
print(f"    Avg OC return: {np.mean([g['oc_return'] for g in up_days]):+.3f}%")
print(f"    Avg fill%:     {np.mean([g['fill_pct'] for g in up_days]):.1f}%")
print(f"    Filled:        {sum(1 for g in up_days if g['filled'])}/{len(up_days)} ({sum(1 for g in up_days if g['filled'])/len(up_days)*100:.1f}%)")

print(f"\n  Gap-down days: {len(down_days)}")
print(f"    Avg OC return: {np.mean([g['oc_return'] for g in down_days]):+.3f}%")
print(f"    Avg fill%:     {np.mean([g['fill_pct'] for g in down_days]):.1f}%")
print(f"    Filled:        {sum(1 for g in down_days if g['filled'])}/{len(down_days)} ({sum(1 for g in down_days if g['filled'])/len(down_days)*100:.1f}%)")

# The data asked: "Is there a time when the market ALWAYS does X?"
print(f"\n  When does the market ALWAYS reverse?")
# Check: after 3 down days, what happens?
three_downs = []
for name, s in stocks.items():
    c = s["close"]
    for i in range(4, len(c)):
        if all((c[j] < c[j-1]) for j in range(i-2, i+1)):
            ret = (c[i] - c[i-1]) / c[i-1] * 100
            three_downs.append(ret)
if three_downs:
    td = np.array(three_downs)
    print(f"    After 3 consecutive down days: {len(td)} events, next day mean: {np.mean(td):+.3f}%, positive: {np.sum(td>0)}/{len(td)} ({np.sum(td>0)/len(td)*100:.1f}%)")

three_ups = []
for name, s in stocks.items():
    c = s["close"]
    for i in range(4, len(c)):
        if all((c[j] > c[j-1]) for j in range(i-2, i+1)):
            ret = (c[i] - c[i-1]) / c[i-1] * 100
            three_ups.append(ret)
if three_ups:
    tu = np.array(three_ups)
    print(f"    After 3 consecutive up days:   {len(tu)} events, next day mean: {np.mean(tu):+.3f}%, positive: {np.sum(tu>0)}/{len(tu)} ({np.sum(tu>0)/len(tu)*100:.1f}%)")

# ─── 11. The steady truth ───
print("\n─── 11. THE STEADY TRUTH — what's most reliable? ───")

# For each stock, what's the one thing you can count on?
print(f"\n  Most reliable pattern per stock (highest win rate):")
for s in sorted(stock_personality, key=lambda x: -x["pos_days"])[:5]:
    print(f"    {s['name']:16s} positive days: {s['pos_days']:.1f}%  gap fill: {s['gap_fill_rate']:.1f}%")

print(f"\n  Least directional (most random):")
for s in sorted(stock_personality, key=lambda x: abs(x["pos_days"] - 50))[:5]:
    print(f"    {s['name']:16s} positive: {s['pos_days']:.1f}%  close to 50/50 coin flip")

# ─── 12. What the data says about itself ───
print("\n─── 12. RAW INSIGHTS (no interpretation) ───")
print(f"""
  Data volume: {len(all_gap_events):,} trading days × stocks
  Average stock moves {np.mean(all_ranges):.2f}% per day
  Average gap is {np.mean([abs(g) for g in all_gaps]):.2f}%
  {np.sum(np.array(all_returns) > 0)/len(all_returns)*100:.1f}% of days are positive
  {np.sum(np.array(all_returns) == 0)/len(all_returns)*100:.1f}% of days are flat
  The largest single-day move was {np.max(all_ranges):.1f}%
  The largest gap was {np.max([abs(g) for g in all_gaps]):.1f}%
  {np.sum(np.array([g['filled'] for g in all_gap_events if g['abs_gap'] >= 0.3])) / len([g for g in all_gap_events if g['abs_gap'] >= 0.3]) * 100:.1f}% of gaps >0.3% fill
  {np.sum(np.array([g['filled'] for g in all_gap_events if g['abs_gap'] >= 0.5])) / len([g for g in all_gap_events if g['abs_gap'] >= 0.5]) * 100:.1f}% of gaps >0.5% fill
""")

print("  EXPLORATION COMPLETE — all numbers are from real yfinance data")
print("  No strategy, no bias, no interpretation — just what's there")
print()
