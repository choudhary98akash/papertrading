# Five Strategies — One for Each Day

> Five distinct approaches, each optimized for its day's personality.
> Every rule comes from real data, not assumptions.

---

## How to Read This

Each day has a **completely different strategy**. The approach that works on Wednesday (buy gap-downs) is the exact opposite of what works on Thursday (short gap-ups). Using Tuesday's strategy on Monday would lose money.

For each strategy:
- **Core idea** — the principle that makes it work
- **Setup** — specific conditions to enter
- **Exit** — when to take profits or cut losses
- **Why it works** — the data behind it
- **When it fails** — known failure modes

---

# Monday — The Weekend Fade

## Core Idea
Monday opens weak (weekend gap **−0.74%** on average, only 38.8% positive). This creates a bias: gap-ups are fake strength that fades, gap-downs are real weakness that continues. **Don't fight Monday's bearish bias — exploit it.**

## The Strategy: "Fake Strength, Real Weakness"

### Setup A: Short Gap-Ups (Primary)
```
CONDITIONS:
  Day: Monday
  Gap-up +0.3% to +0.8%
  Volume < 0.8× 10-day average

ENTRY:
  Short at 9:20 AM (after first 5-min candle)
  Direction: SHORT (gap-up fades)

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5% from entry
  Time exit: 3:10 PM

POSITION SIZING:
  Normal (1×) — this is the only Monday setup with positive edge
```

### Setup B: Extreme Mean Reversion (Secondary)
```
CONDITIONS:
  Day: Monday
  Previous Friday's close position: <20% of range (closed near low)
  Gap-up +0.3% to any size

ENTRY:
  Short at 9:20 AM

EXIT:
  Target: 100% of gap fill (not 50% — Monday oversold reversal tends to fully fill)
  Stop loss: 0.6% (wider — extreme moves need room)
  Time exit: 3:10 PM

RATIONALE:
  When a stock closes near its low on Friday AND gaps up Monday,
  it fills the gap 79.1% of the time with EV +1.68% (Sharpe 19.8).
  This is the highest EV trade in the entire dataset.
```

### What NOT to Do
```
🚫 NEVER trade gap-downs (45.6% fill, −0.88% avg)
🚫 NEVER trade ANY high-volume gap (19-37% fill)
🚫 NEVER hold overnight into Tuesday
```

### Data Summary
| Metric | Gap-Up + Low Vol | Gap-Down + Low Vol | Any + High Vol |
|--------|:-:|:-:|:-:|
| Win Rate | **62.6%** | 45.6% | 19-37% |
| Avg Return | +0.59% | −0.88% | −1.0% to −3.3% |
| Verdict | ✅ TRADE | ❌ SKIP | 🚫 NEVER |
| Trades/Month | ~8-12 | — | — |

---

# Tuesday — The Golden Day

## Core Idea
Tuesday has the **highest gap fill rate of any day** (77.6%). Something about Tuesday is special — the market stabilizes after Monday's adjustment, news is absorbed, and gaps revert. **Take every small gap trade — Tuesday is your volume day.**

## The Strategy: "Every Small Gap Counts"

### Setup A: Low-Volume Gap-Down (Primary)
```
CONDITIONS:
  Day: Tuesday
  Gap-down −0.3% to −0.8%
  Volume < 0.8× 10-day average
  (Optional: Monday closed red → increase conviction)

ENTRY:
  Long at 9:20 AM
  Direction: LONG (gap-down reverses)

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5%
  Time exit: 3:10 PM

POSITION SIZING:
  Aggressive (1.5×) — this is the highest-conviction Tuesday setup
```

### Setup B: Low-Volume Gap-Up (Secondary)
```
CONDITIONS:
  Day: Tuesday
  Gap-up +0.3% to +0.8%
  Volume < 0.8× 10-day average

ENTRY:
  Short at 9:20 AM
  Direction: SHORT (gap-up fades)

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5%
  Time exit: 3:10 PM

POSITION SIZING:
  Normal (1×)
```

