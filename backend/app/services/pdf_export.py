from __future__ import annotations

import json
import os
import re
from datetime import datetime
from decimal import Decimal
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from sqlalchemy.orm import Session

from app.schemas.export import PdfExportRequest
from app.services.export_columns import (
    get_export_column_config,
    get_export_label,
    resolve_export_value,
    validate_requested_columns,
)
from app.services.listing_export_query import (
    build_listing_export_query,
    stream_listing_rows,
)


VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

MAX_COLUMNS_PER_GROUP = 10

LEFT_MARGIN = 10 * mm
RIGHT_MARGIN = 10 * mm
TOP_MARGIN = 10 * mm
BOTTOM_MARGIN = 12 * mm


def register_pdf_fonts() -> tuple[str, str]:
    regular_candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]

    bold_candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arialbd.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]

    regular_path = next(
        (path for path in regular_candidates if path.exists()),
        None,
    )

    bold_path = next(
        (path for path in bold_candidates if path.exists()),
        None,
    )

    if regular_path is None:
        return "Helvetica", "Helvetica-Bold"

    regular_name = "HQaPdfRegular"
    bold_name = "HQaPdfBold"

    registered = set(pdfmetrics.getRegisteredFontNames())

    if regular_name not in registered:
        pdfmetrics.registerFont(
            TTFont(
                regular_name,
                str(regular_path),
            )
        )

    if bold_name not in registered:
        pdfmetrics.registerFont(
            TTFont(
                bold_name,
                str(bold_path or regular_path),
            )
        )

    return regular_name, bold_name


def sanitize_pdf_filename(
    filename: str,
) -> str:
    value = re.sub(
        r'[<>:"/\\|?*\x00-\x1F]',
        "_",
        filename,
    )

    value = value.strip(" .")

    if not value:
        value = "marketplace-listings"

    if not value.lower().endswith(".pdf"):
        value += ".pdf"

    return value[:180]


def normalize_pdf_value(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(value, Decimal):
        return format(value, "f")

    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(VN_TIMEZONE)

        return value.strftime("%d/%m/%Y %H:%M:%S")

    if isinstance(value, (dict, list, tuple)):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    return str(value)


def paragraph_text(
    value: Any,
) -> str:
    text = normalize_pdf_value(value)

    return escape(text).replace(
        "\n",
        "<br/>",
    )


def split_column_groups(
    columns: list[str],
) -> list[list[str]]:
    return [
        columns[index : index + MAX_COLUMNS_PER_GROUP]
        for index in range(
            0,
            len(columns),
            MAX_COLUMNS_PER_GROUP,
        )
    ]


def calculate_column_widths(
    columns: list[str],
    usable_width: float,
) -> list[float]:
    weights = []

    for column in columns:
        config = get_export_column_config(column)

        weights.append(
            max(
                10,
                min(
                    float(config.get("width", 18)),
                    50,
                ),
            )
        )

    total_weight = sum(weights) or 1

    return [usable_width * weight / total_weight for weight in weights]


def create_table_style() -> TableStyle:
    return TableStyle(
        [
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.25,
                colors.HexColor("#CBD5E1"),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                3,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                3,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                3,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                3,
            ),
        ]
    )


