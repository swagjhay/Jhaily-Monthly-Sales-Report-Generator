"""
generate_fake_data.py

This simulates a "sales export" you'd download from a point-of-sale
system like Square. Real exports are messy, so we bake in the same
problems you'd hit with a real file:

- inconsistent date formats (some rows use MM/DD/YYYY, some use YYYY-MM-DD)
- occasional missing values (blank price, blank item name)
- extra whitespace / inconsistent capitalization in text fields
- a few duplicate rows (POS systems sometimes double-log a transaction)
- a couple of "refund" rows with negative amounts

Run this once to produce sample_sales.csv, which we'll treat as if a
real business owner uploaded it to our app.
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)  # so results are reproducible while we're learning

MENU = [
    ("Latte", "Drinks", 4.50),
    ("Cappuccino", "Drinks", 4.25),
    ("Drip Coffee", "Drinks", 2.75),
    ("Cold Brew", "Drinks", 4.75),
    ("Croissant", "Food", 3.25),
    ("Blueberry Muffin", "Food", 3.00),
    ("Avocado Toast", "Food", 7.50),
    ("Bagel", "Food", 2.95),
]

PAYMENT_METHODS = ["Card", "Cash", "Mobile"]

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2025, 4, 30)


def random_date():
    delta_days = (END_DATE - START_DATE).days
    return START_DATE + timedelta(days=random.randint(0, delta_days))


def format_date_messily(d):
    """Randomly pick one of a few date formats -- this is VERY common
    in real exports when data comes from different systems or was
    edited by hand in Excel at some point."""
    fmt = random.choice(["%m/%d/%Y", "%Y-%m-%d", "%d-%b-%Y"])
    return d.strftime(fmt)


def make_row(row_id):
    item, category, price = random.choice(MENU)
    qty = random.choice([1, 1, 1, 2, 2, 3])
    date = random_date()

    # Occasionally mess up the text fields like a human data-entry
    # mistake would
    if random.random() < 0.05:
        item = f"  {item.upper()}  "  # stray whitespace + shouting caps
    if random.random() < 0.03:
        item = ""  # missing item name entirely
    if random.random() < 0.03:
        price = ""  # missing price

    # Occasionally simulate a refund (negative sale)
    is_refund = random.random() < 0.02

    row = {
        "transaction_id": row_id,
        "date": format_date_messily(date),
        "item": item,
        "category": category,
        "quantity": -qty if is_refund else qty,
        "unit_price": price,
        "payment_method": random.choice(PAYMENT_METHODS),
    }
    return row


def main():
    rows = []
    for i in range(1, 1501):  # ~1500 transactions over 4 months
        rows.append(make_row(i))

    # Sprinkle in some exact duplicate rows, like a POS glitch
    for _ in range(15):
        rows.append(random.choice(rows).copy())

    random.shuffle(rows)

    with open("sample_sales.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to sample_sales.csv")


if __name__ == "__main__":
    main()
