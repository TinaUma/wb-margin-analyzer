from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions: Mapped[list["AnalysisSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'done', 'failed')", name="ck_session_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # processing | done | failed
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="processing",
        server_default=text("'processing'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # {purchases_filename, sales_filename, purchases_rows, sales_rows, warnings:[]}
    files_meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")
    products: Mapped[list["Product"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "margin_zone IN ('green', 'yellow', 'red')", name="ck_margin_zone"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    article: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    sold: Mapped[int] = mapped_column(nullable=False)
    returns: Mapped[int] = mapped_column(nullable=False)
    # Calculated fields
    net_revenue: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    logistics_total: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    purchase_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    profit: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    margin_pct: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    # green | yellow | red
    margin_zone: Mapped[str] = mapped_column(String(10), nullable=False)

    session: Mapped["AnalysisSession"] = relationship(back_populates="products")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("session_id", name="uq_reports_session_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False
    )
    ai_interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{role: "user"|"assistant", content: "..."}]
    chat_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped["AnalysisSession"] = relationship(back_populates="report")