def export_listings_to_pdf(
    db: Session,
    request: PdfExportRequest,
) -> tuple[Path, str, int]:
    selected_columns = validate_requested_columns(
        db=db,
        columns=request.columns,
    )

    query = build_listing_export_query(
        filters=request.filters,
        sort=request.sort,
    )

    # Chỉ đặt limit khi người dùng chọn trang hiện tại.
    # FILTERED tuyệt đối không có limit số dòng.
    if request.scope == "CURRENT_PAGE":
        offset = (request.page - 1) * request.page_size

        query = query.offset(offset).limit(request.page_size)

    default_filename = (
        f"marketplace-listings-{datetime.now(VN_TIMEZONE):%Y%m%d-%H%M%S}.pdf"
    )

    filename = sanitize_pdf_filename(request.filename or default_filename)

    temporary_file = NamedTemporaryFile(
        prefix="marketplace-pdf-",
        suffix=".pdf",
        delete=False,
    )

    temporary_path = Path(temporary_file.name)

    temporary_file.close()

    regular_font, bold_font = register_pdf_fonts()

    page_size = landscape(A3)

    page_width, page_height = page_size

    usable_width = page_width - LEFT_MARGIN - RIGHT_MARGIN

    canvas = Canvas(
        str(temporary_path),
        pagesize=page_size,
        pageCompression=1,
    )

    title_style = ParagraphStyle(
        name="PdfTitle",
        fontName=bold_font,
        fontSize=13,
        leading=15,
    )

    header_style = ParagraphStyle(
        name="PdfHeader",
        fontName=bold_font,
        fontSize=6.5,
        leading=7.5,
        textColor=colors.HexColor("#0F172A"),
    )

    cell_style = ParagraphStyle(
        name="PdfCell",
        fontName=regular_font,
        fontSize=6,
        leading=7.2,
        textColor=colors.HexColor("#1E293B"),
    )

    groups = split_column_groups(selected_columns)

    first_page = True

    exported_rows = 0

    page_number = 0

    def start_page(
        group_index: int,
        group_columns: list[str],
    ) -> tuple[float, list[float]]:
        nonlocal first_page
        nonlocal page_number

        if not first_page:
            canvas.showPage()

        first_page = False
        page_number += 1

        y = page_height - TOP_MARGIN

        title = request.title or "Marketplace Listings"

        canvas.setFont(
            bold_font,
            13,
        )

        canvas.drawString(
            LEFT_MARGIN,
            y,
            title,
        )

        canvas.setFont(
            regular_font,
            7,
        )

        canvas.drawRightString(
            page_width - RIGHT_MARGIN,
            y,
            (f"Trang {page_number} · Nhóm cột {group_index + 1}/{len(groups)}"),
        )

        y -= 8 * mm

        canvas.setFont(
            regular_font,
            7,
        )

        canvas.drawString(
            LEFT_MARGIN,
            y,
            datetime.now(VN_TIMEZONE).strftime("Xuất lúc %d/%m/%Y %H:%M:%S"),
        )

        y -= 6 * mm

        column_widths = calculate_column_widths(
            group_columns,
            usable_width,
        )

        header_cells = [
            Paragraph(
                escape(get_export_label(column)),
                header_style,
            )
            for column in group_columns
        ]

        header_table = Table(
            [header_cells],
            colWidths=column_widths,
        )

        header_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#D9EAF7"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor("#94A3B8"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        3,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        _, header_height = header_table.wrap(
            usable_width,
            page_height,
        )

        header_table.drawOn(
            canvas,
            LEFT_MARGIN,
            y - header_height,
        )

        y -= header_height

        return y, column_widths

    try:
        for group_index, group_columns in enumerate(groups):
            y, column_widths = start_page(
                group_index,
                group_columns,
            )

            group_row_count = 0

            for listing in stream_listing_rows(
                db=db,
                query=query,
                batch_size=1_000,
            ):
                values = [
                    resolve_export_value(
                        listing,
                        column,
                    )
                    for column in group_columns
                ]

                cells = [
                    Paragraph(
                        paragraph_text(value),
                        cell_style,
                    )
                    for value in values
                ]

                row_table = Table(
                    [cells],
                    colWidths=column_widths,
                    splitByRow=1,
                    splitInRow=1,
                )

                row_table.setStyle(create_table_style())

                _, row_height = row_table.wrap(
                    usable_width,
                    page_height,
                )

                available_height = y - BOTTOM_MARGIN

                if row_height > available_height:
                    y, column_widths = start_page(
                        group_index,
                        group_columns,
                    )

                    _, row_height = row_table.wrap(
                        usable_width,
                        page_height,
                    )

                row_table.drawOn(
                    canvas,
                    LEFT_MARGIN,
                    y - row_height,
                )

                y -= row_height

                group_row_count += 1

                # Chỉ đếm ở nhóm đầu để tránh nhân đôi số dòng.
                if group_index == 0:
                    exported_rows += 1

            if group_row_count == 0:
                raise ValueError("Không có dữ liệu phù hợp để export PDF")

        canvas.save()

        return (
            temporary_path,
            filename,
            exported_rows,
        )

    except Exception:
        try:
            canvas.save()
        except Exception:
            pass

        temporary_path.unlink(missing_ok=True)

        raise
