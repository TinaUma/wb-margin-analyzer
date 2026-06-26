from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.v1.deps import get_current_user
from backend.db import get_db
from backend.models.models import AnalysisSession, Product, User
from backend.schemas.analyses import (
    AnalysisCreateResponse,
    AnalysisHistoryItem,
    AnalysisStatusResponse,
    ProductResult,
)
from backend.services.analysis_runner import run_analysis
from backend.services.file_validator import (
    ExcelParseError,
    UnsupportedExtensionError,
    validate_purchases,
    validate_sales,
)

router = APIRouter(prefix="/analyses", tags=["analyses"])

_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB — mirrors uploads.py limit


async def _validate_file(validator, data: bytes, filename: str) -> None:
    try:
        await validator(data, filename)
    except UnsupportedExtensionError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        )
    except ExcelParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "", status_code=status.HTTP_202_ACCEPTED, response_model=AnalysisCreateResponse
)
async def create_analysis(
    background_tasks: BackgroundTasks,
    purchases_file: UploadFile = File(...),
    sales_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisCreateResponse:
    purchases_bytes = await purchases_file.read()
    sales_bytes = await sales_file.read()

    for fname, data in (
        (purchases_file.filename or "purchases.xlsx", purchases_bytes),
        (sales_file.filename or "sales.xlsx", sales_bytes),
    ):
        if len(data) > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Файл «{fname}» превышает лимит 20 МБ",
            )

    await _validate_file(
        validate_purchases, purchases_bytes, purchases_file.filename or "purchases.xlsx"
    )
    await _validate_file(
        validate_sales, sales_bytes, sales_file.filename or "sales.xlsx"
    )

    session = AnalysisSession(
        user_id=current_user.id,
        status="processing",
        files_meta={
            "purchases_filename": purchases_file.filename,
            "sales_filename": sales_file.filename,
        },
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    background_tasks.add_task(run_analysis, session.id, purchases_bytes, sales_bytes)

    return AnalysisCreateResponse(analysis_id=session.id, status=session.status)


@router.get("/{analysis_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisStatusResponse:
    session = await db.get(AnalysisSession, analysis_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found"
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    results: list[ProductResult] | None = None
    if session.status == "done":
        rows = await db.execute(
            select(Product).where(Product.session_id == analysis_id)
        )
        results = [ProductResult.model_validate(p) for p in rows.scalars()]

    return AnalysisStatusResponse(
        analysis_id=session.id,
        status=session.status,
        created_at=session.created_at,
        files_meta=session.files_meta,
        results=results,
    )


@router.get("", response_model=list[AnalysisHistoryItem])
async def get_analysis_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnalysisHistoryItem]:
    rows = await db.execute(
        select(AnalysisSession)
        .where(AnalysisSession.user_id == current_user.id)
        .order_by(AnalysisSession.created_at.desc())
    )
    return [
        AnalysisHistoryItem(
            analysis_id=s.id,
            status=s.status,
            created_at=s.created_at,
            files_meta=s.files_meta,
        )
        for s in rows.scalars()
    ]