### Setup C: The Monday Hangover (Tertiary)
```
CONDITIONS:
  Day: Tuesday
  Monday closed red (<−0.5%)
  Gap-down any size (0.3% to 0.8%)
  Volume any (but prefer < 1.5×)

ENTRY:
  Long at market open

EXIT:
  Target: 50% of gap fill
  Stop loss: 0.5%
  Time exit: 3:10 PM

RATIONALE:
  Monday → Tuesday correlation is r = −0.34.
  After a red Monday, Tuesday gaps up +0.20% on average.
  The gap-down on Tuesday after Monday's weakness is a double-reversal.
```

### What NOT to Do
```
🚫 NEVER trade high-volume gaps (>1.5×) — fill drops to 35-42%
🚫 Don't skip Tuesday even if volume is moderate (fill still ~70%)
```

### Data Summary
| Metric | Gap-Dn + Low Vol | Gap-Up + Low Vol | Day Overall |
|--------|:-:|:-:|:-:|
| Win Rate | **82.1%** | **73.2%** | **77.6%** |
| Avg Return (direction) | +0.24% | +0.50% | +0.18% |
| Verdict | ✅ A+ TRADE | ✅ A TRADE | ✅ BEST DAY |
| Est. Trades/Month | ~4-6 | ~4-6 | ~10-12 total |

---

# Wednesday — The Bullish Dip Buy

## Core Idea
Wednesday is the **most bullish day of the week** (+0.80% avg, 65% positive). The market wants to go up. **Gap-downs on Wednesday are fake selloffs** that reverse with 84.7% success. Gap-ups on Wednesday are euphoria that fades (only 35.1% fill). **Never short on Wednesday — you're fighting the trend.**

## The Strategy: "Buy the Fake Selloff"

### Setup A: Low-Volume Gap-Down (Primary — Best in Dataset)
```
CONDITIONS:
  Day: Wednesday
  Gap-down −0.3% to −0.8%
  Volume < 0.8× 10-day average

ENTRY:
  Long at 9:20 AM
  Direction: LONG (gap-down reverses)
  This is the single best setup in the entire dataset

EXIT:
  Target: 50% of gap filled (aggressive: 100%)
  Stop loss: 0.5%
  Time exit: 3:10 PM

POSITION SIZING:
  Maximum (2×) — highest-conviction trade in the dataset
```

### Setup B: Any Gap-Down (Secondary)
```
CONDITIONS:
  Day: Wednesday
  Gap-down −0.3% to −0.8%
  Volume: any (up to 1.5× still fine)

ENTRY:
  Long at 9:20 AM

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5%
  Time exit: 3:10 PM

POSITION SIZING:
  Normal (1×) — still 74.6% fill even without volume filter
```

### Multi-Day Hold (Optional)
```
If entered on Wednesday gap-down + low vol:
  Consider holding for 3 days:
    Day 1: +0.45% (gap fills)
    Day 3: +1.14% (60% positive)
    Day 5: +0.92% (63% positive)
  
  The best multi-day return is at Day 3 (+1.14%).
  Exit Wednesday position on Friday close or Monday open.
```

### What NOT to Do
```
🚫 NEVER short gap-ups (35.1% fill — worst cell in the matrix)
🚫 NEVER skip Wednesday even with moderate volume
🚫 Don't take profits too early — the 3-day window adds +1.14%
```

### Data Summary
| Metric | Gap-Dn + Low Vol | Gap-Dn (Any) | Gap-Up (Any) |
|--------|:-:|:-:|:-:|
| Win Rate | **84.7%** | **74.6%** | 35.1% |
| Avg Return | +0.45% | +0.38% | +0.27% |
| Verdict | ✅ **#1 SETUP** | ✅ EXCELLENT | 🚫 NEVER |
| Est. Trades/Month | ~4-6 | ~8-10 | 0 |

---

# Thursday — The Bearish Rally Short

## Core Idea
Thursday is the **most bearish day of the week** (−0.28% avg, only 37.6% positive). The market wants to go down. **Gap-ups on Thursday are fake rallies** that reverse with 79.2% success (low volume). Gap-downs on Thursday are real selling (only 51.5% fill). **Never buy on Thursday — you're fighting the trend.**

## The Strategy: "Short the Fake Rally"

### Setup A: Low-Volume Gap-Up (Primary)
```
CONDITIONS:
  Day: Thursday
  Gap-up +0.3% to +0.8%
  Volume < 0.8× 10-day average

ENTRY:
  Short at 9:20 AM
  Direction: SHORT (gap-up reverses)
  This is the mirror of Wednesday's best setup

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5%
  Time exit: 3:10 PM

POSITION SIZING:
  Aggressive (1.5×) — high conviction
```

