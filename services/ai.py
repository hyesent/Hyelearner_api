import google.generativeai as genai
import json
from typing import List, Dict, Any, Optional
from config import settings

class AIService:
    def __init__(self):
        self.gemini = None
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("✅ Gemini AI initialized successfully")
            except Exception as e:
                print(f"❌ Gemini initialization failed: {e}")
        else:
            print("⚠️ GEMINI_API_KEY not found in environment")

    # ============================================================
    # 1. AI EXPLANATION — Receives question + user_answer
    # ============================================================
    async def get_explanation(self, question: Dict, user_answer: str) -> Dict:
        """Generate detailed explanation using Gemini"""
        
        # Log what we received
        print(f"📥 Received question: {question.get('question_text', 'N/A')[:50]}...")
        print(f"📥 User answer: {user_answer}")
        
        # Build the prompt
        prompt = f"""
        You are an expert tutor for SSCE/JAMB/WAEC/NECO exam preparation.

        QUESTION: {question.get('question_text', 'No question text provided')}
        OPTIONS: {json.dumps(question.get('options', []))}
        CORRECT ANSWER: {question.get('correct_answer', 'Unknown')}
        USER'S ANSWER: {user_answer}

        Provide a DETAILED explanation. Structure your response exactly like this:

        EXPLANATION:
        [Step-by-step explanation of why the correct answer is right]

        KEY CONCEPT:
        [The main concept being tested]

        WHY USER WAS WRONG:
        [Why the user's answer is incorrect]

        TIPS:
        - Tip 1
        - Tip 2
        - Tip 3

        SHORTCUT:
        [A quick way to remember this concept]
        """

        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                return self._parse_explanation(response.text)
            except Exception as e:
                print(f"❌ Gemini error: {e}")
                return self._fallback_explanation(question, user_answer)

        return self._fallback_explanation(question, user_answer)

    def _parse_explanation(self, text: str) -> Dict:
        """Parse Gemini explanation response"""
        result = {
            "explanation": "",
            "key_concept": "",
            "why_wrong": "",
            "tips": [],
            "shortcut": ""
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            
            if line.startswith('EXPLANATION:'):
                current_section = "explanation"
                continue
            elif line.startswith('KEY CONCEPT:'):
                current_section = "key_concept"
                continue
            elif line.startswith('WHY USER WAS WRONG:'):
                current_section = "why_wrong"
                continue
            elif line.startswith('TIPS:'):
                current_section = "tips"
                continue
            elif line.startswith('SHORTCUT:'):
                current_section = "shortcut"
                continue
            
            if current_section == "tips" and line.startswith('-'):
                result["tips"].append(line[1:].strip())
            elif current_section and line and not line.startswith('-'):
                result[current_section] += line + "\n"

        # Clean up
        for key in result:
            if isinstance(result[key], str):
                result[key] = result[key].strip()

        return result

    def _fallback_explanation(self, question: Dict, user_answer: str) -> Dict:
        return {
            "explanation": f"The correct answer is {question.get('correct_answer', 'N/A')}. Review the concept.",
            "key_concept": "Review the fundamental concept",
            "why_wrong": f"Your answer '{user_answer}' was incorrect. Try to understand the reasoning.",
            "tips": ["Read the question carefully", "Show your working", "Double-check your answer"],
            "shortcut": "Practice similar questions"
        }

    # ============================================================
    # 2. AI WEAKNESS ANALYSIS — Receives mistakes + mastery
    # ============================================================
    async def get_weakness_analysis(self, mistakes: List[Dict], mastery: Dict) -> List[Dict]:
        """Analyze weak areas using Gemini"""
        if not mistakes:
            return []

        # Log what we received
        print(f"📥 Received {len(mistakes)} mistakes")
        print(f"📥 Mastery data: {json.dumps(mastery, indent=2)[:200]}...")

        prompt = f"""
        Analyze this student's exam performance data.

        MISTAKES (wrong answers):
        {json.dumps(mistakes, indent=2)}

        MASTERY DATA (topic performance):
        {json.dumps(mastery, indent=2)}

        Identify the TOP 5 weakest topics.

        For each topic, provide:
        - topic: Name
        - accuracy: Number (0-100)
        - priority: "High", "Medium", or "Low"
        - recommendations: Actionable advice

        Return as JSON array only:
        [
            {{"topic": "Algebra", "accuracy": 38, "priority": "High", "recommendations": "Practice linear equations"}}
        ]
        """

        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                return self._parse_weakness(response.text)
            except Exception as e:
                print(f"❌ Gemini weakness error: {e}")
                return self._fallback_weakness(mistakes)

        return self._fallback_weakness(mistakes)

    def _parse_weakness(self, text: str) -> List[Dict]:
        """Parse Gemini weakness response"""
        try:
            # Try to parse as JSON
            import re
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        # Fallback: manual parsing
        weak_topics = []
        lines = text.split('\n')
        current = {}

        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                if current.get('topic'):
                    weak_topics.append(current)
                current = {'topic': line.strip(' -•*').strip()}
            elif 'accuracy' in line.lower() and current:
                try:
                    acc = ''.join(filter(str.isdigit, line))
                    if acc:
                        current['accuracy'] = int(acc)
                except:
                    current['accuracy'] = 50
            elif 'priority' in line.lower() and current:
                if 'high' in line.lower():
                    current['priority'] = 'High'
                elif 'medium' in line.lower():
                    current['priority'] = 'Medium'
                else:
                    current['priority'] = 'Low'
            elif 'recommend' in line.lower() and current:
                current['recommendations'] = line.replace('Recommendation:', '').strip()

        if current.get('topic'):
            weak_topics.append(current)

        return weak_topics[:5] if weak_topics else self._fallback_weakness([])

    def _fallback_weakness(self, mistakes: List[Dict]) -> List[Dict]:
        topics = {}
        for m in mistakes[:10]:
            topic = m.get('topic', 'General')
            if topic not in topics:
                topics[topic] = {
                    'topic': topic,
                    'accuracy': 50,
                    'priority': 'Medium',
                    'recommendations': 'Practice more questions in this area'
                }
        return list(topics.values())[:5]

    # ============================================================
    # 3. AI STUDY PLAN — Receives goal, subjects, hours, weak_topics, target_score, study_style
    # ============================================================
    async def generate_study_plan(
        self,
        goal: str,
        subjects: List[str],
        hours_per_week: int,
        weak_topics: List[str] = None,
        days_until_exam: int = None,
        target_score: str = None,
        study_style: str = None
    ) -> Dict:
        """Generate personalized study plan using Gemini"""
        
        # Log what we received
        print(f"📥 Goal: {goal}")
        print(f"📥 Subjects: {subjects}")
        print(f"📥 Hours/week: {hours_per_week}")
        print(f"📥 Weak topics: {weak_topics}")
        print(f"📥 Days until exam: {days_until_exam}")
        print(f"📥 Target score: {target_score}")
        print(f"📥 Study style: {study_style}")

        days_text = f"Days until exam: {days_until_exam}" if days_until_exam else "No specific exam date"
        weak_text = f"Weak topics to focus on: {', '.join(weak_topics) if weak_topics else 'None specified'}"
        score_text = f"Target score: {target_score}" if target_score else "No specific target score"
        style_text = f"Study style preference: {study_style}" if study_style else "Balanced approach recommended"

        prompt = f"""
        You are an expert study coach creating a personalized study plan for an exam candidate.

        GOAL: {goal}
        SUBJECTS: {', '.join(subjects)}
        HOURS AVAILABLE PER WEEK: {hours_per_week}
        {days_text}
        {weak_text}
        {score_text}
        {style_text}

        Create a detailed plan. Structure it exactly like this:

        DAILY SCHEDULE:
        [Day-by-day breakdown of what to study, including specific topics and time allocation]

        SUBJECT BREAKDOWN:
        [How to allocate time per subject based on strengths and weaknesses]

        STUDY STYLE TIPS:
        [Tips tailored to the student's preferred study style]

        STRATEGIES:
        - Strategy 1
        - Strategy 2
        - Strategy 3

        MILESTONES:
        - Milestone 1
        - Milestone 2
        - Milestone 3

        TIPS:
        - Tip 1
        - Tip 2
        - Tip 3
        """

        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                return self._parse_study_plan(response.text)
            except Exception as e:
                print(f"❌ Gemini study plan error: {e}")
                return self._fallback_study_plan(subjects, hours_per_week, target_score, study_style)

        return self._fallback_study_plan(subjects, hours_per_week, target_score, study_style)

    def _parse_study_plan(self, text: str) -> Dict:
        """Parse Gemini study plan response"""
        result = {
            "daily_schedule": "",
            "subject_breakdown": "",
            "study_style_tips": "",
            "strategies": [],
            "milestones": [],
            "tips": []
        }

        sections = {
            "DAILY SCHEDULE:": "daily_schedule",
            "SUBJECT BREAKDOWN:": "subject_breakdown",
            "STUDY STYLE TIPS:": "study_style_tips",
            "STRATEGIES:": "strategies",
            "MILESTONES:": "milestones",
            "TIPS:": "tips"
        }

        current_section = None
        for line in text.split('\n'):
            line = line.strip()
            
            # Check if line is a section header
            found_section = False
            for header, key in sections.items():
                if line.startswith(header):
                    current_section = key
                    found_section = True
                    break
            
            if found_section:
                continue

            if current_section in ["strategies", "milestones", "tips"] and line.startswith('-'):
                result[current_section].append(line[1:].strip())
            elif current_section and line and not line.startswith('-'):
                result[current_section] += line + "\n"

        # Clean up
        for key in result:
            if isinstance(result[key], str):
                result[key] = result[key].strip()

        return result

    def _fallback_study_plan(self, subjects: List[str], hours: int, target_score: str = None, study_style: str = None) -> Dict:
        return {
            "daily_schedule": f"Study {', '.join(subjects)} for {hours} hours per week.",
            "subject_breakdown": f"Allocate {hours // len(subjects) if subjects else 2} hours per subject.",
            "study_style_tips": f"Based on your {study_style or 'balanced'} study style, focus on {'active recall and spaced repetition' if study_style == 'active' else 'visual learning and note-taking' if study_style == 'visual' else 'consistent practice and review'}.",
            "strategies": ["Start with weak topics", "Take breaks", "Review daily"],
            "milestones": ["Complete all topics", "Practice tests", f"Reach {target_score or 'target'} score"],
            "tips": ["Stay consistent", "Get enough sleep", "Stay hydrated"]
        }

ai_service = AIService()
