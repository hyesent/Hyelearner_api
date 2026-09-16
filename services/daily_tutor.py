# ============================================================
# services/daily_tutor.py — AI Daily Tutor Service
# ============================================================

import json
import re
from typing import Dict, Any, List
from datetime import datetime

from services.ai import ai_service


# ============================================================
# SYSTEM PROMPTS
# ============================================================

LESSON_SYSTEM_PROMPT = """You are HyeTutor, an expert AI tutor for Nigerian secondary school students preparing for JAMB, WAEC, NECO, and SSCE exams.

Your job: generate a short, personalized, exam-focused lesson for ONE topic. The student will read it and immediately take a quiz on it. The lesson must be:
- Tight enough to finish in 10–15 minutes
- Deep enough to actually teach the concept (not just list facts)
- Written for a student at the level provided
- Shaped by their study style
- Adjusted for anything they've struggled with or reflected on

RULES:

1. STRUCTURE
   - Exactly 4 sections.
   - Each section: a short heading + 2–4 short paragraphs (30–70 words each).
   - Sections progress logically: definition → mechanism → application → common pitfalls.
   - Do NOT use bullet lists inside sections. Write in prose. Bullets are reserved for key_points.

2. LENGTH
   - Total lesson: 350–550 words across all sections.
   - Aim for ~12 minutes of reading.
   - Cut ruthlessly. No filler, no motivational padding, no "welcome to this lesson."

3. STUDY STYLE SHAPING
   - active:  Include mini self-test questions inline ("Pause: can you guess why...?").
   - visual:  Describe diagrams in words ("Imagine a bag..." "Picture two layers...").
   - reading: Dense, well-organised prose. Slightly more formal. Clear topic sentences.
   - balanced: Mostly prose with one or two inline self-tests.

4. DIFFICULTY
   - Match user_level and difficulty_preference.
   - Level 1–3:  Simple analogies. Define jargon immediately.
   - Level 4–6:  Standard exam language. Introduce terminology with brief definitions.
   - Level 7–10: Assume familiarity. Use technical language. Focus on nuance and edge cases.

5. PERSONALIZATION — RECENT_MISTAKES
   - If a recent mistake targets the SAME topic you're teaching, weave a soft warning into the relevant section:
     "⚠️ Note: The mitochondrion is often confused with the ribosome. Remember — the mitochondrion produces ATP; the ribosome builds proteins."
   - Do NOT mention "you got this wrong" or refer to specific questions. Just address the confusion.

6. PERSONALIZATION — RECENT_REFLECTIONS
   - Reflections are ONLY a nudge. Do not mention them in the lesson text.
   - If feeling = "confusing" on a related area → slow down, add an extra example.
   - If feeling = "clear" on a related area → move faster, skip basics.
   - If a note exists and is relevant to the current topic, acknowledge it in content (not text).
   - Ignore reflections on unrelated subjects.

7. WEAK AREAS
   - If directly related to the current topic, spend slightly more time on the connection.
   - If unrelated, ignore. Do not tangent.

8. EXAM FOCUS
   - Prioritise what's commonly tested in JAMB/WAEC/NECO.
   - Call out exam traps where relevant ("Students often lose marks here because...").

9. TONE
   - Direct. Warm but not chatty. No "Hello student!" or "Let's dive in!"
   - Talk to them as a serious learner.

10. OUTPUT
   - Return ONLY valid JSON matching the schema. No markdown. No preamble. No code fences.

OUTPUT SCHEMA:
{
  "title": "Short, descriptive title including the topic",
  "estimated_minutes": 12,
  "difficulty": "easy | medium | hard",
  "sections": [
    { "heading": "Section heading", "body": "Section body text." }
  ],
  "key_points": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "personalization_notes": ["note 1", "note 2"]
}
"""


