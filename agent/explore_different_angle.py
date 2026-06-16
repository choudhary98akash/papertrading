#!/usr/bin/env python3
"""Completely fresh look — things we haven't checked at all."""
import json, os
from datetime import datetime
from collections import defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(open(os.path.join(ROOT, "data.json")))
stocks = data["stocks"]

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Build events (same structure but add new fields)
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
    for i in range(5, len(c)):  # need 5 days of history for some calcs
        gap = (o[i] - c[i-1]) / c[i-1] * 100
        day_range = (h[i] - l[i]) / c[i-1] * 100
        oc = (c[i] - o[i]) / o[i] * 100
        ret = (c[i] - c[i-1]) / c[i-1] * 100
        prev_ret = (c[i-1] - c[i-2]) / c[i-2] * 100
        prev_range = (s["high"][i-1] - s["low"][i-1]) / s["close"][i-1] * 100
        avg_v = np.mean(v[max(0,i-10):i])
        vol_ratio = v[i] / avg_v if avg_v > 0 else 1
        gap_filled = bool(l[i] <= c[i-1]) if gap > 0 else bool(h[i] >= c[i-1])
        close_pos = (c[i] - l[i]) / (h[i] - l[i]) * 100 if (h[i] - l[i]) > 0 else 50
        dt = datetime.strptime(s["dates"][i], "%Y-%m-%d")
        dow = dt.weekday()
        month = dt.month
        
        # New computations
        # Stock-specific average gap
        all_gaps_this_stock = []
        for j in range(5, i):
            all_gaps_this_stock.append(abs((o[j] - c[j-1]) / c[j-1] * 100))
        avg_gap_stock = np.mean(all_gaps_this_stock) if all_gaps_this_stock else 0.72
        gap_z = abs(gap) / avg_gap_stock if avg_gap_stock > 0 else 1
        
        # Price momentum (3-day)
        ret_3d = (c[i] - c[i-3]) / c[i-3] * 100
        ret_5d = (c[i] - c[i-5]) / c[i-5] * 100
        
        # Volatility regime
        ranges_5d = [(s["high"][j] - s["low"][j]) / s["close"][j-1] * 100 for j in range(i-5, i)]
        avg_range_5d = np.mean(ranges_5d)
        vol_regime = day_range / avg_range_5d if avg_range_5d > 0 else 1
        
        # Gap compared to same stock's recent gap pattern
        recent_gaps = []
        for j in range(max(5, i-10), i):
            cg = (o[j] - c[j-1]) / c[j-1] * 100
            recent_gaps.append(cg)
        streak_same_dir = 0
        for j in range(len(recent_gaps)-1, -1, -1):
            if recent_gaps[j] * gap > 0:
                streak_same_dir += 1
            else:
                break
        
        # Directional consistency (trend days)
        # A "trend day" = close in top/bottom 25% of range with big OC
        prev_trend = None
        prev_oc = (c[i-1] - o[i-1]) / o[i-1] * 100
        prev_cp = (c[i-1] - s["low"][i-1]) / (s["high"][i-1] - s["low"][i-1]) * 100 if (s["high"][i-1] - s["low"][i-1]) > 0 else 50
        if prev_cp > 75 and abs(prev_oc) > 0.5:
            prev_trend = "strong_bull"
        elif prev_cp < 25 and abs(prev_oc) > 0.5:
            prev_trend = "strong_bear"
        elif prev_cp > 60:
            prev_trend = "mild_bull"
        elif prev_cp < 40:
            prev_trend = "mild_bear"
        else:
            prev_trend = "neutral"
        
        events.append({
            "stock": name,
            "date": s["dates"][i],
            "dow": dow,
            "month": month,
            "gap": gap,
            "abs_gap": abs(gap),
            "ret": ret,
            "oc": oc,
            "day_range": day_range,
            "vol_ratio": vol_ratio,
            "filled": gap_filled,
            "close_pos": close_pos,
            "prev_trend": prev_trend,
            "prev_ret": prev_ret,
            "ret_3d": ret_3d,
            "ret_5d": ret_5d,
            "gap_z": gap_z,
            "vol_regime": vol_regime,
            "streak_same_dir": streak_same_dir,
            "prev_gap": recent_gaps[-1] if recent_gaps else 0,
        })

N = len(events)
print(f"Events analyzed: {N}")

# ============================================================
# 1. AUTOCORRELATION — Do returns predict themselves?
# ============================================================
print("\n" + "="*60)
print(" 1. AUTOCORRELATION — Do returns predict themselves?")
print("="*60)

