#!/usr/bin/env python3
"""
Independent Strategy Discovery Engine
======================================
No assumptions. No inherited bias. Just raw data analysis.
Tests simple "obvious" strategies on real intraday data to find what actually works.

Usage:
    python find_strategy.py
"""

import sys, json, os, io, warnings
from datetime import datetime, timedelta, date
from collections import defaultdict
from itertools import product

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import re

warnings.filterwarnings("ignore", category=FutureWarning)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

# TATAMOTORS.NS excluded — delisted from Yahoo

TRADING_DAYS = 60  # Look back period

def clean_sym(s):
    return s.replace(".NS", "")

def calc_ema(s, p):
    return s.ewm(span=p, adjust=False).mean()


# ─── Web helper: fetch VIX and market data ───

def fetch_vix():
    try:
        vix = yf.download("^INDIAVIX", period="1mo", progress=False)
        if not vix.empty:
            return round(vix["Close"].iloc[-1], 2)
    except:
        pass
    return None


# ─── Daily data fetcher ───

def fetch_daily(symbol, period="3mo"):
    df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
    if df.empty or len(df) < 20:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.name = symbol
    return df


def fetch_intraday(symbol):
    """Fetch 5-min intraday data for last 30 trading days."""
    try:
        df = yf.download(symbol, period="1mo", interval="5m", progress=False, auto_adjust=True)
        if df.empty or len(df) < 78:
            df = yf.download(symbol, period="2mo", interval="5m", progress=False, auto_adjust=True)
        if df.empty or len(df) < 78:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.name = symbol
        return df
    except:
        return None


# ════════════════════════════════════════════════════════════════
# STRATEGY 1: Opening Range Breakout (ORB)
# ════════════════════════════════════════════════════════════════

