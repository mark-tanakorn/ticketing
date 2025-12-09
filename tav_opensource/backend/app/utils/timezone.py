"""
Timezone utilities for consistent datetime handling.

Ensures all timestamps use local timezone, not UTC.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import os


def get_local_timezone() -> ZoneInfo:
    """
    Get the local system timezone.
    
    Returns:
        ZoneInfo: Local timezone object
    """
    # Try to get from environment first
    tz_name = os.environ.get('TZ')
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    
    # Fall back to system local timezone
    try:
        # This will use the system's local timezone
        return ZoneInfo('localtime')
    except Exception:
        # If all else fails, use UTC
        return timezone.utc


def get_local_now() -> datetime:
    """
    Get current datetime in local timezone.
    
    Returns:
        datetime: Current time in local timezone with timezone info
    """
    return datetime.now(tz=get_local_timezone())


def to_local(dt: datetime) -> datetime:
    """
    Convert a datetime to local timezone.
    
    Args:
        dt: Datetime to convert (can be naive or aware)
        
    Returns:
        datetime: Datetime in local timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(get_local_timezone())


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC.
    
    Args:
        dt: Datetime to convert (can be naive or aware)
        
    Returns:
        datetime: Datetime in UTC
    """
    if dt.tzinfo is None:
        # Assume local if naive
        dt = dt.replace(tzinfo=get_local_timezone())
    
    return dt.astimezone(timezone.utc)

