from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.services.export_columns import (
    get_export_column_options,
)

from app.services.pdf_export import (
    export_listings_to_pdf,
)
from app.core.database import get_db
from app.schemas.export import (
    ExcelExportRequest,
    GoogleSheetExportRequest,
    GoogleSheetPreviewRequest,
    PdfExportRequest,
)
from app.services.excel_export import (
    export_listings_to_excel,
)
from app.services.google_sheet_export import (
    build_google_sheets_service,
    export_listings_to_google_sheet,
    get_spreadsheet_metadata,
    parse_google_sheet_url,
)

router = APIRouter(
    prefix="/exports",
    tags=["Exports"],
)


def remove_temporary_file(
    path: str,
):
    Path(path).unlink(missing_ok=True)


@router.post("/excel")
def export_excel(
    payload: ExcelExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        (
            file_path,
            filename,
            exported_rows,
        ) = export_listings_to_excel(
            db=db,
            request=payload,
        )

        background_tasks.add_task(
            remove_temporary_file,
            str(file_path),
        )

        response = FileResponse(
            path=file_path,
            filename=filename,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            background=background_tasks,
        )

        response.headers["X-Exported-Rows"] = str(exported_rows)

        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(
            "Excel export error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="Không thể tạo file Excel.",
        ) from exc


@router.post("/google-sheet/preview")
def preview_google_sheet(
    payload: GoogleSheetPreviewRequest,
    db: Session = Depends(get_db),
):
    try:
        parsed_url = parse_google_sheet_url(payload.spreadsheet_url)

        service = build_google_sheets_service(db)

        metadata = get_spreadsheet_metadata(
            service=service,
            spreadsheet_id=(parsed_url.spreadsheet_id),
        )

        tabs = []

        for sheet in metadata.get(
            "sheets",
            [],
        ):
            properties = sheet.get(
                "properties",
                {},
            )

            tabs.append(
                {
                    "sheet_id": properties.get("sheetId"),
                    "title": properties.get("title"),
                    "index": properties.get("index"),
                }
            )

        return {
            "spreadsheet_id": (parsed_url.spreadsheet_id),
            "spreadsheet_title": (
                metadata.get(
                    "properties",
                    {},
                ).get("title")
            ),
            "selected_sheet_id": (parsed_url.sheet_id),
            "tabs": tabs,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(
            "Google Sheet preview error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=("Không thể kiểm tra Google Sheet."),
        ) from exc


@router.post("/google-sheet")
def export_google_sheet(
    payload: GoogleSheetExportRequest,
    db: Session = Depends(get_db),
):
    try:
        result = export_listings_to_google_sheet(
            db=db,
            request=payload,
        )

        return {
            "message": ("Export Google Sheet thành công"),
            **result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(
            "Google Sheet export error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=("Không thể export Google Sheet."),
        ) from exc


@router.get("/columns")
def list_export_columns(
    db: Session = Depends(get_db),
):
    try:
        return get_export_column_options(db)

    except Exception as exc:
        print(
            "Export columns error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=("Không thể đọc danh sách cột từ nguồn đồng bộ."),
        ) from exc


@router.post("/pdf")
def export_pdf(
    payload: PdfExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        (
            file_path,
            filename,
            exported_rows,
        ) = export_listings_to_pdf(
            db=db,
            request=payload,
        )

        background_tasks.add_task(
            remove_temporary_file,
            str(file_path),
        )

        response = FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/pdf",
            background=background_tasks,
        )

        response.headers["X-Exported-Rows"] = str(exported_rows)

        return response

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        print(
            "PDF export error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail="Không thể tạo file PDF.",
        ) from exc
