# services/syllabus.py
"""
Dynamic syllabus generator from question index.
Builds exam-specific syllabus data with topic weights and priorities.
Supports: JAMB, WAEC, NECO, SSCE, and custom exams.
"""

from typing import Dict, List, Optional
from .question_index import QUESTION_INDEX, get_subject_topics, get_all_subjects

# ============================================================
# EXAM-SPECIFIC TOPIC WEIGHTS (Expandable)
# ============================================================

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
        },
        "Biology": {
            "Cell Biology": 0.20,
            "Genetics": 0.15,
            "Ecology": 0.15,
            "Evolution": 0.10,
            "Human Body": 0.15,
            "Plants": 0.10,
            "Animals": 0.10,
            "Microorganisms": 0.05
        }
    },
    "waec": {
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
        },
        "Physics": {
            "Mechanics": 0.22,
            "Waves": 0.15,
            "Electricity": 0.15,
            "Optics": 0.10,
            "Magnetism": 0.10,
            "Heat": 0.10,
            "Modern Physics": 0.18
        },
        "Chemistry": {
            "Organic Chemistry": 0.18,
            "Inorganic Chemistry": 0.18,
            "Physical Chemistry": 0.18,
            "Atomic Structure": 0.12,
            "Chemical Bonding": 0.12,
            "Acids and Bases": 0.12,
            "Equilibrium": 0.10
        },
        "Biology": {
            "Cell Biology": 0.18,
            "Genetics": 0.15,
            "Ecology": 0.15,
            "Evolution": 0.10,
            "Human Body": 0.15,
            "Plants": 0.10,
            "Animals": 0.10,
            "Microorganisms": 0.07
        }
    },
    "neco": {
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
    },
    "ssce": {
        "Mathematics": {
            "Algebra": 0.25,
            "Geometry": 0.20,
            "Trigonometry": 0.15,
            "Statistics": 0.10,
            "Probability": 0.10,
            "Calculus": 0.05,
            "Vectors": 0.05,
            "Number System": 0.10
        },
        "English Language": {
            "Grammar": 0.25,
            "Comprehension": 0.20,
            "Vocabulary": 0.20,
            "Essay Writing": 0.15,
            "Lexis and Structure": 0.10,
            "Oral English": 0.05,
            "Summary": 0.05
        }
    },
    "pre-university": {
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
        },
        "Physics": {
            "Mechanics": 0.22,
            "Waves": 0.15,
            "Electricity": 0.15,
            "Optics": 0.10,
            "Magnetism": 0.10,
            "Heat": 0.10,
            "Modern Physics": 0.18
        },
        "Chemistry": {
            "Organic Chemistry": 0.18,
            "Inorganic Chemistry": 0.18,
            "Physical Chemistry": 0.18,
            "Atomic Structure": 0.12,
            "Chemical Bonding": 0.12,
            "Acids and Bases": 0.12,
            "Equilibrium": 0.10
        },
        "Biology": {
            "Cell Biology": 0.18,
            "Genetics": 0.15,
            "Ecology": 0.15,
            "Evolution": 0.10,
            "Human Body": 0.15,
            "Plants": 0.10,
            "Animals": 0.10,
            "Microorganisms": 0.07
        },
        "Geography": {
            "World Geography": 0.20,
            "Nigeria Geography": 0.15,
            "Physical Geography": 0.15,
            "Human Geography": 0.15,
            "Map Reading": 0.10,
            "Climate": 0.10,
            "Geological Processes": 0.10,
            "GIS": 0.05
        }
}
    
}

# ============================================================
# DEFAULT WEIGHTS (For unknown subjects/exams)
# ============================================================

