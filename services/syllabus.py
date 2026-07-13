# services/syllabus.py
"""
Dynamic syllabus generator from question index.
Builds exam-specific syllabus data with topic weights and priorities.
Can be extended for multiple exam types (JAMB, WAEC, NECO, etc.)
"""

from typing import Dict, List, Optional
from .question_index import QUESTION_INDEX, get_subject_topics, get_all_subjects

# ============================================================
# EXAM-SPECIFIC TOPIC WEIGHTS
# ============================================================

# These can be extended for different exam types
EXAM_WEIGHTS = {
    "jamb": {
        "Mathematics": {
            "Algebra": 0.25,
            "Trigonometry": 0.15,
            "Statistics": 0.15,
            "Probability": 0.10,
            "Calculus": 0.10,
            "Geometry": 0.10,
            "Vectors": 0.05,
            "Number System": 0.10
        },
        "English Language": {
            "Grammar": 0.20,
            "Comprehension": 0.20,
            "Vocabulary": 0.15,
            "Essay Writing": 0.15,
            "Lexis and Structure": 0.10,
            "Oral English": 0.10,
            "Summary": 0.10
        },
        "Physics": {
            "Mechanics": 0.25,
            "Waves": 0.15,
            "Electricity": 0.15,
            "Optics": 0.10,
            "Magnetism": 0.10,
            "Heat": 0.10,
            "Modern Physics": 0.15
        },
        "Chemistry": {
            "Organic Chemistry": 0.20,
            "Inorganic Chemistry": 0.20,
            "Physical Chemistry": 0.20,
            "Atomic Structure": 0.10,
            "Chemical Bonding": 0.10,
            "Acids and Bases": 0.10,
            "Equilibrium": 0.10
        }
    },
    "waec": {
        # WAEC-specific weights (slightly different from JAMB)
        "Mathematics": {
            "Algebra": 0.20,
            "Geometry": 0.15,
            "Trigonometry": 0.12,
            "Statistics": 0.12,
            "Probability": 0.08,
            "Calculus": 0.08,
            "Vectors": 0.05,
            "Number System": 0.20
        },
        "English Language": {
            "Grammar": 0.20,
            "Comprehension": 0.20,
            "Vocabulary": 0.15,
            "Essay Writing": 0.15,
            "Lexis and Structure": 0.15,
            "Oral English": 0.10,
            "Summary": 0.05
        }
    },
    "neco": {
        # NECO-specific weights
        "Mathematics": {
            "Algebra": 0.22,
            "Geometry": 0.15,
            "Trigonometry": 0.12,
            "Statistics": 0.12,
            "Probability": 0.08,
            "Calculus": 0.08,
            "Vectors": 0.05,
            "Number System": 0.18
        },
        "English Language": {
            "Grammar": 0.22,
            "Comprehension": 0.18,
            "Vocabulary": 0.15,
            "Essay Writing": 0.15,
            "Lexis and Structure": 0.15,
            "Oral English": 0.10,
            "Summary": 0.05
        }
    }
}

# ============================================================
# PRIORITY MAPPING
# ============================================================

def get_priority_from_weight(weight: float) -> str:
    """Convert weight to priority level"""
    if weight >= 0.20:
        return "high"
    elif weight >= 0.12:
        return "medium"
    else:
        return "low"


# ============================================================
# SYLLABUS GENERATOR
# ============================================================

def build_syllabus(exam_type: str = "jamb") -> Dict:
    """
    Build complete syllabus dictionary for a specific exam type.
    Merges question index with exam-specific weights.
    """
    syllabus = {}
    exam_weights = EXAM_WEIGHTS.get(exam_type.lower(), {})

    for subject_entry in QUESTION_INDEX:
        subject = subject_entry["subject"]
        topics = {}
        subject_weights = exam_weights.get(subject, {})

        for topic in subject_entry["topics"]:
            topic_name = topic["name"]
            weight = subject_weights.get(topic_name, 0.08)  # Default weight 0.08
            priority = get_priority_from_weight(weight)

            topics[topic_name] = {
                "weight": weight,
                "priority": priority,
                "has_questions": topic.get("completed", False),
                "file": topic.get("file", ""),
                "is_weak": False,  # Will be updated with user data
                "mastery_score": 0.0  # Will be updated with user data
            }

        syllabus[subject] = {
            "topics": topics,
            "total_topics": len(topics),
            "completed_topics": 0,
            "is_complete": subject_entry.get("completed", False),
            "total_questions": 0,  # Can be calculated from actual question files
            "exam_duration": 120  # Default minutes
        }

    return syllabus


