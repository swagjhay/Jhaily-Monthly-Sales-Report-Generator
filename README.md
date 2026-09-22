# Jhaily

Automated monthly sales reports for small businesses. A business owner uploads a sales
export (or connects a live spreadsheet link) once, and every month afterward, Jhaily
cleans the data, analyzes it, and emails a report — no dashboard to check, nothing to
remember.

## What it does

- **Cleans genuinely messy real-world data**: mixed date formats, missing prices,
  inconsistent item-name casing, duplicate rows
- **Computes real business metrics**: monthly revenue trend, best-selling item and
  category, busiest/slowest weekday, average transaction value (refund-corrected),
  refund rate, and payment method mix
- **Sends a styled HTML email** with an embedded chart, plus a downloadable PDF version
  of the same report
- **Runs on a schedule** automatically, once a month, via APScheduler
- **Real user accounts**: register/login/logout, with securely hashed passwords
  (never stored or readable as plaintext)
- **Multi-business support**: one account can track several businesses, each with its
  own recipient email and data source
- **Flexible data sources**: upload a CSV directly, or point at a live link (e.g. a
  published Google Sheets CSV export) so the report always uses current data with no
  manual re-upload
- **Real unsubscribe**: a unique link per business, included in every email

## Tech stack

- **Backend**: Flask
- **Database**: Flask-SQLAlchemy (SQLite)
- **Auth**: Flask-Login, with Werkzeug's password hashing
- **Data processing**: pandas
- **Charts**: matplotlib
- **PDF generation**: xhtml2pdf
- **Scheduling**: APScheduler
- **Email**: smtplib (Gmail SMTP)

## Project structure

```
extensions.py        # Shared Flask app/db/login setup (avoids circular imports)
models.py            # User and Business (subscription) database models
app.py               # Web routes: register, login, dashboard, add/update business, unsubscribe
generate_report.py   # The actual data pipeline, email/PDF generation, and the monthly scheduler
templates/           # HTML pages (landing, login, register, dashboard, unsubscribe confirmation)
```

## Setup

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

3. Copy `.env.example` to `.env` and fill in your real values (a Gmail address with an
   [App Password](https://myaccount.google.com/apppasswords), and a random secret key).

4. Run the web app:
   ```
   python app.py
   ```
   Visit `http://127.0.0.1:5000`.

5. Run the monthly scheduler separately (in its own terminal, for it to actually send
   reports on schedule):
   ```
   python generate_report.py
   ```

## Notes

- SQLite database and uploaded files are created locally (`instance/`, `uploads/`) and
  are excluded from version control, along with `.env` — see `.gitignore`.
- Currently configured for Gmail's SMTP server; swapping to another provider or a
  transactional email service (SendGrid, Mailgun, etc.) only requires changing the
  SMTP connection details in `generate_report.py`.
