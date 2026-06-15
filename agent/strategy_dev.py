#!/usr/bin/env python3
"""
Nifty 50 Strategy Developer
============================
Devises and refines a 1% SL / 1-2% target intraday strategy using live yfinance data.
Analyzes Nifty 50 index conditions first, then applies to individual stocks.

Usage:
    python strategy_dev.py
"""

import sys, json, warnings, io, csv, os
from datetime import datetime, timedelta, date
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

NIFTY_50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "HINDUNILVR.NS", "ITC.NS", "INFY.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "SBIN.NS", "WIPRO.NS", "LT.NS", "HCLTECH.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ASIANPAINT.NS", "AXISBANK.NS", "ULTRACEMCO.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "M&M.NS", "TRENT.NS",
    "COALINDIA.NS", "ADANIENT.NS", "ADANIPORTS.NS", "BEL.NS", "BAJAJFINSV.NS",
    "NESTLEIND.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "JSWSTEEL.NS",
    "HINDALCO.NS", "BPCL.NS", "GRASIM.NS", "EICHERMOT.NS", "BRITANNIA.NS",
    "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "SBILIFE.NS", "APOLLOHOSP.NS",
    "HDFCLIFE.NS", "SHRIRAMFIN.NS", "BAJAJHLDNG.NS", "HEROMOTOCO.NS", "INDUSINDBK.NS",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def clean_sym(s):
    return s.replace(".NS", "")

def calc_ema(s, p):
    return s.ewm(span=p, adjust=False).mean()

def calc_atr(df, p=14):
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def calc_rsi(s, p=14):
    delta = s.diff()
    gain = delta.clip(lower=0).rolling(p).mean()
    loss = (-delta.clip(upper=0)).rolling(p).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def fetch_data(symbol, period="3mo"):
    df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
    if df.empty or len(df) < 25:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.name = symbol
    return df


# ─── Phase 1: Analyze Nifty 50 Index ───

