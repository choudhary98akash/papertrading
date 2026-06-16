# Pure Data Findings

> No strategy. No bias. No interpretation. Just what the data says.
> Source: Real yfinance data for 49 Nifty 50 stocks, Mar 16 – Jun 15 2026 (62 trading days, 2,988 observations)

---

## 1. The Day-of-Week Effect (Strongest Signal in the Data)

| Day | Avg Return | % Positive | Personality |
|-----|-----------|-----------|-------------|
| Monday | **−0.283%** | 45.4% | Weak, bearish |
| Tuesday | **+0.180%** | 53.8% | Mildly bullish |
| **Wednesday** | **+0.798%** | **65.0%** | **Strongly bullish** |
| **Thursday** | **−0.280%** | **37.6%** | **Strongly bearish** |
| Friday | −0.046% | 45.8% | Neutral, weak |

Wednesday is the outlier: stocks go up 65% of the time, averaging +0.80%.
Thursday is the mirror: stocks go down 62.4% of the time.
The swing between Wednesday and Thursday is **1.08%** — the largest predictable pattern in the dataset.

---

## 2. Gap Size vs Fill Rate (Monotonic Relationship)

| Gap Range | Events | Filled | Fill Rate |
|-----------|--------|--------|-----------|
| 0.0–0.3% | 1,073 | 975 | 90.9% |
| 0.3–0.5% | 436 | 324 | 74.3% |
| 0.5–0.8% | 482 | 312 | 64.7% |
| 0.8–1.2% | 448 | 220 | 49.1% |
| 1.2–2.0% | 365 | 128 | 35.1% |
| 2.0–5.0% | 172 | 44 | 25.6% |
| >5.0% | 12 | 1 | 8.3% |

The relationship is clean and monotonic: **smaller gaps fill more often, larger gaps fill less often.** There is no threshold where this reverses — every step up in gap size reduces fill probability.

---

## 3. Gap Fill Rate by Day of Week

| Day | Gaps | Filled | Fill Rate |
|-----|------|--------|-----------|
| Monday | 637 | 363 | 57.0% |
| **Tuesday** | **539** | **418** | **77.6%** |
| Wednesday | 637 | 390 | 61.2% |
| Thursday | 588 | 412 | 70.1% |
| Friday | 587 | 421 | 71.7% |

Tuesday is the best day for gap fills (77.6%). Monday is the worst (57.0%).

---

## 4. Gap Fill Rate vs Previous Day's Range

| Prev Day Range | Gaps | Filled | Fill Rate |
|---------------|------|--------|-----------|
| 0.0–1.0% | 184 | 147 | 79.9% |
| 1.0–1.5% | 398 | 278 | 69.8% |
| 1.5–2.0% | 688 | 488 | 70.9% |
| 2.0–3.0% | 1,044 | 670 | 64.2% |
| >3.0% | 674 | 421 | 62.5% |

When the previous day was calm (range <1%), gaps fill 79.9% of the time. When the previous day was volatile (range >3%), gaps fill only 62.5%.

---

## 5. Gap Direction + Previous Day Direction

| Pattern | Gaps | Filled | Fill Rate |
|---------|------|--------|-----------|
| Gap continues prev day trend | 1,173 | 745 | 63.5% |
| Gap reverses prev day trend | 999 | 521 | 52.2% |

Gaps that continue the trend fill more often (63.5%) than gaps that reverse the trend (52.2%). This contradicts the assumption that "reversal gaps fill more."

---

## 6. Gap-Up vs Gap-Down

| | Events | Avg OC Return | Avg Fill % | Filled |
|--|--------|--------------|-----------|--------|
| Gap-Up | 1,463 | +0.035% | 79.4% | 63.0% |
| Gap-Down | 1,260 | −0.052% | 80.4% | 64.9% |

Gap-down days fill slightly more often (64.9% vs 63.0%). Both directions see ~80% average fill percentage (including partial fills).

---

## 7. What Correlates with Next Day's Return?

| Factor | Correlation (r) |
|--------|----------------|
| Today's gap size | **−0.103** |
| Today's return | −0.053 |
| Today's volume vs average | −0.039 |
| Today's range | +0.039 |

Gap size has the strongest (negative) correlation with next day's return: larger gaps today predict lower returns tomorrow.

---

## 8. Stock Personalities

