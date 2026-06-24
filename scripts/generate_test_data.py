"""
Generate test Excel files for WB Margin Analyzer.

Produces:
  purchases.xlsx  — Артикул, Название, Закупочная цена, Категория WB, Вес (кг)
  sales.xlsx      — Артикул, Цена продажи, Продано штук, Возвраты штук

20 products across 4 WB categories with varied margin levels:
  ~5 green  (margin > 25%)
  ~10 yellow (margin 10-25%)
  ~5 red    (margin < 10% or negative)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Force UTF-8 output on Windows (cp1251 can't render emoji/Cyrillic together)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMMISSION_RATES = {
    "Косметика": 0.15,
    "Электроника": 0.10,
    "Игрушки": 0.12,
    "Одежда": 0.23,
    "Прочее": 0.18,
}
LOGISTICS_RATE = 80  # руб/кг
RETURN_LOGISTICS_COEF = 1.5


def compute_margin(purchase, sale, weight, category, sold, returns):
    """Return (profit, margin_pct) using ТЗ v2.0 formulas."""
    if sold == 0:
        return 0.0, 0.0
    return_coef = returns / sold
    net_revenue = sale * sold * (1 - return_coef)
    commission = net_revenue * COMMISSION_RATES.get(category, 0.18)
    logistics_forward = weight * LOGISTICS_RATE * sold
    logistics_return = weight * LOGISTICS_RATE * returns * RETURN_LOGISTICS_COEF
    purchase_cost = purchase * sold
    profit = (
        net_revenue - commission - logistics_forward - logistics_return - purchase_cost
    )
    margin_pct = (profit / net_revenue * 100) if net_revenue else 0
    return profit, margin_pct


def margin_zone(margin_pct):
    if margin_pct > 25:
        return "🟢 GREEN"
    if margin_pct >= 10:
        return "🟡 YELLOW"
    return "🔴 RED"


# fmt: off
PRODUCTS = [
    # --- GREEN (>25%) ---
    # Косметика — high markup, low returns, light weight
    {"article": "WB-K001", "name": "Крем для лица SPF50",         "purchase": 150,  "sale": 890,  "weight": 0.10, "category": "Косметика",   "sold": 120, "returns": 4},
    {"article": "WB-K002", "name": "Сыворотка гиалуроновая 30мл", "purchase": 280,  "sale": 1490, "weight": 0.12, "category": "Косметика",   "sold": 90,  "returns": 5},
    # Электроника — light accessory, very high markup
    {"article": "WB-E001", "name": "TWS наушники беспроводные",   "purchase": 380,  "sale": 1990, "weight": 0.25, "category": "Электроника", "sold": 75,  "returns": 4},
    {"article": "WB-E006", "name": "Чехол для смартфона",         "purchase": 60,   "sale": 590,  "weight": 0.08, "category": "Электроника", "sold": 200, "returns": 8},
    # Игрушки — premium constructor, good markup
    {"article": "WB-T001", "name": "LEGO конструктор 300 дет.",   "purchase": 450,  "sale": 1990, "weight": 0.80, "category": "Игрушки",     "sold": 95,  "returns": 4},

    # --- YELLOW (10-25%) ---
    # Косметика — heavier items, moderate margins
    {"article": "WB-K003", "name": "Мицеллярная вода 400мл",      "purchase": 350,  "sale": 590,  "weight": 0.45, "category": "Косметика",   "sold": 180, "returns": 12},
    {"article": "WB-K004", "name": "Тональный крем стойкий",      "purchase": 500,  "sale": 890,  "weight": 0.12, "category": "Косметика",   "sold": 65,  "returns": 7},
    # Электроника — bulkier products or compressed margins
    {"article": "WB-E002", "name": "Bluetooth колонка портатив.", "purchase": 1500, "sale": 2490, "weight": 0.60, "category": "Электроника", "sold": 55,  "returns": 5},
    {"article": "WB-E003", "name": "Зарядное устройство 65W",     "purchase": 560,  "sale": 890,  "weight": 0.30, "category": "Электроника", "sold": 120, "returns": 8},
    {"article": "WB-E004", "name": "Кабель USB-C 2м",             "purchase": 180,  "sale": 290,  "weight": 0.10, "category": "Электроника", "sold": 300, "returns": 15},
    # Игрушки — mid-range products
    {"article": "WB-T002", "name": "Кукла интерактивная",         "purchase": 850,  "sale": 1490, "weight": 0.70, "category": "Игрушки",     "sold": 70,  "returns": 8},
    {"article": "WB-T003", "name": "Набор для творчества",        "purchase": 450,  "sale": 790,  "weight": 0.50, "category": "Игрушки",     "sold": 150, "returns": 10},
    {"article": "WB-T004", "name": "Машинка р/у 1:24",            "purchase": 680,  "sale": 1190, "weight": 0.65, "category": "Игрушки",     "sold": 80,  "returns": 9},
    # Одежда — 23% commission squeezes margins
    {"article": "WB-O001", "name": "Платье летнее",               "purchase": 980,  "sale": 1990, "weight": 0.40, "category": "Одежда",      "sold": 85,  "returns": 15},
    {"article": "WB-O002", "name": "Джинсы классические",         "purchase": 1400, "sale": 2990, "weight": 0.70, "category": "Одежда",      "sold": 55,  "returns": 12},

    # --- RED (<10% or negative) ---
    # Косметика — high returns destroy margin
    {"article": "WB-K005", "name": "Помада стойкая",              "purchase": 420,  "sale": 650,  "weight": 0.08, "category": "Косметика",   "sold": 100, "returns": 28},
    # Электроника — heavy item, high purchase cost
    {"article": "WB-E005", "name": "Робот-пылесос",               "purchase": 4500, "sale": 5990, "weight": 3.50, "category": "Электроника", "sold": 30,  "returns": 6},
    # Игрушки — heavy, high returns, thin markup
    {"article": "WB-T005", "name": "Детская игровая палатка",     "purchase": 780,  "sale": 990,  "weight": 1.80, "category": "Игрушки",     "sold": 45,  "returns": 12},
    # Одежда — 23% commission + high returns = losses
    {"article": "WB-O003", "name": "Пуховик зимний",              "purchase": 2800, "sale": 3990, "weight": 1.20, "category": "Одежда",      "sold": 40,  "returns": 18},
    {"article": "WB-O004", "name": "Костюм спортивный",           "purchase": 1200, "sale": 1890, "weight": 0.60, "category": "Одежда",      "sold": 60,  "returns": 20},
]
# fmt: on


def build_dataframes():
    purchases_rows = []
    sales_rows = []

    for p in PRODUCTS:
        purchases_rows.append(
            {
                "Артикул": p["article"],
                "Название": p["name"],
                "Закупочная цена": p["purchase"],
                "Категория WB": p["category"],
                "Вес (кг)": p["weight"],
            }
        )
        sales_rows.append(
            {
                "Артикул": p["article"],
                "Цена продажи": p["sale"],
                "Продано штук": p["sold"],
                "Возвраты штук": p["returns"],
            }
        )

    return pd.DataFrame(purchases_rows), pd.DataFrame(sales_rows)


def print_margin_summary():
    print("\n--- Margin preview " + "-" * 53)
    print(f"{'Артикул':<10} {'Название':<32} {'Маржа%':>7}  Зона")
    print("-" * 72)
    counts = {"GREEN": 0, "YELLOW": 0, "RED": 0}
    for p in PRODUCTS:
        _, margin = compute_margin(
            p["purchase"],
            p["sale"],
            p["weight"],
            p["category"],
            p["sold"],
            p["returns"],
        )
        zone = margin_zone(margin)
        key = zone.split()[-1]
        counts[key] += 1
        print(f"{p['article']:<10} {p['name']:<32} {margin:>6.1f}%  {zone}")
    print("-" * 72)
    print(
        f"GREEN: {counts['GREEN']}  YELLOW: {counts['YELLOW']}  RED: {counts['RED']}  (total: {sum(counts.values())})"
    )
    print()


def main():
    parser = argparse.ArgumentParser(description="Generate WB test Excel files")
    parser.add_argument(
        "--output",
        "-o",
        default="data",
        help="Output directory (default: data/)",
    )
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    purchases_df, sales_df = build_dataframes()

    purchases_path = out_dir / "purchases.xlsx"
    sales_path = out_dir / "sales.xlsx"

    try:
        purchases_df.to_excel(purchases_path, index=False)
        sales_df.to_excel(sales_path, index=False)
    except (PermissionError, OSError) as exc:
        print(f"ERROR: Cannot write output files — {exc}", file=sys.stderr)
        print(
            "Tip: close the files in Excel if they are currently open.", file=sys.stderr
        )
        sys.exit(1)

    print(f"Generated: {purchases_path}  ({len(purchases_df)} rows)")
    print(f"Generated: {sales_path}  ({len(sales_df)} rows)")

    print_margin_summary()


if __name__ == "__main__":
    main()