def analyze_index():
    print(f"\n{'='*70}")
    print(f"  PHASE 1: NIFTY 50 INDEX ANALYSIS")
    print(f"{'='*70}")

    nifty = yf.download("^NSEI", period="3mo", progress=False, auto_adjust=True)
    if nifty.empty:
        print("  Could not fetch nifty data")
        return None, None
    
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.get_level_values(0)
    
    nifty["returns"] = nifty["Close"].pct_change() * 100
    nifty["range_pct"] = (nifty["High"] - nifty["Low"]) / nifty["Open"] * 100
    nifty["ema9"] = calc_ema(nifty["Close"], 9)
    nifty["ema21"] = calc_ema(nifty["Close"], 21)
    nifty["atr14"] = calc_atr(nifty, 14)
    nifty["atr_pct"] = nifty["atr14"] / nifty["Close"] * 100
    nifty["rsi14"] = calc_rsi(nifty["Close"], 14)
    nifty["above_ema9"] = nifty["Close"] > nifty["ema9"]
    nifty["above_ema21"] = nifty["Close"] > nifty["ema21"]
    nifty["ema9_above_ema21"] = nifty["ema9"] > nifty["ema21"]

    recent = nifty.tail(60)
    
    print(f"\n  ┌──────────────────────────┬───────────┐")
    print(f"  │ Metric                   │ Value     │")
    print(f"  ├──────────────────────────┼───────────┤")
    print(f"  │ Current Close            │ {recent['Close'].iloc[-1]:>9.2f} │")
    print(f"  │ Avg Daily Range %        │ {recent['range_pct'].mean():>9.2f}% │")
    print(f"  │ Max Daily Range %        │ {recent['range_pct'].max():>9.2f}% │")
    print(f"  │ Avg Daily Return %       │ {recent['returns'].mean():>+9.3f}% │")
    print(f"  │ Std Dev Daily Return %   │ {recent['returns'].std():>9.3f}% │")
    print(f"  │ Avg ATR %                │ {recent['atr_pct'].mean():>9.2f}% │")
    print(f"  │ Avg RSI (14)             │ {recent['rsi14'].mean():>9.1f}  │")
    print(f"  │ Days Above 9 EMA         │ {recent['above_ema9'].sum():>5d}/{len(recent)}  │")
    print(f"  │ Days Above 21 EMA        │ {recent['above_ema21'].sum():>5d}/{len(recent)}  │")
    print(f"  │ EMA9 > EMA21 (uptrend)   │ {recent['ema9_above_ema21'].sum():>5d}/{len(recent)}  │")
    print(f"  └──────────────────────────┴───────────┘")

    # Find days where nifty moved 1-2% up (the target zone)
    up_days = recent[recent["returns"] > 0]
    target_days = recent[(recent["returns"] >= 0.8) & (recent["returns"] <= 2.5)]
    
    print(f"\n  Days with 0.8-2.5% up move: {len(target_days)}/{len(recent)} ({len(target_days)/len(recent)*100:.1f}%)")
    
    # Condition analysis: what predicts an up day?
    conditions = {
        "Above 9 EMA": recent["above_ema9"],
        "Above 21 EMA": recent["above_ema21"],
        "EMA Bullish (9>21)": recent["ema9_above_ema21"],
        "RSI > 50": recent["rsi14"] > 50,
        "RSI 40-60": (recent["rsi14"] > 40) & (recent["rsi14"] < 60),
        "RSI < 40 (oversold)": recent["rsi14"] < 40,
        "ATR > 1%": recent["atr_pct"] > 1.0,
        "Prev Day Down": recent["returns"].shift(1) < 0,
        "Prev Day Up": recent["returns"].shift(1) > 0,
        "2 Days Down": (recent["returns"].shift(1) < 0) & (recent["returns"].shift(2) < 0),
        "Above EMA9 + RSI>50": recent["above_ema9"] & (recent["rsi14"] > 50),
        "Above Both EMA + RSI>50": recent["above_ema9"] & recent["above_ema21"] & (recent["rsi14"] > 50),
    }

    print(f"\n  ┌──────────────────────────┬──────────┬───────────┬──────────┐")
    print(f"  │ Condition                │   Days   │ Up Days   │ Win %    │")
    print(f"  ├──────────────────────────┼──────────┼───────────┼──────────┤")
    
    best_conditions = []
    for name, mask in conditions.items():
        subset = recent[mask]
        up_subset = subset[subset["returns"] > 0]
        win_pct = len(up_subset) / len(subset) * 100 if len(subset) > 0 else 0
        print(f"  │ {name:24s} │ {len(subset):>4d}/{len(recent):<2d} │ {len(up_subset):>5d}    │ {win_pct:>5.1f}%  │")
        best_conditions.append((name, win_pct, len(subset)))
    
    best_conditions.sort(key=lambda x: -x[1])
    print(f"  └──────────────────────────┴──────────┴───────────┴──────────┘")
    
    print(f"\n  Top 3 conditions for up-move prediction:")
    for name, wp, cnt in best_conditions[:3]:
        print(f"    {wp:>5.1f}%  {name} ({cnt} occurrences)")

    return nifty, recent


# ─── Phase 2: Test Strategy on Individual Stocks ───

