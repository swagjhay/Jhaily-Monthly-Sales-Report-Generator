# Jhaily

Automated monthly sales reports for small businesses. A business owner uploads a sales
export (or connects a live spreadsheet link) once, and every month afterward, Jhaily
cleans the data, analyzes it, and emails a report — no dashboard to check, nothing to
remember.

**Live**: https://jhaily.onrender.com

## What it does

- **Cleans genuinely messy real-world data**: mixed date formats, missing prices,
  inconsistent item-name casing, duplicate rows
- **Computes real business metrics**: monthly revenue trend, best-selling item and
  category, busiest/slowest weekday, average transaction value (refund-corrected),
  refund rate, and payment method mix
- **Sends a styled HTML email** with an embedded chart, plus a downloadable PDF version
  of the same report
- **Real user accounts**: register/login/logout, with securely hashed passwords
  (never stored or readable as plaintext)
- **Multi-business support**: one account can track several businesses, each with its
  own recipient email and data source
- **Flexible data sources**: upload a CSV directly, or point at a live link (e.g. a
  published Google Sheets CSV export) so the report always uses current data with no
  manual re-upload
- **Real unsubscribe**: a unique link per business, included in every email

## Tech stack

- **Backend**: Flask, served with gunicorn in production
- **Database**: PostgreSQL (Neon, free tier) in production; SQLite for local development
- **File storage**: Cloudflare R2 (private bucket, accessed via short-lived presigned
  URLs) for uploaded CSVs, so files survive redeploys on Render's ephemeral filesystem
- **Auth**: Flask-Login, with Werkzeug's password hashing
- **Data processing**: pandas
- **Charts**: matplotlib
- **PDF generation**: xhtml2pdf
- **Hosting**: Render (free web service tier)
- **Monthly scheduling**: a GitHub Actions scheduled workflow calls a secured API
  endpoint (`POST /run-monthly-reports`) once a month, rather than running a persistent
  background worker — Render's free tier doesn't include one, and this avoids the
  $7/month minimum a dedicated worker would otherwise cost
- **Email**: smtplib (Gmail SMTP)

## Project structure

```
extensions.py        # Shared Flask app/db/login setup (avoids circular imports)
models.py            # User and Business (subscription) database models
app.py               # Web routes: register, login, dashboard, add/update business,
                      # unsubscribe, and the secured monthly-trigger endpoint
generate_report.py   # The data pipeline, email/PDF generation, and report-sending logic
storage.py           # Cloudflare R2 upload/delete/presigned-URL helpers
templates/           # HTML pages
.github/workflows/   # The scheduled GitHub Actions workflow that triggers monthly reports
```

## Local development setup

1. Clone the repo and create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate   # Windows
   source venv/bin/activate   # Mac/Linux
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your real values. With no `DATABASE_URL`
   set, the app falls back to a local SQLite database automatically — no Postgres
   setup needed just to develop locally. R2 credentials are still required for file
   uploads to work, even locally.

4. Run the web app:
   ```
   python app.py
   ```
   Visit `http://127.0.0.1:5000`.

5. (Optional, local testing only) To test the report-sending logic without deploying,
   you can run the scheduler script directly — this uses a local `BlockingScheduler`
   loop, which is NOT what production uses:
   ```
   python generate_report.py
   ```
   In production, reports are instead triggered by the GitHub Actions workflow calling
   the deployed app's `/run-monthly-reports` endpoint — see below.

## Production deployment (Render)

- **Database**: a Neon Postgres connection string, set as `DATABASE_URL`
- **File storage**: a private Cloudflare R2 bucket; credentials set as `R2_ACCOUNT_ID`,
  `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `gunicorn app:app`
- **Monthly trigger**: a GitHub Actions workflow (`.github/workflows/monthly-reports.yml`)
  runs on a cron schedule and calls `POST /run-monthly-reports` with a shared secret
  (`SCHEDULER_SECRET`, set identically in both Render's environment variables and the
  repo's GitHub Actions secrets) — authenticated with a timing-safe comparison
  (`hmac.compare_digest`) rather than a plain `==` check
- Required environment variables on Render: `DATABASE_URL`, `SECRET_KEY`,
  `GMAIL_SENDER`, `GMAIL_APP_PASSWORD`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`,
  `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `SCHEDULER_SECRET`, `APP_BASE_URL`

## Notes

- `.env` is never committed — see `.gitignore`. Use `.env.example` as a template.
- SQLAlchemy's engine is configured with `pool_pre_ping` and a recycle interval, since
  Neon's free tier (like most serverless/free-tier databases) can drop idle connections;
  without this, an infrequent job like the monthly trigger can hit a stale connection.
- Currently configured for Gmail's SMTP server; swapping to another provider or a
  transactional email service (SendGrid, Mailgun, etc.) only requires changing the
  SMTP connection details in `generate_report.py`.