### Most Volatile (Highest Avg Daily Range)
| Stock | Avg Range | Avg Gap | Gap Fill % |
|-------|-----------|---------|-----------|
| ADANIENT | 3.21% | 0.94% | 57.8% |
| SHRIRAMFIN | 3.04% | 1.15% | 39.6% |
| TRENT | 2.99% | 0.87% | 47.4% |
| BPCL | 2.85% | 1.23% | 36.6% |
| BAJAJHLDNG | 2.79% | 0.66% | 48.8% |

### Most Stable (Lowest Avg Daily Range)
| Stock | Avg Range | Avg Gap | Gap Fill % |
|-------|-----------|---------|-----------|
| ITC | 1.70% | 0.43% | 52.9% |
| RELIANCE | 1.99% | 0.68% | 64.1% |
| ICICIBANK | 2.00% | 0.68% | 38.5% |
| BRITANNIA | 2.05% | 0.51% | 53.3% |
| CIPLA | 2.06% | 0.52% | 67.5% |

### Best Gap Fill Stocks
| Stock | Fill Rate |
|-------|-----------|
| ONGC | 79.3% |
| NESTLEIND | 76.7% |
| BHARTIARTL | 75.6% |
| NTPC | 74.4% |
| COALINDIA | 73.1% |

### Worst Gap Fill Stocks
| Stock | Fill Rate |
|-------|-----------|
| LT | 33.3% |
| BPCL | 36.6% |
| INDUSINDBK | 38.1% |
| ICICIBANK | 38.5% |
| M&M | 39.1% |

---

## 9. Outliers

### Largest Gap-Ups (all unfilled)
| Stock | Date | Gap |
|-------|------|-----|
| ADANIENT | 2026-04-08 | +6.26% |
| ADANIPORTS | 2026-04-08 | +6.08% |
| LT | 2026-04-08 | +6.04% |
| HINDALCO | 2026-04-15 | +5.90% |
| BPCL | 2026-04-08 | +5.78% |

### Largest Gap-Downs
| Stock | Date | Gap | Filled? |
|-------|------|-----|---------|
| HDFCBANK | 2026-03-19 | −8.66% | No |
| HCLTECH | 2026-04-22 | −6.68% | No |
| COALINDIA | 2026-05-27 | −6.36% | Yes |
| WIPRO | 2026-06-05 | −6.26% | No |
| BPCL | 2026-04-13 | −5.04% | No |

---

## 10. Summary Statistics

| Metric | Value |
|--------|-------|
| Total observations | 2,988 stock-day events |
| Average daily return | +0.078% |
| Median daily return | +0.000% |
| Std dev of daily return | 1.871% |
| Average daily range | 2.37% |
| Average absolute gap | 0.72% |
| % positive days | 49.6% |
| % flat days | 3.3% |
| Largest single-day move | 10.5% |
| Largest gap | 8.7% (down) |
| Overall gap fill rate (>0.3%) | 53.7% |
| Overall gap fill rate (>0.5%) | 47.7% |
| Best correlation with next day | Gap size (r = −0.10) |

---

## 11. Overlooked Patterns (Deeper Exploration)

### 11.1 Volume Surge Effect — Strongest Filter We Missed

| Volume Ratio (vs 10d avg) | Events | Filled | Fill Rate |
|--------------------------|--------|--------|-----------|
| 0.0–0.5x | 158 | 109 | 69.0% |
| 0.5–0.8x | 544 | 309 | 56.8% |
| 0.8–1.0x | 373 | 195 | 52.3% |
| 1.0–1.2x | 276 | 142 | 51.4% |
| 1.2–1.5x | 256 | 123 | 48.0% |
| 1.5–2.0x | 158 | 75 | 47.5% |
| 2.0–3.0x | 79 | 37 | 46.8% |
| 3.0x+ | 53 | 25 | 47.2% |

Fill rate drops **monotonically** from 69% (quiet) to 47% (high volume).
Low vol + gap-down: **63.0%** fill. High vol + gap-down: only **43.8%**.

### 11.2 Close Position in Range → Next Day

| Close Position | Events | Avg Next Return | Positive % |
|---------------|--------|----------------|-----------|
| Bottom 20% | 654 | +0.074% | 50.2% |
| 20–40% | 612 | −0.054% | 48.3% |
| 40–60% | 599 | −0.042% | 45.6% |
| 60–80% | 531 | −0.032% | 47.7% |
| **Top 20%** | **543** | **+0.360%** | **52.7%** |

