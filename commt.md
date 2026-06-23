p[e## Scans

- **Morning**: `0 4 * * *` (04:00 UTC = 09:30 IST) — scans gaps at open, places pending trades
- **Evening**: `30 10 * * *` (10:30 UTC = 16:00 IST) — resolves pending trades with EOD data
- Runs daily incl weekends (writes dashboard with timestamp, no picks on Sat/Sun)

## Fixes

- **IST timezone**: All modes use `datetime.now(IST)` so dates are correct at 04:00 IST
- **Cron reverted**: `0 23 * * 0-4` → `0 4 * * *` (was running before market open at 4:30 AM IST)
- **Footer**: Shows "Last run: ... IST"
