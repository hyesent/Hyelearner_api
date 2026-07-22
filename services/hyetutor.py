# ============================================================
# services/hyetutor.py — HyeTutor AI Service
# ============================================================

import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import random

from services.ai import ai_service


class HyetutorService:
    """HyeTutor AI Service — Daily Digest + Insights"""
    
    def __init__(self):
        self.ai = ai_service
    
    def build_ai_prompt(self, data: Dict[str, Any], exam_date: str = None) -> str:
        """Build the AI prompt from bundled data"""
        
        # Extract key data
        profile = data.get("profile", {})
        study_plan = data.get("study_plan", {})
        mastery = data.get("mastery", {})
        sessions = data.get("sessions", [])
        mistakes = data.get("mistakes", [])
        weak_topics = data.get("weak_topics", [])
        gamification = data.get("gamification", {})
        preferences = data.get("preferences", {})
        consistency = data.get("consistency", {})
        
        # Get weak topics from mastery (topics with accuracy < 60%)
        weak_from_mastery = [
            {"topic": topic, "accuracy": data.get("accuracy", 0)}
            for topic, data in mastery.items()
            if data.get("accuracy", 0) < 60
        ]
        
        # Combine weak topics
        all_weak_topics = weak_topics + weak_from_mastery
        all_weak_topics = sorted(all_weak_topics, key=lambda x: x.get("accuracy", 100))[:5]
        
        # Recent sessions (last 7 days)
        recent_sessions = sessions[:10] if sessions else []
        
        prompt = f"""
You are HyeTutor, an AI study coach for the Hyelearner platform.

STUDENT PROFILE:
- Name: {profile.get('name', 'Student')}
- Exam: {profile.get('exam', 'JAMB').upper()}
- Subjects: {', '.join(profile.get('subjects', []))}
- Target Score: {preferences.get('target_score', 'Not set')}
- Study Style: {preferences.get('study_style', 'balanced')}

CURRENT STATUS:
- Level: {gamification.get('level', 1)}
- XP: {gamification.get('xp', 0)}
- Streak: {gamification.get('streak', 0)} days
- Total Sessions: {gamification.get('total_sessions', 0)}
- Badges: {gamification.get('badges', [])}

EXAM INFO:
- Exam Date: {exam_date or 'Not set'}
- Days Remaining: {study_plan.get('exam_info', {}).get('days_remaining', 'Unknown')}
- Topics Remaining: {study_plan.get('summary', {}).get('topics_remaining', 'Unknown')}

MASTERY DATA (Accuracy % per topic):
{json.dumps(mastery, indent=2)[:1000]}

WEAK TOPICS (Priority order):
{json.dumps(all_weak_topics, indent=2)[:500]}

RECENT SESSIONS (Last 7 days):
{json.dumps(recent_sessions, indent=2)[:800]}

RECENT MISTAKES (Last 10):
{json.dumps(mistakes[:10], indent=2)[:500]}

CONSISTENCY:
- Study Days: {consistency.get('study_days', 0)}/20
- Missed Days: {consistency.get('missed_days', 0)}
- Avg Sessions/Day: {consistency.get('avg_sessions_per_day', 0)}

Based on this data, provide a personalized daily digest. Return as JSON only with this structure:

{{
  "missions": [
    {{
      "id": "mission_001",
      "text": "string",
      "reason": "why this mission",
      "priority": "critical|high|medium|low",
      "xp_reward": 30,
      "estimated_time": 25,
      "completed": false,
      "order": 1
    }}
  ],
  "total_xp_reward": 120,
  "missions_progress": 0,
  "subjects": [
    {{
      "name": "Mathematics",
      "mastery": 78,
      "confidence": 92,
      "status": "in_progress|danger|completed|not_started",
      "trend": "up|down|stable",
      "trend_amount": -5,
      "priority": "critical|high|medium|low"
    }}
  ],
  "next_session": {{
    "time": "7:00 PM",
    "subject": "Mathematics",
    "topic": "Quadratic Equations",
    "duration": 45,
    "difficulty": "Medium",
    "priority": "high",
    "reason": "Scheduled task from your study plan"
  }},
  "time_budget": {{
    "total": 2.75,
    "completed": 1.33,
    "remaining": 1.42,
    "unit": "hours"
  }},
  "weekly_goal": {{
    "total": 24,
    "completed": 18,
    "remaining": 6,
    "percentage": 75,
    "unit": "hours"
  }},
  "performance": {{
    "exam_readiness": 89,
    "confidence": 91,
    "consistency": 87,
    "focus": 84,
    "burnout_risk": "Low",
    "burnout_signs": []
  }},
  "forecast": {{
    "days_remaining": 52,
    "topics_remaining": 45,
    "topics_per_day_needed": 2.46,
    "current_pace": 2.1,
    "pace_status": "ahead|on_track|behind",
    "estimated_completion": "2026-09-10",
    "days_behind": 10,
    "completion_probability": 72,
    "needs_adjustment": true,
    "recommendation": "Increase daily study by 2 hours to catch up.",
    "daily_target": 4.5
  }},
  "insights": [
    {{
      "id": "insight_001",
      "type": "critical|warning|positive|recommendation",
      "message": "string",
      "action": "action_name",
      "priority": "high|medium|low",
      "suggestion": "suggestion text"
    }}
  ],
  "habits": [
    {{
      "icon": "clock|trending|lightbulb|target|brain",
      "text": "You perform best between 7 PM and 9 PM",
      "detail": "Focus sessions during this time are 34% more effective"
    }}
  ],
  "momentum": {{
    "hours": 18.4,
    "average_per_day": 2.6,
    "best_day": "Tuesday",
    "longest_session": "2h 13m",
    "missed_days": 1,
    "streak": 7,
    "weekly_data": []
  }},
  "revision_queue": [
    {{
      "topic": "Vectors",
      "subject": "Mathematics",
      "days_ago": 3,
      "priority": "medium",
      "confidence": 65
    }}
  ],
  "quick_stats": {{
    "topics_remaining": 34,
    "lessons_remaining": 12,
    "questions_remaining": 486,
    "days_ahead": 11
  }},
  "motivation": "string",
  "plan_adjustments": {{
    "add": [],
    "remove": [],
    "reschedule": [],
    "new_load": 2.5,
    "previous_load": 3.0,
    "adjusted": true
  }},
  "emergency": {{
    "active": false,
    "reason": null,
    "days_to_exam": 52
  }},
  "rewards": [
    {{
      "id": "week_4_complete",
      "label": "Week 4 Complete",
      "xp": 500,
      "badge": "Week Warrior",
      "unlocked": true,
      "claimed": false
    }}
  ]
}}

Be specific, actionable, and encouraging. Use the exact JSON structure above.
"""
        
        return prompt
    
    def parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response into structured data"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return self._ensure_required_fields(data)
        except Exception as e:
            print(f"❌ Failed to parse AI response: {e}")
        
        # Return fallback if parsing fails
        return self._get_fallback_response()
    
    def _ensure_required_fields(self, data: Dict) -> Dict:
        """Ensure all required fields exist in the response"""
        required = {
            "missions": [],
            "total_xp_reward": 0,
            "missions_progress": 0,
            "subjects": [],
            "next_session": {},
            "time_budget": {"total": 2, "completed": 0, "remaining": 2, "unit": "hours"},
            "weekly_goal": {"total": 20, "completed": 0, "remaining": 20, "percentage": 0, "unit": "hours"},
            "performance": {"exam_readiness": 50, "confidence": 50, "consistency": 50, "focus": 50, "burnout_risk": "Low", "burnout_signs": []},
            "forecast": {},
            "insights": [],
            "habits": [],
            "momentum": {},
            "revision_queue": [],
            "quick_stats": {},
            "motivation": "Keep pushing forward! 💪",
            "plan_adjustments": {},
            "emergency": {"active": False, "reason": None, "days_to_exam": 0},
            "rewards": []
        }
        
        for key, default in required.items():
            if key not in data or data[key] is None:
                data[key] = default
        
        return data
    
    def _get_fallback_response(self) -> Dict[str, Any]:
        """Fallback response when AI fails"""
        return {
            "missions": [
                {
                    "id": "mission_001",
                    "text": "Review your weakest topic from yesterday",
                    "reason": "AI temporarily unavailable — but you can still study!",
                    "priority": "high",
                    "xp_reward": 25,
                    "estimated_time": 30,
                    "completed": False,
                    "order": 1
                },
                {
                    "id": "mission_002",
                    "text": "Complete 20 practice questions on any subject",
                    "reason": "Daily practice is essential for retention",
                    "priority": "medium",
                    "xp_reward": 30,
                    "estimated_time": 40,
                    "completed": False,
                    "order": 2
                }
            ],
            "total_xp_reward": 55,
            "missions_progress": 0,
            "subjects": [],
            "next_session": {
                "time": "7:00 PM",
                "subject": "Your weakest subject",
                "topic": "Review",
                "duration": 45,
                "difficulty": "Medium",
                "priority": "high",
                "reason": "Focus on areas that need improvement"
            },
            "time_budget": {"total": 2, "completed": 0, "remaining": 2, "unit": "hours"},
            "weekly_goal": {"total": 20, "completed": 0, "remaining": 20, "percentage": 0, "unit": "hours"},
            "performance": {
                "exam_readiness": 50,
                "confidence": 50,
                "consistency": 50,
                "focus": 50,
                "burnout_risk": "Low",
                "burnout_signs": []
            },
            "forecast": {
                "days_remaining": 0,
                "topics_remaining": 0,
                "topics_per_day_needed": 0,
                "current_pace": 0,
                "pace_status": "on_track",
                "estimated_completion": "",
                "days_behind": 0,
                "completion_probability": 50,
                "needs_adjustment": False,
                "recommendation": "Keep studying consistently every day.",
                "daily_target": 2
            },
            "insights": [
                {
                    "id": "insight_001",
                    "type": "positive",
                    "message": "You're building a strong study habit. Keep going!",
                    "action": None,
                    "priority": "medium",
                    "suggestion": None
                }
            ],
            "habits": [],
            "momentum": {
                "hours": 0,
                "average_per_day": 0,
                "best_day": "None",
                "longest_session": "0m",
                "missed_days": 0,
                "streak": 0,
                "weekly_data": []
            },
            "revision_queue": [],
            "quick_stats": {
                "topics_remaining": 0,
                "lessons_remaining": 0,
                "questions_remaining": 0,
                "days_ahead": 0
            },
            "motivation": "Every session brings you closer to your goal. Don't stop now! 💪",
            "plan_adjustments": {
                "add": [],
                "remove": [],
                "reschedule": [],
                "new_load": 2,
                "previous_load": 2,
                "adjusted": False
            },
            "emergency": {
                "active": False,
                "reason": None,
                "days_to_exam": 0
            },
            "rewards": []
        }

    # ============================================================
    # GENERATE DAILY DIGEST — AI CALL
    # ============================================================
    
    async def generate_daily_digest(self, data: Dict[str, Any], exam_date: str = None) -> Dict[str, Any]:
        """Generate daily digest using Gemini (primary) and Groq (fallback)."""
        prompt = self.build_ai_prompt(data, exam_date)
        
        response_text = None
        
        # Try Gemini first
        if self.ai.gemini:
            try:
                response = self.ai.gemini.generate_content(prompt)
                response_text = response.text
                print("✅ Gemini generated HyeTutor digest")
            except Exception as e:
                print(f"❌ Gemini error: {e}")
        
        # Fallback to Groq if Gemini fails
        if not response_text and self.ai.groq:
            try:
                response = self.ai.groq.chat.completions.create(
                    model=self.ai.groq_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2500,
                    temperature=0.7
                )
                response_text = response.choices[0].message.content
                print("✅ Groq generated HyeTutor digest (fallback)")
            except Exception as e:
                print(f"❌ Groq error: {e}")
        
        if not response_text:
            print("❌ Both AI providers failed, using fallback")
            return self._get_fallback_response()
        
        return self.parse_ai_response(response_text)


# ============================================================
# INSTANCE
# ============================================================

hyetutor_service = HyetutorService()