Stocks closing at the top of their range outperform next day. Strength begets strength — no mean reversion edge.

### 11.3 2-Day "Extreme Persistence" (Not Reversal)

| 2-Day Close Position | Events | Avg Next Return | Positive % |
|---------------------|--------|----------------|-----------|
| > +30 (mild strength) | 571 | +0.420% | 55.0% |
| > +50 (strength) | 289 | +0.573% | 58.8% |
| **> +70 (extreme)** | **127** | **+0.971%** | **62.2%** |
| < −30 (mild weak) | 740 | +0.162% | 52.3% |
| < −50 (weak) | 407 | +0.278% | 56.0% |
| < −70 (extreme) | 116 | +0.392% | 57.8% |

Stocks that have been strong for 2 consecutive days continue being strong. The more extreme the 2-day strength, the stronger the next day. This directly contradicts the "overbought = reversal" assumption.

### 11.4 EMA9 Proximity — Gap Fill Rate

| Distance from EMA9 | Events | Fill Rate |
|-------------------|--------|-----------|
| 0–1% | 651 | **64.5%** |
| 1–2% | 506 | 55.5% |
| 2–5% | 649 | 43.6% |

Gaps near the EMA9 fill far more reliably (64.5%) than gaps far from it (43.6%).

### 11.5 RSI Zones — Gap Fill vs Return Divergence

| RSI Zone | Events | Fill Rate | Avg Return |
|---------|--------|-----------|-----------|
| <30 (oversold) | 123 | **69.9%** | **−0.614%** |
| 30–40 | 207 | 55.6% | −0.398% |
| 40–50 | 300 | 57.7% | −0.002% |
| 50–60 | 312 | 53.5% | +0.569% |
| 60–70 | 262 | 53.4% | +0.485% |
| >70 (overbought) | 214 | **64.0%** | **+0.870%** |

RSI < 30: gap fills 69.9% of the time but stock still closes **−0.61%** (gap fills but trend is down).
RSI > 70: gap fills 64% but stock closes **+0.87%** (momentum survives the fill).

### 11.6 Day × Gap Direction — Best Combos

| Day | Direction | Events | Fill Rate | Avg OC Return |
|-----|-----------|--------|-----------|--------------|
| **Tue** | Gap-down | 152 | **69.7%** | **+0.234%** |
| **Wed** | Gap-down | 114 | **74.6%** | **+0.383%** |
| Thu | Gap-up | 150 | 71.3% | −0.144% |
| Mon | Gap-down | 273 | 39.9% | −0.288% |
| Wed | Gap-up | 305 | 35.1% | +0.265% |

Wednesday gap-downs: **74.6%** fill rate with **+0.38%** avg return — the single best cell in the grid.
Monday gap-ups: only 35.1% fill (worst).
Tuesday gap-downs: 69.7% fill, +0.23% return.

### 11.7 Stock-By-Stock Best Conditions

| Condition | Stocks Where It's #1 | Avg WR |
|-----------|---------------------|--------|
| **Tuesday** | **16 stocks** | **86.2%** |
| gap 0.3–0.5% | 15 stocks | 88.7% |
| gap 0.5–0.8% | 5 stocks | 85.3% |
| Thursday | 4 stocks | 91.7% |
| Low volume | 3 stocks | 81.0% |
| Wednesday | 2 stocks | 88.5% |
| Previous day down | 2 stocks | 88.3% |

Tuesday is the highest-signal day: 16/49 stocks have their best WR on Tuesday (avg 86.2%).
Small gaps (0.3–0.5%) are the best blanket condition: 15 stocks, avg 88.7% WR.

### 11.8 Weekend Effect

| Metric | Value |
|--------|-------|
| Avg weekend gap (Fri close → Mon open) | **−0.741%** |
| Positive weekends | 228/587 (38.8%) |
| Weekends with >0.3% gap | 553/587 (94.2%) |

Nearly all weekends produce a gap, and 61% of those gaps are negative. Monday opens weak.

### 11.9 Open = Daily High/Low (Extreme Intraday Reversals)

| Pattern | Events | Avg OC Return |
|---------|--------|--------------|
| Open = Day's High | 116 | **−1.928%** |
| Open = Day's Low | 108 | **+1.985%** |

When a stock opens at its high (never trades higher), it closes nearly 2% lower on average.
When it opens at its low (never trades lower), it closes nearly 2% higher.
Rare event (~4% of days) but extremely reliable when it happens.

