from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.core.config import settings
from app.core.security import decrypt_text
from app.models.google_connection import GoogleConnection


def credentials_from_connection(connection: GoogleConnection) -> Credentials:
    return Credentials(
        token=decrypt_text(connection.access_token_encrypted),
        refresh_token=decrypt_text(connection.refresh_token_encrypted),
        token_uri=connection.token_uri,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=connection.scopes.split(),
    )


def get_service(connection: GoogleConnection):
    return build("sheets", "v4", credentials=credentials_from_connection(connection), cache_discovery=False)


def read_sheet_snapshot(connection: GoogleConnection) -> tuple[list[str], list[list], int]:
    service = get_service(connection)
    sheet = settings.google_sheet_name.replace("'", "''")
    result = service.spreadsheets().values().get(
        spreadsheetId=settings.google_spreadsheet_id,
        range=f"'{sheet}'!A1:AQ",
        majorDimension="ROWS",
        valueRenderOption="UNFORMATTED_VALUE",
        dateTimeRenderOption="SERIAL_NUMBER",
    ).execute()
    values = result.get("values", [])
    if not values:
        return [], [], 1
    headers = [str(x).strip() for x in values[0]]
    rows = values[1:]
    while rows and not any(value not in (None, "") for value in rows[-1]):
        rows.pop()
    return headers, rows, len(rows) + 1


def clear_processed_rows(connection: GoogleConnection, last_row: int) -> str:
    if last_row < 2:
        return ""
    service = get_service(connection)
    sheet = settings.google_sheet_name.replace("'", "''")
    clear_range = f"'{sheet}'!A2:AQ{last_row}"
    service.spreadsheets().values().clear(
        spreadsheetId=settings.google_spreadsheet_id,
        range=clear_range,
        body={},
    ).execute()
    return clear_range