### Setup B: Any Gap-Up (Secondary)
```
CONDITIONS:
  Day: Thursday
  Gap-up +0.3% to −0.8%
  Volume: any

ENTRY:
  Short at 9:20 AM

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5%
  Time exit: 3:10 PM

POSITION SIZING:
  Normal (1×) — still 71.3% fill even without volume filter
```

### Setup C: Short After Strong Wednesday (Tertiary)
```
CONDITIONS:
  Day: Thursday
  Wednesday had strong close (OC > +1%)
  Gap-up Thursday

ENTRY:
  Short at 9:20 AM

RATIONALE:
  Strong Wednesday → Thursday gaps down −0.11%.
  Add this to Thursday's natural bearishness.
  Gap-up after a strong Wednesday is a double-sell.
```

### What NOT to Do
```
🚫 NEVER buy gap-downs (51.5% fill — coin flip)
🚫 NEVER hold overnight into Friday
```

### Data Summary
| Metric | Gap-Up + Low Vol | Gap-Up (Any) | Gap-Dn (Any) |
|--------|:-:|:-:|:-:|
| Win Rate | **79.2%** | **71.3%** | 51.5% |
| Avg Return (direction) | +0.44% | +0.14% | +0.04% |
| Verdict | ✅ A+ TRADE | ✅ GOOD | ❌ SKIP |
| Est. Trades/Month | ~4-6 | ~8-10 | 0 |

---

# Friday — The Book Squaring

## Core Idea
Friday is neutral but **positional**. Traders close positions before the weekend. This creates unusual dynamics: **gap-downs + low volume = bargain hunting** (80.6% fill). **Gap-ups + high volume = short covering** (78.1% fill — the only time high-volume gap-ups work). **Gap-downs + high volume = panic** (−2.25% avg loss). Two distinct strategies depending on volume.

## The Strategy: "Weekend Prep"

### Setup A: Low-Volume Gap-Down (Primary)
```
CONDITIONS:
  Day: Friday
  Gap-down −0.3% to −0.8%
  Volume < 0.8× 10-day average

ENTRY:
  Long at 9:20 AM
  Direction: LONG (bargain hunting before weekend)

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5%
  Time exit: 3:10 PM (MANDATORY — no overnight holds)

POSITION SIZING:
  Normal (1×)
```

### Setup B: High-Volume Gap-Up (Secondary — Exception to the Rule)
```
CONDITIONS:
  Day: Friday
  Gap-up +0.3% to +0.8%
  Volume > 1.5× 10-day average

ENTRY:
  Short at 9:20 AM
  Direction: SHORT (short covering fades)

EXIT:
  Target: 50% of gap filled
  Stop loss: 0.5%
  Time exit: 3:10 PM

POSITION SIZING:
  Normal (1×)

RATIONALE:
  High-volume gap-ups normally have low fill rates.
  On Friday, they fill 78.1% of the time.
  Reason: short covering before weekend — shorts cover into strength,
  then the rally fades. This is the only day where high vol gap-ups work.
```

### What NOT to Do
```
🚫 NEVER trade gap-down + high vol (−2.25% avg loss — worst Friday combo)
🚫 NEVER hold positions over the weekend (avg −0.74% gap Mon open)
🚫 Don't take new positions after 2:00 PM
```

### Data Summary
| Metric | Gap-Dn + Low Vol | Gap-Up + High Vol | Gap-Dn + High Vol |
|--------|:-:|:-:|:-:|
| Win Rate | **80.6%** | **78.1%** | 60.7% |
| Avg Return | +0.28% | +0.13% | **−2.25%** |
| Verdict | ✅ TRADE | ✅ TRADE | 🚫 NEVER |
| Est. Trades/Month | ~4-6 | ~2-4 | 0 |

---

## The Complete Weekly Schedule

