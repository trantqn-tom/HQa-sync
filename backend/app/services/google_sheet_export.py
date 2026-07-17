from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_text, encrypt_text
from app.models.google_connection import GoogleConnection
from app.schemas.export import GoogleSheetExportRequest
from app.services.excel_columns import EXPORT_COLUMN_CONFIG
from app.services.listing_export_query import (
    build_listing_export_query,
    stream_listing_rows,
)


VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

GOOGLE_SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"

DEFAULT_BATCH_SIZE = 1_000


@dataclass
class ParsedGoogleSheetUrl:
    spreadsheet_id: str
    sheet_id: int | None


# =========================================================
# Parse và chuẩn hóa URL
# =========================================================


def parse_google_sheet_url(
    spreadsheet_url: str,
) -> ParsedGoogleSheetUrl:
    """
    Phân tích URL Google Sheet để lấy:

    - spreadsheet_id: ID của file Google Sheet.
    - sheet_id: gid của tab, nếu URL có gid.

    Hỗ trợ:
    - .../edit?gid=123
    - .../edit#gid=123
    """
    url = spreadsheet_url.strip()

    match = re.search(
        r"/spreadsheets/d/([a-zA-Z0-9_-]+)",
        url,
    )

    if not match:
        raise ValueError(
            "Google Sheet URL không hợp lệ hoặc không chứa spreadsheet ID."
        )

    spreadsheet_id = match.group(1)
    parsed_url = urlparse(url)

    sheet_id: int | None = None

    query_values = parse_qs(parsed_url.query)

    if "gid" in query_values:
        try:
            sheet_id = int(query_values["gid"][0])
        except (
            TypeError,
            ValueError,
            IndexError,
        ):
            sheet_id = None

    if sheet_id is None and parsed_url.fragment:
        fragment_values = parse_qs(parsed_url.fragment)

        if "gid" in fragment_values:
            try:
                sheet_id = int(fragment_values["gid"][0])
            except (
                TypeError,
                ValueError,
                IndexError,
            ):
                sheet_id = None

    return ParsedGoogleSheetUrl(
        spreadsheet_id=spreadsheet_id,
        sheet_id=sheet_id,
    )


def escape_sheet_title(
    sheet_title: str,
) -> str:
    """
    Escape dấu nháy đơn để dùng tên tab trong A1 notation.

    Ví dụ:
    John's Sheet
    → John''s Sheet
    """
    return sheet_title.replace(
        "'",
        "''",
    )


def sanitize_sheet_title(
    sheet_title: str,
) -> str:
    """
    Chuẩn hóa tên tab theo giới hạn Google Sheets.
    """
    cleaned = sheet_title.strip()

    forbidden_characters = [
        ":",
        "\\",
        "/",
        "?",
        "*",
        "[",
        "]",
    ]

    for character in forbidden_characters:
        cleaned = cleaned.replace(
            character,
            "-",
        )

    cleaned = cleaned.strip("'")

    if not cleaned:
        cleaned = datetime.now(VN_TIMEZONE).strftime("Export %d-%m-%Y %H-%M")

    return cleaned[:100]


# =========================================================
# Google OAuth Credentials
# =========================================================


def get_active_google_connection(
    db: Session,
) -> GoogleConnection:
    """
    Lấy kết nối Google đang active mới nhất.
    """
    connection = db.scalar(
        select(GoogleConnection)
        .where(GoogleConnection.is_active.is_(True))
        .order_by(GoogleConnection.id.desc())
    )

    if connection is None:
        raise ValueError("Chưa kết nối tài khoản Google.")

    if not connection.refresh_token_encrypted:
        raise ValueError(
            "Kết nối Google không có refresh token. "
            "Vui lòng kết nối lại tài khoản Google."
        )

    return connection


