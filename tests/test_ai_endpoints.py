"""Tests for POST /analyses/{id}/interpret and POST /analyses/{id}/chat — Task 7 AC."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.deps import get_current_user
from backend.db import get_db
from backend.main import app
from backend.models.models import AnalysisSession, Product, Report
from tests.conftest import FAKE_USER

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


# ── Fake model builders ───────────────────────────────────────────────────────


def _fake_session(status: str = "done", user_id: int = 1) -> AnalysisSession:
    s = AnalysisSession()
    s.id = 42
    s.user_id = user_id
    s.status = status
    s.created_at = _NOW
    s.files_meta = {}
    return s


def _fake_product() -> Product:
    p = Product()
    p.id = 1
    p.session_id = 42
    p.article = "SKU-001"
    p.name = "Товар тестовый"
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


def _fake_report(
    ai_interpretation: str | None = None, chat_history: list | None = None
) -> Report:
    r = Report()
    r.id = 1
    r.session_id = 42
    r.ai_interpretation = ai_interpretation
    r.chat_history = chat_history or []
    r.created_at = _NOW
    return r


# ── DB mock helpers ───────────────────────────────────────────────────────────


def _make_db(
    session_obj=None,
    products: list | None = None,
    report_obj=None,
) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()

    # db.get returns session by default
    db.get.return_value = session_obj

    # db.execute returns different results depending on call order
    products_result = MagicMock()
    products_result.scalars.return_value = products or []

    report_result = MagicMock()
    report_result.scalar_one_or_none.return_value = report_obj

    # first execute → products, second execute → report
    db.execute.side_effect = [products_result, report_result]

    return db


def _db_dep(db):
    async def _override():
        yield db

    return _override


# ── AC-1: POST /interpret returns 200 with 3 sections ────────────────────────


def test_interpret_returns_interpretation():
    db = _make_db(session_obj=_fake_session("done"), products=[_fake_product()])
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    fake_text = "## Диагноз\nОК\n## Рекомендации\nРек.\n## Риски\nРиск."
    with patch(
        "backend.api.v1.analyses.generate_interpretation",
        new=AsyncMock(return_value=fake_text),
    ):
        try:
            with TestClient(app) as c:
                resp = c.post("/api/v1/analyses/42/interpret")
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["interpretation"] == fake_text
    db.commit.assert_awaited_once()


# ── AC-1 (negative): analysis not done → 400 ─────────────────────────────────


def test_interpret_returns_400_if_not_done():
    db = _make_db(session_obj=_fake_session("processing"))
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    try:
        with TestClient(app) as c:
            resp = c.post("/api/v1/analyses/42/interpret")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 400


# ── AC-4 (negative): non-existent analysis_id → 404 ─────────────────────────


def test_interpret_404_for_missing_analysis():
    db = _make_db(session_obj=None)
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    try:
        with TestClient(app) as c:
            resp = c.post("/api/v1/analyses/999/interpret")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_chat_404_for_missing_analysis():
    db = _make_db(session_obj=None)
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    try:
        with TestClient(app) as c:
            resp = c.post("/api/v1/analyses/999/chat", json={"message": "Привет"})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


# ── AC-2: POST /chat returns {reply} ─────────────────────────────────────────


def test_chat_returns_reply():
    existing_report = _fake_report(
        ai_interpretation="## Диагноз\nОК",
        chat_history=[],
    )
    db = _make_db(
        session_obj=_fake_session("done"),
        products=[_fake_product()],
        report_obj=existing_report,
    )
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    with patch(
        "backend.api.v1.analyses.chat_reply",
        new=AsyncMock(return_value="Ответ ИИ"),
    ):
        try:
            with TestClient(app) as c:
                resp = c.post("/api/v1/analyses/42/chat", json={"message": "Как дела?"})
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["reply"] == "Ответ ИИ"


# ── AC-3: chat history is persisted ──────────────────────────────────────────


def test_chat_persists_history():
    existing_report = _fake_report(chat_history=[])
    db = _make_db(
        session_obj=_fake_session("done"),
        products=[_fake_product()],
        report_obj=existing_report,
    )
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    with patch(
        "backend.api.v1.analyses.chat_reply",
        new=AsyncMock(return_value="Ответ"),
    ):
        try:
            with TestClient(app) as c:
                c.post("/api/v1/analyses/42/chat", json={"message": "Вопрос"})
        finally:
            app.dependency_overrides.clear()

    history = existing_report.chat_history
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Вопрос"}
    assert history[1] == {"role": "assistant", "content": "Ответ"}
    db.commit.assert_awaited_once()


# ── AC-5 (negative): Claude API error → 503 ──────────────────────────────────


def test_interpret_503_on_ai_error():
    from fastapi import HTTPException

    db = _make_db(session_obj=_fake_session("done"), products=[_fake_product()])
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    async def _raise_503(*_a, **_kw):
        raise HTTPException(
            status_code=503,
            detail="Сервис AI временно недоступен. Пожалуйста, попробуйте позже.",
        )

    with patch("backend.api.v1.analyses.generate_interpretation", new=_raise_503):
        try:
            with TestClient(app) as c:
                resp = c.post("/api/v1/analyses/42/interpret")
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert "недоступен" in resp.json()["detail"]


def test_chat_503_on_ai_error():
    from fastapi import HTTPException

    existing_report = _fake_report()
    db = _make_db(
        session_obj=_fake_session("done"),
        products=[_fake_product()],
        report_obj=existing_report,
    )
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = _db_dep(db)

    async def _raise_503(*_a, **_kw):
        raise HTTPException(
            status_code=503,
            detail="Сервис AI временно недоступен. Пожалуйста, попробуйте позже.",
        )

    with patch("backend.api.v1.analyses.chat_reply", new=_raise_503):
        try:
            with TestClient(app) as c:
                resp = c.post("/api/v1/analyses/42/chat", json={"message": "Привет"})
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 503
    assert "недоступен" in resp.json()["detail"]
