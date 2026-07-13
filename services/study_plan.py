# services/study_plan.py
"""
Premium Study Plan Generator v2
Uses dynamic syllabus + user performance + AI insights
Built for 50+ subjects with 300+ topics
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from .syllabus import (
    get_cached_syllabus,
    get_subject_syllabus,
    get_topic_data,
    get_all_topics,
    get_weak_topics_with_weights,
    get_recommended_hours,
    get_topic_weight
)
from .question_index import get_subject_topics, get_all_subjects


class StudyPlanGenerator:
    """Generate personalized premium study plans"""

    def __init__(
        self,
        user_data: Dict,
        weak_topics: List[str],
        exam_type: str = "jamb",
        mastery_data: Optional[Dict] = None
    ):
        self.user = user_data
        self.weak_topics = weak_topics or []
        self.exam_type = exam_type or "jamb"
        self.mastery = mastery_data or {}
        self.subjects = user_data.get("subjects", [])
        self.hours_per_week = user_data.get("hours_per_week", 10)
        self.target_score = user_data.get("target_score", "300+")
        self.study_style = user_data.get("study_style", "balanced")
        self.days_remaining = max(1, user_data.get("days_until_exam", 30))
        self.goal = user_data.get("goal", "Pass exam")
        self.syllabus = get_cached_syllabus(self.exam_type)
        self.study_styles = {
            "active": {
                "name": "Active Learning",
                "tips": [
                    "Do active recall after each topic",
                    "Teach what you've learned to someone else",
                    "Use flashcards daily",
                    "Take short quizzes after each session",
                    "Practice with past questions"
                ],
                "techniques": ["Spaced Repetition", "Active Recall", "Practice Testing"]
            },
            "visual": {
                "name": "Visual Learning",
                "tips": [
                    "Create mind maps for each topic",
                    "Use color-coded notes",
                    "Draw diagrams and flowcharts",
                    "Watch video explanations",
                    "Use visual mnemonics"
                ],
                "techniques": ["Mind Mapping", "Color Coding", "Visualization"]
            },
            "reading": {
                "name": "Reading/Writing",
                "tips": [
                    "Take detailed notes while reading",
                    "Summarize topics in your own words",
                    "Create outlines and bullet points",
                    "Write practice essays",
                    "Read multiple sources"
                ],
                "techniques": ["Note-Taking", "Summarization", "Outlining"]
            },
            "balanced": {
                "name": "Balanced Approach",
                "tips": [
                    "Read → Practice → Review → Repeat",
                    "Take 5-minute breaks every 25 minutes",
                    "Review yesterday's work before starting new",
                    "Stay consistent — same time daily",
                    "Mix different study methods"
                ],
                "techniques": ["Mixed Methods", "Consistent Routine", "Regular Review"]
            }
        }

    def generate_plan(self) -> Dict:
        """Generate complete study plan"""
        return {
            "summary": self._generate_summary(),
            "weekly_schedule": self._generate_weekly_schedule(),
            "daily_breakdown": self._generate_daily_breakdown(),
            "topic_priorities": self._generate_topic_priorities(),
            "subject_breakdown": self._generate_subject_breakdown(),
            "recommendations": self._generate_recommendations(),
            "milestones": self._generate_milestones(),
            "study_tips": self._generate_study_tips(),
            "techniques": self._generate_techniques(),
            "progress_tracker": self._generate_progress_tracker(),
            "exam_strategy": self._generate_exam_strategy()
        }

    def _generate_summary(self) -> Dict:
        """Generate plan summary"""
        total_hours = self.hours_per_week * (self.days_remaining // 7)
        weak_count = len(self.weak_topics)
        total_topics = sum(
            len(get_subject_topics(s)) for s in self.subjects
        )

        return {
            "days_remaining": self.days_remaining,
            "weeks_remaining": max(1, self.days_remaining // 7),
            "total_hours": total_hours,
            "weekly_hours": self.hours_per_week,
            "subjects": self.subjects,
            "weak_areas": self.weak_topics[:5],
            "weak_count": weak_count,
            "total_topics": total_topics,
            "target_score": self.target_score,
            "exam_type": self.exam_type.upper(),
            "estimated_effort": self._calculate_effort_level(),
            "completion_percentage": self._calculate_completion_percentage()
        }

    def _generate_weekly_schedule(self) -> List[Dict]:
        """Generate 7-day weekly schedule with specific topics"""
        schedule = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Pre-calculate subject distribution
        subjects_by_day = self._distribute_subjects()

        for i, day in enumerate(days):
            day_topics = []
            day_subjects = subjects_by_day[i % len(subjects_by_day)]

            for subject in day_subjects:
                # Get recommended topics for this subject
                topics = self._get_topics_for_subject(subject)
                weak_topics = [t for t in topics if t in self.weak_topics]

                # Prioritize weak topics
                if weak_topics:
                    selected = weak_topics[:2]  # Max 2 weak topics per day
                else:
                    selected = topics[:2] if topics else ["Revision"]

                for topic in selected:
                    hours = self._calculate_hours_for_topic(subject, topic)
                    is_weak = topic in self.weak_topics
                    topic_data = get_topic_data(self.exam_type, subject, topic)

                    day_topics.append({
                        "subject": subject,
                        "topic": topic,
                        "hours": hours,
                        "priority": "High" if is_weak else "Normal",
                        "weight": topic_data.get("weight", 0.08),
                        "is_weak": is_weak,
                        "file": topic_data.get("file", ""),
                        "completed": False,
                        "resources": self._get_topic_resources(subject, topic)
                    })

            schedule.append({
                "day": day,
                "topics": day_topics,
                "total_hours": round(sum(t["hours"] for t in day_topics), 1),
                "focus": self._get_day_focus(day_topics)
            })

        return schedule

    def _generate_daily_breakdown(self) -> List[Dict]:
        """Generate day-by-day breakdown for the next 2 weeks"""
        breakdown = []
        max_days = min(14, self.days_remaining)

        for i in range(max_days):
            date = datetime.utcnow() + timedelta(days=i)
            day_num = i + 1
            focus = self._get_daily_focus(i)

            breakdown.append({
                "day": day_num,
                "date": date.strftime("%Y-%m-%d"),
                "focus": focus,
                "hours": round(self.hours_per_week / 7, 1),
                "completed": False,
                "notes": ""
            })

        return breakdown

    def _generate_topic_priorities(self) -> List[Dict]:
        """Generate prioritized topic list combining weight + weakness"""
        priorities = []

        for subject in self.subjects:
            topics = get_subject_topics(subject)

            for topic in topics:
                weight = get_topic_weight(self.exam_type, subject, topic)
                is_weak = topic in self.weak_topics
                mastery = self.mastery.get(topic, 0.5)

                # Combined priority score
                weakness_score = 1 - mastery
                priority_score = (weakness_score * 0.6) + (weight * 0.4)

                priorities.append({
                    "subject": subject,
                    "topic": topic,
                    "weight": round(weight, 2),
                    "mastery": round(mastery * 100, 1),
                    "is_weak": is_weak,
                    "priority_score": round(priority_score, 3),
                    "priority": self._get_priority_label(priority_score),
                    "recommended_hours": round(self._calculate_hours_for_topic(subject, topic), 1),
                    "file": get_topic_data(self.exam_type, subject, topic).get("file", "")
                })

        return sorted(priorities, key=lambda x: x["priority_score"], reverse=True)

    def _generate_subject_breakdown(self) -> Dict:
        """Generate subject-level breakdown with hours and priorities"""
        breakdown = {}
        total_hours = self.hours_per_week

        for subject in self.subjects:
            topics = get_subject_topics(subject)
            weak_topics = [t for t in topics if t in self.weak_topics]
            subject_weight = sum(
                get_topic_weight(self.exam_type, subject, t) for t in topics
            )

            hours = (subject_weight / max(1, sum(
                sum(get_topic_weight(self.exam_type, s, t) for t in get_subject_topics(s))
                for s in self.subjects
            ))) * total_hours

            breakdown[subject] = {
                "topics": topics,
                "weak_topics": weak_topics,
                "total_topics": len(topics),
                "weak_count": len(weak_topics),
                "hours_per_week": round(hours, 1),
                "weight": round(subject_weight, 2),
                "priority": "High" if len(weak_topics) > len(topics) // 2 else "Normal",
                "recommended_focus": ", ".join(weak_topics[:3]) if weak_topics else "All topics"
            }

        return breakdown

    def _generate_recommendations(self) -> List[str]:
        """Generate personalized study recommendations"""
        recommendations = []

        # Weak topic recommendations
        if self.weak_topics:
            weak_list = ", ".join(self.weak_topics[:3])
            recommendations.append(f"🎯 Focus on these weak topics: {weak_list}")
        else:
            recommendations.append("📚 Keep up the great work! All topics are balanced")

        # Time-based recommendations
        if self.days_remaining < 30:
            recommendations.append("⚡ Intensive practice: Do 2+ hours daily minimum")
            recommendations.append("📝 Daily past questions: At least 20 questions per day")
        elif self.days_remaining < 60:
            recommendations.append("📊 Consistent practice: 1.5 hours daily")
            recommendations.append("📝 Practice past questions: 15 questions per day")
        else:
            recommendations.append("📖 Build foundation: 1 hour daily minimum")

        # Subject-specific
        if len(self.subjects) > 4:
            recommendations.append("🎯 Prioritize subjects with most weak topics first")
            recommendations.append("📊 Rotate subjects: Don't study same subject 2 days in a row")

        # Style-specific
        style = self.study_style or "balanced"
        style_tips = self.study_styles.get(style, self.study_styles["balanced"])

        # Add style recommendations
        for tip in style_tips["tips"][:2]:
            recommendations.append(f"💡 {tip}")

        return recommendations

    def _generate_milestones(self) -> List[Dict]:
        """Generate milestone checkpoints"""
        milestones = []
        intervals = [0.25, 0.50, 0.75, 1.0]
        icons = ["🌱", "📈", "🎯", "🏆"]

        for i, pct in enumerate(intervals):
            day = int(self.days_remaining * pct)
            if day <= 0:
                continue

            milestones.append({
                "day": day,
                "percentage": int(pct * 100),
                "icon": icons[i % len(icons)],
                "target": f"Complete {int(pct * 100)}% of topics",
                "reward": "Take a break day" if i % 2 == 0 else "Practice test",
                "completed": False
            })

        return milestones

    def _generate_study_tips(self) -> List[str]:
        """Generate study tips based on style and time remaining"""
        style = self.study_style or "balanced"
        style_data = self.study_styles.get(style, self.study_styles["balanced"])

        # Base tips
        tips = style_data["tips"].copy()

        # Time-based tips
        if self.days_remaining < 30:
            tips.append("⏰ Focus on past questions more than reading")
            tips.append("🔄 Review weak topics every other day")
        elif self.days_remaining < 60:
            tips.append("📖 Read → Practice → Review cycle")
            tips.append("📝 Start keeping a mistake log")

        # Subject count tips
        if len(self.subjects) > 4:
            tips.append("🎯 Spend more time on weak subjects first")
            tips.append("📊 Don't spend equal time on all subjects")

        return tips[:10]

    def _generate_techniques(self) -> List[str]:
        """Generate study techniques based on style"""
        style = self.study_style or "balanced"
        style_data = self.study_styles.get(style, self.study_styles["balanced"])

        techniques = style_data["techniques"].copy()

        # Add universal techniques
        techniques.extend([
            "Pomodoro Technique (25 min study, 5 min break)",
            "Active Recall",
            "Spaced Repetition"
        ])

        return techniques[:8]

    def _generate_progress_tracker(self) -> Dict:
        """Generate progress tracking template"""
        return {
            "total_topics": sum(
                len(get_subject_topics(s)) for s in self.subjects
            ),
            "completed_topics": 0,
            "mastered_topics": 0,
            "current_streak": 0,
            "last_study_date": None,
            "daily_goal": 0.3,  # 30% of weekly goal per day
            "weekly_goal": self.hours_per_week,
            "streak_goal": 7,
            "badges": {
                "first_study": False,
                "streak_3": False,
                "streak_7": False,
                "mastered_topic": False
            }
        }

    def _generate_exam_strategy(self) -> Dict:
        """Generate exam-specific strategy"""
        return {
            "strategy": self._get_exam_strategy(),
            "time_management": self._get_time_management(),
            "question_priorities": self._get_question_priorities(),
            "common_pitfalls": self._get_common_pitfalls(),
            "tips_for_exam_day": self._get_exam_day_tips()
        }

    def _get_topic_resources(self, subject: str, topic: str) -> List[str]:
        """Get recommended resources for a topic"""
        resources = []
        file_path = get_topic_data(self.exam_type, subject, topic).get("file", "")

        if file_path:
            resources.append(f"📄 Practice questions: {file_path}")

        # Generic resources
        resources.append("📚 Study notes")
        resources.append("📝 Past questions")

        return resources

    def _distribute_subjects(self) -> List[List[str]]:
        """Distribute subjects across days of the week"""
        subjects = self.subjects.copy()
        if not subjects:
            return [[]]

        # Shuffle subjects to distribute evenly
        import random
        random.shuffle(subjects)

        # Try to put weak subjects on separate days
        weak_subjects = []
        strong_subjects = []

        for s in subjects:
            topics = get_subject_topics(s)
            weak_count = sum(1 for t in topics if t in self.weak_topics)
            if weak_count > 0:
                weak_subjects.append(s)
            else:
                strong_subjects.append(s)

        # Arrange: weak subjects spread across early days
        result = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        # Distribute weak subjects first
        for i, subject in enumerate(weak_subjects):
            day_idx = i % 5  # Weekdays only
            if day_idx >= len(result):
                result.append([])
            result[day_idx].append(subject)

        # Distribute strong subjects
        for i, subject in enumerate(strong_subjects):
            day_idx = (i + 3) % 7  # Spread across all days
            if day_idx >= len(result):
                result.append([])
            result[day_idx].append(subject)

        return result

    def _get_topics_for_subject(self, subject: str) -> List[str]:
        """Get topics for a subject from syllabus"""
        return get_subject_topics(subject)

    def _calculate_hours_for_topic(self, subject: str, topic: str) -> float:
        """Calculate hours needed for a specific topic"""
        weight = get_topic_weight(self.exam_type, subject, topic)
        is_weak = topic in self.weak_topics

        # Base hours per day
        base_hours = self.hours_per_week / 7 / max(1, len(self.subjects))

        # Adjust for difficulty
        if is_weak:
            return round(base_hours * 1.8, 1)
        elif weight > 0.2:
            return round(base_hours * 1.4, 1)
        elif weight > 0.1:
            return round(base_hours * 1.1, 1)
        else:
            return round(base_hours * 0.7, 1)

    def _get_day_focus(self, topics: List[Dict]) -> str:
        """Get focus description for a day"""
        if not topics:
            return "Rest day or review"

        weak_topics = [t for t in topics if t.get("is_weak")]
        if weak_topics:
            subjects = ", ".join(set(t["subject"] for t in weak_topics))
            return f"Weak areas: {subjects}"
        else:
            subjects = ", ".join(set(t["subject"] for t in topics))
            return f"Topics: {subjects}"

    def _get_daily_focus(self, day_num: int) -> str:
        """Get daily focus based on day number"""
        if not self.subjects:
            return "No subjects selected"

        subject_idx = day_num % len(self.subjects)
        subject = self.subjects[subject_idx]

        topics = get_subject_topics(subject)
        if not topics:
            return f"Review: {subject}"

        topic_idx = day_num % len(topics)
        return f"{subject}: {topics[topic_idx]}"

    def _get_priority_label(self, score: float) -> str:
        """Convert priority score to label"""
        if score >= 0.7:
            return "High"
        elif score >= 0.4:
            return "Medium"
        else:
            return "Low"

    def _calculate_effort_level(self) -> str:
        """Calculate effort level based on hours and days"""
        if self.hours_per_week > 15 and self.days_remaining < 30:
            return "Critical"
        elif self.hours_per_week > 12 or self.days_remaining < 45:
            return "High"
        elif self.hours_per_week > 8:
            return "Medium"
        else:
            return "Low"

    def _calculate_completion_percentage(self) -> int:
        """Calculate estimated completion percentage"""
        if not self.subjects:
            return 0

        total_topics = sum(len(get_subject_topics(s)) for s in self.subjects)
        if total_topics == 0:
            return 0

        # Estimate based on weak topics remaining
        weak_count = len(self.weak_topics)
        completed = max(0, total_topics - weak_count)
        return min(100, int((completed / total_topics) * 100))

    def _get_exam_strategy(self) -> str:
        """Get exam-specific strategy"""
        strategies = {
            "jamb": "Focus on speed and accuracy. JAMB has 180 questions in 3 hours. Practice timing yourself.",
            "waec": "Focus on depth and explanation. WAEC requires detailed answers. Practice essay writing.",
            "neco": "Focus on both speed and depth. NECO combines JAMB and WAEC styles.",
            "ssce": "Focus on fundamentals. SSCE tests basic understanding of concepts."
        }
        return strategies.get(self.exam_type.lower(), "Focus on consistent practice and review.")

    def _get_time_management(self) -> str:
        """Get time management tips"""
        if self.days_remaining < 30:
            return "Time is critical! Study 2+ hours daily. Focus on weak topics first. Practice past questions daily."
        elif self.days_remaining < 60:
            return "Good time available. Study 1.5 hours daily. Mix reading and practice."
        else:
            return "Plenty of time. Study 1 hour daily. Build strong foundation."

    def _get_question_priorities(self) -> List[str]:
        """Get question priority tips"""
        return [
            "Start with questions you know",
            "Skip difficult questions, return later",
            "Check your answers carefully",
            "Don't spend too long on one question"
        ]

    def _get_common_pitfalls(self) -> List[str]:
        """Get common pitfalls to avoid"""
        return [
            "Rushing through questions",
            "Not reading questions carefully",
            "Overlooking negative signs",
            "Forgetting to check units",
            "Not managing time properly"
        ]

    def _get_exam_day_tips(self) -> List[str]:
        """Get exam day tips"""
        return [
            "Get 8 hours of sleep",
            "Eat a good breakfast",
            "Arrive early to the exam center",
            "Read all instructions carefully",
            "Stay calm and focused",
            "Review your answers if time permits"
        ]


# ============================================================
# PRESET STUDY PLANS
# ============================================================

def get_preset_plans() -> Dict:
    """Get preset study plans for different scenarios"""
    return {
        "crash_course": {
            "name": "Crash Course (30 Days)",
            "hours_per_week": 20,
            "description": "Intensive 30-day plan for immediate exam preparation",
            "priority": "all_topics"
        },
        "balanced": {
            "name": "Balanced (60 Days)",
            "hours_per_week": 12,
            "description": "Steady 60-day plan with balanced approach",
            "priority": "weak_topics_first"
        },
        "long_term": {
            "name": "Long Term (90+ Days)",
            "hours_per_week": 8,
            "description": "Comprehensive 90+ day plan for solid foundation",
            "priority": "foundation_first"
        }
    }
