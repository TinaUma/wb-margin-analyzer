from __future__ import annotations

import asyncio
import io
import logging

import pandas as pd

from backend.db import get_session_factory
from backend.models.models import AnalysisSession, Product
from backend.services.analyzer import (
    DEFAULT_WEIGHT_KG,
    _PURCHASE_PRICE_ALIASES,
    _QTY_SOLD_ALIASES,
    calculate_margin,
)

logger = logging.getLogger(__name__)


def _pick_col(df: pd.DataFrame, aliases: list[str]) -> str | None:
    for col in aliases:
        if col in df.columns:
            return col
    return None


async def _mark_failed(session_id: int) -> None:
    """Open a fresh session to mark analysis as failed (called after rollback)."""
    try:
        async with get_session_factory()() as db:
            analysis = await db.get(AnalysisSession, session_id)
            if analysis:
                analysis.status = "failed"
                await db.commit()
    except Exception:
        logger.exception("Failed to mark session %s as failed", session_id)


async def run_analysis(
    session_id: int,
    purchases_bytes: bytes,
    sales_bytes: bytes,
) -> None:
    """Execute margin analysis in the background and persist per-product results.

    On success: sets AnalysisSession.status = 'done', creates one Product row per article.
    On failure: rolls back, opens a new session, sets status = 'failed'.
    Expected columns — purchases: Артикул, Себестоимость/Закупочная цена, [Название, Категория WB, Вес (кг)]
                      sales:     Артикул, Цена продажи, Продано штук/Количество продаж, [Комиссия WB %, Возвраты штук]
    """
    loop = asyncio.get_running_loop()

    async with get_session_factory()() as db:
        analysis = await db.get(AnalysisSession, session_id)
        if analysis is None:
            return

        try:
            purchases_df = await loop.run_in_executor(
                None, lambda: pd.read_excel(io.BytesIO(purchases_bytes))
            )
            sales_df = await loop.run_in_executor(
                None, lambda: pd.read_excel(io.BytesIO(sales_bytes))
            )

            result_df = await loop.run_in_executor(
                None, calculate_margin, purchases_df, sales_df
            )

            # Build O(1) lookup indices (mirrors calculate_margin's internal str cast)
            p = purchases_df.copy()
            p["Артикул"] = p["Артикул"].astype(str)
            s = sales_df.copy()
            s["Артикул"] = s["Артикул"].astype(str)
            p_idx = p.set_index("Артикул")
            s_idx = s.set_index("Артикул")

            price_col = (
                _pick_col(p, _PURCHASE_PRICE_ALIASES) or _PURCHASE_PRICE_ALIASES[0]
            )
            qty_col = _pick_col(s, _QTY_SOLD_ALIASES) or _QTY_SOLD_ALIASES[0]

            products: list[Product] = []
            for _, row in result_df.iterrows():
                article = row["Артикул"]
                if article not in p_idx.index or article not in s_idx.index:
                    logger.warning(
                        "Article %r missing from lookup index — skipped", article
                    )
                    continue

                p_row = p_idx.loc[article]
                s_row = s_idx.loc[article]

                name = (
                    str(p_row["Название"]) if "Название" in p_idx.columns else article
                )
                category = (
                    str(p_row["Категория WB"])
                    if "Категория WB" in p_idx.columns
                    else "Прочее"
                )
                purchase_price = float(p_row[price_col])
                sale_price = float(s_row["Цена продажи"])
                weight = (
                    float(p_row["Вес (кг)"])
                    if "Вес (кг)" in p_idx.columns
                    else DEFAULT_WEIGHT_KG
                )
                sold = int(s_row[qty_col])
                returns_val = (
                    int(s_row["Возвраты штук"])
                    if "Возвраты штук" in s_idx.columns
                    else 0
                )

                products.append(
                    Product(
                        session_id=session_id,
                        article=article,
                        name=name,
                        category=category,
                        purchase_price=purchase_price,
                        sale_price=sale_price,
                        weight=weight,
                        sold=sold,
                        returns=returns_val,
                        net_revenue=float(row["выручка_чистая"]),
                        commission=float(row["комиссия_сумма"]),
                        logistics_total=float(row["логистика_итого"]),
                        purchase_cost=float(row["затраты_закупка"]),
                        profit=float(row["прибыль"]),
                        margin_pct=float(row["маржа_%"]),
                        margin_zone=row["зона"].lower(),
                    )
                )

            db.add_all(products)
            analysis.status = "done"
            await db.commit()

        except Exception:
            logger.exception("run_analysis failed for session_id=%s", session_id)
            await db.rollback()

    # Use a fresh session to write 'failed' so we don't rely on a rolled-back session
    if analysis.status != "done":
        await _mark_failed(session_id)