def stock_screener_analysis(nifty_recent):
    print(f"\n{'='*70}")
    print(f"  PHASE 2: INDIVIDUAL STOCK STRATEGY ANALYSIS")
    print(f"{'='*70}")
    
    # Get last 45 trading days for backtesting
    results = []
    stock_stats = {}
    
    for i, sym in enumerate(NIFTY_50):
        name = clean_sym(sym)
        print(f"\n  [{i+1:2d}/50] {name:16s} ... ", end="", flush=True)
        
        df = fetch_data(sym, "3mo")
        if df is None or len(df) < 25:
            print("SKIP (no data)")
            continue
        
        # Use last 45 days for testing
        test = df.tail(45)
        if len(test) < 20:
            print("SKIP (short data)")
            continue
        
        df_full = df
        
        # Test multiple entry condition variants
        variants = {
            "base": {"min_price": 500, "min_vol": 1_000_000, "vol_surge": 1.2, "min_atr": 0.012, "require_ema": True},
            "strict": {"min_price": 1000, "min_vol": 1_500_000, "vol_surge": 1.5, "min_atr": 0.015, "require_ema": True},
            "vol_surge_low": {"min_price": 500, "min_vol": 1_000_000, "vol_surge": 1.1, "min_atr": 0.010, "require_ema": True},
            "no_ema": {"min_price": 500, "min_vol": 1_000_000, "vol_surge": 1.2, "min_atr": 0.012, "require_ema": False},
            "high_price": {"min_price": 1500, "min_vol": 500_000, "vol_surge": 1.3, "min_atr": 0.012, "require_ema": True},
            "atr_loose": {"min_price": 500, "min_vol": 1_000_000, "vol_surge": 1.2, "min_atr": 0.008, "require_ema": True},
        }
        
        best_variant = None
        best_score = -999
        
        for vname, v in variants.items():
            trades = []
            for idx in range(20, len(test) - 2):
                row = test.iloc[idx]
                price = row["Close"]
                
                # Price filter
                if price < v["min_price"]:
                    continue
                
                # Volume filter
                vol_today = row["Volume"]
                lookback_vol = test["Volume"].iloc[max(0, idx-10):idx]
                avg_vol = lookback_vol.mean() if len(lookback_vol) > 0 else 0
                if vol_today < v["min_vol"] or avg_vol == 0:
                    continue
                vol_surge = vol_today / avg_vol
                if vol_surge < v["vol_surge"]:
                    continue
                
                # ATR filter
                atr_series = calc_atr(df_full)
                atr_val = atr_series.iloc[-1] if not atr_series.empty else 0
                lookback_atr = atr_series.iloc[len(df_full) - len(test) + idx]
                if np.isnan(lookback_atr) or (lookback_atr / price) < v["min_atr"]:
                    continue
                
                # EMA filter
                if v["require_ema"]:
                    close_series = test["Close"]
                    ema9 = calc_ema(close_series, 9)
                    ema21 = calc_ema(close_series, 21)
                    e9 = ema9.iloc[idx]
                    e21 = ema21.iloc[idx]
                    if pd.isna(e9) or pd.isna(e21) or price < e9 or price < e21:
                        continue
                
                # Simulate trade
                entry = price
                sl = entry * 0.99
                target = entry * 1.02
                
                future = test.iloc[idx + 1: idx + 6]
                if len(future) == 0:
                    continue
                
                exit_price = None
                exit_reason = "HOLD"
                for _, frow in future.iterrows():
                    if frow["Low"] <= sl:
                        exit_price = sl
                        exit_reason = "SL_HIT"
                        break
                    if frow["High"] >= target:
                        exit_price = target
                        exit_reason = "TARGET_HIT"
                        break
                
                if exit_price is None:
                    exit_price = future.iloc[-1]["Close"]
                    exit_reason = "TIME_EXIT"
                
                pnl = round(((exit_price - entry) / entry) * 100, 2)
                trades.append({
                    "date": str(row.name.date()),
                    "entry": round(entry, 2),
                    "exit": round(exit_price, 2),
                    "result": exit_reason,
                    "pnl": pnl,
                })
            
            if len(trades) >= 2:
                wins = sum(1 for t in trades if t["pnl"] > 0)
                total_pnl = sum(t["pnl"] for t in trades)
                win_rate = wins / len(trades) * 100
                # Score: combine win rate and total pnl, prefer consistency
                score = win_rate * 0.5 + (total_pnl / max(len(trades), 1)) * 20
                
                if score > best_score:
                    best_score = score
                    best_variant = {
                        "variant": vname,
                        "trades": len(trades),
                        "wins": wins,
                        "win_rate": round(win_rate, 1),
                        "total_pnl": round(total_pnl, 2),
                        "avg_pnl": round(total_pnl / len(trades), 2),
                    }
        
        if best_variant:
            stock_stats[name] = best_variant
            print(f"best: {best_variant['variant']:14s} | {best_variant['trades']:2d} trades | WR {best_variant['win_rate']:5.1f}% | PnL {best_variant['total_pnl']:+.2f}%", end="")
            if best_variant['win_rate'] > 35:
                print(f" ★", end="")
            print()
        else:
            print("no signals")

    return stock_stats


# ─── Phase 3: Refined Strategy with Nifty Index Filter ───

