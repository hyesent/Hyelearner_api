from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import json
import csv
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from database import get_db
from models import Mistake, User, Question
from schemas import MistakeResponse, MistakeExplanationResponse
from dependencies import get_current_user
from services.ai import ai_service

router = APIRouter()


@router.get("/", response_model=List[MistakeResponse])
async def get_mistakes(
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's mistakes"""
    query = db.query(Mistake).filter(Mistake.user_id == current_user.id)
    
    if subject:
        query = query.filter(Mistake.subject.ilike(subject))
    if topic:
        query = query.filter(Mistake.topic.ilike(topic))
    if resolved is not None:
        query = query.filter(Mistake.is_resolved == resolved)
    
    mistakes = query.order_by(Mistake.created_at.desc()).offset(offset).limit(limit).all()
    return mistakes


@router.get("/{mistake_id}", response_model=MistakeResponse)
async def get_mistake(
    mistake_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific mistake"""
    mistake = db.query(Mistake).filter(
        Mistake.id == mistake_id,
        Mistake.user_id == current_user.id
    ).first()
    
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")
    
    return mistake


@router.get("/{mistake_id}/explanation", response_model=MistakeExplanationResponse)
async def get_mistake_explanation(
    mistake_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI explanation for a mistake"""
    mistake = db.query(Mistake).filter(
        Mistake.id == mistake_id,
        Mistake.user_id == current_user.id
    ).first()
    
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")
    
    # Check if cached
    if mistake.explanation:
        try:
            return json.loads(mistake.explanation)
        except:
            pass
    
    # Get question
    question = db.query(Question).filter(Question.id == mistake.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Generate explanation
    explanation = await ai_service.get_explanation(
        {
            "question_text": question.question,
            "options": question.options,
            "correct_answer": question.answer
        },
        mistake.user_answer
    )
    
    # Cache explanation
    mistake.explanation = json.dumps(explanation)
    db.commit()
    
    return explanation


@router.put("/{mistake_id}/resolve")
async def resolve_mistake(
    mistake_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a mistake as resolved"""
    mistake = db.query(Mistake).filter(
        Mistake.id == mistake_id,
        Mistake.user_id == current_user.id
    ).first()
    
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")
    
    mistake.is_resolved = True
    mistake.resolved_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Mistake resolved successfully"}


@router.delete("/{mistake_id}")
async def delete_mistake(
    mistake_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a mistake"""
    mistake = db.query(Mistake).filter(
        Mistake.id == mistake_id,
        Mistake.user_id == current_user.id
    ).first()
    
    if not mistake:
        raise HTTPException(status_code=404, detail="Mistake not found")
    
    db.delete(mistake)
    db.commit()
    
    return {"message": "Mistake deleted successfully"}


@router.delete("/clear")
async def clear_mistakes(
    only_resolved: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear all resolved mistakes"""
    query = db.query(Mistake).filter(Mistake.user_id == current_user.id)
    
    if only_resolved:
        query = query.filter(Mistake.is_resolved == True)
    
    count = query.count()
    query.delete()
    db.commit()
    
    return {"message": f"Cleared {count} mistakes", "count": count}


@router.get("/export")
async def export_mistakes(
    format: str = Query("pdf", regex="^(pdf|csv)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export mistakes as PDF or CSV"""
    mistakes = db.query(Mistake).filter(
        Mistake.user_id == current_user.id,
        Mistake.is_resolved == False
    ).all()
    
    if not mistakes:
        raise HTTPException(status_code=404, detail="No mistakes to export")
    
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Question", "Your Answer", "Correct Answer", "Subject", "Topic", "Date"])
        
        for m in mistakes:
            writer.writerow([
                m.question_id,
                m.user_answer,
                m.correct_answer,
                m.subject,
                m.topic,
                m.created_at.strftime("%Y-%m-%d %H:%M")
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=mistakes_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
        )
    
    # PDF Export
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=30
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=10
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#374151'),
        spaceAfter=6
    )
    
    content = []
    
    # Title
    content.append(Paragraph("Hyelearner — Mistake Book", title_style))
    content.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p')}", body_style))
    content.append(Paragraph(f"Total Mistakes: {len(mistakes)}", body_style))
    content.append(Spacer(1, 20))
    
    # Table
    table_data = [["#", "Question", "Your Answer", "Correct Answer", "Subject", "Topic"]]
    
    for idx, m in enumerate(mistakes, 1):
        question_text = m.question_id[:50] + "..." if len(m.question_id) > 50 else m.question_id
        table_data.append([
            str(idx),
            question_text,
            m.user_answer,
            m.correct_answer,
            m.subject,
            m.topic
        ])
    
    table = Table(table_data, colWidths=[0.3*inch, 2.2*inch, 1*inch, 1*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F9FAFB'), colors.HexColor('#FFFFFF')]),
    ]))
    
    content.append(table)
    content.append(Spacer(1, 30))
    content.append(Paragraph("Keep practicing! You got this! 💪", body_style))
    
    doc.build(content)
    buffer.seek(0)
    
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=mistakes_{datetime.utcnow().strftime('%Y%m%d')}.pdf"}
    )