DEFAULT_WEIGHTS = {
    "Mathematics": 0.20,
    "English Language": 0.20,
    "Physics": 0.15,
    "Chemistry": 0.15,
    "Biology": 0.15,
    "Economics": 0.10,
    "Government": 0.10,
    "Geography": 0.10,
    "History": 0.10,
    "Literature": 0.10,
    "Accounting": 0.10,
    "Commerce": 0.10,
    "Business Studies": 0.10,
    "Agricultural Science": 0.10,
    "Computer Science": 0.10,
    "CRS": 0.10,
    "Civics": 0.10,
    "Psychology": 0.10,
    "Sociology": 0.10,
    "Philosophy": 0.10,
    "Religious Studies": 0.10,
    "Ethics": 0.10,
    "French": 0.10,
    "Spanish": 0.10,
    "German": 0.10,
    "Yoruba": 0.10,
    "Igbo": 0.10,
    "Hausa": 0.10,
    "Swahili": 0.10,
    "Fine Arts": 0.10,
    "Music": 0.10,
    "Drama": 0.10,
    "Creative Arts": 0.10,
    "Health Science": 0.10,
    "Physical Education": 0.10,
    "Home Economics": 0.10,
    "Food and Nutrition": 0.10,
    "Information Technology": 0.10,
    "Further Mathematics": 0.10,
    "Technical Drawing": 0.10,
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_exam_weight(exam_type: str, subject: str, topic: str) -> float:
    """Get weight for a specific topic in a specific exam"""
    exam_weights = EXAM_WEIGHTS.get(exam_type.lower(), {})
    subject_weights = exam_weights.get(subject, {})
    return subject_weights.get(topic, DEFAULT_WEIGHTS.get(subject, 0.10))


def get_exam_duration(exam_type: str) -> int:
    """Get exam duration in minutes"""
    durations = {
        "jamb": 120,
        "waec": 120,
        "neco": 120,
        "ssce": 90
    }
    return durations.get(exam_type.lower(), 120)


def get_exam_questions(exam_type: str, subject: str) -> int:
    """Get number of questions per subject for an exam"""
    questions = {
        "jamb": {
            "Mathematics": 40,
            "English Language": 60,
            "Physics": 40,
            "Chemistry": 40,
            "Biology": 40,
            "Economics": 40,
            "Government": 40,
            "Geography": 40,
            "History": 40,
            "Literature": 40,
            "Accounting": 40,
            "Commerce": 40,
            "Business Studies": 40,
            "Agricultural Science": 40,
            "Computer Science": 40,
            "CRS": 40,
            "Civics": 40,
            "Psychology": 40,
            "Sociology": 40,
            "Philosophy": 40,
            "Religious Studies": 40,
            "Ethics": 40,
            "French": 40,
            "Spanish": 40,
            "German": 40,
            "Yoruba": 40,
            "Igbo": 40,
            "Hausa": 40,
            "Swahili": 40,
            "Fine Arts": 40,
            "Music": 40,
            "Drama": 40,
            "Creative Arts": 40,
            "Health Science": 40,
            "Physical Education": 40,
            "Home Economics": 40,
            "Food and Nutrition": 40,
            "Information Technology": 40,
            "Further Mathematics": 40,
            "Technical Drawing": 40
        },
        "waec": {
            "Mathematics": 50,
            "English Language": 50,
            "Physics": 50,
            "Chemistry": 50,
            "Biology": 50,
            "Economics": 50,
            "Government": 50,
            "Geography": 50,
            "History": 50,
            "Literature": 50,
            "Accounting": 50,
            "Commerce": 50,
            "Business Studies": 50,
            "Agricultural Science": 50,
            "Computer Science": 50,
            "CRS": 50,
            "Civics": 50,
            "Psychology": 50,
            "Sociology": 50,
            "Philosophy": 50,
            "Religious Studies": 50,
            "Ethics": 50,
            "French": 50,
            "Spanish": 50,
            "German": 50,
            "Yoruba": 50,
            "Igbo": 50,
            "Hausa": 50,
            "Swahili": 50,
            "Fine Arts": 50,
            "Music": 50,
            "Drama": 50,
            "Creative Arts": 50,
            "Health Science": 50,
            "Physical Education": 50,
            "Home Economics": 50,
            "Food and Nutrition": 50,
            "Information Technology": 50,
            "Further Mathematics": 50,
            "Technical Drawing": 50
        }
    }
    return questions.get(exam_type.lower(), {}).get(subject, 40)


# ============================================================
# SYLLABUS GENERATOR (Global — All Exams)
# ============================================================

def build_syllabus(exam_type: str = "jamb") -> Dict:
    """
    Build complete syllabus dictionary for any exam type.
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
            weight = subject_weights.get(topic_name, DEFAULT_WEIGHTS.get(subject, 0.10))
            priority = "high" if weight >= 0.20 else "medium" if weight >= 0.12 else "low"

            topics[topic_name] = {
                "weight": weight,
                "priority": priority,
                "has_questions": topic.get("completed", False),
                "file": topic.get("file", ""),
                "is_weak": False,
                "mastery_score": 0.0
            }

        syllabus[subject] = {
            "topics": topics,
            "total_topics": len(topics),
            "completed_topics": 0,
            "is_complete": subject_entry.get("completed", False),
            "total_questions": get_exam_questions(exam_type, subject),
            "exam_duration": get_exam_duration(exam_type)
        }

    return syllabus


def get_cached_syllabus(exam_type: str = "jamb") -> Dict:
    """Get syllabus from cache for performance"""
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
    return data.get("weight", 0.10)


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
    """Get weak topics with their weights for a specific subject"""
    subject_syllabus = get_subject_syllabus(exam_type, subject)
    topics = subject_syllabus.get("topics", {})
    weak_topics = []

    for name, data in topics.items():
        if not data.get("has_questions", False):
            continue

        mastery = user_mastery.get(name, 0.5)
        weakness = 1 - mastery
        weight = data.get("weight", 0.10)

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

    return sorted(weak_topics, key=lambda x: x["priority_score"], reverse=True)


def get_exam_list() -> List[str]:
    """Get list of all supported exams"""
    return list(EXAM_WEIGHTS.keys())


def get_recommended_hours(exam_type: str, subject: str, days_remaining: int) -> int:
    """Calculate recommended hours per week"""
    subject_syllabus = get_subject_syllabus(exam_type, subject)
    total_topics = subject_syllabus.get("total_topics", 10)
    total_questions = subject_syllabus.get("total_questions", 40)

    # More topics/questions = more hours
    base_hours = 3
    if total_topics > 20 or total_questions > 50:
        base_hours = 4
    elif total_topics > 10 or total_questions > 30:
        base_hours = 3
    else:
        base_hours = 2

    # Adjust for time remaining
    if days_remaining < 30:
        base_hours = min(base_hours * 2, 6)
    elif days_remaining < 60:
        base_hours = min(base_hours * 1.5, 5)

    return base_hours


# ============================================================
# SYLLABUS CACHE (Pre-build for all exam types)
# ============================================================

SYLLABUS_CACHE = {
    "jamb": build_syllabus("jamb"),
    "waec": build_syllabus("waec"),
    "neco": build_syllabus("neco"),
    "ssce": build_syllabus("ssce")
}


def get_cached_syllabus(exam_type: str = "jamb") -> Dict:
    """Get syllabus from cache for performance"""
    return SYLLABUS_CACHE.get(exam_type.lower(), SYLLABUS_CACHE["jamb"])
