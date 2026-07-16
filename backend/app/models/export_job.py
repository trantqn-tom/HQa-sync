import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.timeutil import now_vn


class ExportJob(Base):
    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    requested_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    resource_type: Mapped[str] = mapped_column(
        String(30),
        default="LISTINGS",
        nullable=False,
    )

    export_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    export_scope: Mapped[str] = mapped_column(
        String(30),
        default="FILTERED",
        nullable=False,
    )

    filters: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    selected_columns: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    sort_config: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    destination_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    processed_rows: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    output_filename: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    output_path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    output_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_vn,
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