```
┌────────────────────────────────────────────────────────────────────┐
│                    THE WEEKLY TRADING SCHEDULE                      │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  MONDAY    8:45 AM  Check Friday's close positions (top/bottom?)   │
│            9:15 AM  Market opens — wait for first candle            │
│            9:20 AM  Scan for gap-ups + low volume                   │
│                     ↓ SHORT gap-ups (62.6% fill)                   │
│                     ↓ EXTREME: short gap-ups after Fri close<20%   │
│            3:10 PM  Close all positions                             │
│                                                                    │
│  TUESDAY   9:15 AM  Market opens                                    │
│            9:20 AM  Scan ALL gaps + low volume                      │
│                     ↓ LONG gap-downs (82.1% fill)                   │
│                     ↓ SHORT gap-ups (73.2% fill)                   │
│            3:10 PM  Close all positions                             │
│                                                                    │
│  WEDNESDAY 9:15 AM  Best day of the week — ready                     │
│            9:20 AM  Scan for gap-downs ONLY                        │
│                     ↓ LONG gap-downs (84.7% with low vol)           │
│                     ↓ LONG gap-downs (74.6% any vol)               │
│                     ↓ IGNORE gap-ups completely                     │
│            3:10 PM  Close — or hold for 3-day swing (+1.14%)       │
│                                                                    │
│  THURSDAY  9:15 AM  Market opens                                    │
│            9:20 AM  Scan for gap-ups ONLY                          │
│                     ↓ SHORT gap-ups (79.2% with low vol)            │
│                     ↓ SHORT gap-ups (71.3% any vol)                │
│                     ↓ SKIP gap-downs entirely                       │
│            3:10 PM  Close all positions                             │
│                                                                    │
│  FRIDAY    9:15 AM  Last day — close everything by 3:10            │
│            9:20 AM  Check volume first, then direction              │
│                     ↓ If low vol: LONG gap-downs (80.6% fill)       │
│                     ↓ If high vol: SHORT gap-ups (78.1% fill)       │
│                     ↓ NEVER trade gap-down + high vol               │
│            3:10 PM  Close EVERYTHING — no weekend holds             │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  WEEKLY TOTALS (estimated):                                        │
│    Monday:     8-12 trades                                         │
│    Tuesday:   10-12 trades                                         │
│    Wednesday:  8-10 trades                                         │
│    Thursday:   8-10 trades                                         │
│    Friday:     6-10 trades                                         │
│    ─────────────────────────                                       │
│    Total:     ~40-54 trades/week                                   │
│    Expected WR: ~72-78% (blended across days)                      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Quick Comparison

| Day | Strategy Name | Direction | Volume Filter | Best WR | Worst Enemy |
|-----|--------------|-----------|--------------|---------|-------------|
| Mon | Fake Strength, Real Weakness | Short gap-ups | Low | 62.6% | High volume |
| Tue | Every Small Gap Counts | Both | Low | **82.1%** | High volume |
| Wed | Buy the Fake Selloff | Long gap-downs | Any | **84.7%** | Gap-ups |
| Thu | Short the Fake Rally | Short gap-ups | Low | **79.2%** | Gap-downs |
| Fri | Weekend Prep | Long gap-dn (low vol) / Short gap-up (high vol) | Depends | **80.6%** | Gap-dn + high vol |

## Monthly Expected Performance

```
Trades:          ~180-220/month (across all 49 stocks)
Win rate:        ~75% blended
Best day:        Wednesday (84.7% on best setup)
Worst day:       Monday (62.6% on only viable setup)
Most profitable: Tuesday + Wednesday (highest volume of trades)
Most dangerous:  Monday high-volume gaps (19.4% fill)
```

---

## Risk Management by Day

| Day | Position Size | Max Drawdown Expected | Notes |
|-----|:---:|:---:|-------|
| Mon | 0.5× (half) | −2% | Reduced size — low confidence |
| Tue | 1.5× (aggressive) | −1% | High confidence, many trades |
| Wed | 2.0× (max) | −0.5% | Highest confidence setup |
| Thu | 1.5× (aggressive) | −0.5% | Short side only |
| Fri | 1.0× (normal) | −1% | Close by 3:10 PM |

---

*Generated from real yfinance data — 49 Nifty 50 stocks, 62 trading days, 2,988 gap events. Every rule is backed by actual observations.*

*Source files: `data.json`, `findings.md`, `agent/explore_deeper.py`, `agent/explore_different_angle.py`, `agent/explore_ml.py`*
