from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.timeutil import now_vn
from app.models.google_connection import GoogleConnection
from app.models.listing import EbayListing, EbayListingChange, EbayListingDetail
from app.models.sync_run import SyncRun
from app.services.google_sheets import clear_processed_rows, read_sheet_snapshot
from app.services.normalizer import changed_fields, json_safe, normalize_row

LOCK_ID = 8302026
EXPECTED_HEADERS = {
    "research_date",
    "collected_at",
    "product_id",
    "brand",
    "model",
    "category",
    "keyword",
    "marketplace",
    "listing_id",
    "listing_title",
    "listing_status",
    "price",
    "total_price",
}


def _connection(db: Session) -> GoogleConnection:
    connection = db.scalar(
        select(GoogleConnection)
        .where(GoogleConnection.is_active.is_(True))
        .order_by(GoogleConnection.id.desc())
    )
    if not connection:
        raise RuntimeError("Google OAuth chưa được kết nối")
    return connection


def run_sync(db: Session, trigger_type: str = "MANUAL") -> SyncRun:
    locked = db.execute(
        text("SELECT pg_try_advisory_lock(:id)"), {"id": LOCK_ID}
    ).scalar()
    if not locked:
        raise RuntimeError("Một tiến trình đồng bộ khác đang chạy")

    run = SyncRun(
        trigger_type=trigger_type,
        status="RUNNING",
        spreadsheet_id=settings.google_spreadsheet_id,
        sheet_name=settings.google_sheet_name,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        connection = _connection(db)
        headers, rows, last_row = read_sheet_snapshot(connection)
        run.snapshot_last_row = last_row
        run.source_rows = len(rows)

        missing = EXPECTED_HEADERS.difference(headers)
        if missing:
            raise ValueError(f"Thiếu header bắt buộc: {', '.join(sorted(missing))}")

        mapped_rows: list[tuple[dict, dict]] = []
        invalid: list[dict] = []
        for source_row, values in enumerate(rows, start=2):
            raw = {
                header: values[index] if index < len(values) else None
                for index, header in enumerate(headers)
            }
            if not any(value not in (None, "") for value in raw.values()):
                continue
            normalized, errors = normalize_row(raw)
            raw["_source_row_number"] = source_row
            if errors:
                invalid.append({"row": source_row, "errors": errors})
            else:
                mapped_rows.append((normalized, raw))

        run.valid_rows = len(mapped_rows)
        run.invalid_rows = len(invalid)
        run.error_count = len(invalid)
        run.details = json_safe(
            {
                # Lưu đúng thứ tự cột tại thời điểm đồng bộ.
                "source_headers": headers,
                # Chỉ lưu tối đa 100 dòng lỗi để tránh JSON quá lớn.
                "invalid_rows": invalid[:100],
            }
        )
        if invalid:
            raise ValueError("Có dòng dữ liệu không hợp lệ; Sheet chưa được clear")

        now = now_vn()
        incoming_ids = list({item[0]["listing_id"] for item in mapped_rows})
        existing_items = (
            db.scalars(
                select(EbayListing).where(EbayListing.listing_id.in_(incoming_ids))
            ).all()
            if incoming_ids
            else []
        )
        existing_map = {
            (item.marketplace, item.listing_id, item.product_id, item.keyword_key): item
            for item in existing_items
        }

        for normalized, raw in mapped_rows:
            business_key = (
                normalized["marketplace"],
                normalized["listing_id"],
                normalized["product_id"],
                normalized["keyword_key"],
            )
            existing = existing_map.get(business_key)
            payload_hash = normalized.pop("payload_hash")
            safe_raw = json_safe(raw)
            if existing is None:
                listing = EbayListing(
                    **normalized,
                    last_seen_at=now,
                    last_sync_action="INSERT",
                    last_sync_run_id=run.id,
                )
                listing.detail = EbayListingDetail(
                    raw_payload=safe_raw, payload_hash=payload_hash
                )
                db.add(listing)
                existing_map[business_key] = listing
                run.insert_count += 1
                continue

            if existing.data_hash == normalized["data_hash"]:
                existing.last_seen_at = now
                existing.last_sync_action = "SKIP"
                existing.last_sync_run_id = run.id
                run.skip_count += 1
                if existing.detail and existing.detail.payload_hash != payload_hash:
                    existing.detail.raw_payload = safe_raw
                    existing.detail.payload_hash = payload_hash
                continue

            before = {
                field: getattr(existing, field)
                for field in normalized
                if hasattr(existing, field)
            }
            changes = changed_fields(before, normalized)
            for key, value in normalized.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            existing.last_seen_at = now
            existing.last_sync_action = "UPDATE"
            existing.last_sync_run_id = run.id
            if existing.detail:
                existing.detail.raw_payload = safe_raw
                existing.detail.payload_hash = payload_hash
            else:
                existing.detail = EbayListingDetail(
                    raw_payload=safe_raw, payload_hash=payload_hash
                )
            # Flush so newly inserted listings in this run get DB ids before history rows.
            if existing.id is None:
                db.flush()
            db.add(
                EbayListingChange(
                    listing_id_fk=existing.id,
                    sync_run_id=run.id,
                    change_type="UPDATE",
                    changed_fields=changes,
                )
            )
            run.update_count += 1

        if run.valid_rows != run.insert_count + run.update_count + run.skip_count:
            raise RuntimeError("Đối soát Insert/Update/Skip không khớp")

        db.commit()
        run.database_committed_at = now_vn()

        if settings.auto_clear_after_sync and last_row >= 2:
            run.cleared_range = clear_processed_rows(connection, last_row)
            run.sheet_cleared = True
            run.sheet_cleared_at = now_vn()

        run.status = "COMPLETED_AND_CLEARED" if run.sheet_cleared else "COMPLETED"
        run.completed_at = now_vn()
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        db.rollback()
        run = db.get(SyncRun, run.id)
        run.status = "FAILED"
        run.error_message = str(exc)
        run.completed_at = now_vn()
        db.commit()
        raise
    finally:
        db.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
        db.commit()