def build_google_credentials(
    db: Session,
) -> Credentials:
    """
    Khôi phục Google Credentials từ token đã mã hóa
    trong bảng google_connections.

    Nếu access token hết hạn, hàm tự refresh token
    và cập nhật token mới vào database.
    """
    connection = get_active_google_connection(db)

    access_token = decrypt_text(connection.access_token_encrypted)

    refresh_token = decrypt_text(connection.refresh_token_encrypted)

    scopes = [scope for scope in (connection.scopes or "").split() if scope]

    if GOOGLE_SHEETS_SCOPE not in scopes:
        raise ValueError(
            "Kết nối Google hiện tại chưa có quyền "
            "ghi Google Sheets. Vui lòng kết nối lại."
        )

    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=connection.token_uri,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=scopes,
    )

    # Google Auth thường so sánh credentials.expiry
    # với UTC datetime dạng offset-naive.
    # Nếu PostgreSQL trả về datetime có timezone,
    # cần chuyển về UTC rồi bỏ tzinfo.
    if connection.token_expiry:
        expiry = connection.token_expiry

        if expiry.tzinfo is not None:
            expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)

        credentials.expiry = expiry

    try:
        if not credentials.valid:
            if not credentials.refresh_token:
                raise ValueError("Không có refresh token Google.")

            credentials.refresh(Request())

            connection.access_token_encrypted = encrypt_text(credentials.token)

            if credentials.refresh_token:
                connection.refresh_token_encrypted = encrypt_text(
                    credentials.refresh_token
                )

            # Google Auth thường trả expiry dạng
            # offset-naive UTC. Database đang dùng
            # DateTime(timezone=True), nên cần thêm
            # UTC timezone trước khi lưu.
            if credentials.expiry:
                refreshed_expiry = credentials.expiry

                if refreshed_expiry.tzinfo is None:
                    refreshed_expiry = refreshed_expiry.replace(tzinfo=timezone.utc)
                else:
                    refreshed_expiry = refreshed_expiry.astimezone(timezone.utc)

                connection.token_expiry = refreshed_expiry

            connection.last_error = None

            db.commit()

    except Exception as exc:
        print(
            "Google credential refresh error:",
            type(exc).__name__,
            repr(exc),
        )

        db.rollback()

        failed_connection = db.get(
            GoogleConnection,
            connection.id,
        )

        if failed_connection is not None:
            failed_connection.last_error = str(exc)[:2_000]

            db.commit()

        raise ValueError(
            "Không thể làm mới kết nối Google. Vui lòng kết nối lại tài khoản Google."
        ) from exc

    return credentials


def build_google_sheets_service(
    db: Session,
) -> Resource:
    """
    Tạo Google Sheets API client.
    """
    credentials = build_google_credentials(db)

    return build(
        "sheets",
        "v4",
        credentials=credentials,
        cache_discovery=False,
    )


# =========================================================
# Xử lý lỗi Google API
# =========================================================


def get_http_status(
    exc: HttpError,
) -> int | None:
    return getattr(
        exc.resp,
        "status",
        None,
    )


def raise_google_api_error(
    exc: HttpError,
    default_message: str,
) -> None:
    status_code = get_http_status(exc)

    if status_code == 400:
        raise ValueError(
            "Google Sheets từ chối yêu cầu. "
            "Vui lòng kiểm tra URL, tên tab "
            "và cấu trúc dữ liệu."
        ) from exc

    if status_code == 401:
        raise ValueError(
            "Kết nối Google đã hết hiệu lực. Vui lòng kết nối lại tài khoản Google."
        ) from exc

    if status_code == 403:
        raise ValueError(
            "Tài khoản Google hiện tại không có quyền chỉnh sửa file này."
        ) from exc

    if status_code == 404:
        raise ValueError(
            "Không tìm thấy Google Sheet hoặc "
            "tài khoản hiện tại không có quyền truy cập."
        ) from exc

    if status_code == 429:
        raise ValueError(
            "Google Sheets API đang giới hạn số lượng yêu cầu. Vui lòng thử lại sau."
        ) from exc

    raise ValueError(default_message) from exc


# =========================================================
# Metadata và tab
# =========================================================


def get_spreadsheet_metadata(
    service: Resource,
    spreadsheet_id: str,
) -> dict:
    """
    Lấy tên spreadsheet và danh sách các tab.
    """
    try:
        return (
            service.spreadsheets()
            .get(
                spreadsheetId=spreadsheet_id,
                fields=("spreadsheetId,properties.title,sheets.properties"),
            )
            .execute()
        )

    except HttpError as exc:
        raise_google_api_error(
            exc,
            "Không thể đọc thông tin Google Sheet.",
        )

    raise ValueError("Không thể đọc thông tin Google Sheet.")


def find_sheet_by_id(
    metadata: dict,
    sheet_id: int,
) -> dict | None:
    for sheet in metadata.get(
        "sheets",
        [],
    ):
        properties = sheet.get(
            "properties",
            {},
        )

        if properties.get("sheetId") == sheet_id:
            return properties

    return None


def find_sheet_by_title(
    metadata: dict,
    sheet_title: str,
) -> dict | None:
    for sheet in metadata.get(
        "sheets",
        [],
    ):
        properties = sheet.get(
            "properties",
            {},
        )

        if properties.get("title") == sheet_title:
            return properties

    return None


