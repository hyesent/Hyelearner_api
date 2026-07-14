import google.generativeai as genai
from groq import Groq
import json
from typing import List, Dict, Any, Optional
from config import settings

class AIService:
    def __init__(self):
        self.gemini = None
        self.groq = None
        
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("✅ Gemini AI initialized successfully")
            except Exception as e:
                print(f"❌ Gemini initialization failed: {e}")
        else:
            print("⚠️ GEMINI_API_KEY not found in environment")
        
        if settings.GROQ_API_KEY:
            try:
                self.groq = Groq(api_key=settings.GROQ_API_KEY)
                print("✅ Groq AI initialized successfully")
            except Exception as e:
                print(f"❌ Groq initialization failed: {e}")
        else:
            print("⚠️ GROQ_API_KEY not found in environment")

    # ============================================================
    # 1. AI EXPLANATION
    # ============================================================
    async def get_explanation(self, question: Dict, user_answer: str) -> Dict:
        """Generate detailed explanation using Gemini"""
        print(f"📥 Received question: {question.get('question_text', 'N/A')[:50]}...")
        print(f"📥 User answer: {user_answer}")

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
    # 2. AI WEAKNESS ANALYSIS
    # ============================================================
    async def get_weakness_analysis(self, mistakes: List[Dict], mastery: Dict) -> List[Dict]:
        """Analyze weak areas using Gemini"""
        if not mistakes:
            return []

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
        try:
            import re
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

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
    # 3. AI STUDY PLAN (Legacy v1)
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
        """Generate personalized study plan using Gemini (v1)"""
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

    # ============================================================
    # 4. AI STUDY PLAN V2 (Premium)
    # ============================================================
    async def enhance_study_plan(self, plan: Dict, user_data: Dict, weak_topics: List[str]) -> Dict:
        """Use AI to enhance the study plan with additional insights"""
        if not self.gemini:
            return self._fallback_enhancement()

        prompt = f"""
        You are an expert study coach. Review this study plan and provide personalized insights.

        USER DATA:
        - Goal: {user_data.get('goal', 'Pass exam')}
        - Subjects: {user_data.get('subjects', [])}
        - Target Score: {user_data.get('target_score', '300+')}
        - Study Style: {user_data.get('study_style', 'balanced')}
        - Days Remaining: {user_data.get('days_until_exam', 30)}
        - Weak Topics: {weak_topics[:5] if weak_topics else 'None'}

        PLAN SUMMARY:
        - Total Hours: {plan.get('summary', {}).get('total_hours', 0)}
        - Weekly Hours: {plan.get('summary', {}).get('weekly_hours', 0)}
        - Topics: {plan.get('summary', {}).get('total_topics', 0)}
        - Weak Areas: {plan.get('summary', {}).get('weak_areas', [])}

        Provide:
        1. Key insights (3-5 bullet points) — what the student should focus on
        2. Critical advice — the most important thing for success
        3. Confidence score (0-100) — based on the plan's completeness
        4. Suggestions for improvement

        Return as JSON:
        {{
            "insights": ["insight 1", "insight 2", "insight 3"],
            "critical_advice": "your advice",
            "confidence_score": 85,
            "suggestions": "your suggestions"
        }}
        """

        try:
            response = self.gemini.generate_content(prompt)
            return self._parse_enhancement(response.text)
        except Exception as e:
            print(f"❌ Gemini enhancement error: {e}")
            return self._fallback_enhancement()

    def _parse_enhancement(self, text: str) -> Dict:
        try:
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass

        return self._fallback_enhancement()

    def _fallback_enhancement(self) -> Dict:
        return {
            "insights": [
                "Focus on weak topics first",
                "Consistency beats intensity",
                "Practice past questions regularly"
            ],
            "critical_advice": "Stay consistent with your study schedule. Review weak topics every other day.",
            "confidence_score": 70,
            "suggestions": "Review your progress weekly and adjust your schedule accordingly."
        }

    # ============================================================
    # 5. AI QUESTION GENERATOR
    # ============================================================
    async def generate_questions(self, topic: str, count: int, difficulty: Optional[str] = None) -> List[Dict]:
        """Generate AI-powered practice questions"""
        prompt = f"""
        Generate {count} {difficulty or 'mixed'} difficulty practice questions on the topic: {topic}.

        Each question should be multiple choice with 4 options.

        Return as JSON array:
        [
            {{
                "question": "What is the question?",
                "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
                "answer": "A. Option 1",
                "explanation": "Why this is correct"
            }}
        ]
        """

        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                import re
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"❌ Gemini generate error: {e}")

        return []

    # ============================================================
    # 6. NEW: CHECK ADMISSION ELIGIBILITY (Global Course Finder)
    # ============================================================

    async def check_admission_eligibility(
        self,
        university: str,
        country: str,
        course: str,
        score: float,
        score_type: str,
        subjects: List[str]
    ) -> dict:
        """Check if user qualifies for a course at ANY university in the world"""
        
        prompt = f"""
        You are an expert university admissions advisor.

        UNIVERSITY: {university}
        COUNTRY: {country}
        COURSE: {course}
        SCORE: {score}
        SCORE TYPE: {score_type}
        SUBJECTS: {', '.join(subjects)}

        Return as JSON only:
        {{
            "university": "{university}",
            "country": "{country}",
            "course": "{course}",
            "requirements": {{
                "score_needed": 0,
                "score_type": "{score_type}",
                "subjects_needed": ["Subject1", "Subject2"]
            }},
            "result": {{
                "status": "qualified|partial|not_qualified|unknown",
                "message": "User-friendly message with emoji",
                "details": "Detailed explanation",
                "chances": "Excellent|Good|Possible|Unlikely",
                "chance_percentage": 85,
                "score_gap": 0
            }}
        }}
        """
        
        # Try Gemini first
        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                result = self._parse_json(response.text)
                result["recommendations"] = self._generate_combined_recommendations(
                    status=result.get("result", {}).get("status", "unknown"),
                    score_gap=result.get("result", {}).get("score_gap", 0),
                    course=course,
                    score_type=score_type
                )
                result["alternatives"] = self._generate_alternatives_with_percentages(
                    university=university,
                    course=course,
                    score=score
                )
                return result
            except Exception as e:
                print(f"❌ Gemini failed: {e}")
        
        # Fallback to Groq
        if self.groq:
            try:
                response = self.groq.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[{"role": "user", "content": prompt}]
                )
                result = self._parse_json(response.choices[0].message.content)
                result["recommendations"] = self._generate_combined_recommendations(
                    status=result.get("result", {}).get("status", "unknown"),
                    score_gap=result.get("result", {}).get("score_gap", 0),
                    course=course,
                    score_type=score_type
                )
                result["alternatives"] = self._generate_alternatives_with_percentages(
                    university=university,
                    course=course,
                    score=score
                )
                return result
            except Exception as e:
                print(f"❌ Groq failed: {e}")
        
        # Final fallback
        return self._fallback_admission_check(university, course, score, score_type)

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from AI response"""
        try:
            return json.loads(text)
        except:
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
            return {}

    def _generate_combined_recommendations(
        self,
        status: str,
        score_gap: int,
        course: str,
        score_type: str
    ) -> List[dict]:
        """Generate mix of AI advice + app feature recommendations"""
        
        recommendations = []
        
        # AI Advice (user-friendly, no routes)
        if status == "not_qualified" and score_gap > 50:
            recommendations.append({
                "type": "ai_advice",
                "title": "📚 Consider Retaking Your Exam",
                "description": f"Your score is {score_gap} points below the requirement. Focus on targeted practice to close this gap."
            })
        
        if status in ["partial", "not_qualified"]:
            recommendations.append({
                "type": "ai_advice",
                "title": "🎯 Focus on Your Weakest Subject",
                "description": "Identify which subject is pulling your score down and dedicate extra time to it."
            })
        
        if status == "qualified":
            recommendations.append({
                "type": "ai_advice",
                "title": "🌟 Maintain Your Momentum",
                "description": "Keep practicing to ensure you don't lose your edge. Stay consistent."
            })
        
        recommendations.append({
            "type": "ai_advice",
            "title": "📝 Start Your Application Early",
            "description": f"Applications for {course} at this university are highly competitive. Give yourself plenty of time to prepare."
        })
        
        recommendations.append({
            "type": "ai_advice",
            "title": "🔍 Research the Program",
            "description": f"Look into the specific modules, professors, and research opportunities in {course} at this university."
        })
        
        # App Features (drive users into the app)
        recommendations.append({
            "type": "app_feature",
            "title": "📚 Create Your Study Plan",
            "description": f"Get a personalized study plan to improve your chances for {course}.",
            "feature": "study_plan"
        })
        
        if status in ["partial", "not_qualified"]:
            recommendations.append({
                "type": "app_feature",
                "title": "🧠 Find Your Weak Areas",
                "description": "Identify exactly where you're losing points and focus on improvement.",
                "feature": "weakness"
            })
        
        recommendations.append({
            "type": "app_feature",
            "title": "📝 Practice Daily",
            "description": f"Practice {score_type.upper()} questions daily to build confidence and speed.",
            "feature": "practice"
        })
        
        if status in ["partial", "not_qualified"]:
            recommendations.append({
                "type": "app_feature",
                "title": "📖 Track Your Mistakes",
                "description": "Review and learn from your mistakes to avoid repeating them.",
                "feature": "mistakes"
            })
        
        if status == "qualified":
            recommendations.append({
                "type": "app_feature",
                "title": "📅 Plan Your Revision",
                "description": "Create a revision schedule to maintain your edge and stay on track.",
                "feature": "revision"
            })
        
        return recommendations

    def _generate_alternatives_with_percentages(
        self,
        university: str,
        course: str,
        score: int
    ) -> List[dict]:
        """Generate alternative universities with percentage chances"""
        
        alternatives = [
            {
                "university": "MIT",
                "course": course,
                "score_needed": 1500,
                "chance_percentage": self._calculate_chance(score, 1500),
                "message": "✅ You have an excellent chance at MIT with your current score." if score >= 1500 else "⚠️ MIT is competitive. Consider improving your score."
            },
            {
                "university": "Stanford",
                "course": course,
                "score_needed": 1530,
                "chance_percentage": self._calculate_chance(score, 1530),
                "message": "✅ Stanford is within reach!" if score >= 1530 else "⚠️ Stanford is a reach. Consider retaking your exam."
            }
        ]
        
        return alternatives

    def _calculate_chance(self, score: int, needed: int) -> int:
        """Calculate percentage chance based on score vs requirement"""
        if score >= needed:
            base = 70
            bonus = min((score - needed) // 10 * 5, 25)
            return min(base + bonus, 98)
        else:
            base = max(0, 70 - (needed - score) // 5 * 5)
            return min(base, 68)

    def _fallback_admission_check(self, university: str, course: str, score: float, score_type: str) -> dict:
        """Fallback response when AI fails"""
        return {
            "university": university,
            "country": "Unknown",
            "course": course,
            "requirements": {
                "score_needed": "Check university website",
                "score_type": score_type or "unknown",
                "subjects_needed": ["Check university website"]
            },
            "result": {
                "status": "unknown",
                "message": "⚠️ Could not verify admission requirements automatically.",
                "details": f"Please check {university}'s official website for {course} admission requirements.",
                "chances": "Unknown",
                "chance_percentage": 50,
                "score_gap": 0
            },
            "recommendations": [
                {
                    "type": "ai_advice",
                    "title": "🔍 Check Official Website",
                    "description": f"Visit {university}'s admissions page for accurate requirements."
                },
                {
                    "type": "ai_advice",
                    "title": "📧 Contact Admissions Office",
                    "description": "Reach out to the admissions office directly for clarification."
                },
                {
                    "type": "app_feature",
                    "title": "📚 Create Your Study Plan",
                    "description": "Get a personalized study plan while you research.",
                    "feature": "study_plan"
                }
            ],
            "alternatives": []
        }


# ============================================================
# INSTANCE
# ============================================================

ai_service = AIService()
