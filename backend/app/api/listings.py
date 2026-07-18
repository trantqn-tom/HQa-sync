from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload
from app.core.database import get_db
from app.models.listing import EbayListing, EbayListingChange

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("/meta/statuses")
def list_statuses(db: Session = Depends(get_db)):
    """Distinct listing_status values present in DB (synced from Google Sheet)."""
    rows = db.scalars(
        select(EbayListing.listing_status)
        .where(
            EbayListing.listing_status.is_not(None),
            EbayListing.listing_status != "",
        )
        .distinct()
        .order_by(EbayListing.listing_status.asc())
    ).all()
    return {"statuses": list(rows)}


@router.get("/meta/marketplaces")
def list_marketplaces(db: Session = Depends(get_db)):
    """Distinct marketplace values present in DB (synced from Google Sheet)."""
    rows = db.scalars(
        select(EbayListing.marketplace)
        .where(
            EbayListing.marketplace.is_not(None),
            EbayListing.marketplace != "",
        )
        .distinct()
        .order_by(EbayListing.marketplace.asc())
    ).all()
    return {"marketplaces": list(rows)}


@router.get("/meta/sellers")
def list_sellers(
    db: Session = Depends(get_db),
):
    """
    Lấy toàn bộ seller/shop không rỗng trong database.

    Danh sách được:
    - Loại trùng bằng DISTINCT.
    - Sắp xếp tăng dần.
    """
    rows = db.scalars(
        select(
            EbayListing.seller_or_shop,
        )
        .where(
            EbayListing.seller_or_shop.is_not(
                None,
            ),
            EbayListing.seller_or_shop != "",
        )
        .distinct()
        .order_by(
            EbayListing.seller_or_shop.asc(),
        )
    ).all()

    return {
        "sellers": list(rows),
    }


@router.get("")
def list_items(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    q: str | None = None,
    status: list[str] | None = Query(None),
    marketplace: list[str] | None = Query(None),
    seller: list[str] | None = Query(None),
    action: str | None = None,
    product_id: str | None = None,
):
    filters = []
    if q:
        filters.append(
            or_(
                EbayListing.listing_title.ilike(f"%{q}%"),
                EbayListing.listing_id.ilike(f"%{q}%"),
                EbayListing.brand.ilike(f"%{q}%"),
            )
        )
    if status:
        values = [item for item in status if item]
        if values:
            filters.append(EbayListing.listing_status.in_(values))
    if marketplace:
        values = [item for item in marketplace if item]
        if values:
            filters.append(EbayListing.marketplace.in_(values))
    if seller:
        values = [item for item in seller if item]
        if values:
            filters.append(EbayListing.seller_or_shop.in_(values))
    if action:
        filters.append(EbayListing.last_sync_action == action)
    if product_id:
        filters.append(EbayListing.product_id == product_id)

    where = and_(*filters) if filters else True
    total = db.scalar(select(func.count()).select_from(EbayListing).where(where)) or 0
    items = db.scalars(
        select(EbayListing)
        .where(where)
        .order_by(EbayListing.last_seen_at.desc(), EbayListing.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{listing_pk}")
def detail(listing_pk: int, db: Session = Depends(get_db)):
    item = db.scalar(
        select(EbayListing)
        .options(selectinload(EbayListing.detail))
        .where(EbayListing.id == listing_pk)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy listing")
    history = db.scalars(
        select(EbayListingChange)
        .where(EbayListingChange.listing_id_fk == listing_pk)
        .order_by(EbayListingChange.created_at.desc())
        .limit(50)
    ).all()
    return {
        "listing": item,
        "raw_payload": item.detail.raw_payload if item.detail else {},
        "history": history,
    }
