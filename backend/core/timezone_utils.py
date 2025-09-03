"""
Timezone utilities for consistent KST (Korea Standard Time) timestamps
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# Korea Standard Time (UTC+9)
KST = timezone(timedelta(hours=9))

def now_kst() -> datetime:
    """Get current time in KST"""
    return datetime.now(KST)

def now_kst_iso() -> str:
    """Get current time in KST as ISO format string"""
    return now_kst().isoformat()

def now_kst_str(format: str = "%Y%m%d_%H%M%S") -> str:
    """Get current time in KST as formatted string"""
    return now_kst().strftime(format)

def to_kst(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert any datetime to KST"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)

def utc_to_kst_iso(utc_string: str) -> str:
    """Convert UTC ISO string to KST ISO string"""
    try:
        dt = datetime.fromisoformat(utc_string.replace('Z', '+00:00'))
        return to_kst(dt).isoformat()
    except:
        return utc_string