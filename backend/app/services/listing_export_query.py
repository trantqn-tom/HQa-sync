from collections.abc import Sequence

from sqlalchemy import (
    Select,
    and_,
    asc,
    desc,
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.models.listing import EbayListing
from app.schemas.export import (
    ExportSort,
    ListingExportFilters,
)


SORT_FIELDS = {
    "last_seen_at": EbayListing.last_seen_at,
    "updated_at": EbayListing.updated_at,
    "created_at": EbayListing.created_at,
    "listing_published_at": (EbayListing.listing_published_at),
    "price": EbayListing.price,
    "shipping_price": EbayListing.shipping_price,
    "total_price": EbayListing.total_price,
    "listing_status": EbayListing.listing_status,
    "listing_title": EbayListing.listing_title,
    "seller_or_shop": EbayListing.seller_or_shop,
    "marketplace": EbayListing.marketplace,
}


def clean_string_list(
    values: list[str],
) -> list[str]:
    result = []

    for value in values:
        cleaned = value.strip()

        if cleaned and cleaned not in result:
            result.append(cleaned)

    return result


def build_listing_conditions(
    filters: ListingExportFilters,
) -> Sequence:
    conditions = []

    if filters.q:
        keyword = filters.q.strip()

        if keyword:
            pattern = f"%{keyword}%"

            conditions.append(
                or_(
                    EbayListing.listing_title.ilike(pattern),
                    EbayListing.listing_id.ilike(pattern),
                    EbayListing.product_id.ilike(pattern),
                    EbayListing.keyword.ilike(pattern),
                    EbayListing.brand.ilike(pattern),
                    EbayListing.model.ilike(pattern),
                    EbayListing.seller_or_shop.ilike(pattern),
                    EbayListing.category_name.ilike(pattern),
                )
            )

    statuses = clean_string_list(filters.statuses)

    if statuses:
        conditions.append(EbayListing.listing_status.in_(statuses))

    marketplaces = clean_string_list(filters.marketplaces)

    if marketplaces:
        conditions.append(EbayListing.marketplace.in_(marketplaces))

    if filters.action:
        action = filters.action.strip()

        if action:
            conditions.append(EbayListing.last_sync_action == action)

    if filters.product_id:
        product_id = filters.product_id.strip()

        if product_id:
            conditions.append(EbayListing.product_id == product_id)

    if filters.brand:
        brand = filters.brand.strip()

        if brand:
            conditions.append(EbayListing.brand.ilike(f"%{brand}%"))

    if filters.category_name:
        category_name = filters.category_name.strip()

        if category_name:
            conditions.append(EbayListing.category_name == category_name)

    if filters.condition:
        condition = filters.condition.strip()

        if condition:
            conditions.append(EbayListing.condition == condition)

    if filters.price_min is not None:
        conditions.append(EbayListing.total_price >= filters.price_min)

    if filters.price_max is not None:
        conditions.append(EbayListing.total_price <= filters.price_max)

    return conditions


def build_listing_export_query(
    filters: ListingExportFilters,
    sort: ExportSort,
) -> Select:
    query = select(EbayListing)

    conditions = build_listing_conditions(filters)

    if conditions:
        query = query.where(and_(*conditions))

    sort_column = SORT_FIELDS.get(
        sort.field,
        EbayListing.last_seen_at,
    )

    if sort.order == "asc":
        sort_expression = asc(sort_column)
    else:
        sort_expression = desc(sort_column)

    return query.order_by(
        sort_expression,
        EbayListing.id.desc(),
    )


def stream_listing_rows(
    db: Session,
    query: Select,
    batch_size: int = 2000,
):
    result = db.execute(
        query.execution_options(
            yield_per=batch_size,
            stream_results=True,
        )
    )

    for listing in result.scalars():
        yield listing
