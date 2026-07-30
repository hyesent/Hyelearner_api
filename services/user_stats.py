# ============================================================
# services/user_stats.py — User Stats Service
# ============================================================

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

from models import User, UserStats, Session as PracticeSession, UserDailyStats


class UserStatsService:
    """Service for managing user daily stats"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================================
    # GET TODAY'S STATS (Cached or Fresh)
    # ============================================================
    
    def get_today_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get today's user stats.
        Returns cached daily stats if available, otherwise computes fresh.
        """
        today = date.today()
        
        # Try to get today's stats from cache
        stats = self.db.query(UserDailyStats).filter(
            UserDailyStats.user_id == user_id,
            UserDailyStats.date == today
        ).first()
        
        if stats:
            return {
                "date": stats.date.isoformat(),
                "xp": stats.xp,
                "level": stats.level,
                "streak": stats.streak,
                "accuracy": stats.accuracy,
                "sessions": stats.sessions,
                "totalQuestions": stats.total_questions,
                "correct": stats.correct,
                "wrong": stats.wrong,
                "studyTime": stats.study_time_minutes,
                "fromCache": True,
                "cachedAt": stats.updated_at.isoformat() if stats.updated_at else None
            }
        
        # Compute fresh stats
        return self._compute_fresh_stats(user_id)
    
    # ============================================================
    # COMPUTE FRESH STATS
    # ============================================================
    
    def _compute_fresh_stats(self, user_id: int) -> Dict[str, Any]:
        """Compute user stats from scratch"""
        today = date.today()
        
        # Get all completed sessions
        sessions = self.db.query(PracticeSession).filter(
            PracticeSession.user_id == user_id,
            PracticeSession.is_completed == True
        ).all()
        
        # Get gamification stats
        gamification = self.db.query(UserStats).filter(
            UserStats.user_id == user_id
        ).first()
        
        # Calculate overall stats
        total_questions = sum(s.total_questions or 0 for s in sessions)
        correct = sum(s.correct_answers or 0 for s in sessions)
        wrong = sum(s.wrong_answers or 0 for s in sessions)
        accuracy = (correct / total_questions * 100) if total_questions > 0 else 0
        
        # Get today's sessions
        today_sessions = [
            s for s in sessions 
            if s.completed_at and s.completed_at.date() == today
        ]
        
        # Calculate study time
        study_time_minutes = sum(
            (s.time_taken or 0) for s in today_sessions
        ) // 60
        
        result = {
            "date": today.isoformat(),
            "xp": gamification.xp if gamification else 0,
            "level": gamification.level if gamification else 1,
            "streak": gamification.streak if gamification else 0,
            "accuracy": round(accuracy, 1),
            "sessions": len(today_sessions),
            "totalQuestions": total_questions,
            "correct": correct,
            "wrong": wrong,
            "studyTime": study_time_minutes,
            "fromCache": False
        }
        
        # Save to cache
        self._save_daily_stats(user_id, result)
        
        return result
    
    # ============================================================
    # SAVE DAILY STATS
    # ============================================================
    
    def _save_daily_stats(self, user_id: int, stats_data: Dict[str, Any]) -> UserDailyStats:
        """Save daily stats to database"""
        today = date.today()
        
        stats = self.db.query(UserDailyStats).filter(
            UserDailyStats.user_id == user_id,
            UserDailyStats.date == today
        ).first()
        
        if stats:
            stats.xp = stats_data.get("xp", stats.xp)
            stats.level = stats_data.get("level", stats.level)
            stats.streak = stats_data.get("streak", stats.streak)
            stats.accuracy = stats_data.get("accuracy", stats.accuracy)
            stats.sessions = stats_data.get("sessions", stats.sessions)
            stats.total_questions = stats_data.get("totalQuestions", stats.total_questions)
            stats.correct = stats_data.get("correct", stats.correct)
            stats.wrong = stats_data.get("wrong", stats.wrong)
            stats.study_time_minutes = stats_data.get("studyTime", stats.study_time_minutes)
            stats.updated_at = datetime.utcnow()
        else:
            stats = UserDailyStats(
                user_id=user_id,
                date=today,
                xp=stats_data.get("xp", 0),
                level=stats_data.get("level", 1),
                streak=stats_data.get("streak", 0),
                accuracy=stats_data.get("accuracy", 0),
                sessions=stats_data.get("sessions", 0),
                total_questions=stats_data.get("totalQuestions", 0),
                correct=stats_data.get("correct", 0),
                wrong=stats_data.get("wrong", 0),
                study_time_minutes=stats_data.get("studyTime", 0)
            )
            self.db.add(stats)
        
        self.db.commit()
        return stats
    
    def save_stats(self, user_id: int, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """Public method to save stats"""
        stats = self._save_daily_stats(user_id, stats_data)
        return {
            "success": True,
            "date": stats.date.isoformat(),
            "saved": True
        }
    
    # ============================================================
    # GET STATS RANGE
    # ============================================================
    
    def get_stats_range(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """Get user stats for a date range"""
        start_date = date.today() - timedelta(days=days)
        
        stats = self.db.query(UserDailyStats).filter(
            UserDailyStats.user_id == user_id,
            UserDailyStats.date >= start_date
        ).order_by(UserDailyStats.date).all()
        
        return {
            "range": f"Last {days} days",
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
            "stats": [
                {
                    "date": s.date.isoformat(),
                    "xp": s.xp,
                    "level": s.level,
                    "streak": s.streak,
                    "accuracy": s.accuracy,
                    "sessions": s.sessions,
                    "studyTime": s.study_time_minutes
                }
                for s in stats
            ],
            "total": len(stats)
        }
    
    # ============================================================
    # GET TODAY'S PROGRESS
    # ============================================================
    
    def get_today_progress(self, user_id: int) -> Dict[str, Any]:
        """Quick check: how many sessions today?"""
        today = date.today()
        
        # Count today's sessions
        session_count = self.db.query(PracticeSession).filter(
            PracticeSession.user_id == user_id,
            func.date(PracticeSession.completed_at) == today,
            PracticeSession.is_completed == True
        ).count()
        
        # Get today's stats
        stats = self.db.query(UserDailyStats).filter(
            UserDailyStats.user_id == user_id,
            UserDailyStats.date == today
        ).first()
        
        # Get gamification for streak
        gamification = self.db.query(UserStats).filter(
            UserStats.user_id == user_id
        ).first()
        
        return {
            "sessions_today": session_count,
            "goal": 5,  # Daily goal
            "remaining": max(0, 5 - session_count),
            "xp_today": stats.xp if stats else 0,
            "streak": gamification.streak if gamification else 0,
            "accuracy": stats.accuracy if stats else 0
        }
    
    # ============================================================
    # GET WEEKLY STATS
    # ============================================================
    
    def get_weekly_stats(self, user_id: int) -> Dict[str, Any]:
        """Get weekly aggregated stats (last 7 days)"""
        start_date = date.today() - timedelta(days=7)
        
        # Get stats for last 7 days
        stats = self.db.query(UserDailyStats).filter(
            UserDailyStats.user_id == user_id,
            UserDailyStats.date >= start_date
        ).all()
        
        # If no daily stats, compute from sessions
        if not stats:
            sessions = self.db.query(PracticeSession).filter(
                PracticeSession.user_id == user_id,
                func.date(PracticeSession.completed_at) >= start_date,
                PracticeSession.is_completed == True
            ).all()
            
            # Group by date
            daily_data = {}
            for s in sessions:
                if s.completed_at:
                    day = s.completed_at.date().isoformat()
                    if day not in daily_data:
                        daily_data[day] = {
                            "sessions": 0, 
                            "xp": 0, 
                            "accuracy": 0, 
                            "correct": 0, 
                            "total": 0
                        }
                    daily_data[day]["sessions"] += 1
                    daily_data[day]["correct"] += s.correct_answers or 0
                    daily_data[day]["total"] += s.total_questions or 0
            
            # Format response
            weekly_data = []
            for day, data in daily_data.items():
                acc = (data["correct"] / data["total"] * 100) if data["total"] > 0 else 0
                weekly_data.append({
                    "day": day,
                    "sessions": data["sessions"],
                    "accuracy": round(acc, 1),
                    "xp": data["sessions"] * 10  # Estimate
                })
            
            return {
                "range": "Last 7 days",
                "start": start_date.isoformat(),
                "end": date.today().isoformat(),
                "stats": weekly_data,
                "total_sessions": sum(d["sessions"] for d in weekly_data),
                "avg_accuracy": round(
                    sum(d["accuracy"] for d in weekly_data) / len(weekly_data), 1
                ) if weekly_data else 0
            }
        
        return {
            "range": "Last 7 days",
            "start": start_date.isoformat(),
            "end": date.today().isoformat(),
            "stats": [
                {
                    "day": s.date.isoformat(),
                    "sessions": s.sessions,
                    "accuracy": s.accuracy,
                    "xp": s.xp
                }
                for s in stats
            ],
            "total_sessions": sum(s.sessions for s in stats),
            "avg_accuracy": round(
                sum(s.accuracy for s in stats) / len(stats), 1
            ) if stats else 0
        }
    
    # ============================================================
    # CLEANUP OLD STATS
    # ============================================================
    
    def cleanup_old_stats(self, user_id: int, days_to_keep: int = 30) -> Dict[str, Any]:
        """Cleanup stats older than specified days"""
        cutoff = date.today() - timedelta(days=days_to_keep)
        
        deleted = self.db.query(UserDailyStats).filter(
            UserDailyStats.user_id == user_id,
            UserDailyStats.date < cutoff
        ).delete()
        
        self.db.commit()
        
        return {
            "success": True,
            "deleted": deleted,
            "days_kept": days_to_keep,
            "cutoff_date": cutoff.isoformat()
        }


# ============================================================
# INSTANCE
# ============================================================

def get_user_stats_service(db: Session) -> UserStatsService:
    """Dependency to get UserStatsService instance"""
    return UserStatsService(db)