### 11.10 March vs May — The Month Effect

| Month | Events | Fill Rate | Avg Return |
|-------|--------|-----------|-----------|
| March | 325 | 31.1% | −0.777% |
| April | 653 | 52.2% | +0.543% |
| **May** | **546** | **62.8%** | **+0.088%** |
| **June** | **373** | **61.7%** | **+0.127%** |

March was an outlier — only 31.1% gap fill and −0.78% avg return. May/June are much more favorable with 62% fill rates. A strategy's March performance would look terrible, and May would look great — same strategy, different calendar.

---

## 12. Even Deeper — Autocorrelation, Z-Score, Sequences & Interactions

### 12.1 Return Autocorrelation — Some Stocks Trend, Some Revert

| Stock | Autocorrelation (r) | Personality |
|-------|-------------------|-------------|
| ADANIPORTS | **−0.313** | Strong mean-reverter |
| INDUSINDBK | −0.292 | Mean-reverter |
| ASIANPAINT | −0.259 | Mean-reverter |
| DIVISLAB | −0.198 | Mean-reverter |
| TCS | −0.175 | Mild mean-reverter |
| ... | | |
| INFY | **+0.194** | **Trending** |
| BHARTIARTL | +0.186 | Trending |
| HDFCLIFE | +0.177 | Trending |
| NTPC | +0.167 | Trending |
| WIPRO | +0.147 | Trending |

The same strategy would produce opposite results on ADANIPORTS (fade moves) vs INFY (follow moves).
Overall market: r = −0.042 (very slightly mean-reverting).

### 12.2 Gap Z-Score — Gap as Multiple of Stock's Own Average

| Gap / Stock's Avg Gap | Events | Fill Rate | Avg Ret |
|----------------------|--------|-----------|---------|
| 0.0–0.5x | 625 | **77.0%** | +0.097% |
| 0.5–0.8x | 431 | 65.7% | +0.044% |
| 0.8–1.2x | 411 | 56.4% | +0.023% |
| 1.2–1.5x | 223 | 43.5% | +0.147% |
| 1.5–2.0x | 196 | 41.3% | +0.117% |
| 2.0–3.0x | 149 | 39.6% | +0.623% |
| 3.0–10.0x | 84 | 29.8% | +1.031% |

This discriminates better than raw gap size. A 0.5% gap in ITC (avg 0.43%) is "typical" — a 0.5% gap in ADANIENT (avg 0.94%) is "small." The z-score captures this.

### 12.3 The Interaction Grid — Previous Return × Gap Size

Fill rate as a function of yesterday's return (rows) and today's gap (columns):

| Prev Ret ↓ / Gap → | Big Gap-Down | Small Gap-Down | Tiny Gap | Small Gap-Up | Big Gap-Up |
|--------------------|:------------:|:--------------:|:--------:|:------------:|:----------:|
| **Big Red (−2 to −10%)** | **17.8%** (45) | 82.6% (23) | 91.9% (86) | 75.0% (32) | 37.3% (83) |
| Moderate Red (−1 to −2%) | 37.7% (53) | 64.2% (53) | 93.2% (133) | 66.2% (74) | 36.6% (71) |
| Slight Red (−0.3 to −1%) | 42.6% (54) | 71.8% (71) | 90.7% (161) | 65.8% (76) | 34.8% (66) |
| **Flat (±0.3%)** | 49.3% (69) | 71.8% (85) | 89.8% (235) | 71.9% (89) | 43.0% (93) |
| Slight Green (+0.3 to +1%) | 40.6% (64) | 68.7% (67) | 89.4% (160) | 65.4% (78) | 38.2% (55) |
| Moderate Green (+1 to +2%) | 52.5% (59) | 75.4% (65) | 90.0% (150) | 74.6% (67) | 37.9% (58) |
| **Big Green (+2 to +10%)** | 46.8% (79) | 70.7% (41) | 92.2% (77) | 66.7% (48) | 42.3% (71) |

Most striking cell: **big red day + same-direction big gap → 17.8% fill.** The trend continues.
Most reliable cell: **moderate red day + tiny gap → 93.2% fill.** Almost guaranteed bounce.

### 12.4 Monday Predicts Tuesday (r = −0.34)

