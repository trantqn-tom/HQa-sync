from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, get_db
from app.models.sync_run import SyncRun
from app.services.sync_service import run_sync

router = APIRouter(prefix="/sync", tags=["Sync"])


def _run_background():
    with SessionLocal() as db:
        try:
            run_sync(db, "MANUAL")
        except Exception:
            pass


@router.post("/run")
def start_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_background)
    return {"message": "Đã bắt đầu đồng bộ"}


@router.get("/runs")
def runs(db: Session = Depends(get_db), limit: int = 20):
    items = db.scalars(select(SyncRun).order_by(SyncRun.started_at.desc()).limit(min(limit, 100))).all()
    return items


@router.get("/runs/{run_id}")
def run_detail(run_id: str, db: Session = Depends(get_db)):
    item = db.get(SyncRun, run_id)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lần đồng bộ")
    return item