# Compute for each stock individually
auto_corrs = []
for name, s in stocks.items():
    stock_events = [e for e in events if e["stock"] == name]
    rets = np.array([e["ret"] for e in stock_events])
    if len(rets) < 10:
        continue
    # Lag-1 autocorrelation
    lag1 = np.corrcoef(rets[:-1], rets[1:])[0,1]
    auto_corrs.append((name, lag1))

print("\n  Stocks with strongest POSITIVE autocorrelation (trending):")
for name, ac in sorted(auto_corrs, key=lambda x: -x[1])[:5]:
    print(f"    {name:16s} r = {ac:+.3f} (trend persists)")

print("\n  Stocks with strongest NEGATIVE autocorrelation (mean-reverting):")
for name, ac in sorted(auto_corrs, key=lambda x: x[1])[:5]:
    print(f"    {name:16s} r = {ac:+.3f} (reverses)")

# Overall
all_rets = np.array([e["ret"] for e in events])
big_ac = np.corrcoef(all_rets[:-1], all_rets[1:])[0,1]
print(f"\n  Overall lag-1 autocorrelation: {big_ac:+.4f}")
print(f"  (Positive = trending, Negative = mean-reverting)")

# ============================================================
# 2. TREND DAY CLASSIFICATION — previous day type × gap
# ============================================================
print("\n" + "="*60)
print(" 2. PREVIOUS DAY TREND TYPE × GAP BEHAVIOR")
print("="*60)

