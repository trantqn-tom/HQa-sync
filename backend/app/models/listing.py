from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.timeutil import now_vn


class EbayListing(Base):
    __tablename__ = "ebay_listings"
    __table_args__ = (
        UniqueConstraint("marketplace", "listing_id", "product_id", "keyword_key", name="uq_ebay_business_key"),
        Index("ix_ebay_status_seen", "listing_status", "last_seen_at"),
        Index("ix_ebay_product_seen", "product_id", "last_seen_at"),
        Index("ix_ebay_price", "total_price"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    marketplace: Mapped[str] = mapped_column(String(30), default="ebay")
    listing_id: Mapped[str] = mapped_column(String(255), index=True)
    product_id: Mapped[str] = mapped_column(String(100), default="")
    keyword: Mapped[str] = mapped_column(Text, default="")
    keyword_key: Mapped[str] = mapped_column(String(500), default="")
    brand: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(255))
    listing_title: Mapped[str | None] = mapped_column(Text)
    listing_url: Mapped[str | None] = mapped_column(Text)
    seller_or_shop: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    shipping_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    currency: Mapped[str | None] = mapped_column(String(20))
    listing_status: Mapped[str | None] = mapped_column(String(100))
    condition: Mapped[str | None] = mapped_column(Text)
    category_name: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int | None] = mapped_column(Integer)
    match_type: Mapped[str | None] = mapped_column(String(50))
    exclude_flag: Mapped[bool | None] = mapped_column(Boolean)
    raw_confidence: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    listing_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_vn, index=True)
    last_status_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_hash: Mapped[str] = mapped_column(String(64))
    last_sync_action: Mapped[str] = mapped_column(String(20), default="INSERT")
    last_sync_run_id: Mapped[object | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_vn)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_vn, onupdate=now_vn)

    detail: Mapped["EbayListingDetail"] = relationship(back_populates="listing", uselist=False, cascade="all, delete-orphan")


class EbayListingDetail(Base):
    __tablename__ = "ebay_listing_details"

    listing_id_fk: Mapped[int] = mapped_column(BigInteger, ForeignKey("ebay_listings.id", ondelete="CASCADE"), primary_key=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB)
    payload_hash: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_vn, onupdate=now_vn)

    listing: Mapped[EbayListing] = relationship(back_populates="detail")


class EbayListingChange(Base):
    __tablename__ = "ebay_listing_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id_fk: Mapped[int] = mapped_column(BigInteger, ForeignKey("ebay_listings.id", ondelete="CASCADE"), index=True)
    sync_run_id: Mapped[object] = mapped_column(UUID(as_uuid=True), index=True)
    change_type: Mapped[str] = mapped_column(String(20))
    changed_fields: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_vn, index=True)