QUIZ_SYSTEM_PROMPT = """You are HyeTutor, generating a multiple-choice quiz for a Nigerian exam student (JAMB/WAEC/NECO/SSCE).

CRITICAL CONTEXT: The student JUST READ a lesson you generated. This quiz must test the EXACT lesson they just read. Not generic facts about the topic — the specific concepts, terminology, and takeaways from this lesson.

RULES:

1. SOURCE OF QUESTIONS
   - Every question must test a concept covered in lesson_key_points or lesson_section_headings.
   - Do NOT introduce concepts the lesson did not cover.
   - Do NOT quiz on trivia; quiz on understanding.

2. RE-TEST RECENT MISTAKES
   - If recent_mistakes includes a mistake on the SAME topic, include at least ONE question testing that exact concept (worded differently).
   - Example: if they missed "which organelle produces ATP", ask "which organelle is the site of cellular respiration" — same concept, different phrasing.
   - Max 2 re-test questions. The rest should be new.

3. DIFFICULTY DISTRIBUTION
   - Default: 2 easy, 2 medium, 1 hard (adjust proportionally if question_count differs).
   - The hard one should require applying the concept, not just recalling it.

4. QUESTION FORMAT
   - Each question: clear, unambiguous, single correct answer.
   - Exactly 4 options. No "all of the above" or "none of the above."
   - Distractors must be plausible — common misconceptions, not random wrong answers.
   - No negative phrasing ("Which is NOT...") unless unavoidable.
   - Keep questions under 30 words.

5. EXPLANATIONS
   - Each question comes with a 1–2 sentence explanation.
   - Explanation should reinforce the lesson, not just state the answer.
   - If the question re-tests a mistake, gently address the confusion.

6. CONCEPT TAGGING
   - Each question gets a `concept` tag (snake_case) for progress tracking.
   - Reuse the same tag across questions testing the same idea.

7. TONE
   - Exam-style English. Neutral. No humour.

8. OUTPUT
   - Return ONLY valid JSON matching the schema. No markdown. No preamble. No code fences.

OUTPUT SCHEMA:
{
  "questions": [
    {
      "id": "q1",
      "question": "Question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Option B",
      "explanation": "1–2 sentence explanation.",
      "difficulty": "easy | medium | hard",
      "topic": "Topic name",
      "concept": "snake_case_concept"
    }
  ],
  "personalization_notes": ["note 1", "note 2"]
}
"""


# ============================================================
# SERVICE
# ============================================================

