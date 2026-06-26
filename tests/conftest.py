"""Shared pytest fixtures for WB Margin Analyzer tests."""

from __future__ import annotations

import io

import openpyxl
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.api.v1.deps import get_current_user
from backend.models.models import User


# ── Excel helpers ─────────────────────────────────────────────────────────────


def make_xlsx(columns: list[str], rows: list[list]) -> bytes:
    """Build an in-memory .xlsx with given header + data rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture()
def purchases_xlsx() -> bytes:
    return make_xlsx(
        ["Артикул", "Себестоимость", "Вес", "Название товара"],
        [
            ["SKU-001", 500, 0.3, "Товар 1"],
            ["SKU-002", 700, 0.5, "Товар 2"],
            ["SKU-003", 300, 0.2, "Товар 3"],
            ["SKU-004", 400, 0.4, "Товар 4"],
        ],
    )


@pytest.fixture()
def sales_xlsx() -> bytes:
    return make_xlsx(
        ["Артикул", "Цена продажи", "Количество продаж", "Комиссия WB %", "Возвраты"],
        [
            ["SKU-001", 1200, 10, 15, 1],
            ["SKU-002", 1500, 5, 15, 0],
            ["SKU-003", 900, 20, 15, 3],
            ["SKU-004", 1100, 8, 15, 2],
        ],
    )


@pytest.fixture()
def purchases_no_ves_xlsx() -> bytes:
    """Purchases file missing the Вес column."""
    return make_xlsx(
        ["Артикул", "Себестоимость", "Название товара"],
        [["SKU-001", 500, "Товар 1"]],
    )


@pytest.fixture()
def purchases_no_cost_xlsx() -> bytes:
    """Purchases file missing required Себестоимость column."""
    return make_xlsx(
        ["Артикул", "Вес"],
        [["SKU-001", 0.3]],
    )


# ── Auth override ─────────────────────────────────────────────────────────────

FAKE_USER = User(id=1, email="test@example.com", hashed_password="x")


def _override_auth():
    return FAKE_USER


# ── Test client ───────────────────────────────────────────────────────────────


@pytest.fixture()
def client() -> TestClient:
    """TestClient with auth dependency overridden (no DB needed)."""
    app.dependency_overrides[get_current_user] = _override_auth
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_no_auth() -> TestClient:
    """TestClient without auth override (real auth enforcement)."""
    app.dependency_overrides.clear()
    return TestClient(app)


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
