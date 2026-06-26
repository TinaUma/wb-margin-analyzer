from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass
from functools import partial

import pandas as pd

logger = logging.getLogger(__name__)

# ── Column definitions ────────────────────────────────────────────────────────

PURCHASES_REQUIRED = {"Артикул", "Себестоимость"}
SALES_REQUIRED = {"Артикул", "Цена продажи", "Количество продаж", "Комиссия WB %"}

MAX_PREVIEW_ROWS = 3
MAX_ROWS = 200_000
MAX_COLS = 1_000

# Extensions supported by openpyxl only
_SUPPORTED_EXTENSIONS = {"xlsx", "xlsm"}

# OOXML magic bytes (ZIP PK header)
_XLSX_MAGIC = b"PK\x03\x04"


class UnsupportedExtensionError(Exception):
    """Raised when the file extension is not in the accepted list (→ 415)."""


class ExcelParseError(Exception):
    """Raised when pd.read_excel fails to parse file content (→ 422)."""


@dataclass
class FileValidationResult:
    columns_detected: list[str]
    rows_count: int
    issues: list[str]
    preview: list[dict]
    file_type: str  # "purchases" or "sales"


def _read_excel_sync(data: bytes, filename: str) -> pd.DataFrame:
    """Synchronous Excel parse — call via run_in_executor to avoid blocking the event loop.

    Raises:
        UnsupportedExtensionError: extension not in _SUPPORTED_EXTENSIONS (→ 415)
        ExcelParseError: pd.read_excel fails to parse content (→ 422)
    """
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in _SUPPORTED_EXTENSIONS:
        raise UnsupportedExtensionError(
            f"Неподдерживаемый формат «.{suffix}». "
            f"Принимаются только: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}"
        )

    # Magic-bytes check — OOXML is always a ZIP
    if not data.startswith(_XLSX_MAGIC):
        raise ExcelParseError("Файл не является корректным Excel-файлом (OOXML)")

    try:
        df = pd.read_excel(io.BytesIO(data), engine="openpyxl", nrows=MAX_ROWS)
    except MemoryError:
        raise
    except Exception as exc:
        # Catches BadZipFile, KeyError, ValueError, TypeError, AttributeError,
        # OSError ('no valid workbook part'), lxml.etree.XMLSyntaxError (SyntaxError
        # subclass), and any other openpyxl/pandas parse error → always 422, never 500.
        logger.warning("Excel parse failed for %r: %s", filename, exc)
        raise ExcelParseError("Файл повреждён или имеет неверную структуру") from exc

    if len(df.columns) > MAX_COLS:
        raise ExcelParseError(
            f"Файл содержит слишком много колонок ({len(df.columns)} > {MAX_COLS})"
        )

    return df


async def _safe_read_excel(data: bytes, filename: str) -> pd.DataFrame:
    """Async wrapper: runs the sync parse in a thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_read_excel_sync, data, filename))


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all column names are strings (handles numeric/None headers)."""
    df.columns = [str(c) for c in df.columns]
    return df


def _check_required(
    columns: set[str],
    required: set[str],
    issues: list[str],
) -> None:
    for col in sorted(required):
        if col not in columns:
            issues.append(f"Отсутствует обязательная колонка: «{col}»")


async def validate_purchases(data: bytes, filename: str) -> FileValidationResult:
    df = await _safe_read_excel(data, filename)
    df = _normalize_columns(df)
    df = df.dropna(how="all")

    if len(df) == 0:
        raise ValueError("Файл закупок пустой — нет строк данных")

    cols = set(df.columns.tolist())
    issues: list[str] = []

    _check_required(cols, PURCHASES_REQUIRED, issues)

    if "Вес" not in cols:
        issues.append(
            "Отсутствует колонка «Вес» — логистика рассчитана по среднему 0.5 кг"
        )

    preview = df.head(MAX_PREVIEW_ROWS).fillna("").astype(str).to_dict(orient="records")

    return FileValidationResult(
        columns_detected=df.columns.tolist(),
        rows_count=len(df),
        issues=issues,
        preview=preview,
        file_type="purchases",
    )


async def validate_sales(data: bytes, filename: str) -> FileValidationResult:
    df = await _safe_read_excel(data, filename)
    df = _normalize_columns(df)
    df = df.dropna(how="all")

    if len(df) == 0:
        raise ValueError("Файл продаж пустой — нет строк данных")

    cols = set(df.columns.tolist())
    issues: list[str] = []

    _check_required(cols, SALES_REQUIRED, issues)

    preview = df.head(MAX_PREVIEW_ROWS).fillna("").astype(str).to_dict(orient="records")

    return FileValidationResult(
        columns_detected=df.columns.tolist(),
        rows_count=len(df),
        issues=issues,
        preview=preview,
        file_type="sales",
    )
