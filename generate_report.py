#!/usr/bin/env python3
import os
import smtplib
import base64

import matplotlib
import pandas as pd
from dateutil import parser
from email.message import EmailMessage
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from xhtml2pdf import pisa


def generate_and_send_report(sales_file, recipient_email, unsubscribe_token=None):
  import uuid
  run_id = uuid.uuid4().hex
  chart_path = f"revenue_chart_{run_id}.png"
  pdf_path = f"report_{run_id}.pdf"

  df = pd.read_csv(sales_file)
  required_columns = {"date", "item", "quantity", "unit_price"}
  missing = required_columns - set(df.columns)
  if missing:
    raise ValueError(f"Your file is missing required column(s): {', '.join(missing)}")

  df = df.drop_duplicates()

  def clean_date(raw_string):
    try:
      return parser.parse(raw_string).date()
    except (parser.ParserError, TypeError):
      return None

  df["sale_date"] = df["date"].apply(clean_date)
  df["sale_date"] = pd.to_datetime(df["sale_date"])
  df["item"] = df["item"].fillna("unknown item")
  df["item"] = df["item"].str.strip().str.title()
  typical_prices = df.groupby("item")["unit_price"].transform(lambda x: x.mode()[0])
  df["unit_price"] = df["unit_price"].fillna(typical_prices)
  df["revenue"] = df["quantity"] * df["unit_price"]

  monthly_revenue = df.groupby(df["sale_date"].dt.to_period("M"))["revenue"].sum()
  best_selling_item = df.groupby(df["item"])["revenue"].sum()
  top_item = best_selling_item.idxmax()
  df["weekday_name"] = df["sale_date"].dt.day_name()
  weekly_day_sales = df.groupby(df["weekday_name"])["revenue"].sum()
  real_sales = df[df["quantity"] > 0]
  monthly_real_revenue = real_sales.groupby(real_sales["sale_date"].dt.to_period("M"))["revenue"].sum()
  monthly_transactions_count = real_sales.groupby(real_sales["sale_date"].dt.to_period("M"))["quantity"].count()
  average_transaction_value = monthly_real_revenue / monthly_transactions_count
  total_revenue_per_category = df.groupby(df["category"])["revenue"].sum()
  top_category = total_revenue_per_category.idxmax()
  total_transaction_count = df.groupby(df["sale_date"].dt.to_period("M"))["quantity"].count()
  refunds = df[df["quantity"] < 0]
  refunds_count = refunds.groupby(refunds["sale_date"].dt.to_period("M"))["quantity"].count()
  total_refunds = refunds.groupby(refunds["sale_date"].dt.to_period("M"))["revenue"].sum()
  refund_percentage = (refunds_count / total_transaction_count) * 100
  total_paymentmethod_count = df.groupby(df["payment_method"])["revenue"].sum()
  percentage_payment_split = (total_paymentmethod_count / total_paymentmethod_count.sum()) * 100
  slowest_day = weekly_day_sales.idxmin()
  busiest_day = weekly_day_sales.idxmax()
  latest_month = monthly_revenue.index[-1]
  latest_avg_transaction = average_transaction_value.iloc[-1]
  latest_revenue = monthly_revenue.iloc[-1]
  monthly_growth = monthly_revenue.pct_change()
  latest_growth = monthly_growth.iloc[-1]
  latest_refund_total = total_refunds.iloc[-1] if len(total_refunds) else 0
  latest_refund_pct = refund_percentage.iloc[-1] if len(refund_percentage) else 0
  card_pct = percentage_payment_split.get("Card", 0)
  cash_pct = percentage_payment_split.get("Cash", 0)
  mobile_pct = percentage_payment_split.get("Mobile", 0)

  msg = EmailMessage()
  summary = f"""In {latest_month.strftime("%B %Y")}, revenue was ${latest_revenue}, a change of {latest_growth:.1%} from last month.
Customers spent an average of ${latest_avg_transaction:.2f} per visit.
{top_category} was your strongest category, and {top_item} was your top-selling item overall.
{busiest_day}s tend to have the highest sales and {slowest_day}s tend to have the lowest sales.
You had ${abs(latest_refund_total):.2f} in refunds this month, about {latest_refund_pct:.1f}% of your transactions."""
  growth_color = "green" if latest_growth >= 0 else "red"

  unsubscribe_html = ""
  if unsubscribe_token:
    unsubscribe_html = f'<p style="font-size:12px; color:#4A5568;">Don\'t want these emails? <a href="https://jhaily.app/unsubscribe/{unsubscribe_token}">Unsubscribe</a>.</p>'

  html_body = f"""
    <html><body style="font-family: Arial, sans-serif; color: #1E2A3A; max-width: 480px; margin: 0 auto;">
      <div style="background:#1E2A3A; padding: 18px 24px; border-radius: 4px 4px 0 0;">
        <span style="color:white; font-family: Georgia, serif; font-size: 20px;">Jhai<span style="color:#3C6E52;">ly</span></span>
      </div>
      <div style="padding: 24px; border: 1px solid #DAD5C7; border-top: none;">
        <p>Hi there,</p>
        <p>Here's how {latest_month.strftime("%B")} went for your business.</p>
        <img src="cid:chart" alt="Monthly Revenue Chart" style="width:100%; max-width:420px;">
        <p>Revenue: <strong>${latest_revenue:,.2f}</strong></p>
        <p>Change from last month: <strong style="color:{growth_color};">{latest_growth:.1%}</strong></p>
        <p>Top-selling item: <strong>{top_item}</strong></p>
        <p><b>{busiest_day}s</b> tend to have the highest sales.<br><b>{slowest_day}s</b> tend to have the lowest sales.</p>
        <p>Average sale: <strong>${latest_avg_transaction:,.2f}</strong></p>
        <p>Top category: <strong>{top_category}</strong></p>
        <p>Refunds: <strong>${abs(latest_refund_total):,.2f}</strong> ({latest_refund_pct:.1f}% of transactions)</p>
        <p>Payment mix: Card {card_pct:.0f}% &middot; Cash {cash_pct:.0f}% &middot; Mobile {mobile_pct:.0f}%</p>
        <p>Your full report is attached as a PDF if you'd like to save or share it.</p>
      </div>
      {unsubscribe_html}
    </body></html>
  """

  def format_currency(x, position):
    return f"${x:,.0f}"

  x_values = monthly_revenue.index.strftime("%b %Y")
  y_values = monthly_revenue.values
  plt.gca().yaxis.set_major_formatter(FuncFormatter(format_currency))
  plt.bar(x_values, y_values)
  plt.title("Monthly Revenue")
  plt.savefig(chart_path)
  plt.close()

  with open(chart_path, "rb") as f:
    image_data = f.read()

  msg.set_content(summary)
  msg.add_alternative(html_body, subtype="html")
  msg.get_payload()[1].add_related(image_data, "image", "png", cid="chart")

  encoded_chart = base64.b64encode(image_data).decode("utf-8")
  pdf_html = html_body.replace('src="cid:chart"', f'src="data:image/png;base64,{encoded_chart}"')
  with open(pdf_path, "wb") as f:
    pisa.CreatePDF(pdf_html, dest=f)
  with open(pdf_path, "rb") as f:
    pdf_data = f.read()
  msg.add_attachment(pdf_data, maintype="application", subtype="pdf", filename="monthly_report.pdf")

  # Clean up the temporary per-run files now that their bytes are safely inside `msg`
  os.remove(chart_path)
  os.remove(pdf_path)

  msg["Subject"] = "Your Monthly Sales Report"
  msg["From"] = f"Jhaily <{os.environ['GMAIL_SENDER']}>"
  msg["To"] = recipient_email

  gmail_user = os.environ["GMAIL_SENDER"]
  gmail_password = os.environ["GMAIL_APP_PASSWORD"]

  with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(gmail_user, gmail_password)
    server.send_message(msg)


if __name__ == "__main__":
  from apscheduler.schedulers.blocking import BlockingScheduler
  from extensions import app
  from models import Business

  def run_all_active_businesses():
    with app.app_context():
      active_businesses = Business.query.filter_by(active=True).all()
      for business in active_businesses:
        try:
          generate_and_send_report(business.sales_file_path, business.recipient_email, business.unsubscribe_token)
        except Exception as e:
          print(f"Failed to send report for business {business.id} ({business.name}): {e}")

  scheduler = BlockingScheduler()
  scheduler.add_job(run_all_active_businesses, "cron", day=1, hour=8)
  scheduler.start()
