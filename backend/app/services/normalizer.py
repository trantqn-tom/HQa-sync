import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

GOOGLE_EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)

CORE_FIELDS = [
    "marketplace", "listing_id", "product_id", "keyword", "brand", "model", "category",
    "listing_title", "listing_url", "seller_or_shop", "image_url", "price", "shipping_price",
    "total_price", "currency", "listing_status", "condition", "category_name", "location",
    "quantity", "match_type", "exclude_flag", "raw_confidence", "listing_published_at",
    "collected_at", "last_status_checked_at"
]


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.0001"))
    except (InvalidOperation, ValueError):
        return None


def parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return GOOGLE_EPOCH + timedelta(days=float(value))
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256(data: dict) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def normalize_row(raw: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    listing_id = clean_text(raw.get("listing_id"))
    if not listing_id:
        errors.append("missing_listing_id")

    keyword = clean_text(raw.get("keyword")) or ""
    normalized = {
        "marketplace": (clean_text(raw.get("marketplace")) or "unknown").lower(),
        "listing_id": listing_id,
        "product_id": clean_text(raw.get("product_id")) or "",
        "keyword": keyword,
        "keyword_key": keyword.lower()[:500],
        "brand": clean_text(raw.get("brand")),
        "model": clean_text(raw.get("model")),
        "category": clean_text(raw.get("category")),
        "listing_title": clean_text(raw.get("listing_title")),
        "listing_url": clean_text(raw.get("listing_url")),
        "seller_or_shop": clean_text(raw.get("seller_or_shop")),
        "image_url": clean_text(raw.get("image_url")),
        "price": parse_decimal(raw.get("price")),
        "shipping_price": parse_decimal(raw.get("shipping_price")),
        "total_price": parse_decimal(raw.get("total_price")),
        "currency": clean_text(raw.get("currency")),
        "listing_status": clean_text(raw.get("listing_status")),
        "condition": clean_text(raw.get("condition")),
        "category_name": clean_text(raw.get("category_name")),
        "location": clean_text(raw.get("location")),
        "quantity": parse_int(raw.get("quantity")),
        "match_type": clean_text(raw.get("match_type")),
        "exclude_flag": parse_bool(raw.get("exclude_flag")),
        "raw_confidence": parse_decimal(raw.get("raw_confidence")),
        "listing_published_at": parse_datetime(raw.get("listing_published_at")),
        "collected_at": parse_datetime(raw.get("collected_at")),
        "last_status_checked_at": parse_datetime(raw.get("last_status_checked_at")),
    }
    comparable = {key: normalized.get(key) for key in CORE_FIELDS}
    normalized["data_hash"] = sha256(comparable)
    normalized["payload_hash"] = sha256(raw)
    return normalized, errors


def json_safe(value: Any) -> Any:
    """Convert values so they can be stored in JSONB / json.dumps."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def changed_fields(old: dict[str, Any], new: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for field in CORE_FIELDS:
        old_value = old.get(field)
        new_value = new.get(field)
        if str(old_value) != str(new_value):
            result[field] = {"old": json_safe(old_value), "new": json_safe(new_value)}
    return result
