"""
One-off migration: adds product_id, quantity, total_price columns to the
existing `orders` table.

Why this is needed: Base.metadata.create_all() (used in seed_db.py) only
creates tables that don't exist yet -- it will NOT alter a table that's
already there. Since `orders` already exists from your first seed run,
the new columns on the Order model won't show up in the actual database
until you run this once.

Usage:
    python migrate_add_order_columns.py
"""

from sqlalchemy import text
from app.database import engine

STATEMENTS = [
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS product_id VARCHAR",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS quantity INTEGER",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS total_price FLOAT",
]


def migrate():
    with engine.begin() as conn:
        for stmt in STATEMENTS:
            print(f"Running: {stmt}")
            conn.execute(text(stmt))
    print("Done.")


if __name__ == "__main__":
    migrate()
