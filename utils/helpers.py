import re
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}{timestamp}{random_part}" if prefix else f"{timestamp}{random_part}"


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length].rsplit(' ', 1)[0] + suffix


def calculate_percentage(part: float, total: float) -> float:
    """Calculate percentage"""
    if total == 0:
        return 0.0
    return round((part / total) * 100, 1)


def get_level_from_xp(xp: int) -> int:
    """Calculate level from XP"""
    if xp < 100:
        return 1
    elif xp < 1000:
        return (xp // 100) + 1
    else:
        return 10 + ((xp - 1000) // 200)


def get_xp_for_level(level: int) -> int:
    """Get XP required for a level"""
    if level <= 1:
        return 0
    elif level <= 10:
        return (level - 1) * 100
    else:
        return 1000 + (level - 10) * 200


def get_level_progress(xp: int) -> int:
    """Get progress to next level (0-100)"""
    level = get_level_from_xp(xp)
    current_xp = get_xp_for_level(level)
    next_xp = get_xp_for_level(level + 1)
    return calculate_percentage(xp - current_xp, next_xp - current_xp)


def format_date(date: datetime, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime to string"""
    if not date:
        return ""
    return date.strftime(format_str)


def time_ago(date: datetime) -> str:
    """Get time ago string"""
    if not date:
        return ""
    
    now = datetime.utcnow()
    diff = now - date
    
    if diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return "Just now"


def extract_difficulty(level: int) -> str:
    """Extract difficulty from level"""
    if level <= 2:
        return "easy"
    elif level <= 4:
        return "medium"
    else:
        return "hard"


def is_valid_uuid(uuid_str: str) -> bool:
    """Check if string is a valid UUID"""
    uuid_regex = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_regex, uuid_str.lower()))


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result