def test_orb_strategy(df, range_minutes=15, sl_pct=0.01, target_pct=0.02):
    """
    Classic ORB: Take the high/low of first N minutes.
    If price breaks above high → long.
    If price breaks below low → short.
    """
    if df is None or len(df) < 20:
        return None

    # Group by trading day
    df = df.copy()
    df["date"] = df.index.date
    results = []

    for day, day_data in df.groupby("date"):
        day_data = day_data.sort_index()
        if len(day_data) < 13:
            continue

        # First N minutes of data (each candle = 5 min)
        range_candles = max(1, range_minutes // 5)
        opening_range = day_data.iloc[:range_candles]
        if opening_range.empty:
            continue

        range_high = opening_range["High"].max()
        range_low = opening_range["Low"].min()
        range_close = opening_range["Close"].iloc[-1]

        # Test both directions
        for direction, break_level in [("LONG", range_high), ("SHORT", range_low)]:
            entry_candle = None
            for idx in range(range_candles, len(day_data)):
                candle = day_data.iloc[idx]
                if direction == "LONG" and candle["High"] > break_level:
                    entry_candle = candle
                    entry_price = break_level
                    break
                elif direction == "SHORT" and candle["Low"] < break_level:
                    entry_candle = candle
                    entry_price = break_level
                    break

            if entry_candle is None:
                continue

            sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
            tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

            # Look for exit in subsequent candles
            exit_idx = day_data.index.get_loc(entry_candle.name)
            remaining = day_data.iloc[exit_idx + 1:]
            exit_price = None
            exit_reason = "TIME_EXIT"

            for _, candle in remaining.iterrows():
                if direction == "LONG":
                    if candle["Low"] <= sl:
                        exit_price = sl
                        exit_reason = "SL_HIT"
                        break
                    if candle["High"] >= tgt:
                        exit_price = tgt
                        exit_reason = "TARGET_HIT"
                        break
                else:
                    if candle["High"] >= sl:
                        exit_price = sl
                        exit_reason = "SL_HIT"
                        break
                    if candle["Low"] <= tgt:
                        exit_price = tgt
                        exit_reason = "TARGET_HIT"
                        break

            if exit_price is None:
                exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

            pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
            if direction == "SHORT":
                pnl_pct = -pnl_pct

            results.append({
                "date": str(day),
                "direction": direction,
                "entry": round(entry_price, 2),
                "sl": round(sl, 2),
                "target": round(tgt, 2),
                "exit_price": round(exit_price, 2),
                "result": exit_reason,
                "pnl": pnl_pct,
            })

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 2: Gap Mean Reversion
# ════════════════════════════════════════════════════════════════

def test_gap_strategy(df, gap_pct=0.005, sl_pct=0.01, target_pct=0.015):
    """
    If stock gaps up > gap_pct% at open, short it (reversion to fill gap).
    If gaps down > gap_pct%, go long.
    Rationale: Most gaps get filled intraday.
    """
    if df is None or len(df) < 10:
        return None

    df = df.copy()
    df["date"] = df.index.date
    results = []

    for day, day_data in df.groupby("date"):
        day_data = day_data.sort_index()
        if len(day_data) < 10:
            continue

        # Get the gap: compare previous close (last candle of previous day isn't available)
        # Approximation: use first candle open vs previous day's close
        first_candle = day_data.iloc[0]
        if len(day_data) < 2:
            continue

        open_price = first_candle["Open"]
        close_prev = first_candle["Close"]  # approximation

        # Better: check if the first candle's open is significantly different
        # We'll use the first 5-min candle's close as reference for "yesterday's close"
        # Actually for gap, compare today's open to yesterday's close
        # yfinance intraday data groups by date, so the first candle of each day
        # has the open price. The previous day's close would be the last candle's close
        # of the previous group.

        gap = (open_price - close_prev) / close_prev

        if abs(gap) < gap_pct:
            continue  # No significant gap

        direction = "LONG" if gap < 0 else "SHORT"  # Reverse the gap
        entry_price = open_price
        sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
        tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

        remaining = day_data.iloc[1:]
        exit_price = None
        exit_reason = "TIME_EXIT"

        for _, candle in remaining.iterrows():
            if direction == "LONG":
                if candle["Low"] <= sl:
                    exit_price = sl; exit_reason = "SL_HIT"; break
                if candle["High"] >= tgt:
                    exit_price = tgt; exit_reason = "TARGET_HIT"; break
            else:
                if candle["High"] >= sl:
                    exit_price = sl; exit_reason = "SL_HIT"; break
                if candle["Low"] <= tgt:
                    exit_price = tgt; exit_reason = "TARGET_HIT"; break

        if exit_price is None:
            exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

        pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
        if direction == "SHORT": pnl_pct = -pnl_pct

        results.append({
            "date": str(day),
            "direction": direction,
            "gap_pct": round(gap * 100, 2),
            "entry": round(entry_price, 2),
            "sl": round(sl, 2),
            "target": round(tgt, 2),
            "result": exit_reason,
            "pnl": pnl_pct,
        })

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 3: Previous Day High/Low Breakout
# ════════════════════════════════════════════════════════════════

def test_pdhl_strategy(df, sl_pct=0.01, target_pct=0.02):
    """
    Breakout of previous day's high or low.
    If today's price breaks above yesterday's high → long.
    If today's price breaks below yesterday's low → short.
    One of the oldest breakout strategies.
    """
    if df is None or len(df) < 20:
        return None

    df = df.copy()
    df["date"] = df.index.date

    # Calculate daily levels
    daily = df.groupby("date").agg({
        "High": "max", "Low": "min", "Close": "last", "Open": "first"
    })

    results = []
    for i in range(1, len(daily)):
        prev = daily.iloc[i - 1]
        today_date = daily.index[i]
        today_data = df[df["date"] == today_date]

        if len(today_data) < 5:
            continue

        prev_high = prev["High"]
        prev_low = prev["Low"]

        for direction, break_level in [("LONG", prev_high), ("SHORT", prev_low)]:
            entry_candle = None
            for idx in range(len(today_data)):
                candle = today_data.iloc[idx]
                if direction == "LONG" and candle["High"] > break_level:
                    entry_candle = candle; entry_price = break_level; break
                elif direction == "SHORT" and candle["Low"] < break_level:
                    entry_candle = candle; entry_price = break_level; break

            if entry_candle is None:
                continue

            sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
            tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

            entry_idx = today_data.index.get_loc(entry_candle.name)
            remaining = today_data.iloc[entry_idx + 1:]
            exit_price = None; exit_reason = "TIME_EXIT"

            for _, candle in remaining.iterrows():
                if direction == "LONG":
                    if candle["Low"] <= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if candle["High"] >= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break
                else:
                    if candle["High"] >= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if candle["Low"] <= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break

            if exit_price is None:
                exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

            pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
            if direction == "SHORT": pnl_pct = -pnl_pct

            results.append({
                "date": str(today_date),
                "direction": direction,
                "entry": round(entry_price, 2),
                "sl": round(sl, 2),
                "target": round(tgt, 2),
                "result": exit_reason,
                "pnl": pnl_pct,
            })

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 4: VWAP Deviation Mean Reversion
# ════════════════════════════════════════════════════════════════

def test_vwap_strategy(df, deviation_pct=0.008, sl_pct=0.01, target_pct=0.012):
    """
    When price deviates too far from VWAP, it tends to revert.
    Go long when price < VWAP - deviation.
    Go short when price > VWAP + deviation.
    """
    if df is None or len(df) < 15:
        return None

    df = df.copy()
    df["date"] = df.index.date
    results = []

    for day, day_data in df.groupby("date"):
        day_data = day_data.sort_index()
        if len(day_data) < 10:
            continue

        # Calculate VWAP
        cum_pv = (day_data["High"] + day_data["Low"] + day_data["Close"]) / 3 * day_data["Volume"]
        cum_v = day_data["Volume"]
        day_data["vwap"] = cum_pv.cumsum() / cum_v.cumsum()

        for idx in range(2, len(day_data)):
            candle = day_data.iloc[idx]
            vwap = day_data["vwap"].iloc[idx]
            price = candle["Close"]
            deviation = (price - vwap) / vwap

            if abs(deviation) < deviation_pct:
                continue

            direction = "LONG" if deviation < 0 else "SHORT"
            entry_price = price
            sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
            tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

            remaining = day_data.iloc[idx + 1:]
            exit_price = None; exit_reason = "TIME_EXIT"
            for _, c in remaining.iterrows():
                if direction == "LONG":
                    if c["Low"] <= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["High"] >= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break
                else:
                    if c["High"] >= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["Low"] <= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break

            if exit_price is None:
                exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

            pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
            if direction == "SHORT": pnl_pct = -pnl_pct

            results.append({
                "date": str(day),
                "direction": direction,
                "deviation_pct": round(deviation * 100, 2),
                "entry": round(entry_price, 2),
                "result": exit_reason,
                "pnl": pnl_pct,
            })

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 5: Time-Based Momentum (First Hour Direction)
# ════════════════════════════════════════════════════════════════

def test_time_momentum(df, lookback_minutes=60, hold_minutes=120):
    """
    If the stock moves up in the first hour, continue holding for next 2 hours.
    Simple time-based momentum. The market's first hour sets the tone.
    """
    if df is None or len(df) < 20:
        return None

    df = df.copy()
    df["date"] = df.index.date
    results = []

    for day, day_data in df.groupby("date"):
        day_data = day_data.sort_index()
        if len(day_data) < lookback_minutes // 5 + hold_minutes // 5:
            continue

        lookback_candles = lookback_minutes // 5
        first_hour = day_data.iloc[:lookback_candles]
        if len(first_hour) < lookback_candles // 2:
            continue

        open_price = first_hour["Open"].iloc[0]
        close_first_hour = first_hour["Close"].iloc[-1]
        first_hour_move = (close_first_hour - open_price) / open_price

        if abs(first_hour_move) < 0.003:
            continue  # No clear direction

        direction = "LONG" if first_hour_move > 0 else "SHORT"
        entry_price = close_first_hour
        sl = entry_price * (1 - 0.01) if direction == "LONG" else entry_price * (1 + 0.01)
        tgt = entry_price * (1 + 0.015) if direction == "LONG" else entry_price * (1 - 0.015)

        remaining = day_data.iloc[lookback_candles:lookback_candles + (hold_minutes // 5)]
        if remaining.empty:
            continue

        exit_price = None; exit_reason = "TIME_EXIT"
        for _, c in remaining.iterrows():
            if direction == "LONG":
                if c["Low"] <= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                if c["High"] >= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break
            else:
                if c["High"] >= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                if c["Low"] <= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break

        if exit_price is None:
            exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

        pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
        if direction == "SHORT": pnl_pct = -pnl_pct

        results.append({
            "date": str(day),
            "direction": direction,
            "first_hour_move": round(first_hour_move * 100, 2),
            "entry": round(entry_price, 2),
            "result": exit_reason,
            "pnl": pnl_pct,
        })

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 6: 10:15 AM Reversal (Anti-ORB)
# ════════════════════════════════════════════════════════════════

def test_reversal_strategy(df, sl_pct=0.01, target_pct=0.015):
    """
    The "10 AM Reversal" — after the first 45-60 min, the market often reverses
    its initial direction. If first 45 min were up, go short. If down, go long.
    """
    if df is None or len(df) < 20:
        return None

    df = df.copy()
    df["date"] = df.index.date
    results = []

    for day, day_data in df.groupby("date"):
        day_data = day_data.sort_index()
        if len(day_data) < 20:
            continue

        # First 9 candles = 45 min
        first_45 = day_data.iloc[:9]
        if len(first_45) < 5:
            continue

        open_p = first_45["Open"].iloc[0]
        close_45 = first_45["Close"].iloc[-1]
        initial_move = (close_45 - open_p) / open_p

        if abs(initial_move) < 0.004:
            continue

        # Reverse
        direction = "SHORT" if initial_move > 0 else "LONG"
        entry_price = close_45
        sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
        tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

        remaining = day_data.iloc[9:25]  # next ~80 min
        if remaining.empty:
            continue

        exit_price = None; exit_reason = "TIME_EXIT"
        for _, c in remaining.iterrows():
            if direction == "LONG":
                if c["Low"] <= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                if c["High"] >= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break
            else:
                if c["High"] >= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                if c["Low"] <= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break

        if exit_price is None:
            exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

        pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
        if direction == "SHORT": pnl_pct = -pnl_pct

        results.append({
            "date": str(day),
            "direction": direction,
            "first_45_move": round(initial_move * 100, 2),
            "entry": round(entry_price, 2),
            "result": exit_reason,
            "pnl": pnl_pct,
        })

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 7: Nifty Relative Strength
# ════════════════════════════════════════════════════════════════

# We'll compute this separately — compare stock performance vs Nifty intraday


# ════════════════════════════════════════════════════════════════
# STRATEGY 8: Simple 5-Min SMA Crossover
# ════════════════════════════════════════════════════════════════

def test_sma_crossover(df, fast=3, slow=8, sl_pct=0.01, target_pct=0.015):
    """
    Simplest possible: when fast SMA crosses above slow SMA → long.
    When fast crosses below → short.
    """
    if df is None or len(df) < 30:
        return None

    df = df.copy()
    df["date"] = df.index.date
    df["sma_fast"] = df["Close"].rolling(fast).mean()
    df["sma_slow"] = df["Close"].rolling(slow).mean()
    df["prev_fast"] = df["sma_fast"].shift(1)
    df["prev_slow"] = df["sma_slow"].shift(1)
    results = []

    for day, day_data in df.groupby("date"):
        day_data = day_data.sort_index()
        if len(day_data) < 15:
            continue

        for idx in range(slow + 1, len(day_data)):
            candle = day_data.iloc[idx]

            # Detect crossover
            prev_f = day_data["prev_fast"].iloc[idx]
            prev_s = day_data["prev_slow"].iloc[idx]
            curr_f = day_data["sma_fast"].iloc[idx]
            curr_s = day_data["sma_slow"].iloc[idx]

            if pd.isna(prev_f) or pd.isna(prev_s) or pd.isna(curr_f) or pd.isna(curr_s):
                continue

            if prev_f <= prev_s and curr_f > curr_s:
                direction = "LONG"
            elif prev_f >= prev_s and curr_f < curr_s:
                direction = "SHORT"
            else:
                continue

            entry_price = candle["Close"]
            sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
            tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

            remaining = day_data.iloc[idx + 1:]
            if remaining.empty:
                continue

            exit_price = None; exit_reason = "TIME_EXIT"
            for _, c in remaining.iterrows():
                if direction == "LONG":
                    if c["Low"] <= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["High"] >= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break
                else:
                    if c["High"] >= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["Low"] <= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break

            if exit_price is None:
                exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

            pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
            if direction == "SHORT": pnl_pct = -pnl_pct

            results.append({
                "date": str(day),
                "direction": direction,
                "entry": round(entry_price, 2),
                "result": exit_reason,
                "pnl": pnl_pct,
            })
            break  # Only first signal per day

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 9: Nifty Index Relative Strength (Stock vs Nifty)
# ════════════════════════════════════════════════════════════════

def test_relative_strength(stock_df, nifty_df, sl_pct=0.01, target_pct=0.015):
    """
    If stock is outperforming Nifty intraday (by X%), go long the stock.
    If stock is underperforming, go short.
    Mean reversion of the spread.
    """
    if stock_df is None or nifty_df is None:
        return None
    if len(stock_df) < 20 or len(nifty_df) < 20:
        return None

    s = stock_df.copy()
    n = nifty_df.copy()
    s["date"] = s.index.date
    n["date"] = n.index.date
    results = []

    for day in set(s["date"]).intersection(set(n["date"])):
        sd = s[s["date"] == day].sort_index()
        nd = n[n["date"] == day].sort_index()

        if len(sd) < 10 or len(nd) < 10:
            continue

        # Align by common time index
        common_idx = sd.index.intersection(nd.index)
        sd = sd.loc[common_idx]
        nd = nd.loc[common_idx]

        # Calculate relative performance from open
        s_open = sd["Open"].iloc[0]
        n_open = nd["Open"].iloc[0]
        sd["rel_strength"] = (sd["Close"] / s_open) - (nd["Close"] / n_open)

        for idx in range(3, len(sd)):
            rel = sd["rel_strength"].iloc[idx]
            if abs(rel) < 0.005:
                continue

            direction = "LONG" if rel < 0 else "SHORT"  # Reversion: if stock weak, buy (expect catch-up)
            entry_price = sd["Close"].iloc[idx]

            sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
            tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

            remaining = sd.iloc[idx + 1:]
            if remaining.empty:
                continue

            exit_price = None; exit_reason = "TIME_EXIT"
            for _, c in remaining.iterrows():
                if direction == "LONG":
                    if c["Low"] <= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["High"] >= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break
                else:
                    if c["High"] >= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["Low"] <= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break

            if exit_price is None:
                exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

            pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
            if direction == "SHORT": pnl_pct = -pnl_pct

            results.append({
                "date": str(day),
                "direction": direction,
                "rel_strength": round(rel * 100, 2),
                "entry": round(entry_price, 2),
                "result": exit_reason,
                "pnl": pnl_pct,
            })
            break  # One signal per day per stock

    return results if results else None


# ════════════════════════════════════════════════════════════════
# STRATEGY 10: Nifty Trend Following on Stocks
# ════════════════════════════════════════════════════════════════

def test_nifty_trend_strategy(stock_df, nifty_df, sl_pct=0.01, target_pct=0.02, lb=3):
    """
    Simplest thing in the world: if Nifty is up X% in last N candles,
    buy all stocks. If Nifty is down, short all stocks.
    "The tide lifts all boats."
    """
    from itertools import product

    if stock_df is None or nifty_df is None:
        return None

    s = stock_df.copy()
    n = nifty_df.copy()
    s["date"] = s.index.date
    n["date"] = n.index.date
    results = []

    for day in set(s["date"]).intersection(set(n["date"])):
        sd = s[s["date"] == day].sort_index()
        nd = n[n["date"] == day].sort_index()

        if len(sd) < lb + 5 or len(nd) < lb + 5:
            continue

        common_idx = sd.index.intersection(nd.index)
        sd = sd.loc[common_idx]
        nd = nd.loc[common_idx]

        for idx in range(lb, len(sd) - 2):
            nifty_move = (nd["Close"].iloc[idx] - nd["Close"].iloc[idx - lb]) / nd["Close"].iloc[idx - lb]

            if abs(nifty_move) < 0.003:
                continue

            direction = "LONG" if nifty_move > 0 else "SHORT"
            entry_price = sd["Close"].iloc[idx]

            sl = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
            tgt = entry_price * (1 + target_pct) if direction == "LONG" else entry_price * (1 - target_pct)

            remaining = sd.iloc[idx + 1:]
            if remaining.empty:
                continue

            exit_price = None; exit_reason = "TIME_EXIT"
            for _, c in remaining.iterrows():
                if direction == "LONG":
                    if c["Low"] <= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["High"] >= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break
                else:
                    if c["High"] >= sl: exit_price = sl; exit_reason = "SL_HIT"; break
                    if c["Low"] <= tgt: exit_price = tgt; exit_reason = "TARGET_HIT"; break

            if exit_price is None:
                exit_price = remaining.iloc[-1]["Close"] if not remaining.empty else entry_price

            pnl_pct = round(((exit_price - entry_price) / entry_price) * 100, 2)
            if direction == "SHORT": pnl_pct = -pnl_pct

            results.append({
                "date": str(day),
                "direction": direction,
                "nifty_move_pct": round(nifty_move * 100, 2),
                "entry": round(entry_price, 2),
                "result": exit_reason,
                "pnl": pnl_pct,
            })
            break

    return results if results else None


# ════════════════════════════════════════════════════════════════
# RUN ALL STRATEGIES
# ════════════════════════════════════════════════════════════════

def analyze_results(results_list, strategy_name):
    """Compute stats for a list of trade results."""
    if not results_list:
        return None

    total = len(results_list)
    wins = sum(1 for r in results_list if r["pnl"] > 0)
    losses = total - wins
    win_rate = round(wins / total * 100, 1)
    total_pnl = round(sum(r["pnl"] for r in results_list), 2)
    avg_pnl = round(total_pnl / total, 2)
    avg_win = round(sum(r["pnl"] for r in results_list if r["pnl"] > 0) / max(wins, 1), 2)
    avg_loss = round(sum(r["pnl"] for r in results_list if r["pnl"] <= 0) / max(losses, 1), 2)
    max_win = max(r["pnl"] for r in results_list)
    max_loss = min(r["pnl"] for r in results_list)

    gross_w = sum(r["pnl"] for r in results_list if r["pnl"] > 0)
    gross_l = abs(sum(r["pnl"] for r in results_list if r["pnl"] < 0))
    pf = round(gross_w / gross_l, 2) if gross_l > 0 else float("inf")

    exit_reasons = defaultdict(int)
    for r in results_list:
        exit_reasons[r["result"]] += 1

    # Consecutive losses
    max_consec = 0
    cur = 0
    for r in results_list:
        if r["pnl"] <= 0:
            cur += 1
            max_consec = max(max_consec, cur)
        else:
            cur = 0

    return {
        "strategy": strategy_name,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "avg_pnl": avg_pnl,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_win": max_win,
        "max_loss": max_loss,
        "profit_factor": pf,
        "max_consec_losses": max_consec,
        "exit_breakdown": dict(exit_reasons),
    }


def test_strategies_on_stock(symbol, nifty_intraday=None):
    """Run all strategies on one stock and return best result."""
    name = clean_sym(symbol)
    df = fetch_intraday(symbol)
    if df is None:
        return None

    strategies = {}

    # Strategy 1: ORB with various range minutes
    for mins in [15, 30, 45, 60]:
        r = test_orb_strategy(df, range_minutes=mins)
        if r:
            strategies[f"ORB_{mins}min"] = r

    # Strategy 2: Gap mean reversion
    for gap in [0.003, 0.005, 0.008]:
        r = test_gap_strategy(df, gap_pct=gap)
        if r:
            strategies[f"GapReversal_{int(gap*1000)}bp"] = r

    # Strategy 3: Prev day high/low breakout
    r = test_pdhl_strategy(df)
    if r:
        strategies["PDHL_Breakout"] = r

    # Strategy 5: Time momentum
    for lb in [30, 45, 60]:
        r = test_time_momentum(df, lookback_minutes=lb)
        if r:
            strategies[f"TimeMom_{lb}min"] = r

    # Strategy 6: Reversal
    r = test_reversal_strategy(df)
    if r:
        strategies["10AM_Reversal"] = r

    # Strategy 8: SMA crossover
    for f, s in [(3, 8), (5, 13), (3, 13)]:
        r = test_sma_crossover(df, fast=f, slow=s)
        if r:
            strategies[f"SMA_{f}x{s}"] = r

    # Strategy 9: Relative strength vs nifty
    if nifty_intraday is not None:
        r = test_relative_strength(df, nifty_intraday)
        if r:
            strategies["RelStrength_Nifty"] = r

        r = test_nifty_trend_strategy(df, nifty_intraday)
        if r:
            strategies["NiftyTrend"] = r

    # Analyze all
    results = {}
    for sname, trades in strategies.items():
        stats = analyze_results(trades, sname)
        if stats and stats["total_trades"] >= 2:
            results[sname] = stats

    return results, df


def main():
    print(f"{'='*72}")
    print(f"  INDEPENDENT STRATEGY DISCOVERY ENGINE")
    print(f"  No inherited bias · Pure data analysis · Real intraday data")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*72}")

    # Fetch VIX
    vix_raw = fetch_vix()
    vix = float(vix_raw.iloc[-1]) if hasattr(vix_raw, 'iloc') else vix_raw
    print(f"\n  India VIX: {vix}")

    # Fetch Nifty intraday once for relative strategies
    print(f"\n  Fetching Nifty 50 intraday data...")
    nifty_intraday = fetch_intraday("^NSEI")

    # Track best overall strategy
    all_strategy_results = defaultdict(list)
    stock_best_strategies = {}
    stock_trade_counts = defaultdict(int)

    for i, sym in enumerate(NIFTY_50):
        name = clean_sym(sym)
        print(f"\n  [{i+1:2d}/50] {name:16s} ... ", end="", flush=True)

        result = test_strategies_on_stock(sym, nifty_intraday)
        if result is None:
            print("NO DATA")
            continue

        strategies, df = result
        if not strategies:
            print("no signals")
            continue

        # Find best for this stock
        best = max(strategies.values(), key=lambda x: (x["win_rate"] * 0.4 + x["total_pnl"] * 3 + x["profit_factor"] * 5))
        stock_best_strategies[name] = {
            "best_strategy": best["strategy"],
            "win_rate": best["win_rate"],
            "total_pnl": best["total_pnl"],
            "trades": best["total_trades"],
            "profit_factor": best["profit_factor"],
        }

        # Aggregate all
        for sname, stats in strategies.items():
            all_strategy_results[sname].append(stats)

        print(f"{best['strategy']:18s} WR={best['win_rate']:5.1f}% PnL={best['total_pnl']:+.2f}%")

    # ── Overall strategy ranking ──
    print(f"\n{'='*72}")
    print(f"  OVERALL STRATEGY RANKING")
    print(f"{'='*72}")

    combined = []
    for sname, results_list in all_strategy_results.items():
        total_trades = sum(r["total_trades"] for r in results_list)
        total_wins = sum(r["wins"] for r in results_list)
        total_pnl = sum(r["total_pnl"] for r in results_list)

        if total_trades < 10:
            continue

        win_rate = round(total_wins / total_trades * 100, 1)
        avg_pnl = round(total_pnl / len(results_list), 2)

        gross_w = sum(r["avg_win"] * r["wins"] for r in results_list)
        gross_l = sum(abs(r["avg_loss"]) * r["losses"] for r in results_list)
        pf = round(gross_w / gross_l, 2) if gross_l > 0 else float("inf")

        stocks_with = len(results_list)

        combined.append({
            "strategy": sname,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl_per_stock": avg_pnl,
            "profit_factor": pf,
            "stocks_with_signals": stocks_with,
        })

    combined.sort(key=lambda x: (-x["win_rate"], -x["total_pnl"]))

    print(f"\n  ┌──────────────────────────┬──────────┬────────┬──────────┬───────┬──────────┐")
    print(f"  │ Strategy                 │ Trades   │ Win %  │ Total PnL│ PF    │ Stocks   │")
    print(f"  ├──────────────────────────┼──────────┼────────┼──────────┼───────┼──────────┤")

    for r in combined[:15]:
        print(f"  │ {r['strategy']:24s} │ {r['total_trades']:>6d}   │ {r['win_rate']:>5.1f}% │ {r['total_pnl']:>+7.2f}% │ {r['profit_factor']:>4.1f}  │ {r['stocks_with_signals']:>3d}    │")

    print(f"  └──────────────────────────┴──────────┴────────┴──────────┴───────┴──────────┘")

    # ── Best strategy deep dive ──
    if combined:
        best_overall = combined[0]
        print(f"\n{'='*72}")
        print(f"  WINNER: {best_overall['strategy']}")
        print(f"  Trades: {best_overall['total_trades']} | Win Rate: {best_overall['win_rate']}%")
        print(f"  Total PnL: {best_overall['total_pnl']:+.2f}% | Profit Factor: {best_overall['profit_factor']}")
        print(f"  Works on: {best_overall['stocks_with_signals']}/{len(NIFTY_50)} stocks")
        print(f"{'='*72}")

    # ── Top performing stocks with their best strategy ──
    print(f"\n{'='*72}")
    print(f"  TOP STOCKS WITH THEIR BEST STRATEGY")
    print(f"{'='*72}")

    sorted_stocks = sorted(stock_best_strategies.items(), key=lambda x: (-x[1]["win_rate"], -x[1]["total_pnl"]))

    print(f"\n  ┌──────────────────────┬────────────────────┬────────┬──────────┬───────┐")
    print(f"  │ Stock                │ Best Strategy      │ Trades │ Win %    │ PnL   │")
    print(f"  ├──────────────────────┼────────────────────┼────────┼──────────┼───────┤")

    for name, data in sorted_stocks:
        if data["trades"] < 2:
            continue
        print(f"  │ {name:20s} │ {data['best_strategy']:18s} │ {data['trades']:>4d}   │ {data['win_rate']:>5.1f}%  │ {data['total_pnl']:>+5.2f}% │")

    print(f"  └──────────────────────┴────────────────────┴────────┴──────────┴───────┘")

    # ── Output final strategy ──
    print(f"\n{'='*72}")
    print(f"  FINAL STRATEGY RECOMMENDATION")
    print(f"{'='*72}")

    if combined:
        winner = combined[0]
        strat_name = winner["strategy"]
        print(f"\n  >>> {strat_name}")

        # Decode strategy from name
        if "ORB" in strat_name:
            print(f"  >>> OPENING RANGE BREAKOUT")
            print(f"  >>> Range: {strat_name.split('_')[1]}")
            print(f"  >>> SL: 1% | Target: 1.5-2%")
            print(f"  >>> Entry: First {strat_name.split('_')[1]} high/low breakout")
            print(f"  >>> Direction: LONG on high break, SHORT on low break")
            print(f"  >>> Best for: Trending days with high volume")
        elif "Gap" in strat_name:
            print(f"  >>> GAP MEAN REVERSION")
            print(f"  >>> Entry: After gap {'>'+strat_name.split('_')[1] if len(strat_name.split('_'))>1 else '>0.5%'} at open")
            print(f"  >>> Direction: Reverse the gap (gap up = short, gap down = long)")
            print(f"  >>> SL: 1% | Target: 1.5%")
            print(f"  >>> Rationale: Most gaps get filled intraday")
        elif "PDHL" in strat_name:
            print(f"  >>> PREVIOUS DAY HIGH/LOW BREAKOUT")
            print(f"  >>> Entry: Break of prev day high/low")
            print(f"  >>> SL: 1% | Target: 2%")
        elif "TimeMom" in strat_name:
            print(f"  >>> TIME-BASED MOMENTUM")
            print(f"  >>> Lookback: {strat_name.split('_')[1]}")
            print(f"  >>> Follow first hour direction for next 2 hours")
            print(f"  >>> SL: 1% | Target: 1.5%")
        elif "Reversal" in strat_name:
            print(f"  >>> 10 AM REVERSAL")
            print(f"  >>> After 45 min, fade the initial move")
            print(f"  >>> SL: 1% | Target: 1.5%")
        elif "SMA" in strat_name:
            print(f"  >>> SMA CROSSOVER")
            parts = strat_name.split("_")[1].split("x")
            print(f"  >>> Fast SMA: {parts[0]} | Slow SMA: {parts[1]}")
            print(f"  >>> Entry: Crossover on 5-min chart")
            print(f"  >>> SL: 1% | Target: 1.5%")
        elif "RelStrength" in strat_name:
            print(f"  >>> RELATIVE STRENGTH vs NIFTY")
            print(f"  >>> Entry: Stock deviates from Nifty by >0.5%")
            print(f"  >>> Direction: Reversion to the mean")
        elif "NiftyTrend" in strat_name:
            print(f"  >>> NIFTY TREND FOLLOWING")
            print(f"  >>> Entry: Nifty moves >0.3% in last 3 candles")
            print(f"  >>> Direction: Same as Nifty")
            print(f"  >>> 'The tide lifts all boats'")

        print(f"\n  >>> PERFORMANCE: {winner['win_rate']}% win rate | {winner['total_pnl']:+.2f}% total PnL")
        print(f"  >>> Based on {winner['total_trades']} trades across {winner['stocks_with_signals']} Nifty 50 stocks")
        print(f"  >>> Profit Factor: {winner['profit_factor']}")

    # ── Save results ──
    output = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vix": vix,
        "strategy_ranking": combined[:20],
        "stock_best_strategies": {k: v for k, v in sorted_stocks if v["trades"] >= 2},
        "winner": combined[0] if combined else None,
    }

    out_path = os.path.join(BASE_DIR, "strategy_discovery.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Full results saved: {out_path}")
    print()


if __name__ == "__main__":
    main()
