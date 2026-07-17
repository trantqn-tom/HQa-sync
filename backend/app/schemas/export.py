from typing import Literal

from pydantic import BaseModel, Field, field_validator


DEFAULT_EXPORT_COLUMNS = [
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
    "quantity",
    "last_sync_action",
    "last_seen_at",
]


ALLOWED_EXPORT_COLUMNS = {
    "marketplace",
    "listing_id",
    "product_id",
    "keyword",
    "brand",
    "model",
    "category",
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
    "quantity",
    "match_type",
    "exclude_flag",
    "raw_confidence",
    "last_sync_action",
    "listing_published_at",
    "collected_at",
    "last_seen_at",
    "last_status_checked_at",
    "created_at",
    "updated_at",
}


class ListingExportFilters(BaseModel):
    q: str | None = None

    statuses: list[str] = Field(default_factory=list)

    marketplaces: list[str] = Field(default_factory=list)

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
        unique_columns = []

        for column in columns:
            if column not in ALLOWED_EXPORT_COLUMNS:
                raise ValueError(f"Cột export không hợp lệ: {column}")

            if column not in unique_columns:
                unique_columns.append(column)

        if not unique_columns:
            raise ValueError("Phải chọn ít nhất một cột export")

        return unique_columns


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