def nifty_filtered_strategy(nifty_recent):
    print(f"\n{'='*70}")
    print(f"  PHASE 3: NIFTY FILTERED STRATEGY")
    print(f"{'='*70}")
    
    # Determine current nifty regime
    nifty_recent = nifty_recent.copy()
    nifty_recent["returns"] = nifty_recent["Close"].pct_change() * 100
    nifty_recent["ema9"] = calc_ema(nifty_recent["Close"], 9)
    nifty_recent["ema21"] = calc_ema(nifty_recent["Close"], 21)
    nifty_recent["rsi14"] = calc_rsi(nifty_recent["Close"], 14)
    nifty_recent["atr14"] = calc_atr(nifty_recent, 14)
    nifty_recent["atr_pct"] = nifty_recent["atr14"] / nifty_recent["Close"] * 100
    
    last = nifty_recent.iloc[-1]
    
    nifty_uptrend = last["Close"] > nifty_recent["ema9"].iloc[-1] > nifty_recent["ema21"].iloc[-1]
    nifty_rsi = last["rsi14"]
    nifty_atr = last["atr_pct"]
    
    print(f"\n  Current Nifty Regime:")
    print(f"    Close: {last['Close']:.2f}")
    print(f"    EMA9: {nifty_recent['ema9'].iloc[-1]:.2f}")
    print(f"    EMA21: {nifty_recent['ema21'].iloc[-1]:.2f}")
    print(f"    RSI(14): {nifty_rsi:.1f}")
    print(f"    ATR%: {nifty_atr:.2f}%")
    print(f"    Trend: {'UPTREND' if nifty_uptrend else 'NEUTRAL/DOWN'}")
    
    # Run filtered strategy on each stock using nifty conditions as additional filter
    filtered_results = []
    
    for i, sym in enumerate(NIFTY_50):
        name = clean_sym(sym)
        print(f"  [{i+1:2d}/50] {name:16s} ... ", end="", flush=True)
        
        df = fetch_data(sym, "3mo")
        if df is None or len(df) < 25:
            print("SKIP")
            continue
        
        test = df.tail(60)
        if len(test) < 20:
            print("SKIP")
            continue
        
        # Only take signals when nifty is in uptrend (above both EMAs)
        nifty_subset = nifty_recent.tail(len(test))
        
        trades = []
        for idx in range(20, len(test) - 2):
            row = test.iloc[idx]
            price = row["Close"]
            
            if price < 500:
                continue
            
            vol_today = row["Volume"]
            lookback_vol = test["Volume"].iloc[max(0, idx-10):idx]
            avg_vol = lookback_vol.mean() if len(lookback_vol) > 0 else 0
            if vol_today < 500_000 or avg_vol == 0:
                continue
            vol_surge = vol_today / avg_vol
            if vol_surge < 1.2:
                continue
            
            atr_series = calc_atr(df)
            lookback_atr = atr_series.iloc[len(df) - len(test) + idx]
            if np.isnan(lookback_atr) or (lookback_atr / price) < 0.010:
                continue
            
            close_series = test["Close"]
            ema9 = calc_ema(close_series, 9).iloc[idx]
            ema21 = calc_ema(close_series, 21).iloc[idx]
            if pd.isna(ema9) or pd.isna(ema21) or price < ema9 or price < ema21:
                continue
            
            # Nifty condition filter
            nifty_idx = min(idx, len(nifty_subset) - 1)
            if nifty_idx < 20:
                continue
            nifty_row = nifty_subset.iloc[nifty_idx]
            nifty_ema9 = nifty_subset["Close"].ewm(span=9, adjust=False).mean().iloc[nifty_idx]
            nifty_ema21 = nifty_subset["Close"].ewm(span=21, adjust=False).mean().iloc[nifty_idx]
            
            if pd.isna(nifty_ema9) or pd.isna(nifty_ema21):
                continue
            
            # ONLY take trades when Nifty is above both EMAs (bullish filter)
            if not (nifty_row["Close"] > nifty_ema9 and nifty_row["Close"] > nifty_ema21):
                continue
            
            entry = price
            sl = entry * 0.99
            target = entry * 1.02
            
            future = test.iloc[idx + 1: idx + 6]
            if len(future) == 0:
                continue
            
            exit_price = None
            exit_reason = "HOLD"
            for _, frow in future.iterrows():
                if frow["Low"] <= sl:
                    exit_price = sl
                    exit_reason = "SL_HIT"
                    break
                if frow["High"] >= target:
                    exit_price = target
                    exit_reason = "TARGET_HIT"
                    break
            
            if exit_price is None:
                exit_price = future.iloc[-1]["Close"]
                exit_reason = "TIME_EXIT"
            
            pnl = round(((exit_price - entry) / entry) * 100, 2)
            trades.append(pnl)
        
        if len(trades) >= 2:
            wins = sum(1 for t in trades if t > 0)
            total_pnl = sum(trades)
            win_rate = wins / len(trades) * 100
            filtered_results.append({
                "symbol": name,
                "trades": len(trades),
                "wins": wins,
                "losses": len(trades) - wins,
                "win_rate": round(win_rate, 1),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl": round(total_pnl / len(trades), 2),
            })
            print(f"{len(trades):2d} trades | WR {win_rate:5.1f}% | PnL {total_pnl:+.2f}%")
        else:
            print("insufficient signals")
    
    # Sort filtered results by win rate then total pnl
    filtered_results.sort(key=lambda x: (-x["win_rate"], -x["total_pnl"]))
    
    print(f"\n  ┌──────────────────────┬────────┬──────┬───────┬──────────┬──────────┐")
    print(f"  │ Stock                │ Trades │ Wins │ Loss  │ Win Rate │ Total PnL│")
    print(f"  ├──────────────────────┼────────┼──────┼───────┼──────────┼──────────┤")
    for r in filtered_results:
        wr_c = "4ade80" if r["win_rate"] >= 40 else "eab308" if r["win_rate"] >= 30 else "f87171"
        pnl_c = "4ade80" if r["total_pnl"] >= 0 else "f87171"
        print(f"  │ {r['symbol']:20s} │ {r['trades']:>4d}   │ {r['wins']:>3d}  │ {r['losses']:>4d} │ \033[38;2;{hex_to_rgb(wr_c)}m{r['win_rate']:>5.1f}%\033[0m  │ \033[38;2;{hex_to_rgb(pnl_c)}m{r['total_pnl']:>+7.2f}%\033[0m │")
    print(f"  └──────────────────────┴────────┴──────┴───────┴──────────┴──────────┘")
    
    total_trades = sum(r["trades"] for r in filtered_results)
    total_wins = sum(r["wins"] for r in filtered_results)
    total_pnl = sum(r["total_pnl"] for r in filtered_results)
    overall_wr = round(total_wins / total_trades * 100, 1) if total_trades > 0 else 0
    
    print(f"\n  OVERALL (Nifty-filtered strategy):")
    print(f"    Total trades: {total_trades}")
    print(f"    Win rate: {overall_wr}%")
    print(f"    Total PnL: {total_pnl:+.2f}%")
    
    return filtered_results