def generate_unique_sheet_title(
    metadata: dict,
    preferred_title: str | None,
) -> str:
    """
    Tạo tên tab không bị trùng.
    """
    if preferred_title:
        base_title = sanitize_sheet_title(preferred_title)
    else:
        base_title = datetime.now(VN_TIMEZONE).strftime("Export %d-%m-%Y %H-%M")

    existing_titles = {
        sheet.get(
            "properties",
            {},
        ).get("title")
        for sheet in metadata.get(
            "sheets",
            [],
        )
    }

    if base_title not in existing_titles:
        return base_title

    counter = 2

    while True:
        suffix = f" ({counter})"

        candidate = base_title[: 100 - len(suffix)] + suffix

        if candidate not in existing_titles:
            return candidate

        counter += 1


def create_new_sheet(
    service: Resource,
    spreadsheet_id: str,
    sheet_title: str,
) -> dict:
    """
    Tạo tab mới trong Google Sheet.
    """
    try:
        result = (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title": (sheet_title),
                                }
                            }
                        }
                    ]
                },
            )
            .execute()
        )

    except HttpError as exc:
        raise_google_api_error(
            exc,
            "Không thể tạo tab mới trong Google Sheet.",
        )

    replies = result.get(
        "replies",
        [],
    )

    if not replies:
        raise ValueError("Google Sheets API không trả về thông tin tab mới.")

    add_sheet_result = replies[0].get(
        "addSheet",
        {},
    )

    properties = add_sheet_result.get("properties")

    if not properties:
        raise ValueError("Không lấy được thông tin tab mới.")

    return properties


def delete_sheet(
    service: Resource,
    spreadsheet_id: str,
    sheet_id: int,
) -> None:
    """
    Xóa tab. Chủ yếu dùng để dọn tab mới tạo
    nếu export thất bại trước khi có dữ liệu.
    """
    try:
        (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": [{"deleteSheet": {"sheetId": (sheet_id)}}]},
            )
            .execute()
        )

    except HttpError:
        # Không làm hỏng lỗi export chính nếu
        # thao tác dọn tab thất bại.
        return


def clear_sheet_values(
    service: Resource,
    spreadsheet_id: str,
    sheet_title: str,
) -> None:
    """
    Xóa giá trị trong tab nhưng không xóa tab.
    """
    safe_title = escape_sheet_title(sheet_title)

    try:
        (
            service.spreadsheets()
            .values()
            .clear(
                spreadsheetId=spreadsheet_id,
                range=f"'{safe_title}'",
                body={},
            )
            .execute()
        )

    except HttpError as exc:
        raise_google_api_error(
            exc,
            "Không thể xóa dữ liệu tab đích.",
        )


# =========================================================
# Chuẩn hóa dữ liệu
# =========================================================


def normalize_google_sheet_value(
    value: Any,
) -> Any:
    if value is None:
        return ""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(VN_TIMEZONE)

        return value.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    return str(value)


def build_sheet_header(
    columns: list[str],
) -> list[str]:
    header: list[str] = []

    for column in columns:
        config = EXPORT_COLUMN_CONFIG.get(column)

        if config is None:
            raise ValueError(f"Không có cấu hình export cho cột: {column}")

        header.append(config["label"])

    return header


def build_listing_row(
    listing: Any,
    columns: list[str],
) -> list[Any]:
    return [
        normalize_google_sheet_value(
            getattr(
                listing,
                column,
                None,
            )
        )
        for column in columns
    ]


def chunk_rows(
    rows: Iterable[list[Any]],
    chunk_size: int = DEFAULT_BATCH_SIZE,
):
    """
    Chia dữ liệu thành từng batch để tránh gọi
    Google Sheets API cho từng dòng.
    """
    batch: list[list[Any]] = []

    for row in rows:
        batch.append(row)

        if len(batch) >= chunk_size:
            yield batch
            batch = []

    if batch:
        yield batch


def column_number_to_letter(
    number: int,
) -> str:
    """
    Chuyển số cột thành chữ:

    1 -> A
    26 -> Z
    27 -> AA
    """
    if number < 1:
        raise ValueError("Số cột phải lớn hơn 0.")

    result = ""

    while number:
        number, remainder = divmod(
            number - 1,
            26,
        )

        result = chr(65 + remainder) + result

    return result


# =========================================================
# Đọc và ghi dữ liệu
# =========================================================


