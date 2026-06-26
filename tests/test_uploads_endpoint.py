"""Integration tests for POST /api/v1/uploads/validate — all 6 AC."""

from __future__ import annotations

from tests.conftest import XLSX_MIME


def _files(
    p_bytes: bytes,
    s_bytes: bytes,
    p_name="p.xlsx",
    s_name="s.xlsx",
    p_mime=XLSX_MIME,
    s_mime=XLSX_MIME,
) -> dict:
    return {
        "purchases_file": (p_name, p_bytes, p_mime),
        "sales_file": (s_name, s_bytes, s_mime),
    }


# ── AC-1: happy path — correct response shape ─────────────────────────────────


def test_validate_returns_200_with_correct_shape(client, purchases_xlsx, sales_xlsx):
    resp = client.post(
        "/api/v1/uploads/validate", files=_files(purchases_xlsx, sales_xlsx)
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in ("purchases", "sales"):
        assert "columns_detected" in body[key]
        assert "rows_count" in body[key]
        assert "issues" in body[key]
        assert "preview" in body[key]
        assert len(body[key]["preview"]) <= 3


def test_validate_rows_count_correct(client, purchases_xlsx, sales_xlsx):
    resp = client.post(
        "/api/v1/uploads/validate", files=_files(purchases_xlsx, sales_xlsx)
    )
    assert resp.status_code == 200
    assert resp.json()["purchases"]["rows_count"] == 4
    assert resp.json()["sales"]["rows_count"] == 4


# ── AC-2: missing required column → 200 + issue warning ──────────────────────


def test_missing_required_column_returns_200_with_issue(
    client, purchases_no_cost_xlsx, sales_xlsx
):
    resp = client.post(
        "/api/v1/uploads/validate",
        files=_files(purchases_no_cost_xlsx, sales_xlsx),
    )
    assert resp.status_code == 200
    issues = resp.json()["purchases"]["issues"]
    assert any("Себестоимость" in i for i in issues)


# ── AC-3: missing Вес → logistics warning ────────────────────────────────────


def test_missing_ves_returns_logistics_warning(
    client, purchases_no_ves_xlsx, sales_xlsx
):
    resp = client.post(
        "/api/v1/uploads/validate",
        files=_files(purchases_no_ves_xlsx, sales_xlsx),
    )
    assert resp.status_code == 200
    issues = resp.json()["purchases"]["issues"]
    assert any("логистика рассчитана по среднему 0.5 кг" in i for i in issues)


# ── AC-4: corrupt Excel → 422 ────────────────────────────────────────────────


def test_corrupt_purchases_returns_422(client, sales_xlsx):
    bad = b"PK\x03\x04" + b"\x00" * 200
    resp = client.post("/api/v1/uploads/validate", files=_files(bad, sales_xlsx))
    assert resp.status_code == 422


def test_corrupt_sales_returns_422(client, purchases_xlsx):
    bad = b"\x00" * 300
    resp = client.post(
        "/api/v1/uploads/validate",
        files=_files(purchases_xlsx, bad),
    )
    assert resp.status_code == 422


# ── AC-5: empty file → 400 ───────────────────────────────────────────────────


def test_empty_purchases_file_returns_400(client, sales_xlsx):
    resp = client.post("/api/v1/uploads/validate", files=_files(b"", sales_xlsx))
    assert resp.status_code == 400
    assert resp.json()["detail"]  # must be descriptive


def test_empty_sales_file_returns_400(client, purchases_xlsx):
    resp = client.post(
        "/api/v1/uploads/validate",
        files=_files(purchases_xlsx, b""),
    )
    assert resp.status_code == 400


# ── AC-6: wrong file type → 415 ──────────────────────────────────────────────


def test_pdf_content_type_returns_415(client, sales_xlsx):
    resp = client.post(
        "/api/v1/uploads/validate",
        files=_files(b"%PDF-1.4 fake", sales_xlsx, p_mime="application/pdf"),
    )
    assert resp.status_code == 415


def test_wrong_extension_returns_415(client, sales_xlsx):
    resp = client.post(
        "/api/v1/uploads/validate",
        files=_files(b"col1,col2\n1,2", sales_xlsx, p_name="data.csv"),
    )
    assert resp.status_code == 415


# ── Auth boundary ─────────────────────────────────────────────────────────────


def test_unauthenticated_request_returns_401(
    client_no_auth, purchases_xlsx, sales_xlsx
):
    resp = client_no_auth.post(
        "/api/v1/uploads/validate",
        files=_files(purchases_xlsx, sales_xlsx),
    )
    assert resp.status_code in (401, 403)
