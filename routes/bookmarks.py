from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from database import get_db
from models import Bookmark, User, Question
from schemas import BookmarkCreate, BookmarkResponse
from dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=List[BookmarkResponse])
async def get_bookmarks(
    question_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bookmarks for current user"""
    query = db.query(Bookmark).filter(Bookmark.user_id == current_user.id)
    
    if question_id:
        query = query.filter(Bookmark.question_id == question_id)
    
    bookmarks = query.order_by(Bookmark.created_at.desc()).all()
    return bookmarks


@router.post("/", response_model=BookmarkResponse)
async def create_bookmark(
    data: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bookmark"""
    # Check if question exists
    question = db.query(Question).filter(Question.id == data.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check if already bookmarked
    existing = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id,
        Bookmark.question_id == data.question_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Question already bookmarked")
    
    bookmark = Bookmark(
        user_id=current_user.id,
        question_id=data.question_id,
        note=data.note
    )
    
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    
    return bookmark


@router.put("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    data: BookmarkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a bookmark"""
    bookmark = db.query(Bookmark).filter(
        Bookmark.id == bookmark_id,
        Bookmark.user_id == current_user.id
    ).first()
    
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    bookmark.note = data.note
    db.commit()
    db.refresh(bookmark)
    
    return bookmark


@router.delete("/{bookmark_id}")
async def delete_bookmark(
    bookmark_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bookmark"""
    bookmark = db.query(Bookmark).filter(
        Bookmark.id == bookmark_id,
        Bookmark.user_id == current_user.id
    ).first()
    
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    db.delete(bookmark)
    db.commit()
    
    return {"message": "Bookmark deleted successfully"}


@router.delete("/question/{question_id}")
async def delete_bookmark_by_question(
    question_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bookmark by question ID"""
    bookmark = db.query(Bookmark).filter(
        Bookmark.user_id == current_user.id,
        Bookmark.question_id == question_id
    ).first()
    
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    db.delete(bookmark)
    db.commit()
    
    return {"message": "Bookmark deleted successfully"}