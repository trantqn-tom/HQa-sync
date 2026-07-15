from datetime import datetime
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def now_vn() -> datetime:
    """Current time in GMT+7 (Asia/Ho_Chi_Minh)."""
    return datetime.now(VN_TZ)
