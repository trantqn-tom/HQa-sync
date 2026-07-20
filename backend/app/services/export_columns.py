from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.google_connection import GoogleConnection
from app.models.listing import EbayListingDetail
from app.models.sync_run import SyncRun
from app.services.google_sheets import get_service


RAW_PREFIX = "raw::"
DB_PREFIX = "db::"


SYSTEM_COLUMNS = [
    {
        "key": "db::last_sync_action",
        "label": "Sync action",
        "source": "system",
    },
    {
        "key": "db::last_seen_at",
        "label": "Last seen at",
        "source": "system",
    },
    {
        "key": "db::created_at",
        "label": "Created at",
        "source": "system",
    },
    {
        "key": "db::updated_at",
        "label": "Updated at",
        "source": "system",
    },
]


DEFAULT_HEADER_NAMES = [
    "marketplace",
    "listing_id",
    "product_id",
    "keyword",
    "brand",
    "model",
    "category_name",
    "listing_title",
    "listing_url",
    "seller_or_shop",
    "price",
    "shipping_price",
    "total_price",
    "currency",
    "listing_status",
    "condition",
    "location",
]


NUMBER_FIELDS = {
    "price",
    "shipping_price",
    "total_price",
    "listing_views",
    "quantity",
    "raw_confidence",
    "source_total_results",
    "source_limit",
    "source_offset",
}


DATE_FIELDS = {
    "research_date",
    "collected_at",
    "listing_published_at",
    "last_status_checked_at",
    "last_seen_at",
    "created_at",
    "updated_at",
}


def clean_headers(values: list[Any]) -> list[str]:
    result: list[str] = []

    for value in values:
        header = str(value or "").strip()

        if not header:
            continue

        if header not in result:
            result.append(header)

    return result


def get_headers_from_latest_sync(
    db: Session,
) -> list[str]:
    run = db.scalar(
        select(SyncRun)
        .where(
            SyncRun.spreadsheet_id == settings.google_spreadsheet_id,
            SyncRun.sheet_name == settings.google_sheet_name,
        )
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )

    if run is None or not run.details:
        return []

    headers = run.details.get("source_headers")

    if not isinstance(headers, list):
        return []

    return clean_headers(headers)


def get_headers_from_google_sheet(
    db: Session,
) -> list[str]:
    connection = db.scalar(
        select(GoogleConnection)
        .where(GoogleConnection.is_active.is_(True))
        .order_by(GoogleConnection.id.desc())
    )

    if connection is None:
        return []

    service = get_service(connection)

    safe_sheet_name = settings.google_sheet_name.replace(
        "'",
        "''",
    )

    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=settings.google_spreadsheet_id,
            range=f"'{safe_sheet_name}'!1:1",
            majorDimension="ROWS",
            valueRenderOption="FORMATTED_VALUE",
        )
        .execute()
    )

    values = result.get("values", [])

    if not values:
        return []

    return clean_headers(values[0])


def get_headers_from_latest_payload(
    db: Session,
) -> list[str]:
    payload = db.scalar(
        select(EbayListingDetail.raw_payload)
        .order_by(EbayListingDetail.updated_at.desc())
        .limit(1)
    )

    if not isinstance(payload, dict):
        return []

    return clean_headers(
        [key for key in payload.keys() if not str(key).startswith("_")]
    )


def get_source_headers(
    db: Session,
) -> list[str]:
    # Ưu tiên header đã lưu tại lần đồng bộ.
    headers = get_headers_from_latest_sync(db)

    if headers:
        return headers

    # Khi chưa có lần sync mới, đọc trực tiếp dòng 1 Google Sheet.
    try:
        headers = get_headers_from_google_sheet(db)
    except Exception:
        headers = []

    if headers:
        return headers

    # Cuối cùng mới suy ra từ raw_payload.
    return get_headers_from_latest_payload(db)


def get_export_column_options(
    db: Session,
) -> dict:
    headers = get_source_headers(db)

    source_columns = [
        {
            "key": f"{RAW_PREFIX}{header}",
            "label": header,
            "source": "google_sheet",
        }
        for header in headers
    ]

    available_headers = set(headers)

    default_columns = [
        f"{RAW_PREFIX}{header}"
        for header in DEFAULT_HEADER_NAMES
        if header in available_headers
    ]

    if not default_columns:
        default_columns = [item["key"] for item in source_columns[:12]]

    return {
        "columns": [
            *source_columns,
            *SYSTEM_COLUMNS,
        ],
        "source_headers": headers,
        "default_columns": default_columns,
    }


def validate_requested_columns(
    db: Session,
    columns: list[str],
) -> list[str]:
    options = get_export_column_options(db)

    allowed = {item["key"] for item in options["columns"]}

    result: list[str] = []

    for column in columns:
        value = str(column or "").strip()

        if not value:
            continue

        if value not in allowed:
            raise ValueError(f"Cột export không tồn tại trong nguồn dữ liệu: {value}")

        if value not in result:
            result.append(value)

    if not result:
        raise ValueError("Phải chọn ít nhất một cột export")

    return result


def get_export_label(
    column: str,
) -> str:
    if column.startswith(RAW_PREFIX):
        return column[len(RAW_PREFIX) :]

    if column.startswith(DB_PREFIX):
        field_name = column[len(DB_PREFIX) :]

        labels = {
            "last_sync_action": "Sync action",
            "last_seen_at": "Last seen at",
            "created_at": "Created at",
            "updated_at": "Updated at",
        }

        return labels.get(field_name, field_name)

    return column


def get_export_column_config(
    column: str,
) -> dict:
    label = get_export_label(column)

    field_name = label.lower()

    width = 18

    if "title" in field_name:
        width = 48
    elif "url" in field_name:
        width = 42
    elif "keyword" in field_name:
        width = 30
    elif "seller" in field_name:
        width = 26
    elif "location" in field_name:
        width = 24
    elif "category" in field_name:
        width = 26
    elif "date" in field_name or "_at" in field_name:
        width = 22
    elif "id" in field_name:
        width = 24

    config = {
        "label": label,
        "width": width,
    }

    if field_name in NUMBER_FIELDS:
        config["format"] = "#,##0.####"

    if field_name in DATE_FIELDS:
        config["format"] = "dd/mm/yyyy hh:mm:ss"

    return config


def resolve_export_value(
    listing,
    column: str,
):
    if column.startswith(RAW_PREFIX):
        source_field = column[len(RAW_PREFIX) :]

        payload = listing.detail.raw_payload if listing.detail is not None else {}

        return payload.get(source_field)

    if column.startswith(DB_PREFIX):
        database_field = column[len(DB_PREFIX) :]

        return getattr(
            listing,
            database_field,
            None,
        )

    return None