class DailyTutorService:
    """AI service for generating daily lessons and quizzes."""

    def __init__(self):
        self.ai = ai_service

    # ============================================================
    # LESSON GENERATION
    # ============================================================

    async def generate_lesson(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a personalized lesson using AI."""

        user_payload = self._build_lesson_payload(data)

        response_text = None

        # Try Gemini first (system + user content)
        if self.ai.gemini:
            try:
                response = self.ai.gemini.generate_content(
                    f"{LESSON_SYSTEM_PROMPT}\n\n---\n\n{user_payload}"
                )
                response_text = response.text
                print("✅ Gemini generated lesson")
            except Exception as e:
                print(f"❌ Gemini lesson error: {e}")

        # Fallback to Groq
        if not response_text and self.ai.groq:
            try:
                response = self.ai.groq.chat.completions.create(
                    model=self.ai.groq_model,
                    messages=[
                        {"role": "system", "content": LESSON_SYSTEM_PROMPT},
                        {"role": "user", "content": user_payload},
                    ],
                    max_tokens=3000,
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )
                response_text = response.choices[0].message.content
                print("✅ Groq generated lesson (fallback)")
            except Exception as e:
                print(f"❌ Groq lesson error: {e}")

        if not response_text:
            return {
                "success": False,
                "error": "Failed to generate lesson. Please try again."
            }

        lesson = self._parse_lesson_response(response_text, data)

        if not lesson:
            return {
                "success": False,
                "error": "AI returned invalid lesson format. Please try again."
            }

        return {
            "success": True,
            "generated_at": datetime.utcnow().isoformat(),
            "lesson": lesson
        }

    def _build_lesson_payload(self, data: Dict[str, Any]) -> str:
        """Build user-message content for lesson generation."""

        weak_areas_text = "None specified"
        if data.get("weak_areas"):
            weak_areas_text = "\n".join([
                f"- {w['topic']} ({w['subject']}): {w['accuracy']}% accuracy"
                for w in data["weak_areas"][:5]
            ])

        mistakes_text = "None specified"
        if data.get("recent_mistakes"):
            mistakes_text = "\n".join([
                f"- Topic: {m['topic']}\n  Q: {m['question']}\n  User said: {m['user_answer']}\n  Correct: {m['correct_answer']}"
                for m in data["recent_mistakes"][:5]
            ])

        reflections_text = "None specified"
        if data.get("recent_reflections"):
            reflections_text = "\n".join([
                f"- {r['topic']} ({r['date']}): {r['feeling']}"
                + (f" — {r['note']}" if r.get("note") else "")
                for r in data["recent_reflections"][:5]
            ])

        plan = data.get("plan_context", {})

        return f"""STUDENT PROFILE:
- Level: {data['user_level']}
- Study Style: {data['study_style']}
- Difficulty Preference: {data['difficulty_preference']}
- Target Score: {data['target_score']}
- Exam: {data['exam_type'].upper()}

TODAY'S LESSON:
- Topic: {data['topic']}
- Subject: {data['subject']}
- Day {plan.get('day', 1)} of {plan.get('total_days', 1)}
- Weekly Focus: {plan.get('weekly_focus', 'General')}
- Time Allocated: {plan.get('hours_allocated', 0.5)} hours

STUDENT'S WEAK AREAS:
{weak_areas_text}

RECENT MISTAKES:
{mistakes_text}

RECENT REFLECTIONS:
{reflections_text}

TASK:
Create the lesson on "{data['topic']}" for {data['subject']} following the system rules and output schema exactly.
"""

    def _parse_lesson_response(self, text: str, data: Dict) -> Dict[str, Any]:
        """Parse AI response into structured lesson."""
        try:
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if not json_match:
                return None

            lesson = json.loads(json_match.group())

            # Normalise / fill defaults
            lesson.setdefault("title", f"{data['topic']} — {data['subject']}")
            lesson.setdefault("estimated_minutes", 12)
            lesson.setdefault("difficulty", "medium")
            lesson.setdefault("sections", [])
            lesson.setdefault("key_points", [])
            lesson.setdefault("personalization_notes", [])

            # Clean sections
            clean_sections = []
            for s in lesson["sections"]:
                if isinstance(s, dict) and "heading" in s and "body" in s:
                    clean_sections.append({
                        "heading": str(s["heading"]).strip(),
                        "body": str(s["body"]).strip(),
                    })
            lesson["sections"] = clean_sections

            # Cap key_points at 5, min 3
            lesson["key_points"] = [
                str(p).strip() for p in lesson["key_points"] if str(p).strip()
            ][:5]

            return lesson

        except Exception as e:
            print(f"❌ Failed to parse lesson: {e}")
            return None

    # ============================================================
    # QUIZ GENERATION
    # ============================================================

    async def generate_quiz(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a quiz based on the lesson content."""

        user_payload = self._build_quiz_payload(data)

        response_text = None

        # Try Gemini first
        if self.ai.gemini:
            try:
                response = self.ai.gemini.generate_content(
                    f"{QUIZ_SYSTEM_PROMPT}\n\n---\n\n{user_payload}"
                )
                response_text = response.text
                print("✅ Gemini generated quiz")
            except Exception as e:
                print(f"❌ Gemini quiz error: {e}")

        # Fallback to Groq
        if not response_text and self.ai.groq:
            try:
                response = self.ai.groq.chat.completions.create(
                    model=self.ai.groq_model,
                    messages=[
                        {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                        {"role": "user", "content": user_payload},
                    ],
                    max_tokens=2000,
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )
                response_text = response.choices[0].message.content
                print("✅ Groq generated quiz (fallback)")
            except Exception as e:
                print(f"❌ Groq quiz error: {e}")

        if not response_text:
            return {
                "success": False,
                "error": "Failed to generate quiz. Please try again."
            }

        quiz = self._parse_quiz_response(response_text, data)

        if not quiz:
            return {
                "success": False,
                "error": "AI returned invalid quiz format. Please try again."
            }

        return {
            "success": True,
            "generated_at": datetime.utcnow().isoformat(),
            "quiz": quiz
        }

    def _build_quiz_payload(self, data: Dict[str, Any]) -> str:
        """Build user-message content for quiz generation."""

        key_points = "\n".join([
            f"- {p}" for p in data.get("lesson_key_points", [])
        ]) or "None"

        headings = "\n".join([
            f"- {h}" for h in data.get("lesson_section_headings", [])
        ]) or "None"

        mistakes_text = "None"
        if data.get("recent_mistakes"):
            mistakes_text = "\n".join([
                f"- Topic: {m['topic']}\n  User said: {m['user_answer']}\n  Correct: {m['correct_answer']}"
                for m in data["recent_mistakes"][:3]
            ])

        return f"""LESSON TOPIC: {data['topic']}
SUBJECT: {data['subject']}
EXAM: {data['exam_type'].upper()}
STUDENT LEVEL: {data['user_level']}
QUESTION COUNT: {data['question_count']}

LESSON KEY POINTS:
{key_points}

LESSON SECTION HEADINGS:
{headings}

RECENT MISTAKES TO RE-TEST:
{mistakes_text}

TASK:
Generate exactly {data['question_count']} questions following the system rules and output schema exactly.
"""

    def _parse_quiz_response(self, text: str, data: Dict) -> Dict[str, Any]:
        """Parse AI response into structured quiz."""
        try:
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if not json_match:
                return None

            quiz = json.loads(json_match.group())
            quiz.setdefault("questions", [])
            quiz.setdefault("personalization_notes", [])

            clean_questions = []
            for i, q in enumerate(quiz["questions"]):
                if not isinstance(q, dict):
                    continue

                options = q.get("options") or []
                if not isinstance(options, list):
                    options = []

                answer = q.get("answer") or (options[0] if options else "")

                # Ensure answer matches one of the options
                if answer not in options and options:
                    answer = options[0]

                clean_questions.append({
                    "id": q.get("id") or f"q{i + 1}",
                    "question": str(q.get("question", "")).strip(),
                    "options": [str(o).strip() for o in options],
                    "answer": str(answer).strip(),
                    "explanation": str(q.get("explanation", "")).strip(),
                    "difficulty": q.get("difficulty", "medium"),
                    "topic": q.get("topic") or data["topic"],
                    "concept": q.get("concept") or "general",
                })

            quiz["questions"] = clean_questions
            return quiz

        except Exception as e:
            print(f"❌ Failed to parse quiz: {e}")
            return None


# ============================================================
# INSTANCE
# ============================================================

daily_tutor_service = DailyTutorService()
