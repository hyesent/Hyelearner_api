import google.generativeai as genai
import json
from typing import List, Dict, Any, Optional
from config import settings

class AIService:
    def __init__(self):
        self.gemini = None
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def get_explanation(self, question: Dict, user_answer: str) -> Dict:
        """Generate detailed explanation using Gemini"""
        prompt = f"""
        Question: {question.get('question_text', '')}
        Options: {json.dumps(question.get('options', []))}
        Correct Answer: {question.get('correct_answer', '')}
        User's Answer: {user_answer}
        
        Provide:
        1. Explanation of the correct answer
        2. Why the user's answer is wrong (if applicable)
        3. Key concept being tested
        4. 3 tips to avoid this mistake
        """
        
        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                return self._parse_explanation(response.text)
            except Exception as e:
                print(f"Gemini error: {e}")
                return self._fallback_explanation(question, user_answer)
        
        return self._fallback_explanation(question, user_answer)
    
    async def get_weakness_analysis(self, mistakes: List[Dict], mastery: Dict) -> List[Dict]:
        """Analyze weak areas using Gemini"""
        if not mistakes:
            return []
        
        prompt = f"""
        Analyze these student mistakes:
        {json.dumps(mistakes, indent=2)}
        
        Student's mastery data:
        {json.dumps(mastery, indent=2)}
        
        Identify the top 5 weakest topics. For each, provide:
        - topic name
        - accuracy percentage (0-100)
        - priority (High/Medium/Low)
        - brief recommendation
        """
        
        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                return self._parse_weakness(response.text)
            except Exception as e:
                print(f"Gemini weakness error: {e}")
                return self._fallback_weakness(mistakes)
        
        return self._fallback_weakness(mistakes)
    
    async def generate_study_plan(
        self,
        goal: str,
        subjects: List[str],
        hours_per_week: int,
        weak_topics: List[str],
        days_until_exam: Optional[int] = None
    ) -> Dict:
        """Generate personalized study plan using Gemini"""
        days_text = f"Days until exam: {days_until_exam}" if days_until_exam else "No specific exam date"
        
        prompt = f"""
        Create a personalized study plan for a student.
        
        Goal: {goal}
        Subjects: {', '.join(subjects)}
        Hours available per week: {hours_per_week}
        {days_text}
        Weak topics to focus on: {', '.join(weak_topics) if weak_topics else 'None specified'}
        
        Provide a weekly schedule with:
        1. Daily breakdown of topics to study
        2. Time allocation per subject
        3. Recommended practice strategies
        4. Milestone checkpoints
        """
        
        if self.gemini:
            try:
                response = self.gemini.generate_content(prompt)
                return self._parse_study_plan(response.text)
            except Exception as e:
                print(f"Gemini study plan error: {e}")
                return self._fallback_study_plan(subjects, hours_per_week)
        
        return self._fallback_study_plan(subjects, hours_per_week)
    
    def _parse_explanation(self, text: str) -> Dict:
        """Parse Gemini explanation response"""
        return {
            "explanation": text,
            "key_concept": self._extract_section(text, "key concept"),
            "tips": self._extract_list(text, "tips"),
            "wrong_explanations": None
        }
    
    def _parse_weakness(self, text: str) -> List[Dict]:
        """Parse Gemini weakness analysis"""
        weak_topics = []
        lines = text.split('\n')
        current = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('-') or line.startswith('•') or line.startswith('*'):
                if current.get('topic'):
                    weak_topics.append(current)
                current = {'topic': line.strip(' -•*')}
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
        
        if not weak_topics:
            return self._fallback_weakness([])
        
        return weak_topics[:5]
    
    def _parse_study_plan(self, text: str) -> Dict:
        """Parse Gemini study plan response"""
        return {
            "plan": text,
            "schedule": self._extract_schedule(text),
            "tips": self._extract_list(text, "tips")
        }
    
    def _extract_section(self, text: str, keyword: str) -> str:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                return '\n'.join(lines[i+1:i+5]).strip()
        return ""
    
    def _extract_list(self, text: str, keyword: str) -> List[str]:
        items = []
        lines = text.split('\n')
        in_section = False
        for line in lines:
            if keyword.lower() in line.lower():
                in_section = True
                continue
            if in_section and line.strip().startswith(('-', '•', '*')):
                items.append(line.strip(' -•*').strip())
            elif in_section and line.strip() and not line.strip().startswith(('-', '•', '*')):
                break
        return items[:5]
    
    def _extract_schedule(self, text: str) -> List[Dict]:
        schedule = []
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        lines = text.split('\n')
        current_day = None
        
        for line in lines:
            for day in days:
                if day in line:
                    current_day = day
                    schedule.append({'day': day, 'topics': []})
                    break
            if current_day and ':' in line and not any(d in line for d in days):
                parts = line.split(':')
                if len(parts) >= 2:
                    topic = parts[0].strip(' -•*').strip()
                    hours = parts[1].strip()
                    if schedule and topic:
                        schedule[-1]['topics'].append({'name': topic, 'hours': float(hours) if hours.replace('.', '').isdigit() else 1.0})
        
        return schedule
    
    def _fallback_explanation(self, question: Dict, user_answer: str) -> Dict:
        return {
            "explanation": f"Review the question carefully. Correct answer is: {question.get('correct_answer', 'N/A')}",
            "key_concept": "Review the fundamental concept",
            "tips": ["Read the question carefully", "Show your working", "Double-check your answer"],
            "wrong_explanations": None
        }
    
    def _fallback_weakness(self, mistakes: List[Dict]) -> List[Dict]:
        topics = {}
        for m in mistakes[:10]:
            topic = m.get('topic', 'General')
            if topic not in topics:
                topics[topic] = {'topic': topic, 'accuracy': 50, 'priority': 'Medium', 'recommendations': 'Practice more questions'}
        
        return list(topics.values())[:5]
    
    def _fallback_study_plan(self, subjects: List[str], hours: int) -> Dict:
        return {
            "plan": f"Study {', '.join(subjects)} for {hours} hours per week. Focus on weak areas first.",
            "schedule": [
                {"day": "Monday", "topics": [{"name": subjects[0] if subjects else "Math", "hours": hours/3}]},
                {"day": "Wednesday", "topics": [{"name": subjects[1] if len(subjects) > 1 else "English", "hours": hours/3}]},
                {"day": "Friday", "topics": [{"name": subjects[2] if len(subjects) > 2 else "Science", "hours": hours/3}]}
            ],
            "tips": ["Take breaks every 30 minutes", "Review weak topics first", "Practice daily"]
        }

ai_service = AIService()