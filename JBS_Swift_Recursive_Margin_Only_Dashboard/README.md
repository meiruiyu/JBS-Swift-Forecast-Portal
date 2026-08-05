# JBS Swift Recursive Margin Forecast Portal

This version preserves the original portal styling and complete account/email system, but the dashboard reads and displays only:

`data/june_2026_recursive_margin_forecast.csv`

No sales forecast file is included or mixed into the dashboard.

## Dataset

- 90 rows and 10 columns
- June 1–30, 2026
- Channels: Stores, E-commerce, Vans
- Primary measure: `predicted_margin`
- Forecast mode: `recursive_locked_month`

The dashboard provides date/channel filters, total margin, average margin, peak margin, a daily channel chart, channel comparison cards, all ten CSV fields in the result table, filtered CSV download, and chart export. The Channel dropdown is generated dynamically from the CSV's unique `channel` values; it is not hardcoded.

Because Vans margins are much smaller than Stores margins, the chart uses a clearly labeled right-side Vans axis while Stores and E-commerce use the left axis. The result table keeps the original visual style but groups long technical metadata into a readable Forecast Details cell instead of crowding nine narrow columns.

## Preserved features

- Original CSS, colors, layout language, and responsive behavior
- Columbia email registration restriction
- Gmail SMTP delivery through Flask-Mail
- Six-digit hashed verification codes with 10-minute expiration
- Resend verification code
- Login, logout, session protection, and API 401 handling
- Forgot-password and email reset-code flow
- Existing `users.db` and migration-safe reset columns

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 app.py
```

Open `http://127.0.0.1:5000`.
