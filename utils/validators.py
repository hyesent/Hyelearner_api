import re
from typing import Optional, Tuple


def validate_email(email: str) -> bool:
    """Validate email format"""
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(regex, email))


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"


def validate_username(username: str) -> Tuple[bool, str]:
    """Validate username"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username must be less than 30 characters"
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    return True, "Username is valid"


def validate_phone(phone: str) -> bool:
    """Validate phone number"""
    # Basic phone validation (can be customized per country)
    return bool(re.match(r'^\+?[0-9]{10,15}$', phone))


def validate_url(url: str) -> bool:
    """Validate URL"""
    regex = r'^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$'
    return bool(re.match(regex, url))


def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    # Remove potentially dangerous characters
    text = re.sub(r'[<>]', '', text)
    text = text.strip()
    return text


def validate_subject(subject: str) -> bool:
    """Validate subject name"""
    valid_subjects = [
        "Mathematics", "English", "Physics", "Chemistry", 
        "Biology", "Economics", "Government", "CRS"
    ]
    return subject in valid_subjects


def validate_exam_type(exam: str) -> bool:
    """Validate exam type"""
    valid_exams = ["jamb", "waec", "neco", "ssce", "general"]
    return exam.lower() in valid_exams


def validate_difficulty(difficulty: str) -> bool:
    """Validate difficulty level"""
    valid_difficulties = ["easy", "medium", "hard"]
    return difficulty.lower() in valid_difficulties