def write_rows_batch(
    service: Resource,
    spreadsheet_id: str,
    sheet_title: str,
    start_row: int,
    rows: list[list[Any]],
) -> None:
    """
    Ghi một batch dữ liệu bằng values.update.
    """
    if not rows:
        return

    column_count = len(rows[0])

    if column_count == 0:
        raise ValueError("Không có cột để ghi Google Sheet.")

    end_column = column_number_to_letter(column_count)

    end_row = start_row + len(rows) - 1

    safe_title = escape_sheet_title(sheet_title)

    range_name = f"'{safe_title}'!A{start_row}:{end_column}{end_row}"

    try:
        (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={
                    "majorDimension": "ROWS",
                    "values": rows,
                },
            )
            .execute()
        )

    except HttpError as exc:
        raise_google_api_error(
            exc,
            f"Không thể ghi dữ liệu vào vùng {range_name}.",
        )


def read_header_row(
    service: Resource,
    spreadsheet_id: str,
    sheet_title: str,
) -> list[str]:
    """
    Đọc hàng đầu tiên của tab.
    """
    safe_title = escape_sheet_title(sheet_title)

    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=f"'{safe_title}'!1:1",
                majorDimension="ROWS",
            )
            .execute()
        )

    except HttpError as exc:
        raise_google_api_error(
            exc,
            "Không thể đọc header tab đích.",
        )

    values = result.get(
        "values",
        [],
    )

    if not values:
        return []

    return [str(value) for value in values[0]]


def get_last_data_row(
    service: Resource,
    spreadsheet_id: str,
    sheet_title: str,
) -> int:
    """
    Đọc cột A để xác định dòng cuối hiện có.

    Phù hợp khi cột đầu tiên luôn có dữ liệu,
    ví dụ Marketplace hoặc Listing ID.
    """
    safe_title = escape_sheet_title(sheet_title)

    try:
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=f"'{safe_title}'!A:A",
                majorDimension="COLUMNS",
            )
            .execute()
        )

    except HttpError as exc:
        raise_google_api_error(
            exc,
            "Không thể xác định dòng cuối của tab đích.",
        )

    values = result.get(
        "values",
        [],
    )

    if not values:
        return 0

    return len(values[0])


def validate_append_header(
    existing_header: list[str],
    expected_header: list[str],
) -> None:
    """
    Chỉ cho phép append khi header cũ trùng
    chính xác với cấu hình export hiện tại.
    """
    if not existing_header:
        return

    normalized_existing = [value.strip() for value in existing_header]

    normalized_expected = [value.strip() for value in expected_header]

    if normalized_existing != normalized_expected:
        raise ValueError(
            "Không thể ghi nối tiếp vì header của tab không khớp với các cột export."
        )


# =========================================================
# Format Google Sheet
# =========================================================


def format_export_sheet(
    service: Resource,
    spreadsheet_id: str,
    sheet_id: int,
    column_count: int,
) -> None:
    """
    - Freeze dòng đầu.
    - In đậm header.
    - Căn giữa header.
    - Bật màu nền nhẹ.
    - Tự điều chỉnh độ rộng cột.
    """
    requests = [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": 1,
                    },
                },
                "fields": ("gridProperties.frozenRowCount"),
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": (column_count),
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 0.85,
                            "green": 0.92,
                            "blue": 0.97,
                        },
                        "textFormat": {
                            "bold": True,
                        },
                        "horizontalAlignment": ("CENTER"),
                        "verticalAlignment": ("MIDDLE"),
                    }
                },
                "fields": (
                    "userEnteredFormat."
                    "backgroundColor,"
                    "userEnteredFormat."
                    "textFormat.bold,"
                    "userEnteredFormat."
                    "horizontalAlignment,"
                    "userEnteredFormat."
                    "verticalAlignment"
                ),
            }
        },
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": column_count,
                }
            }
        },
    ]

    try:
        (
            service.spreadsheets()
            .batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": requests,
                },
            )
            .execute()
        )

    except HttpError as exc:
        raise_google_api_error(
            exc,
            "Đã ghi dữ liệu nhưng không thể format Google Sheet.",
        )


# =========================================================
# Hàm export chính
# =========================================================