| Condition | Events | Tue Avg Gap |
|----------|--------|-------------|
| After Green Monday (+1.37% avg) | 490 | **−0.082%** |
| After Red Monday (−1.69% avg) | 490 | **+0.196%** |

The correlation between Monday's return and Tuesday's gap is **−0.34** — a genuine mean-reversion effect overnight. Red Monday → buy the Tuesday gap-up.

### 12.5 Unfilled Gaps Are Time Bombs

| Timeframe | Unfilled Gaps That Fill |
|-----------|------------------------|
| Within 1 day | **82.8%** |
| Within 2 days | 88.3% |
| Within 3 days | 90.0% |
| Within 5 days | 91.2% |

If a gap doesn't fill on the same day, there's an 83% chance it fills by tomorrow. Unfilled gaps are the exception, not the rule.

### 12.6 Triple Filter — Day × Volume × Direction

| Day | Volume | Direction | Events | Fill Rate | Avg Return |
|-----|--------|-----------|--------|-----------|-----------|
| **Wed** | **Low** | **Gap-Down** | 59 | **84.7%** | −0.243% |
| **Tue** | **Low** | **Gap-Down** | 56 | **82.1%** | −0.385% |
| Thu | Low | Gap-Up | 48 | 79.2% | +0.235% |
| Fri | Low | Gap-Down | 31 | 80.6% | −0.282% |
| Tue | Low | Gap-Up | 41 | 73.2% | +0.500% |
| Mon | Low | Gap-Up | 99 | 62.6% | +0.594% |
| ... | | | | | |
| **Mon** | **High** | **Gap-Down** | 36 | **19.4%** | **−3.283%** |
| **Mon** | **High** | **Gap-Up** | 32 | **37.5%** | **+2.018%** |

The spread between best (Wed low vol gap-down: 84.7%) and worst (Mon high vol gap-down: 19.4%) is **65 percentage points**. The day and volume context changes everything.

### 12.7 Gap Streaks Self-Destruct

| Consecutive Same-Direction Gaps | Events | Fill Rate |
|-------------------------------|--------|-----------|
| 0 (first gap) | 1,117 | 53.6% |
| 1 | 421 | 51.8% |
| **2** | **181** | **64.1%** |
| **3** | **43** | **65.1%** |
| 4 | 19 | 68.4% |
| 5 | 4 | 75.0% |

After 2+ gaps in the same direction, the streak is increasingly likely to break. The more consecutive gaps, the higher the chance the next one fills (reverses).

### 12.8 Three-Day Momentum Is U-Shaped

| 3-Day Return | Events | Gap Fill Rate |
|-------------|--------|-----------|
| <−3% (hammered) | 243 | 41.2% |
| −3 to −1% | 368 | 62.0% |
| −1 to 0% | 269 | **65.4%** |
| 0 to +1% | 209 | 61.7% |
| +1 to +3% | 364 | 57.1% |
| >+3% (ripped) | 312 | 43.3% |

The worst-hit stocks (−3% in 3 days) keep falling (only 41.2% fill). The slightly weak stocks bounce (65.4% fill). The pattern is symmetric — extreme momentum in either direction survives the gap.

### 12.9 Net Gap Bias — Some Stocks Consistently Gap in One Direction

| Most ↑ Biased | % Gap-Ups | Most ↓ Biased | % Gap-Ups |
|--------------|-----------|--------------|-----------|
| ADANIENT | **58.5%** | HDFCBANK | **38.6%** |
| APOLLOHOSP | 57.6% | KOTAKBANK | 40.5% |
| | | SBILIFE | 39.5% |
| | | AXISBANK | 43.2% |

ADANIENT gaps up 58.5% of the time vs HDFCBANK at 38.6% — a 20% difference. This is not random. Each stock has a gap personality.

### 12.10 Gap After a Big Day — Reversal or Continuation?

| Pattern | Events | Fill Rate | Story |
|---------|--------|-----------|-------|
| Big red day (−2%) → gap-up next day | 97 | 41.2% | Low fill but **+1.63%** return (reversal works) |
| Big green day (+2%) → gap-down next day | 98 | 53.1% | Higher fill but **−1.21%** return (more weakness) |

After a big red day: gap-up fills rarely (41%) but when it does, the gains are large (+1.63%).
After a big green day: gap-down fills more often (53%) but the selling continues (−1.21%).

---

*Generated from real yfinance data. No fabricated numbers. No strategy assumptions. Just what the data says.*