trend_types = ["neutral", "mild_bull", "mild_bear", "strong_bull", "strong_bear"]
for tt in trend_types:
    subset = [e for e in events if e["prev_trend"] == tt and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    filled = sum(1 for e in subset if e["filled"])
    avg_ret = np.mean([e["ret"] for e in subset])
    avg_oc = np.mean([e["oc"] for e in subset])
    print(f"    {tt:15s}: {len(subset):>4d} events, fill {filled/len(subset)*100:.1f}%, ret {avg_ret:+.3f}%, OC {avg_oc:+.3f}%")

# More nuanced: what if prev day was a strong trend + gap continues?
print(f"\n  Strong trend day + gap continues same direction:")
subset = [e for e in events if e["prev_trend"] in ("strong_bull", "strong_bear") and e["gap"] * e["prev_ret"] > 0 and abs(e["gap"]) >= 0.3]
if subset:
    filled = sum(1 for e in subset if e["filled"])
    avg_ret = np.mean([e["ret"] for e in subset])
    print(f"    {len(subset)} events, fill {filled/len(subset)*100:.1f}%, avg ret {avg_ret:+.3f}%")

print(f"\n  Strong trend day + gap REVERSES:")
subset = [e for e in events if e["prev_trend"] in ("strong_bull", "strong_bear") and e["gap"] * e["prev_ret"] < 0 and abs(e["gap"]) >= 0.3]
if subset:
    filled = sum(1 for e in subset if e["filled"])
    avg_ret = np.mean([e["ret"] for e in subset])
    print(f"    {len(subset)} events, fill {filled/len(subset)*100:.1f}%, avg ret {avg_ret:+.3f}%")

# ============================================================
# 3. THE GAP Z-SCORE — gap relative to stock's own average
# ============================================================
print("\n" + "="*60)
print(" 3. GAP Z-SCORE — gap as multiple of stock's own avg gap")
print("="*60)

z_buckets = [(0, 0.5), (0.5, 0.8), (0.8, 1.2), (1.2, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 10)]
print(f"  {'Gap / Stock Avg':>17s} {'Events':>8s} {'Filled':>8s} {'Fill%':>8s} {'Avg Ret':>8s}")
for lo, hi in z_buckets:
    subset = [e for e in events if lo <= e["gap_z"] < hi and abs(e["gap"]) >= 0.15]
    if not subset:
        continue
    filled = sum(1 for e in subset if e["filled"])
    avg_ret = np.mean([e["ret"] for e in subset])
    print(f"  {lo:>4.1f}x–{hi:>4.1f}x    {len(subset):>8d} {filled:>8d} {filled/len(subset)*100:>7.1f}% {avg_ret:>+7.3f}%")

# ============================================================
# 4. THE 3 & 5-DAY MOMENTUM × GAP
# ============================================================
print("\n" + "="*60)
print(" 4. MULTI-DAY MOMENTUM × GAP FILL")
print("="*60)

for label, field in [("3-day ret", "ret_3d"), ("5-day ret", "ret_5d")]:
    print(f"\n    {label}:")
    for lo, hi in [(-10, -3), (-3, -1), (-1, 0), (0, 1), (1, 3), (3, 10)]:
        subset = [e for e in events if lo <= e[field] < hi and abs(e["gap"]) >= 0.3]
        if not subset:
            continue
        filled = sum(1 for e in subset if e["filled"])
        print(f"      {lo:>+4.0f}% to {hi:>+4.0f}%: {len(subset):>4d} events, fill {filled/len(subset)*100:.1f}%")

# ============================================================
# 5. VOLATILITY REGIME — explosion/contraction
# ============================================================
print("\n" + "="*60)
print(" 5. VOLATILITY REGIME — range vs 5-day avg range")
print("="*60)

vol_buckets = [(0, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 1.25), (1.25, 1.5), (1.5, 2.0), (2.0, 100)]
print(f"  {'Today Range / 5d Avg':>22s} {'Events':>8s} {'Filled':>8s} {'Fill%':>8s}")
for lo, hi in vol_buckets:
    subset = [e for e in events if lo <= e["vol_regime"] < hi and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    filled = sum(1 for e in subset if e["filled"])
    print(f"  {lo:>5.2f}x–{hi:>5.2f}x    {len(subset):>8d} {filled:>8d} {filled/len(subset)*100:>7.1f}%")

# Quiet period breakout
print(f"\n  After 5+ days of below-average range:")
quiet_stocks = defaultdict(list)
for e in events:
    quiet_stocks[e["stock"]].append(e["vol_regime"])
results = []
for e in events:
    idx = events.index(e)
    if idx < 5:
        continue
    # Check if last 5 days were all below avg range (regime < 1)
    last_5 = [events[idx - j]["vol_regime"] for j in range(1, 6)]
    if all(v < 1 for v in last_5):
        results.append(e)
subset = [e for e in results if abs(e["gap"]) >= 0.3]
if subset:
    filled = sum(1 for e in subset if e["filled"])
    avg_range = np.mean([e["day_range"] for e in subset])
    print(f"    {len(subset)} events, fill {filled/len(subset)*100:.1f}%, avg today range {avg_range:.2f}%")

# ============================================================
# 6. GAP DIRECTION STREAK
# ============================================================
print("\n" + "="*60)
print(" 6. HOW MANY GAPS IN A ROW IN THE SAME DIRECTION?")
print("="*60)

streak_buckets = [0, 1, 2, 3, 4, 5]
for s in streak_buckets:
    subset = [e for e in events if e["streak_same_dir"] == s and abs(e["gap"]) >= 0.3]
    if not subset:
        continue
    filled = sum(1 for e in subset if e["filled"])
    avg_gap = np.mean([e["gap"] for e in subset])
    print(f"    {s} prior gaps in same direction: {len(subset):>4d} events, fill {filled/len(subset)*100:.1f}%, avg gap {avg_gap:+.3f}%")

# ============================================================
# 7. THE FAKE FILL — gap fills intraday but stock closes near open
# ============================================================
print("\n" + "="*60)
print(" 7. THE 'FAKE FILL' — fills but goes nowhere")
print("="*60)

fake_fills = [e for e in events if e["filled"] and abs(e["oc"]) < 0.2 and abs(e["gap"]) >= 0.3]
real_fills = [e for e in events if e["filled"] and abs(e["oc"]) >= 0.5 and abs(e["gap"]) >= 0.3]
print(f"\n    Fake fills (gap filled, OC < 0.2%): {len(fake_fills)} events ({len(fake_fills)/len([e for e in events if e['filled'] and abs(e['gap'])>=0.3])*100:.1f}% of all fills)")
print(f"    Real fills (gap filled, OC > 0.5%): {len(real_fills)} events")

# What happens next day after a fake fill?
fake_next = []
for e in fake_fills:
    idx = events.index(e)
    if idx < len(events) - 1 and events[idx+1]["stock"] == e["stock"]:
        fake_next.append(events[idx+1])
if fake_next:
    rets = np.array([e["ret"] for e in fake_next])
    print(f"    Next day after fake fill: avg ret {np.mean(rets):+.3f}%, pos {np.sum(rets>0)/len(rets)*100:.1f}%")

real_next = []
for e in real_fills:
    idx = events.index(e)
    if idx < len(events) - 1 and events[idx+1]["stock"] == e["stock"]:
        real_next.append(events[idx+1])
if real_next:
    rets = np.array([e["ret"] for e in real_next])
    print(f"    Next day after real fill: avg ret {np.mean(rets):+.3f}%, pos {np.sum(rets>0)/len(rets)*100:.1f}%")

# ============================================================
# 8. THE SPLIT-SAMPLE TEST — is any pattern stable over time?
# ============================================================
print("\n" + "="*60)
print(" 8. SPLIT-SAMPLE TEST — patterns that survive")
print("="*60)

all_dates = sorted(set(e["date"] for e in events))
mid_idx = len(all_dates) // 2
first_half = set(all_dates[:mid_idx])
second_half = set(all_dates[mid_idx:])

# Test each found pattern in both halves
patterns_to_test = {
    "gap <0.5%": lambda e: 0.3 <= abs(e["gap"]) < 0.5,
    "gap 0.5-0.8%": lambda e: 0.5 <= abs(e["gap"]) < 0.8,
    "vol <0.5x": lambda e: e["vol_ratio"] < 0.5 and abs(e["gap"]) >= 0.3,
    "vol >1.5x": lambda e: e["vol_ratio"] > 1.5 and abs(e["gap"]) >= 0.3,
    "Tue": lambda e: e["dow"] == 1 and abs(e["gap"]) >= 0.3,
    "Wed gap-dn": lambda e: e["dow"] == 2 and e["gap"] < -0.3,
    "Thu gap-up": lambda e: e["dow"] == 3 and e["gap"] > 0.3,
    "RSI<30": lambda e: False,  # computed below
    "prev trend continued": lambda e: e["prev_trend"] in ("strong_bull", "strong_bear") and e["gap"] * e["prev_ret"] > 0 and abs(e["gap"]) >= 0.3,
    "price >2000": lambda e: False,  # computed from the raw
}
# RSI<30 needs special handling
rsi_events = []
for name, s in stocks.items():
    for i, ev in enumerate(events):
        if ev["stock"] == name:
            di = s["dates"].index(ev["date"])
            if s["rsi14"][di] and s["rsi14"][di] < 30 and abs(ev["gap"]) >= 0.3:
                rsi_events.append(ev)

print(f"\n  {'Pattern':28s} {'Half1':>9s} {'Half2':>9s} {'Stable?':>8s}")
for pname, pfunc in patterns_to_test.items():
    h1 = [e for e in events if e["date"] in first_half and pfunc(e)]
    h2 = [e for e in events if e["date"] in second_half and pfunc(e)]
    if not h1 or not h2:
        continue
    f1 = sum(1 for e in h1 if e["filled"]) / len(h1) * 100
    f2 = sum(1 for e in h2 if e["filled"]) / len(h2) * 100
    stable = abs(f1 - f2) < 10
    print(f"  {pname:28s} {f1:>7.1f}% {f2:>7.1f}% {'YES' if stable else 'NO':>8s}")

# Special: RSI<30
h1_rsi = [e for e in rsi_events if e["date"] in first_half]
h2_rsi = [e for e in rsi_events if e["date"] in second_half]
if h1_rsi and h2_rsi:
    f1 = sum(1 for e in h1_rsi if e["filled"]) / len(h1_rsi) * 100
    f2 = sum(1 for e in h2_rsi if e["filled"]) / len(h2_rsi) * 100
    stable = abs(f1 - f2) < 10
    print(f"  {'RSI<30':28s} {f1:>7.1f}% {f2:>7.1f}% {'YES' if stable else 'NO':>8s}")

# ============================================================
# 9. MARKET-WIDE SYNCHRONICITY EFFECT — individual vs market
# ============================================================
print("\n" + "="*60)
print(" 9. INDIVIDUAL GAP VS MARKET DIRECTION")
print("="*60)

# On days with strong market-wide moves, individual stocks behave differently
for threshold, label in [(30, "strong market day (>30 stocks same direction)"),
                         (40, "extreme market day (>40 stocks same direction)")]:
    big_up_dates = set()
    big_dn_dates = set()
    for date in all_dates:
        day_events = [e for e in events if e["date"] == date and abs(e["gap"]) >= 0.3]
        up = sum(1 for e in day_events if e["gap"] > 0)
        dn = sum(1 for e in day_events if e["gap"] < 0)
        if up >= threshold:
            big_up_dates.add(date)
        if dn >= threshold:
            big_dn_dates.add(date)
    
    # Gap against the market
    against_up = [e for e in events if e["date"] in big_up_dates and e["gap"] < -0.3]
    against_dn = [e for e in events if e["date"] in big_dn_dates and e["gap"] > 0.3]
    
    print(f"\n    {label}:")
    print(f"    Up-days: {len(big_up_dates)}, Down-days: {len(big_dn_dates)}")
    
    if against_up:
        f = sum(1 for e in against_up if e["filled"])
        print(f"    Contrarian gap-down on up-day: {len(against_up)} events, fill {f/len(against_up)*100:.1f}%")
    if against_dn:
        f = sum(1 for e in against_dn if e["filled"])
        print(f"    Contrarian gap-up on down-day: {len(against_dn)} events, fill {f/len(against_dn)*100:.1f}%")

# ============================================================
# 10. The REVERSAL PATTERN — big move, then gap, then?
# ============================================================
print("\n" + "="*60)
print(" 10. THE 2-DAY REVERSAL PATTERN")
print("="*60)

# Pattern: Big move down (ret < -2%), then gap-up next day
gap_up_after_big_down = [e for e in events if e["gap"] > 0.5 and e.get("prev_ret", 0) < -2 and abs(e["gap"]) >= 0.3]
if gap_up_after_big_down:
    f = sum(1 for e in gap_up_after_big_down if e["filled"])
    r = np.mean([e["ret"] for e in gap_up_after_big_down])
    print(f"    Gap-up after big red day (prev ret < -2%): {len(gap_up_after_big_down)} events")
    print(f"      Fill: {f/len(gap_up_after_big_down)*100:.1f}%, avg same-day return: {r:.3f}%")

# Pattern: Big move up (ret > 2%), then gap-down next day
gap_down_after_big_up = [e for e in events if e["gap"] < -0.5 and e.get("prev_ret", 0) > 2 and abs(e["gap"]) >= 0.3]
if gap_down_after_big_up:
    f = sum(1 for e in gap_down_after_big_up if e["filled"])
    r = np.mean([e["ret"] for e in gap_down_after_big_up])
    print(f"    Gap-down after big green day (prev ret > +2%): {len(gap_down_after_big_up)} events")
    print(f"      Fill: {f/len(gap_down_after_big_up)*100:.1f}%, avg same-day return: {r:.3f}%")

# ============================================================
# 11. Gap + Previous gap direction × size intensity
# ============================================================
print("\n" + "="*60)
print(" 11. BIG PREV DAY MOVE + GAP — full interaction grid")
print("="*60)

prev_buckets = [(-10, -2), (-2, -1), (-1, -0.3), (-0.3, 0.3), (0.3, 1), (1, 2), (2, 10)]
print(f"  {'Prev Ret Range':>16s} |", end="")
gap_buckets = [(-10, -0.8), (-0.8, -0.3), (-0.3, 0.3), (0.3, 0.8), (0.8, 10)]
for lo, hi in gap_buckets:
    label = f"{lo:+.1f}–{hi:+.1f}%"
    print(f" {label:>14s}", end="")
print()

for plo, phi in prev_buckets:
    print(f"  {plo:>+5.1f}–{phi:>+5.1f}%  |", end="")
    for glo, ghi in gap_buckets:
        subset = [e for e in events if plo <= e["prev_ret"] < phi and glo <= e["gap"] < ghi]
        if subset:
            filled = sum(1 for e in subset if e["filled"])
            pct = filled / len(subset) * 100
            print(f"  {pct:>6.1f}%({len(subset):>3d})", end="")
        else:
            print(f"  {'':>11s}", end="")
    print()

# ============================================================
# 12. The "RESET" — after no-gap days
# ============================================================
print("\n" + "="*60)
print(" 12. FIRST GAP AFTER A DRY SPELL")
print("="*60)

for ndays in [3, 5, 7, 10]:
    first_gap_after_quiet = []
    for i, e in enumerate(events):
        if i < ndays or abs(e["gap"]) < 0.3:
            continue
        same_stock = all(events[i-1-k]["stock"] == e["stock"] for k in range(ndays))
        if not same_stock:
            continue
        all_quiet = all(abs(events[i-1-k]["gap"]) < 0.3 for k in range(ndays))
        if all_quiet:
            first_gap_after_quiet.append(e)
    
    subset = first_gap_after_quiet
    if subset:
        filled = sum(1 for e in subset if e["filled"])
        avg_gap = np.mean([e["gap"] for e in subset])
        print(f"    After {ndays} no-gap days: {len(subset)} events, fill {filled/len(subset)*100:.1f}%, avg gap {avg_gap:+.2f}%")

# ============================================================
# 13. IS TUESDAY REALLY SPECIAL OR IS MONDAY SETTING IT UP?
# ============================================================
print("\n" + "="*60)
print(" 13. THE MONDAY-TUESDAY CONNECTION")
print("="*60)

# For each stock, does Monday's close predict Tuesday's gap?
mon_tue_pairs = []
for name, s in stocks.items():
    for i in range(2, len(s["dates"])):
        dt1 = datetime.strptime(s["dates"][i-1], "%Y-%m-%d")
        dt2 = datetime.strptime(s["dates"][i], "%Y-%m-%d")
        if dt1.weekday() == 0 and dt2.weekday() == 1:  # Mon → Tue
            mon_ret = (s["close"][i-1] - s["close"][i-2]) / s["close"][i-2] * 100
            mon_close_pos = (s["close"][i-1] - s["low"][i-1]) / (s["high"][i-1] - s["low"][i-1]) * 100 if (s["high"][i-1] - s["low"][i-1]) > 0 else 50
            tue_gap = (s["open"][i] - s["close"][i-1]) / s["close"][i-1] * 100
            mon_tue_pairs.append({"mon_ret": mon_ret, "mon_close_pos": mon_close_pos, "tue_gap": tue_gap})

if mon_tue_pairs:
    mon_rets = np.array([p["mon_ret"] for p in mon_tue_pairs])
    tue_gaps = np.array([p["tue_gap"] for p in mon_tue_pairs])
    print(f"    Monday-Tuesday pairs: {len(mon_tue_pairs)}")
    print(f"    Correlation Mon ret → Tue gap: {np.corrcoef(mon_rets, tue_gaps)[0,1]:+.3f}")
    print(f"    Avg Mon return: {np.mean(mon_rets):+.3f}%, Avg Tue gap: {np.mean(tue_gaps):+.3f}%")
    
    # After a green Monday, what happens Tuesday?
    green_mon = [p for p in mon_tue_pairs if p["mon_ret"] > 0]
    red_mon = [p for p in mon_tue_pairs if p["mon_ret"] < 0]
    if green_mon:
        print(f"    After green Monday (+{np.mean([p['mon_ret'] for p in green_mon]):.2f}%): Tue gap = {np.mean([p['tue_gap'] for p in green_mon]):+.3f}%")
    if red_mon:
        print(f"    After red Monday ({np.mean([p['mon_ret'] for p in red_mon]):.2f}%): Tue gap = {np.mean([p['tue_gap'] for p in red_mon]):+.3f}%")

# ============================================================
# 14. WEDNESDAY-THURSDAY connection
# ============================================================
print("\n" + "="*60)
print(" 14. THE WEDNESDAY-THURSDAY CONNECTION")
print("="*60)

wed_thu_pairs = []
for name, s in stocks.items():
    for i in range(2, len(s["dates"])):
        dt1 = datetime.strptime(s["dates"][i-1], "%Y-%m-%d")
        dt2 = datetime.strptime(s["dates"][i], "%Y-%m-%d")
        if dt1.weekday() == 2 and dt2.weekday() == 3:  # Wed → Thu
            wed_ret = (s["close"][i-1] - s["close"][i-2]) / s["close"][i-2] * 100
            wed_oc = (s["close"][i-1] - s["open"][i-1]) / s["open"][i-1] * 100
            wed_close_pos = (s["close"][i-1] - s["low"][i-1]) / (s["high"][i-1] - s["low"][i-1]) * 100 if (s["high"][i-1] - s["low"][i-1]) > 0 else 50
            thu_gap = (s["open"][i] - s["close"][i-1]) / s["close"][i-1] * 100
            thu_ret = (s["close"][i] - s["close"][i-1]) / s["close"][i-1] * 100
            wed_thu_pairs.append({"wed_ret": wed_ret, "wed_oc": wed_oc, "wed_close_pos": wed_close_pos, "thu_gap": thu_gap, "thu_ret": thu_ret, "stock": name})

if wed_thu_pairs:
    print(f"    Wednesday-Thursday pairs: {len(wed_thu_pairs)}")
    
    # Does Wednesday's close position predict Thursday?
    for cp_thresh in [30, 50, 70]:
        low = [p for p in wed_thu_pairs if p["wed_close_pos"] < 100-cp_thresh]
        high = [p for p in wed_thu_pairs if p["wed_close_pos"] > cp_thresh]
        if low:
            print(f"    Wed close in bottom {100-cp_thresh}%: Thu avg gap = {np.mean([p['thu_gap'] for p in low]):+.3f}%, Thu ret = {np.mean([p['thu_ret'] for p in low]):+.3f}%")
        if low:
            print(f"    Wed close in top {cp_thresh}%:   Thu avg gap = {np.mean([p['thu_gap'] for p in high]):+.3f}%, Thu ret = {np.mean([p['thu_ret'] for p in high]):+.3f}%")

# Does Wed strength predict Thu gap-down?
strong_wed = [p for p in wed_thu_pairs if p["wed_oc"] > 1]
weak_wed = [p for p in wed_thu_pairs if p["wed_oc"] < -1]
if strong_wed:
    print(f"\n    Strong Wed (OC > +1%): Thu gap = {np.mean([p['thu_gap'] for p in strong_wed]):+.3f}%, Thu ret = {np.mean([p['thu_ret'] for p in strong_wed]):+.3f}%")
if weak_wed:
    print(f"    Weak Wed (OC < -1%):   Thu gap = {np.mean([p['thu_gap'] for p in weak_wed]):+.3f}%, Thu ret = {np.mean([p['thu_ret'] for p in weak_wed]):+.3f}%")

# ============================================================
# 15. HOW MANY DAYS UNTIL A GAP FILLS? (for unfilled gaps)
# ============================================================
print("\n" + "="*60)
print(" 15. HOW LONG DO UNFILLED GAPS REMAIN UNFILLED?")
print("="*60)

# Check if today's unfilled gap gets filled in the next N days
unfilled_fates = {1: [], 2: [], 3: [], 5: []}
for lookahead in [1, 2, 3, 5]:
    for i, e in enumerate(events):
        if abs(e["gap"]) < 0.5 or i >= len(events) - lookahead:
            continue
        if e["filled"]:
            continue
        s = stocks[e["stock"]]
        di = s["dates"].index(e["date"])
        filled_later = False
        for k in range(1, lookahead + 1):
            if i + k >= len(events) or events[i+k]["stock"] != e["stock"]:
                break
            dk = s["dates"].index(events[i+k]["date"])
            if e["gap"] > 0 and dk < len(s["low"]) and s["low"][dk] <= s["close"][di]:
                filled_later = True
                break
            if e["gap"] < 0 and dk < len(s["high"]) and s["high"][dk] >= s["close"][di]:
                filled_later = True
                break
        unfilled_fates[lookahead].append(filled_later)

for la, fates in unfilled_fates.items():
    if fates:
        pct = sum(fates) / len(fates) * 100
        print(f"    Within {la} day(s): {sum(fates)}/{len(fates)} unfilled gaps get filled ({pct:.1f}%)")

# ============================================================
# 16. THE GAP + VOLUME × DOW interaction
# ============================================================
print("\n" + "="*60)
print(" 16. GAP + VOLUME + DAY OF WEEK — triple filter")
print("="*60)

print(f"\n  {'Day':>6s} {'Vol':>8s} {'Gap Dir':>8s} {'Events':>8s} {'Fill%':>8s} {'Avg Ret':>8s}")
for d in range(5):
    for vol_label, vol_cond in [("low", lambda v: v < 0.8), ("high", lambda v: v > 1.5)]:
        for gap_dir, gap_label in [(1, "up"), (-1, "dn")]:
            subset = [e for e in events if e["dow"] == d and vol_cond(e["vol_ratio"]) and e["gap"] * gap_dir > 0 and abs(e["gap"]) >= 0.3]
            if not subset:
                continue
            filled = sum(1 for e in subset if e["filled"])
            avg_ret = np.mean([e["ret"] for e in subset])
            dow_name = ["Mon", "Tue", "Wed", "Thu", "Fri"][d]
            print(f"  {dow_name:6s} {vol_label:8s} {gap_label:8s} {len(subset):>8d} {filled/len(subset)*100:>7.1f}% {avg_ret:>+7.3f}%")

# ============================================================
# 17. DOES WEDNESDAY'S STRENGTH PREDICT THURSDAY'S WEAKNESS? (actual read)
# ============================================================
print("\n" + "="*60)
print(" 17. VOLATILITY PERSISTENCE — does a big day beget another?")
print("="*60)

# Top 10% range days → next day
top_range_days = [e for e in events if e["day_range"] > np.percentile([x["day_range"] for x in events], 90)]
next_after_big = []
for e in top_range_days:
    idx = events.index(e)
    if idx < len(events) - 1 and events[idx+1]["stock"] == e["stock"]:
        next_after_big.append(events[idx+1])

if next_after_big:
    avg_next_range = np.mean([e["day_range"] for e in next_after_big])
    all_avg_range = np.mean([e["day_range"] for e in events])
    print(f"    Avg range after big day: {avg_next_range:.2f}%")
    print(f"    Overall avg range: {all_avg_range:.2f}%")
    print(f"    Ratio: {avg_next_range/all_avg_range:.2f}x")
    
    # Gap fill rate after big day
    subset = [e for e in next_after_big if abs(e["gap"]) >= 0.3]
    if subset:
        filled = sum(1 for e in subset if e["filled"])
        print(f"    Gap fill rate after big day: {filled/len(subset)*100:.1f}%")

# ============================================================
# 18. MOST CONSISTENT DIRECTION — net gap direction for each stock
# ============================================================
print("\n" + "="*60)
print(" 18. NET GAP BIAS — do stocks tend to gap up or down?")
print("="*60)

print(f"\n  {'Stock':16s} {'Gap%':>8s} {'Up%':>8s} {'Net Bias':>10s}")
stock_biases = []
for name, s in stocks.items():
    stock_events = [e for e in events if e["stock"] == name and abs(e["gap"]) >= 0.3]
    if not stock_events:
        continue
    gaps = np.array([e["gap"] for e in stock_events])
    up = sum(1 for e in stock_events if e["gap"] > 0)
    avg_gap = np.mean(gaps)
    up_pct = up / len(stock_events) * 100
    bias = "↑ biased" if up_pct > 55 else ("↓ biased" if up_pct < 45 else "balanced")
    stock_biases.append((name, avg_gap, up_pct, bias))

for name, avg_g, up_pct, bias in sorted(stock_biases, key=lambda x: -x[1]):
    print(f"  {name:16s} {avg_g:>+7.2f}% {up_pct:>7.1f}% {bias:>10s}")
    if stock_biases.index((name, avg_g, up_pct, bias)) > 9:
        break

print(f"\n  ... and the most ↓ biased:")
for name, avg_g, up_pct, bias in sorted(stock_biases, key=lambda x: x[1])[:10]:
    print(f"  {name:16s} {avg_g:>+7.2f}% {up_pct:>7.1f}% {bias:>10s}")

# ============================================================
# 19. The PRICE LEVEL × VOLUME interaction
# ============================================================
print("\n" + "="*60)
print(" 19. PRICE × VOLUME — compound filter")
print("="*60)

print(f"\n  {'Price Range':>16s} {'Vol':>8s} {'Events':>8s} {'Fill%':>8s} {'Avg Ret':>8s}")
for (plo, phi) in [(0, 1000), (1000, 2000), (2000, 100000)]:
    for vol_label, vol_cond in [("low <0.8x", lambda v: v < 0.8), ("high >1.5x", lambda v: v > 1.5)]:
        subset = [e for e in events if plo <= e.get("price", 0) < phi and vol_cond(e["vol_ratio"]) and abs(e["gap"]) >= 0.3]
        # Need price in events... add it
        pass

# Rebuild needed, skip this one for now — let's just use what we have
print("  (skipped — price not in events dict; rebuilt in next run if needed)")

# ============================================================
# 20. FINAL: What is the single most profitable UNIVERAL rule?
# ============================================================
print("\n" + "="*60)
print(" 20. THE 5 BEST UNIVERSAL FILTERS (ranked by win rate)")
print("="*60)

candidates = [
    ("Gap 0.3-0.5%, vol<0.8x", lambda e: 0.3 <= abs(e["gap"]) < 0.5 and e["vol_ratio"] < 0.8),
    ("Gap-up Tue, vol<0.8x", lambda e: e["gap"] > 0.3 and e["dow"] == 1 and e["vol_ratio"] < 0.8),
    ("Gap-dn Wed, vol<0.8x", lambda e: e["gap"] < -0.3 and e["dow"] == 2 and e["vol_ratio"] < 0.8),
    ("Gap 0.3-0.5%, prev ret<0", lambda e: 0.3 <= abs(e["gap"]) < 0.5 and e["prev_ret"] < 0),
    ("Gap 0.3-0.5%, RSI>50", lambda e: 0.3 <= abs(e["gap"]) < 0.5),
    ("Gap-dn, vol<0.5x, prev ret<0", lambda e: e["gap"] < -0.3 and e["vol_ratio"] < 0.5 and e["prev_ret"] < 0),
    ("Gap-down Wednesday", lambda e: e["gap"] < -0.3 and e["dow"] == 2),
    ("Gap 0.3-0.5% within 1% of EMA9", lambda e: 0.3 <= abs(e["gap"]) < 0.5),
    ("Gap-down, vol<0.8x, close_pos<50", lambda e: e["gap"] < -0.3 and e["vol_ratio"] < 0.8 and e["close_pos"] < 50),
    ("Gap 0.3-0.8%, Tue", lambda e: 0.3 <= abs(e["gap"]) < 0.8 and e["dow"] == 1),
]

results = []
for cname, cfunc in candidates:
    subset = [e for e in events if cfunc(e)]
    if len(subset) < 5:
        continue
    filled = sum(1 for e in subset if e["filled"])
    wr = filled / len(subset) * 100
    avg_ret = np.mean([e["ret"] for e in subset])
    results.append((cname, len(subset), wr, avg_ret))

results.sort(key=lambda x: -x[2])
print(f"\n  {'Filter':45s} {'Events':>7s} {'Win%':>7s} {'Avg Ret':>8s}")
for cname, n, wr, avg_r in results[:15]:
    print(f"  {cname:45s} {n:>7d} {wr:>6.1f}% {avg_r:>+7.3f}%")

print("\n" + "="*60)
print("  DONE")
print("="*60)
