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

## Architecture

- **Frontend (Vercel):** static HTML/CSS/JS in `frontend/`
- **Backend (Render):** Flask API in `app.py`
- Browser calls same-origin `/api/*` on Vercel; `frontend/vercel.json` rewrites those requests to the Render service so Flask session cookies keep working.

```text
Browser → Vercel (pages + /api proxy) → Render (Flask + SQLite + Gmail SMTP)
```

## Preserved features

- Original CSS, colors, layout language, and responsive behavior
- Columbia email registration restriction
- Gmail SMTP delivery through Flask-Mail
- Six-digit hashed verification codes with 10-minute expiration
- Resend verification code
- Login, logout, session protection, and API 401 handling
- Forgot-password and email reset-code flow
- Existing `users.db` and migration-safe reset columns

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 app.py
```

Open `http://127.0.0.1:5000` (or `5001` if macOS occupies 5000).

## Deploy

### 1. Backend on Render

1. Connect the GitHub repo in Render and use `render.yaml`, or create a Python Web Service with:
   - Build: `pip install -r requirements.txt`
   - Start: `gunicorn app:app --bind 0.0.0.0:$PORT`
2. Set env vars from `.env.example`, especially `MAIL_*`, `SECRET_KEY`, and `SESSION_COOKIE_SECURE=true`.
3. Confirm health: `https://<your-service>.onrender.com/api/health`

Free Render instances sleep when idle and SQLite is ephemeral unless you attach a paid disk and set `DATABASE_PATH`.

### 2. Frontend on Vercel

1. Import the same GitHub repo in Vercel.
2. Keep the project Root Directory as the repository root (uses root `vercel.json`, which publishes `frontend/`).
3. Or set **Root Directory** to `frontend` and use `frontend/vercel.json`.
4. Deploy and open the Vercel URL.


## Security notes

- Do not commit `.env` or real mail passwords.
- Use a long random `SECRET_KEY` in production.
- Keep `SESSION_COOKIE_SECURE=true` on HTTPS deployments.