def hex_to_rgb(h):
    return f"{int(h[0:2], 16)};{int(h[2:4], 16)};{int(h[4:6], 16)}"


# ─── Phase 4: Final Stock Ranking ───

def rank_stocks(filtered_results):
    print(f"\n{'='*70}")
    print(f"  PHASE 4: FINAL STOCK RANKING")
    print(f"{'='*70}")
    
    # Score each stock: win_rate * 0.4 + (avg_pnl + 1) * 30 + total_trades_weight
    for r in filtered_results:
        consistency_bonus = 0
        if r["win_rate"] >= 40:
            consistency_bonus = 20
        elif r["win_rate"] >= 35:
            consistency_bonus = 10
        elif r["win_rate"] >= 30:
            consistency_bonus = 5
        
        r["score"] = round(
            r["win_rate"] * 0.4 + 
            (r["avg_pnl"] + 1) * 25 +
            min(r["trades"], 10) * 0.5 +
            consistency_bonus,
            1
        )
    
    ranked = sorted(filtered_results, key=lambda x: -x["score"])
    
    print(f"\n  ┌──────┬──────────────────────┬────────┬───────┬──────────┬──────────┬────────┐")
    print(f"  │ Rank │ Stock                │ Trades │ WR %  │ Avg PnL  │ Total    │ Score  │")
    print(f"  ├──────┼──────────────────────┼────────┼───────┼──────────┼──────────┼────────┤")
    for rank, r in enumerate(ranked[:20], 1):
        print(f"  │ {rank:>4d} │ {r['symbol']:20s} │ {r['trades']:>4d}   │ {r['win_rate']:>5.1f} │ {r['avg_pnl']:>+6.2f}% │ {r['total_pnl']:>+6.2f}% │ {r['score']:>6.1f} │")
    print(f"  └──────┴──────────────────────┴────────┴───────┴──────────┴──────────┴────────┘")
    
    return ranked


# ─── Phase 5: Generate Strategy Document ───