def get_syllabus_for_exam(exam_type: str = "jamb") -> Dict:
    """Get syllabus for a specific exam type"""
    return build_syllabus(exam_type)


def get_subject_syllabus(exam_type: str, subject: str) -> Dict:
    """Get syllabus for a specific subject and exam"""
    syllabus = build_syllabus(exam_type)
    return syllabus.get(subject, {})


def get_topic_data(exam_type: str, subject: str, topic: str) -> Dict:
    """Get data for a specific topic"""
    subject_syllabus = get_subject_syllabus(exam_type, subject)
    return subject_syllabus.get("topics", {}).get(topic, {})


def get_topic_weight(exam_type: str, subject: str, topic: str) -> float:
    """Get the weight of a specific topic"""
    data = get_topic_data(exam_type, subject, topic)
    return data.get("weight", 0.08)


def get_topic_priority(exam_type: str, subject: str, topic: str) -> str:
    """Get the priority of a specific topic"""
    data = get_topic_data(exam_type, subject, topic)
    return data.get("priority", "medium")


def get_all_topics(exam_type: str, subject: str) -> List[str]:
    """Get all topics for a subject"""
    subject_syllabus = get_subject_syllabus(exam_type, subject)
    return list(subject_syllabus.get("topics", {}).keys())


def get_high_priority_topics(exam_type: str, subject: str) -> List[Dict]:
    """Get all high-priority topics for a subject"""
    subject_syllabus = get_subject_syllabus(exam_type, subject)
    topics = subject_syllabus.get("topics", {})
    return [
        {"name": name, **data}
        for name, data in topics.items()
        if data.get("priority") == "high" and data.get("has_questions", False)
    ]


def get_weak_topics_with_weights(exam_type: str, subject: str, user_mastery: Dict) -> List[Dict]:
    """
    Get weak topics with their weights for a specific subject.
    Calculates a combined score: weakness * weight
    """
    subject_syllabus = get_subject_syllabus(exam_type, subject)
    topics = subject_syllabus.get("topics", {})
    weak_topics = []

    for name, data in topics.items():
        if not data.get("has_questions", False):
            continue

        mastery = user_mastery.get(name, 0.5)
        weakness = 1 - mastery
        weight = data.get("weight", 0.08)

        # Combined priority score: high weakness + high weight = high priority
        priority_score = (weakness * 0.6) + (weight * 0.4)

        weak_topics.append({
            "name": name,
            "mastery": mastery,
            "weakness": weakness,
            "weight": weight,
            "priority": data.get("priority", "medium"),
            "priority_score": priority_score,
            "file": data.get("file", "")
        })

    # Sort by priority score (descending)
    return sorted(weak_topics, key=lambda x: x["priority_score"], reverse=True)


# ============================================================
# RECOMMENDED STUDY HOURS
# ============================================================

def get_recommended_hours(exam_type: str, subject: str, days_remaining: int) -> int:
    """Calculate recommended hours per week based on exam timeline and subject"""
    subject_syllabus = get_subject_syllabus(exam_type, subject)
    total_topics = subject_syllabus.get("total_topics", 10)

    # More topics = more hours needed
    if total_topics > 20:
        base_hours = 4
    elif total_topics > 10:
        base_hours = 3
    else:
        base_hours = 2

    # Adjust based on time remaining
    if days_remaining < 30:
        base_hours = min(base_hours * 2, 6)
    elif days_remaining < 60:
        base_hours = min(base_hours * 1.5, 5)

    return base_hours


# ============================================================
# INITIALIZE SYLLABUS (Cached)
# ============================================================

# Pre-build syllabus for common exam types
SYLLABUS_CACHE = {
    "jamb": build_syllabus("jamb"),
    "waec": build_syllabus("waec"),
    "neco": build_syllabus("neco")
}

def get_cached_syllabus(exam_type: str = "jamb") -> Dict:
    """Get syllabus from cache for performance"""
    return SYLLABUS_CACHE.get(exam_type.lower(), SYLLABUS_CACHE["jamb"])
