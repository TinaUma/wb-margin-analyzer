"""Unit tests for backend/services/file_validator.py — all 6 AC."""

from __future__ import annotations

import pytest

from backend.services.file_validator import (
    ExcelParseError,
    UnsupportedExtensionError,
    validate_purchases,
    validate_sales,
)
from tests.conftest import make_xlsx


# ── AC-1: correct shape ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_purchases_returns_correct_shape(purchases_xlsx):
    result = await validate_purchases(purchases_xlsx, "purchases.xlsx")
    assert isinstance(result.columns_detected, list)
    assert result.rows_count == 4
    assert isinstance(result.issues, list)
    assert len(result.preview) == 3  # capped at MAX_PREVIEW_ROWS


@pytest.mark.asyncio
async def test_validate_sales_returns_correct_shape(sales_xlsx):
    result = await validate_sales(sales_xlsx, "sales.xlsx")
    assert result.rows_count == 4
    assert len(result.preview) == 3


@pytest.mark.asyncio
async def test_preview_capped_at_three_rows_even_for_large_file():
    data = make_xlsx(
        ["Артикул", "Себестоимость", "Вес"],
        [["SKU-%03d" % i, i * 100, 0.5] for i in range(50)],
    )
    result = await validate_purchases(data, "big.xlsx")
    assert len(result.preview) == 3
    assert result.rows_count == 50


# ── AC-2: missing required column → warning, not error ───────────────────────


@pytest.mark.asyncio
async def test_missing_cost_column_adds_issue_not_error(
    purchases_no_cost_xlsx, sales_xlsx
):
    result = await validate_purchases(purchases_no_cost_xlsx, "p.xlsx")
    assert any("Себестоимость" in i for i in result.issues)


@pytest.mark.asyncio
async def test_missing_sales_required_column_adds_issue():
    data = make_xlsx(
        ["Артикул", "Цена продажи"],  # missing Количество продаж and Комиссия WB %
        [["SKU-001", 1200]],
    )
    result = await validate_sales(data, "s.xlsx")
    assert any("Количество продаж" in i for i in result.issues)
    assert any("Комиссия WB %" in i for i in result.issues)


# ── AC-3: missing Вес → logistics warning ────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_ves_adds_logistics_warning(purchases_no_ves_xlsx):
    result = await validate_purchases(purchases_no_ves_xlsx, "p.xlsx")
    assert any("логистика рассчитана по среднему 0.5 кг" in i for i in result.issues)


@pytest.mark.asyncio
async def test_present_ves_no_logistics_warning(purchases_xlsx):
    result = await validate_purchases(purchases_xlsx, "p.xlsx")
    assert not any("0.5 кг" in i for i in result.issues)


# ── AC-4: corrupt file → ExcelParseError (→ 422 at router level) ─────────────


@pytest.mark.asyncio
async def test_corrupt_bytes_raises_excel_parse_error():
    with pytest.raises(ExcelParseError):
        await validate_purchases(b"\x00\x01\x02\x03" * 100, "bad.xlsx")


@pytest.mark.asyncio
async def test_valid_zip_invalid_ooxml_raises_excel_parse_error():
    # Valid ZIP magic bytes but not a real XLSX structure
    bad = b"PK\x03\x04" + b"\x00" * 200
    with pytest.raises(ExcelParseError):
        await validate_purchases(bad, "fake.xlsx")


# ── AC-5: empty file → ValueError (→ 400 at router level) ────────────────────


@pytest.mark.asyncio
async def test_empty_dataframe_raises_value_error():
    data = make_xlsx(["Артикул", "Себестоимость"], [])
    with pytest.raises(ValueError, match="пустой"):
        await validate_purchases(data, "empty.xlsx")


@pytest.mark.asyncio
async def test_empty_sales_raises_value_error():
    data = make_xlsx(
        ["Артикул", "Цена продажи", "Количество продаж", "Комиссия WB %"], []
    )
    with pytest.raises(ValueError, match="пустой"):
        await validate_sales(data, "empty.xlsx")


# ── AC-6: wrong extension → UnsupportedExtensionError (→ 415 at router) ──────


@pytest.mark.asyncio
async def test_csv_extension_raises_unsupported_extension():
    with pytest.raises(UnsupportedExtensionError):
        await validate_purchases(b"col1,col2\n1,2", "file.csv")


@pytest.mark.asyncio
async def test_pdf_extension_raises_unsupported_extension():
    with pytest.raises(UnsupportedExtensionError):
        await validate_purchases(b"%PDF-1.4", "report.pdf")


@pytest.mark.asyncio
async def test_no_extension_raises_unsupported_extension():
    with pytest.raises(UnsupportedExtensionError):
        await validate_purchases(b"data", "noextension")