def generate_strategy(filtered_results, ranked, nifty_recent):
    print(f"\n{'='*70}")
    print(f"  PHASE 5: STRATEGY OUTPUT")
    print(f"{'='*70}")
    
    # Get top stocks
    top_10 = ranked[:10] if len(ranked) >= 10 else ranked
    safe_stocks = [r for r in ranked if r["win_rate"] >= 35][:10]
    
    # Nifty stats
    nifty_stats = {}
    if nifty_recent is not None:
        nifty_recent = nifty_recent.copy()
        nifty_recent["returns"] = nifty_recent["Close"].pct_change() * 100
        nifty_recent["ema9"] = calc_ema(nifty_recent["Close"], 9)
        nifty_recent["ema21"] = calc_ema(nifty_recent["Close"], 21)
        nifty_recent["rsi14"] = calc_rsi(nifty_recent["Close"], 14)
        nifty_recent["atr14"] = calc_atr(nifty_recent, 14)
        
        last = nifty_recent.iloc[-1]
        nifty_uptrend = last["Close"] > nifty_recent["ema9"].iloc[-1] > nifty_recent["ema21"].iloc[-1]
        
        nifty_stats = {
            "close": round(last["Close"], 2),
            "ema9": round(nifty_recent["ema9"].iloc[-1], 2),
            "ema21": round(nifty_recent["ema21"].iloc[-1], 2),
            "rsi": round(last["rsi14"], 1),
            "atr_pct": round(last["atr14"] / last["Close"] * 100, 2),
            "trend": "UPTREND" if nifty_uptrend else "NEUTRAL/DOWNTREND",
        }
    
    # Overall stats
    all_trades = sum(r["trades"] for r in filtered_results)
    all_wins = sum(r["wins"] for r in filtered_results)
    all_pnl = sum(r["total_pnl"] for r in filtered_results)
    overall_wr = round(all_wins / all_trades * 100, 1) if all_trades > 0 else 0
    
    strategy = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nifty_regime": nifty_stats,
        "overall": {
            "total_trades": all_trades,
            "win_rate": overall_wr,
            "total_pnl": round(all_pnl, 2),
        },
        "top_stocks_by_winrate": [{
            "symbol": r["symbol"],
            "win_rate": r["win_rate"],
            "trades": r["trades"],
            "avg_pnl": r["avg_pnl"],
            "total_pnl": r["total_pnl"],
        } for r in top_10],
        "safe_stocks": [{
            "symbol": r["symbol"],
            "win_rate": r["win_rate"],
            "trades": r["trades"],
        } for r in safe_stocks],
    }
    
    # Save JSON
    json_path = os.path.join(BASE_DIR, "strategy_results.json")
    with open(json_path, "w") as f:
        json.dump(strategy, f, indent=2)
    print(f"  Saved: {json_path}")
    
    return strategy


# ─── Main ───

def main():
    print(f"{'='*70}")
    print(f"  NIFTY 50 INTRADAY STRATEGY DEVELOPER")
    print(f"  Target: 1-2% profit · SL: 1% · Live data via yfinance")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    # Phase 1: Analyze Nifty 50 index
    nifty, nifty_recent = analyze_index()
    
    # Phase 2: Test on individual stocks
    stock_stats = stock_screener_analysis(nifty_recent)
    
    # Phase 3: Nifty-filtered strategy
    filtered_results = nifty_filtered_strategy(nifty_recent)
    
    # Phase 4: Rank stocks
    ranked = rank_stocks(filtered_results)
    
    # Phase 5: Generate strategy output
    strategy = generate_strategy(filtered_results, ranked, nifty_recent)
    
    print(f"\n{'='*70}")
    print(f"  STRATEGY ANALYSIS COMPLETE")
    print(f"  Results saved to: {os.path.join(BASE_DIR, 'strategy_results.json')}")
    print(f"{'='*70}")
    
    ns = strategy.get("nifty_regime", {})
    
    print(f"\n  ─── QUICK SUMMARY ───")
    
    if strategy["overall"]["total_trades"] > 0:
        print(f"  Nifty regime: {ns.get('trend', '?')} (RSI: {ns.get('rsi', '?')}, ATR: {ns.get('atr_pct', '?')}%)")
        print(f"  Overall win rate: {strategy['overall']['win_rate']}%")
        print(f"  Total PnL: {strategy['overall']['total_pnl']}%")
        print(f"  Total trades: {strategy['overall']['total_trades']}")
        has_profitable = sum(1 for r in filtered_results if r['total_pnl'] > 0)
        print(f"  Profitable stocks: {has_profitable}/{len(filtered_results)}")
        
        if ns.get("trend") == "UPTREND":
            print(f"\n  ✅ Nifty is in UPTREND — long trades with 1% SL / 2% target")
        else:
            print(f"\n  ⚠️  Nifty is NOT in uptrend — be selective, prefer defensive stocks")
        
        print(f"\n  Top picks (win rate > 35%):")
        for r in strategy["safe_stocks"][:5]:
            print(f"    {r['symbol']:20s} — WR: {r['win_rate']:.1f}% ({r['trades']} trades)")
    else:
        print("  No data available. Try running during market hours.")
    
    print()


if __name__ == "__main__":
    main()
