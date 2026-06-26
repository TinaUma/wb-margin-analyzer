from __future__ import annotations

from collections.abc import Callable
from typing import Awaitable

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.api.v1.deps import get_current_user
from backend.models.models import User
from backend.schemas.uploads import FilePreview, ValidateFilesResponse
from backend.services.file_validator import (
    ExcelParseError,
    FileValidationResult,
    UnsupportedExtensionError,
    validate_purchases,
    validate_sales,
)

router = APIRouter(prefix="/uploads", tags=["uploads"])

_EXCEL_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
}
_MAX_SIZE = 20 * 1024 * 1024  # 20 MB
_CHUNK = 64 * 1024  # 64 KB
_MAX_CELL_LEN = 500


async def _read_upload(upload: UploadFile) -> bytes:
    """Stream-read upload with size cap; enforces content-type before reading."""
    filename = upload.filename or ""

    # Content-type check is a UX hint (client-supplied, not a security boundary).
    # Real type enforcement is done by openpyxl parse in file_validator.py.
    if upload.content_type not in _EXCEL_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Файл «{filename}» не является Excel-файлом",
        )

    chunks: list[bytes] = []
    total = 0
    try:
        while True:
            chunk = await upload.read(_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Файл «{filename}» превышает лимит 20 МБ",
                )
            chunks.append(chunk)
    finally:
        await upload.close()

    data = b"".join(chunks)
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл «{filename}» пустой",
        )
    return data


def _to_preview(result: FileValidationResult) -> FilePreview:
    """Convert service result to API schema, truncating long cell values."""
    safe_preview = [
        {k: v[:_MAX_CELL_LEN] for k, v in row.items()} for row in result.preview
    ]
    return FilePreview(
        columns_detected=result.columns_detected,
        rows_count=result.rows_count,
        issues=result.issues,
        preview=safe_preview,
    )


async def _run_validator(
    fn: Callable[[bytes, str], Awaitable[FileValidationResult]],
    data: bytes,
    upload: UploadFile,
) -> FileValidationResult:
    """Run async validator; maps domain exceptions to HTTP errors."""
    filename = upload.filename or ""
    try:
        return await fn(data, filename)
    except UnsupportedExtensionError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Файл «{filename}» не является файлом Excel (.xlsx, .xlsm)",
        )
    except ExcelParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/validate",
    response_model=ValidateFilesResponse,
    summary="Validate uploads before analysis",
    responses={
        400: {"description": "Пустой файл или нет данных"},
        413: {"description": "Файл превышает 20 МБ"},
        415: {"description": "Неверный формат файла (не Excel)"},
        422: {"description": "Файл повреждён или имеет неверную структуру"},
    },
)
async def validate_files(
    purchases_file: UploadFile = File(..., description="Excel файл закупок (.xlsx)"),
    sales_file: UploadFile = File(..., description="Excel файл продаж (.xlsx)"),
    _current_user: User = Depends(get_current_user),
) -> ValidateFilesResponse:
    """Validate two Excel files and return column detection + 3-row preview."""
    # _read_upload closes each handle in its own finally — no double-close here.
    purchases_data = await _read_upload(purchases_file)
    sales_data = await _read_upload(sales_file)

    p_result = await _run_validator(validate_purchases, purchases_data, purchases_file)
    s_result = await _run_validator(validate_sales, sales_data, sales_file)

    return ValidateFilesResponse(
        purchases=_to_preview(p_result),
        sales=_to_preview(s_result),
    )
