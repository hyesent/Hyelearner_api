import os
import sys
import json
import re
from pathlib import Path
from sqlalchemy.orm import Session

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Question


def parse_js_question_file(filepath):
    """Extract questions from a JS file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find export default array
    match = re.search(r'export\s+default\s+\[([\s\S]*?)\];', content)
    if not match:
        return []
    
    array_content = match.group(1)
    questions = []
    
    # Extract each question object
    # Find all { ... } objects
    objects = re.finditer(r'\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', array_content)
    
    for obj_match in objects:
        try:
            obj_str = '{' + obj_match.group(1) + '}'
            # Convert to Python dict
            obj_str = obj_str.replace('true', 'True')
            obj_str = obj_str.replace('false', 'False')
            obj_str = obj_str.replace('null', 'None')
            
            # Use eval for simplicity (production would use ast.literal_eval with proper parser)
            question = eval(obj_str)
            
            if 'id' in question and 'question' in question:
                questions.append(question)
        except:
            continue
    
    return questions


def import_questions_from_folder(folder_path):
    """Walk through all JS files and import questions"""
    db = SessionLocal()
    
    try:
        total_imported = 0
        total_skipped = 0
        
        js_files = list(Path(folder_path).rglob('*.js'))
        print(f"📁 Found {len(js_files)} JS files")
        
        for file_path in js_files:
            if file_path.name.startswith('_'):
                continue
            
            questions = parse_js_question_file(file_path)
            print(f"📖 Found {len(questions)} questions in {file_path.name}")
            
            for q in questions:
                existing = db.query(Question).filter(Question.id == q['id']).first()
                if existing:
                    total_skipped += 1
                    continue
                
                question = Question(
                    id=q['id'],
                    type=q.get('type', 'multiple_choice'),
                    question=q['question'],
                    options=q.get('options', []),
                    answer=q['answer'],
                    explanation=q.get('explanation', ''),
                    difficulty=q.get('difficulty', 'medium'),
                    topic=q.get('topic', 'General'),
                    subject=q.get('subject', 'General'),
                    platform=q.get('platform', 'hyelearner'),
                    year=q.get('year', 2025)
                )
                db.add(question)
                total_imported += 1
            
            if total_imported % 100 == 0:
                db.commit()
                print(f"   ✅ {total_imported} questions imported so far...")
        
        db.commit()
        print(f"\n🎉 Import complete!")
        print(f"   ✅ Imported: {total_imported}")
        print(f"   ⏭️  Skipped: {total_skipped}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Update this path to your frontend questions folder
    questions_path = "../hyelearner-frontend/src/data/questions"
    
    print("🚀 Starting question import...")
    print(f"📁 Looking in: {questions_path}")
    
    if not os.path.exists(questions_path):
        print(f"❌ Path not found: {questions_path}")
        print("   Update the path to your frontend questions folder")
        sys.exit(1)
    
    import_questions_from_folder(questions_path)