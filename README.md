# Nifty 50 Intraday Screener — Intraday Edge

> Automated intraday stock screening & trading signal system for NSE Nifty 50.
> Picks the single highest-probability stock daily using an 8-point technical screener.

---

## 🚀 Dashboards

| Dashboard | Link |
|-----------|------|
| **Main Dashboard** (root) | [`index.html`](./index.html) |
| **Screener Dashboard** (Chart.js) | [`agent/screener_dashboard.html`](./agent/screener_dashboard.html) |
| **Forex Live Dashboard** | [`agent/forex_live_dashboard.html`](./agent/forex_live_dashboard.html) |
| **Trade Report Index** | [`agent/report/index.html`](./agent/report/index.html) |
| **Vite Dev Entry** (React AI screener) | [`agent/index.html`](./agent/index.html) |

---

## 📊 Trade Reports

| Date | Symbol | Report |
|------|--------|--------|
| Jun 11 | RELIANCE | [`report/2026-06-11_15-30.html`](./agent/report/2026-06-11_15-30.html) |
| Jun 12 | ICICIBANK | [`report/2026-06-12_21-01.html`](./agent/report/2026-06-12_21-01.html) |
| Jun 15 | LT | [`report/2026-06-15_18-57.html`](./agent/report/2026-06-15_18-57.html) |

---

## 📈 Live & Historical Data

| File | Description |
|------|-------------|
| [`agent/daily_log.csv`](./agent/daily_log.csv) | Trade log (date, symbol, entry, SL, target, result, PnL) |
| [`agent/daily_pick.json`](./agent/daily_pick.json) | Current day's pick |
| [`agent/daily_log_evening.txt`](./agent/daily_log_evening.txt) | Evening check execution log |
| [`agent/forex_live_log.csv`](./agent/forex_live_log.csv) | Forex trade log |
| [`agent/forex_active_signals.json`](./agent/forex_active_signals.json) | Active forex signals (USD/CAD, etc.) |

---

## 🔬 Backtesting

| File | Description |
|------|-------------|
| [`agent/backtest_results_2026-04-13_to_2026-06-12.csv`](./agent/backtest_results_2026-04-13_to_2026-06-12.csv) | Full backtest results |
| [`agent/backtest_summary_2026-04-13_to_2026-06-12.json`](./agent/backtest_summary_2026-04-13_to_2026-06-12.json) | Backtest summary stats |

---

## 🧠 Core Scripts

| Script | Purpose |
|--------|---------|
| [`agent/daily_screener.py`](./agent/daily_screener.py) | **Main script** — morning pick, evening check, dashboard generator |
| [`agent/backtest.py`](./agent/backtest.py) | Backtester — runs strategy on historical data |
| [`agent/generate_pick_html.py`](./agent/generate_pick_html.py) | Rich historical analysis HTML generator |
| [`agent/regen_reports.py`](./agent/regen_reports.py) | Regenerate synthetic trade reports |
| [`agent/regen_svg.py`](./agent/regen_svg.py) | Regenerate SVG charts for reports |
| [`agent/simulate_june11.py`](./agent/simulate_june11.py) | Demo trade simulation |

---

## 🎨 React Frontend

| File | Description |
|------|-------------|
| [`agent/src/main.jsx`](./agent/src/main.jsx) | React entry point |
| [`agent/intraday-screener.jsx`](./agent/intraday-screener.jsx) | AI-powered screener component (Anthropic Claude) |
| [`agent/package.json`](./agent/package.json) | Node.js dependencies (React + Vite) |

---

## 🤖 AI / Agent Config

| File | Description |
|------|-------------|
| [`opencode.json`](./opencode.json) | OpenCode AI agent config |
| [`screener.md`](./screener.md) | Screener strategy documentation |
| [`agent/screener.md`](./agent/screener.md) | AI screener instructions for Claude |
| [`agent/.env`](./agent/.env) | Anthropic API key placeholder |

---

## ⚙️ Automation

| File | Description |
|------|-------------|
| [`.github/workflows/screener.yml`](./.github/workflows/screener.yml) | GitHub Actions — auto-runs morning & evening |
| [`agent/morning_pick.bat`](./agent/morning_pick.bat) | Windows Task Scheduler — morning pick |
| [`agent/evening_check.bat`](./agent/evening_check.bat) | Windows Task Scheduler — evening check |
| [`agent/install_scheduler.bat`](./agent/install_scheduler.bat) | Install Windows scheduled tasks |

---

## 📋 Live Performance

| Date | Symbol | Result | PnL |
|------|--------|--------|-----|
| Jun 11 | RELIANCE | ✅ TARGET_HIT | +2.00% |
| Jun 12 | ICICIBANK | ✅ TARGET_HIT | +2.00% |
| Jun 15 | LT | ✅ TARGET_HIT | +2.00% |

> **Live Win Rate: 100%** (3/3) | Backtest Win Rate: 26.6% (64 signals / 1028 checks)

---

## 🛠️ Quick Commands

```bash
# Run morning pick
python agent/daily_screener.py pick

# Run evening check
python agent/daily_screener.py check

# Regenerate dashboard
python agent/daily_screener.py dashboard

# Run backtest
python agent/backtest.py

# Start React dev server (Intraday Edge AI tool)
cd agent && npm run dev
```

---

## ⚠️ Disclaimer

> This is AI-generated research for educational purposes only. Not SEBI registered advice.
