from __future__ import annotations

import pandas as pd

COMMISSION_RATES: dict[str, float] = {
    "Косметика": 0.15,
    "Электроника": 0.10,
    "Игрушки": 0.12,
    "Одежда": 0.23,
    "Прочее": 0.18,
}
LOGISTICS_RATE: float = 80.0
RETURN_LOGISTICS_COEF: float = 1.5
DEFAULT_WEIGHT_KG: float = 0.5

# Flexible aliases — validator uses one name, generator uses another
_PURCHASE_PRICE_ALIASES = ["Закупочная цена", "Себестоимость"]
_QTY_SOLD_ALIASES = ["Продано штук", "Количество продаж"]


def _find_column(df: pd.DataFrame, aliases: list[str]) -> str:
    for col in aliases:
        if col in df.columns:
            return col
    raise ValueError(
        f"Не найдена ни одна из обязательных колонок: {aliases}. "
        f"Имеющиеся колонки: {df.columns.tolist()}"
    )


def calculate_margin(
    purchases_df: pd.DataFrame,
    sales_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate WB margin per SKU.

    Returns DataFrame: Артикул, выручка_чистая, комиссия_сумма,
    логистика_итого, затраты_закупка, прибыль, маржа_%, зона.

    Raises ValueError if артикулы sets differ between files.
    """
    # Cast Артикул to str in copies to avoid int/str type mismatch in both the
    # set-comparison and merge (original DataFrames are not mutated).
    purchases_df = purchases_df.copy()
    purchases_df["Артикул"] = purchases_df["Артикул"].astype(str)
    sales_df = sales_df.copy()
    sales_df["Артикул"] = sales_df["Артикул"].astype(str)

    p_articles = set(purchases_df["Артикул"])
    s_articles = set(sales_df["Артикул"])
    if p_articles != s_articles:
        missing_in_sales = sorted(p_articles - s_articles)
        missing_in_purchases = sorted(s_articles - p_articles)
        parts: list[str] = []
        if missing_in_sales:
            parts.append(f"нет в продажах: {missing_in_sales}")
        if missing_in_purchases:
            parts.append(f"нет в закупках: {missing_in_purchases}")
        raise ValueError(f"Артикулы не совпадают — {'; '.join(parts)}")

    price_col = _find_column(purchases_df, _PURCHASE_PRICE_ALIASES)
    qty_col = _find_column(sales_df, _QTY_SOLD_ALIASES)

    p_cols = ["Артикул", price_col]
    if "Категория WB" in purchases_df.columns:
        p_cols.append("Категория WB")
    if "Вес (кг)" in purchases_df.columns:
        p_cols.append("Вес (кг)")

    s_cols = ["Артикул", "Цена продажи", qty_col]
    if "Возвраты штук" in sales_df.columns:
        s_cols.append("Возвраты штук")
    if "Комиссия WB %" in sales_df.columns:
        s_cols.append("Комиссия WB %")

    merged = pd.merge(
        purchases_df[p_cols],
        sales_df[s_cols],
        on="Артикул",
        how="inner",
    ).rename(columns={price_col: "_purchase_price", qty_col: "_qty_sold"})

    if "Вес (кг)" not in merged.columns:
        merged["Вес (кг)"] = DEFAULT_WEIGHT_KG
    else:
        merged["Вес (кг)"] = merged["Вес (кг)"].fillna(DEFAULT_WEIGHT_KG)

    if "Возвраты штук" not in merged.columns:
        merged["Возвраты штук"] = 0
    else:
        merged["Возвраты штук"] = merged["Возвраты штук"].fillna(0)

    if "Категория WB" not in merged.columns:
        merged["Категория WB"] = "Прочее"

    sold = merged["_qty_sold"].astype(float)
    returns = merged["Возвраты штук"].astype(float)
    price = merged["Цена продажи"].astype(float)
    purchase = merged["_purchase_price"].astype(float)
    weight = merged["Вес (кг)"].astype(float)
    category = merged["Категория WB"].astype(str)

    # Avoid division by zero when sold = 0; clamp to [0, 1] against bad data
    safe_sold = sold.where(sold > 0, other=pd.NA)
    return_coef = (returns / safe_sold).fillna(0.0).clip(lower=0.0, upper=1.0)

    выручка_чистая = price * sold * (1.0 - return_coef)

    if "Комиссия WB %" in merged.columns:
        commission_rate = merged["Комиссия WB %"].astype(float) / 100.0
    else:
        commission_rate = category.map(
            lambda c: COMMISSION_RATES.get(str(c), COMMISSION_RATES["Прочее"])
        )

    комиссия_сумма = выручка_чистая * commission_rate

    logistics_forward = weight * LOGISTICS_RATE * sold
    logistics_return = weight * LOGISTICS_RATE * returns * RETURN_LOGISTICS_COEF
    логистика_итого = logistics_forward + logistics_return

    # Returned items come back to the seller — only net-sold units incur COGS
    затраты_закупка = purchase * (sold - returns)

    прибыль = выручка_чистая - комиссия_сумма - логистика_итого - затраты_закупка

    # Margin as % of net revenue; 0 when net revenue is 0 (e.g. 100% returns)
    safe_revenue = выручка_чистая.where(выручка_чистая != 0, other=pd.NA)
    маржа_pct = (прибыль / safe_revenue * 100.0).fillna(0.0)

    def _zone(m: float) -> str:
        if m > 25.0:
            return "GREEN"
        if m >= 10.0:
            return "YELLOW"
        return "RED"

    зона = маржа_pct.map(_zone)

    return pd.DataFrame(
        {
            "Артикул": merged["Артикул"],
            "выручка_чистая": выручка_чистая.round(2),
            "комиссия_сумма": комиссия_сумма.round(2),
            "логистика_итого": логистика_итого.round(2),
            "затраты_закупка": затраты_закупка.round(2),
            "прибыль": прибыль.round(2),
            "маржа_%": маржа_pct.round(2),
            "зона": зона,
        }
    ).reset_index(drop=True)
