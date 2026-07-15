from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.sync_service import run_sync

scheduler = BackgroundScheduler(timezone=settings.sync_timezone)


def scheduled_sync():
    with SessionLocal() as db:
        try:
            run_sync(db, "SCHEDULED")
        except Exception:
            pass


def start_scheduler():
    if scheduler.running:
        return
    scheduler.add_job(
        scheduled_sync,
        "cron",
        hour=settings.sync_hour,
        minute=settings.sync_minute,
        id="daily_ebay_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
