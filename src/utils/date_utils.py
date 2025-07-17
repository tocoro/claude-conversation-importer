"""
Date utility functions for conversation processing
"""
from datetime import datetime, timezone
from typing import Optional, Union
from dateutil.parser import parse as parse_date


def parse_timestamp(timestamp: Union[str, int, float, datetime]) -> Optional[datetime]:
    """Parse various timestamp formats to datetime object"""
    if timestamp is None:
        return None
        
    try:
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, (int, float)):
            # Unix timestamp
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(timestamp, str):
            # String timestamp
            return parse_date(timestamp)
        else:
            return None
    except (ValueError, TypeError, OverflowError):
        return None


def format_for_notion(dt: datetime) -> str:
    """Format datetime for Notion API"""
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def format_display(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_date_range_filter(start_date: Optional[str], end_date: Optional[str]) -> Optional[dict]:
    """Create Notion API date filter from date range"""
    if not start_date and not end_date:
        return None
    
    filter_condition = {"property": "日付", "date": {}}
    
    if start_date:
        try:
            start_dt = parse_date(start_date)
            filter_condition["date"]["on_or_after"] = start_dt.isoformat()
        except ValueError:
            print(f"Warning: Invalid start date format: {start_date}")
    
    if end_date:
        try:
            end_dt = parse_date(end_date)
            filter_condition["date"]["on_or_before"] = end_dt.isoformat()
        except ValueError:
            print(f"Warning: Invalid end date format: {end_date}")
    
    return filter_condition if filter_condition["date"] else None