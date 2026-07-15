from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.timeutil import now_vn


class GoogleConnection(Base):
    __tablename__ = "google_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    google_email: Mapped[str | None] = mapped_column(String(255))
    access_token_encrypted: Mapped[str | None] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    token_uri: Mapped[str] = mapped_column(String(500), default="https://oauth2.googleapis.com/token")
    scopes: Mapped[str] = mapped_column(Text)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_vn)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_vn, onupdate=now_vn)
    last_error: Mapped[str | None] = mapped_column(Text)
