"""Unit tests for backend/services/analyzer.py — all 5 AC."""

from __future__ import annotations

import pandas as pd
import pytest

from backend.services.analyzer import (
    LOGISTICS_RATE,
    RETURN_LOGISTICS_COEF,
    calculate_margin,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _purchases(
    articles: list,
    prices: list,
    weights: list | None = None,
    categories: list | None = None,
) -> pd.DataFrame:
    d: dict = {"Артикул": articles, "Закупочная цена": prices}
    if weights is not None:
        d["Вес (кг)"] = weights
    if categories is not None:
        d["Категория WB"] = categories
    return pd.DataFrame(d)


def _sales(
    articles: list,
    prices: list,
    sold: list,
    returns: list | None = None,
) -> pd.DataFrame:
    d: dict = {"Артикул": articles, "Цена продажи": prices, "Продано штук": sold}
    if returns is not None:
        d["Возвраты штук"] = returns
    return pd.DataFrame(d)


# ── AC-1: correct output shape and field values ───────────────────────────────


def test_all_output_columns_present():
    p = _purchases(["SKU-1"], [500], weights=[1.0], categories=["Косметика"])
    s = _sales(["SKU-1"], [1000], [10], returns=[2])
    result = calculate_margin(p, s)
    for col in (
        "Артикул",
        "выручка_чистая",
        "комиссия_сумма",
        "логистика_итого",
        "затраты_закупка",
        "прибыль",
        "маржа_%",
        "зона",
    ):
        assert col in result.columns, f"Missing column: {col}"


def test_normal_single_sku_values():
    """Verify exact formula values for one SKU (Косметика, 15% commission)."""
    # return_coef = 2/10 = 0.2
    # net_revenue = 1000*10*0.8 = 8000
    # commission = 8000*0.15 = 1200
    # logistics_fwd = 1.0*80*10 = 800, logistics_ret = 1.0*80*2*1.5 = 240
    # затраты_закупка = 500*(10-2) = 4000  ← returned units come back, no net COGS
    # profit = 8000 - 1200 - 1040 - 4000 = 1760
    # margin% = 1760/8000*100 = 22.0 → YELLOW
    p = _purchases(["SKU-1"], [500], weights=[1.0], categories=["Косметика"])
    s = _sales(["SKU-1"], [1000], [10], returns=[2])
    row = calculate_margin(p, s).iloc[0]

    assert row["выручка_чистая"] == pytest.approx(8000.0)
    assert row["комиссия_сумма"] == pytest.approx(1200.0)
    assert row["логистика_итого"] == pytest.approx(1040.0)
    assert row["затраты_закупка"] == pytest.approx(4000.0)
    assert row["прибыль"] == pytest.approx(1760.0)
    assert row["маржа_%"] == pytest.approx(22.0)
    assert row["зона"] == "YELLOW"


# ── AC-2: return logistics ×1.5 coefficient ──────────────────────────────────


def test_returns_logistics_coefficient_1_5():
    """Returns logistics must be ×1.5 forward rate."""
    # purchase=0 to isolate logistics; no commission column → Прочее 18%
    p = _purchases(["SKU-1"], [0], weights=[1.0], categories=["Прочее"])
    s = _sales(["SKU-1"], [1000], [10], returns=[4])
    row = calculate_margin(p, s).iloc[0]

    expected_fwd = 1.0 * LOGISTICS_RATE * 10  # 800
    expected_ret = 1.0 * LOGISTICS_RATE * 4 * RETURN_LOGISTICS_COEF  # 480
    assert row["логистика_итого"] == pytest.approx(expected_fwd + expected_ret)


def test_zero_returns_no_return_logistics():
    """When returns=0 only forward logistics exist."""
    p = _purchases(["SKU-1"], [300], weights=[0.5], categories=["Прочее"])
    s = _sales(["SKU-1"], [1000], [10], returns=[0])
    row = calculate_margin(p, s).iloc[0]

    assert row["выручка_чистая"] == pytest.approx(10000.0)
    assert row["логистика_итого"] == pytest.approx(0.5 * LOGISTICS_RATE * 10)


# ── AC-3: color zone boundaries ──────────────────────────────────────────────


def test_boundary_exactly_10_percent_is_yellow():
    """Margin = 10.0% → YELLOW (not RED)."""
    # price=1000, sold=1, weight=0.5, cat=Прочее, purchase=680
    # net=1000, commission=180, logistics=40, purchase_cost=680 → profit=100 → 10%
    p = _purchases(["SKU-1"], [680], weights=[0.5], categories=["Прочее"])
    s = _sales(["SKU-1"], [1000], [1], returns=[0])
    row = calculate_margin(p, s).iloc[0]

    assert row["маржа_%"] == pytest.approx(10.0)
    assert row["зона"] == "YELLOW"


def test_boundary_exactly_25_percent_is_yellow():
    """Margin = 25.0% → YELLOW (not GREEN — zone requires >25)."""
    # net=1000, commission=180, logistics=40, purchase_cost=530 → profit=250 → 25%
    p = _purchases(["SKU-1"], [530], weights=[0.5], categories=["Прочее"])
    s = _sales(["SKU-1"], [1000], [1], returns=[0])
    row = calculate_margin(p, s).iloc[0]

    assert row["маржа_%"] == pytest.approx(25.0)
    assert row["зона"] == "YELLOW"


def test_above_25_percent_is_green():
    """Margin > 25% → GREEN."""
    p = _purchases(["SKU-1"], [100], weights=[0.1], categories=["Прочее"])
    s = _sales(["SKU-1"], [1000], [10], returns=[0])
    row = calculate_margin(p, s).iloc[0]
    # net=10000, commission=1800, logistics=80, purchase=1000 → profit=7120 → 71.2%
    assert row["маржа_%"] == pytest.approx(71.2)
    assert row["зона"] == "GREEN"


def test_below_10_percent_is_red():
    """Margin < 10% → RED."""
    # price=500, sold=10, returns=0, purchase=500, weight=2.0, cat=Одежда 23%
    # net=5000, commission=1150, logistics=1600, purchase_cost=5000 → profit=-750 → RED
    p = _purchases(["SKU-1"], [500], weights=[2.0], categories=["Одежда"])
    s = _sales(["SKU-1"], [500], [10], returns=[0])
    row = calculate_margin(p, s).iloc[0]
    assert row["зона"] == "RED"


# ── AC-4: unknown category falls back to Прочее 18% ─────────────────────────


def test_unknown_category_uses_prochee_18_percent():
    p = _purchases(["SKU-1"], [0], weights=[0.0], categories=["НеизвестнаяКатегория"])
    s = _sales(["SKU-1"], [1000], [10], returns=[0])
    row = calculate_margin(p, s).iloc[0]

    # net_revenue=10000, commission should be 18% (Прочее fallback)
    assert row["комиссия_сумма"] == pytest.approx(10000.0 * 0.18)


def test_100_percent_returns_zone_red_margin_zero():
    """All items returned: net_revenue=0, margin%=0 → RED."""
    p = _purchases(["SKU-1"], [500], weights=[1.0], categories=["Прочее"])
    s = _sales(["SKU-1"], [1000], [5], returns=[5])
    row = calculate_margin(p, s).iloc[0]

    # logistics_fwd = 1.0*80*5=400, logistics_ret = 1.0*80*5*1.5=600 → total=1000
    # затраты_закупка = 500*(5-5)=0 (returned units come back)
    # profit = 0 - 0 - 1000 - 0 = -1000
    assert row["выручка_чистая"] == pytest.approx(0.0)
    assert row["затраты_закупка"] == pytest.approx(0.0)
    assert row["маржа_%"] == pytest.approx(0.0)
    assert row["зона"] == "RED"
    assert row["прибыль"] == pytest.approx(-1000.0)  # only logistics costs remain


# ── AC-5: mismatched артикулы → ValueError ────────────────────────────────────


def test_mismatched_articles_raises_value_error():
    p = _purchases(["SKU-1", "SKU-2"], [100, 200])
    s = _sales(["SKU-1", "SKU-3"], [500, 600], [10, 10])
    with pytest.raises(ValueError, match="Артикул"):
        calculate_margin(p, s)


# ── optional: missing Вес defaults to 0.5 kg ─────────────────────────────────


def test_missing_weight_defaults_to_0_5_kg():
    p = _purchases(["SKU-1"], [300], categories=["Прочее"])  # no weight column
    s = _sales(["SKU-1"], [1000], [10], returns=[0])
    row = calculate_margin(p, s).iloc[0]

    assert row["логистика_итого"] == pytest.approx(0.5 * LOGISTICS_RATE * 10)
