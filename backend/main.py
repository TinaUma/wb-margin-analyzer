from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.analyses import router as analyses_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.uploads import router as uploads_router
from backend.core.config import get_settings

app = FastAPI(title="WB Margin Analyzer API", version="1.0.0")


def _configure_cors() -> None:
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_configure_cors()

app.include_router(auth_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(analyses_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
