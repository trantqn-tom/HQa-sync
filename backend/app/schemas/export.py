from typing import Literal

from pydantic import BaseModel, Field, field_validator


DEFAULT_EXPORT_COLUMNS = [
    "raw::marketplace",
    "raw::listing_id",
    "raw::product_id",
    "raw::keyword",
    "raw::brand",
    "raw::model",
    "raw::category_name",
    "raw::listing_title",
    "raw::listing_url",
    "raw::seller_or_shop",
    "raw::price",
    "raw::shipping_price",
    "raw::total_price",
    "raw::currency",
    "raw::listing_status",
    "raw::condition",
    "raw::location",
]


def normalize_export_columns(
    columns: list[str],
) -> list[str]:
    result: list[str] = []

    for column in columns:
        value = str(column or "").strip()

        if not value:
            continue

        if not value.startswith(("raw::", "db::")):
            raise ValueError(f"Định dạng cột export không hợp lệ: {value}")

        if len(value) > 255:
            raise ValueError("Tên cột export quá dài")

        if value not in result:
            result.append(value)

    if not result:
        raise ValueError("Phải chọn ít nhất một cột export")

    return result


class ListingExportFilters(BaseModel):
    q: str | None = None

    statuses: list[str] = Field(
        default_factory=list,
    )

    marketplaces: list[str] = Field(
        default_factory=list,
    )

    sellers: list[str] = Field(
        default_factory=list,
    )

    action: str | None = None
    product_id: str | None = None
    brand: str | None = None
    category_name: str | None = None
    condition: str | None = None

    price_min: float | None = None
    price_max: float | None = None


class ExportSort(BaseModel):
    field: str = "last_seen_at"

    order: Literal[
        "asc",
        "desc",
    ] = "desc"


class ExcelExportRequest(BaseModel):
    scope: Literal[
        "FILTERED",
        "CURRENT_PAGE",
    ] = "FILTERED"

    filters: ListingExportFilters = Field(default_factory=ListingExportFilters)

    columns: list[str] = Field(default_factory=lambda: DEFAULT_EXPORT_COLUMNS.copy())

    sort: ExportSort = Field(default_factory=ExportSort)

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=30,
        ge=1,
        le=200,
    )

    filename: str | None = None

    @field_validator("columns")
    @classmethod
    def validate_columns(
        cls,
        columns: list[str],
    ) -> list[str]:
        return normalize_export_columns(columns)


class GoogleSheetExportRequest(BaseModel):
    spreadsheet_url: str

    target_tab_name: str | None = None

    write_mode: Literal[
        "NEW_TAB",
        "OVERWRITE",
        "APPEND",
    ] = "NEW_TAB"

    scope: Literal[
        "FILTERED",
        "CURRENT_PAGE",
    ] = "FILTERED"

    filters: ListingExportFilters = Field(default_factory=ListingExportFilters)

    columns: list[str] = Field(default_factory=lambda: DEFAULT_EXPORT_COLUMNS.copy())

    sort: ExportSort = Field(default_factory=ExportSort)

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=30,
        ge=1,
        le=200,
    )

    @field_validator("spreadsheet_url")
    @classmethod
    def validate_spreadsheet_url(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if "/spreadsheets/d/" not in value:
            raise ValueError("Google Sheet URL không hợp lệ")

        return value

    @field_validator("target_tab_name")
    @classmethod
    def validate_tab_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            return None

        forbidden_chars = [
            ":",
            "\\",
            "/",
            "?",
            "*",
            "[",
            "]",
        ]

        if any(char in value for char in forbidden_chars):
            raise ValueError("Tên tab chứa ký tự không hợp lệ")

        if len(value) > 100:
            raise ValueError("Tên tab tối đa 100 ký tự")

        return value


class GoogleSheetPreviewRequest(BaseModel):
    spreadsheet_url: str


class PdfExportRequest(BaseModel):
    scope: Literal[
        "FILTERED",
        "CURRENT_PAGE",
    ] = "FILTERED"

    filters: ListingExportFilters = Field(default_factory=ListingExportFilters)

    columns: list[str] = Field(default_factory=lambda: DEFAULT_EXPORT_COLUMNS.copy())

    sort: ExportSort = Field(default_factory=ExportSort)

    page: int = Field(
        default=1,
        ge=1,
    )

    page_size: int = Field(
        default=30,
        ge=1,
        le=200,
    )

    title: str | None = "Marketplace Listings"

    filename: str | None = None

    @field_validator("columns")
    @classmethod
    def validate_columns(
        cls,
        columns: list[str],
    ) -> list[str]:
        return normalize_export_columns(columns)