def export_listings_to_google_sheet(
    db: Session,
    request: GoogleSheetExportRequest,
) -> dict:
    """
    Export listing sang Google Sheet.

    Hỗ trợ:
    - NEW_TAB
    - OVERWRITE
    - APPEND
    """
    parsed_url = parse_google_sheet_url(request.spreadsheet_url)

    service = build_google_sheets_service(db)

    metadata = get_spreadsheet_metadata(
        service=service,
        spreadsheet_id=(parsed_url.spreadsheet_id),
    )

    sheet_properties: dict | None = None
    created_new_sheet = False

    write_mode = request.write_mode.upper()

    if write_mode not in {
        "NEW_TAB",
        "OVERWRITE",
        "APPEND",
    }:
        raise ValueError("Chế độ ghi Google Sheet không hợp lệ.")

    if write_mode == "NEW_TAB":
        sheet_title = generate_unique_sheet_title(
            metadata=metadata,
            preferred_title=(request.target_tab_name),
        )

        sheet_properties = create_new_sheet(
            service=service,
            spreadsheet_id=(parsed_url.spreadsheet_id),
            sheet_title=sheet_title,
        )

        created_new_sheet = True

    else:
        if request.target_tab_name:
            requested_title = request.target_tab_name.strip()

            sheet_properties = find_sheet_by_title(
                metadata,
                requested_title,
            )

        elif parsed_url.sheet_id is not None:
            sheet_properties = find_sheet_by_id(
                metadata,
                parsed_url.sheet_id,
            )

        if sheet_properties is None:
            raise ValueError(
                "Không tìm thấy tab Google Sheet "
                "đích. Hãy nhập tên tab hoặc dùng "
                "URL có gid hợp lệ."
            )

        sheet_title = sheet_properties["title"]

    sheet_id = sheet_properties["sheetId"]

    expected_header = build_sheet_header(request.columns)

    try:
        if write_mode == "OVERWRITE":
            clear_sheet_values(
                service=service,
                spreadsheet_id=(parsed_url.spreadsheet_id),
                sheet_title=sheet_title,
            )

            write_rows_batch(
                service=service,
                spreadsheet_id=(parsed_url.spreadsheet_id),
                sheet_title=sheet_title,
                start_row=1,
                rows=[expected_header],
            )

            current_row = 2

        elif write_mode == "NEW_TAB":
            write_rows_batch(
                service=service,
                spreadsheet_id=(parsed_url.spreadsheet_id),
                sheet_title=sheet_title,
                start_row=1,
                rows=[expected_header],
            )

            current_row = 2

        else:
            existing_header = read_header_row(
                service=service,
                spreadsheet_id=(parsed_url.spreadsheet_id),
                sheet_title=sheet_title,
            )

            validate_append_header(
                existing_header=existing_header,
                expected_header=expected_header,
            )

            if not existing_header:
                write_rows_batch(
                    service=service,
                    spreadsheet_id=(parsed_url.spreadsheet_id),
                    sheet_title=sheet_title,
                    start_row=1,
                    rows=[expected_header],
                )

                current_row = 2

            else:
                last_row = get_last_data_row(
                    service=service,
                    spreadsheet_id=(parsed_url.spreadsheet_id),
                    sheet_title=sheet_title,
                )

                current_row = last_row + 1

        query = build_listing_export_query(
            filters=request.filters,
            sort=request.sort,
        )

        if request.scope == "CURRENT_PAGE":
            offset = (request.page - 1) * request.page_size

            query = query.offset(offset).limit(request.page_size)

        row_stream = (
            build_listing_row(
                listing,
                request.columns,
            )
            for listing in stream_listing_rows(
                db=db,
                query=query,
                batch_size=2_000,
            )
        )

        exported_rows = 0

        for batch in chunk_rows(
            row_stream,
            chunk_size=DEFAULT_BATCH_SIZE,
        ):
            write_rows_batch(
                service=service,
                spreadsheet_id=(parsed_url.spreadsheet_id),
                sheet_title=sheet_title,
                start_row=current_row,
                rows=batch,
            )

            batch_length = len(batch)

            current_row += batch_length
            exported_rows += batch_length

        if exported_rows == 0:
            raise ValueError("Không có dữ liệu phù hợp để export.")

        format_export_sheet(
            service=service,
            spreadsheet_id=(parsed_url.spreadsheet_id),
            sheet_id=sheet_id,
            column_count=len(request.columns),
        )

    except Exception:
        if created_new_sheet:
            delete_sheet(
                service=service,
                spreadsheet_id=(parsed_url.spreadsheet_id),
                sheet_id=sheet_id,
            )

        raise

    output_url = (
        "https://docs.google.com/"
        "spreadsheets/d/"
        f"{parsed_url.spreadsheet_id}"
        f"/edit#gid={sheet_id}"
    )

    return {
        "spreadsheet_id": (parsed_url.spreadsheet_id),
        "spreadsheet_title": (
            metadata.get(
                "properties",
                {},
            ).get("title")
        ),
        "sheet_id": sheet_id,
        "sheet_title": sheet_title,
        "write_mode": write_mode,
        "exported_rows": exported_rows,
        "output_url": output_url,
    }
