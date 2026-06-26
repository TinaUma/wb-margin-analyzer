"""Tests for POST /analyses, GET /analyses/{id}, GET /analyses — all 6 AC."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.deps import get_current_user
from backend.db import get_db
from backend.main import app
from backend.models.models import AnalysisSession, Product
from tests.conftest import FAKE_USER, make_xlsx

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ── Fake model builders ───────────────────────────────────────────────────────


def _fake_session(status: str = "processing", user_id: int = 1) -> AnalysisSession:
    s = AnalysisSession()
    s.id = 42
    s.user_id = user_id
    s.status = status
    s.created_at = _NOW
    s.files_meta = {"purchases_filename": "p.xlsx", "sales_filename": "s.xlsx"}
    return s


def _fake_product() -> Product:
    p = Product()
    p.id = 1
    p.session_id = 42
    p.article = "SKU-001"
    p.name = "Test product"
    p.category = "Прочее"
    p.purchase_price = Decimal("500.00")
    p.sale_price = Decimal("1000.00")
    p.weight = Decimal("0.50")
    p.sold = 10
    p.returns = 0
    p.net_revenue = Decimal("10000.00")
    p.commission = Decimal("1800.00")
    p.logistics_total = Decimal("400.00")
    p.purchase_cost = Decimal("5000.00")
    p.profit = Decimal("2800.00")
    p.margin_pct = Decimal("28.00")
    p.margin_zone = "green"
    return p


# ── DB mock helpers ───────────────────────────────────────────────────────────


def _make_db(session_obj=None, products=None):
    db = AsyncMock()
    db.add = MagicMock()  # session.add() is synchronous in SQLAlchemy
    db.get.return_value = session_obj

    if products is not None:
        result_mock = MagicMock()
        result_mock.scalars.return_value = list(products)
        db.execute.return_value = result_mock

    async def _fake_refresh(obj):
        if isinstance(obj, AnalysisSession):
            obj.id = 42

    db.refresh.side_effect = _fake_refresh
    return db


def _db_dep(db):
    async def _override():
        yield db

    return _override


# ── Excel fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def purchases_bytes() -> bytes:
    return make_xlsx(
        ["Артикул", "Себестоимость", "Вес", "Название товара"],
        [["SKU-001", 500, 0.5, "Товар"]],
    )


@pytest.fixture()
def sales_bytes() -> bytes:
    return make_xlsx(
        ["Артикул", "Цена продажи", "Количество продаж", "Комиссия WB %"],
        [["SKU-001", 1000, 10, 15]],
    )


# ── AC-1: POST /analyses returns 202 {analysis_id, status: "processing"} ─────


def test_post_analyses_returns_202(purchases_bytes, sales_bytes):
    db = _make_db()
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    with patch("backend.api.v1.analyses.run_analysis", new=AsyncMock()):
        try:
            with TestClient(app) as c:
                resp = c.post(
                    "/api/v1/analyses",
                    files={
                        "purchases_file": ("p.xlsx", purchases_bytes, _CT),
                        "sales_file": ("s.xlsx", sales_bytes, _CT),
                    },
                )
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 202
    body = resp.json()
    assert body["analysis_id"] == 42
    assert body["status"] == "processing"
    db.commit.assert_awaited_once()  # session must be committed to DB


# ── AC-2: GET /analyses/{id} returns status "processing" ─────────────────────


def test_get_analysis_status_processing():
    db = _make_db(session_obj=_fake_session("processing"))
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)
    try:
        with TestClient(app) as c:
            resp = c.get("/api/v1/analyses/42")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["analysis_id"] == 42
    assert body["status"] == "processing"
    assert body["results"] is None


# ── AC-2: GET /analyses/{id} returns "done" + results list ───────────────────


def test_get_analysis_status_done_with_results():
    db = _make_db(session_obj=_fake_session("done"), products=[_fake_product()])
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)
    try:
        with TestClient(app) as c:
            resp = c.get("/api/v1/analyses/42")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert len(body["results"]) == 1
    r = body["results"][0]
    assert r["article"] == "SKU-001"
    assert r["margin_zone"] == "green"
    assert float(r["margin_pct"]) == pytest.approx(28.0)


# ── AC-2: GET /analyses/{id} returns "failed" (no results) ───────────────────


def test_get_analysis_status_failed():
    db = _make_db(session_obj=_fake_session("failed"))
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)
    try:
        with TestClient(app) as c:
            resp = c.get("/api/v1/analyses/42")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"
    assert resp.json()["results"] is None


# ── AC-3: GET /analyses returns history list ──────────────────────────────────


def test_get_analysis_history_returns_list():
    result_mock = MagicMock()
    result_mock.scalars.return_value = [
        _fake_session("done"),
        _fake_session("processing"),
    ]
    db = AsyncMock()
    db.execute.return_value = result_mock

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)
    try:
        with TestClient(app) as c:
            resp = c.get("/api/v1/analyses")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert items[0]["status"] == "done"
    assert items[1]["status"] == "processing"
    assert items[0]["analysis_id"] == 42


# ── AC-3: GET /analyses empty history ────────────────────────────────────────


def test_get_analysis_history_empty():
    result_mock = MagicMock()
    result_mock.scalars.return_value = []
    db = AsyncMock()
    db.execute.return_value = result_mock

    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)
    try:
        with TestClient(app) as c:
            resp = c.get("/api/v1/analyses")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == []


# ── AC-5 (negative): GET /analyses/{id} for another user → 403 ───────────────


def test_get_analysis_forbidden_for_other_user():
    db = _make_db(session_obj=_fake_session("done", user_id=999))
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER  # id=1
    app.dependency_overrides[get_db] = _db_dep(db)
    try:
        with TestClient(app) as c:
            resp = c.get("/api/v1/analyses/42")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 403


# ── AC-6 (negative): POST /analyses without auth → 401 ───────────────────────


def test_post_analyses_without_auth_returns_401(purchases_bytes, sales_bytes):
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        resp = c.post(
            "/api/v1/analyses",
            files={
                "purchases_file": ("p.xlsx", purchases_bytes, _CT),
                "sales_file": ("s.xlsx", sales_bytes, _CT),
            },
        )
    assert resp.status_code == 401
