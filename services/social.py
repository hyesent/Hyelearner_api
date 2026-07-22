# ============================================================
# services/social.py — Social Features Business Logic
# ============================================================

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import secrets

from models import (
    User, FriendRequest, Friendship, Message, DuelInvite,
    StudyGroup, StudyGroupMember, StudyGroupMessage,
    Challenge, ChallengeParticipant, Activity, UserStats, Duel
)


class SocialService:
    """Business logic for all social features"""
    
    # ============================================================
    # USER SEARCH
    # ============================================================
    
    def search_users(self, db: Session, query: str, user_id: int, limit: int = 20) -> List[Dict]:
        """Search for users by username, name, or school"""
        users = db.query(User).filter(
            or_(
                User.username.ilike(f"%{query}%"),
                User.first_name.ilike(f"%{query}%"),
                User.last_name.ilike(f"%{query}%"),
                User.school.ilike(f"%{query}%")
            ),
            User.id != user_id,
            User.is_active == True
        ).limit(limit).all()
        
        # Get friend status for each user
        friend_ids = [f.friend_id for f in db.query(Friendship).filter(Friendship.user_id == user_id).all()]
        request_ids = [r.sender_id for r in db.query(FriendRequest).filter(
            FriendRequest.receiver_id == user_id,
            FriendRequest.status == "pending"
        ).all()]
        
        result = []
        for user in users:
            stats = user.stats
            result.append({
                "id": user.id,
                "username": user.username,
                "firstName": user.first_name,
                "lastName": user.last_name,
                "avatar": user.avatar_url,
                "school": user.school,
                "exam": user.exam,
                "streak": stats.streak if stats else 0,
                "xp": stats.xp if stats else 0,
                "level": stats.level if stats else 1,
                "accuracy": stats.accuracy if stats else 0,
                "isFriend": user.id in friend_ids,
                "friendRequestSent": user.id in request_ids,
                "isOnline": user.last_login and (datetime.utcnow() - user.last_login).seconds < 300
            })
        
        return result
    
    # ============================================================
    # FRIENDS
    # ============================================================
    
    def get_friends(self, db: Session, user_id: int) -> List[User]:
        """Get all friends of a user"""
        friendships = db.query(Friendship).filter(Friendship.user_id == user_id).all()
        friend_ids = [f.friend_id for f in friendships]
        return db.query(User).filter(User.id.in_(friend_ids)).all()
    
    def get_friend_requests(self, db: Session, user_id: int) -> List[FriendRequest]:
        """Get pending friend requests for a user"""
        return db.query(FriendRequest).filter(
            FriendRequest.receiver_id == user_id,
            FriendRequest.status == "pending"
        ).all()
    
    def send_friend_request(self, db: Session, sender_id: int, receiver_id: int) -> FriendRequest:
        """Send a friend request"""
        # Check if already friends
        existing = db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == sender_id, Friendship.friend_id == receiver_id),
                and_(Friendship.user_id == receiver_id, Friendship.friend_id == sender_id)
            )
        ).first()
        if existing:
            raise ValueError("Already friends")
        
        # Check if request already sent
        existing_request = db.query(FriendRequest).filter(
            FriendRequest.sender_id == sender_id,
            FriendRequest.receiver_id == receiver_id,
            FriendRequest.status == "pending"
        ).first()
        if existing_request:
            raise ValueError("Friend request already sent")
        
        # Check if request already received (auto-accept)
        received_request = db.query(FriendRequest).filter(
            FriendRequest.sender_id == receiver_id,
            FriendRequest.receiver_id == sender_id,
            FriendRequest.status == "pending"
        ).first()
        if received_request:
            received_request.status = "accepted"
            received_request.updated_at = datetime.utcnow()
            
            friendship1 = Friendship(user_id=sender_id, friend_id=receiver_id)
            friendship2 = Friendship(user_id=receiver_id, friend_id=sender_id)
            db.add_all([friendship1, friendship2])
            db.commit()
            return received_request
        
        new_request = FriendRequest(
            sender_id=sender_id,
            receiver_id=receiver_id,
            status="pending"
        )
        db.add(new_request)
        db.commit()
        return new_request
    
    def accept_friend_request(self, db: Session, request_id: int, user_id: int) -> FriendRequest:
        """Accept a friend request"""
        request = db.query(FriendRequest).filter(
            FriendRequest.id == request_id,
            FriendRequest.receiver_id == user_id,
            FriendRequest.status == "pending"
        ).first()
        
        if not request:
            raise ValueError("Friend request not found")
        
        request.status = "accepted"
        request.updated_at = datetime.utcnow()
        
        friendship1 = Friendship(user_id=request.sender_id, friend_id=request.receiver_id)
        friendship2 = Friendship(user_id=request.receiver_id, friend_id=request.sender_id)
        db.add_all([friendship1, friendship2])
        db.commit()
        
        return request
    
    def reject_friend_request(self, db: Session, request_id: int, user_id: int) -> FriendRequest:
        """Reject a friend request"""
        request = db.query(FriendRequest).filter(
            FriendRequest.id == request_id,
            FriendRequest.receiver_id == user_id,
            FriendRequest.status == "pending"
        ).first()
        
        if not request:
            raise ValueError("Friend request not found")
        
        request.status = "rejected"
        request.updated_at = datetime.utcnow()
        db.commit()
        return request
    
    def remove_friend(self, db: Session, user_id: int, friend_id: int) -> bool:
        """Remove a friend"""
        friendships = db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
            )
        ).all()
        
        if not friendships:
            return False
        
        for f in friendships:
            db.delete(f)
        db.commit()
        return True
    
    def is_friend(self, db: Session, user_id: int, friend_id: int) -> bool:
        """Check if two users are friends"""
        return db.query(Friendship).filter(
            or_(
                and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id)
            )
        ).first() is not None
    
    # ============================================================
    # MESSAGES
    # ============================================================
    
    def get_conversation(self, db: Session, user_id: int, friend_id: int, limit: int = 50, before: int = None) -> List[Message]:
        """Get conversation between two users"""
        query = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user_id, Message.receiver_id == friend_id),
                and_(Message.sender_id == friend_id, Message.receiver_id == user_id)
            )
        )
        
        if before:
            query = query.filter(Message.id < before)
        
        return query.order_by(desc(Message.id)).limit(limit).all()
    
    def mark_messages_read(self, db: Session, user_id: int, friend_id: int) -> int:
        """Mark all messages from a friend as read"""
        result = db.query(Message).filter(
            Message.sender_id == friend_id,
            Message.receiver_id == user_id,
            Message.is_read == False
        ).update({"is_read": True, "read_at": datetime.utcnow()})
        db.commit()
        return result
    
    def get_unread_counts(self, db: Session, user_id: int) -> Dict:
        """Get unread message counts per conversation"""
        unread = db.query(Message).filter(
            Message.receiver_id == user_id,
            Message.is_read == False
        ).all()
        
        conversations = {}
        for msg in unread:
            if msg.sender_id not in conversations:
                sender = db.query(User).filter(User.id == msg.sender_id).first()
                conversations[msg.sender_id] = {
                    "friendId": msg.sender_id,
                    "friendUsername": sender.username if sender else "Unknown",
                    "friendAvatar": sender.avatar_url if sender else None,
                    "unreadCount": 0,
                    "lastMessage": msg.message,
                    "lastMessageAt": msg.created_at
                }
            conversations[msg.sender_id]["unreadCount"] += 1
            if msg.created_at > conversations[msg.sender_id]["lastMessageAt"]:
                conversations[msg.sender_id]["lastMessage"] = msg.message
                conversations[msg.sender_id]["lastMessageAt"] = msg.created_at
        
        return {
            "totalUnread": len(unread),
            "conversations": list(conversations.values())
        }
    
    # ============================================================
    # DUEL INVITES
    # ============================================================
    
    def create_duel_invite(self, db: Session, sender_id: int, receiver_id: int, subject: str, topic: str = None, question_count: int = 10, time_limit: int = 300) -> DuelInvite:
        """Create a duel invite"""
        invite = DuelInvite(
            sender_id=sender_id,
            receiver_id=receiver_id,
            subject=subject,
            topic=topic,
            question_count=question_count,
            time_limit=time_limit,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.add(invite)
        db.commit()
        return invite
    
    def get_duel_invites(self, db: Session, user_id: int) -> List[DuelInvite]:
        """Get pending duel invites for a user"""
        return db.query(DuelInvite).filter(
            DuelInvite.receiver_id == user_id,
            DuelInvite.status == "pending"
        ).order_by(DuelInvite.invited_at.desc()).all()
    
    def respond_duel_invite(self, db: Session, invite_id: int, user_id: int, accept: bool) -> DuelInvite:
        """Respond to a duel invite"""
        invite = db.query(DuelInvite).filter(
            DuelInvite.id == invite_id,
            DuelInvite.receiver_id == user_id,
            DuelInvite.status == "pending"
        ).first()
        
        if not invite:
            raise ValueError("Invite not found")
        
        if invite.expires_at < datetime.utcnow():
            invite.status = "expired"
            db.commit()
            raise ValueError("Invite has expired")
        
        invite.status = "accepted" if accept else "rejected"
        invite.updated_at = datetime.utcnow()
        db.commit()
        return invite
    
    # ============================================================
    # STUDY GROUPS
    # ============================================================
    
    def create_study_group(self, db: Session, name: str, created_by: int, description: str = None, subject: str = None, member_ids: List[int] = None) -> StudyGroup:
        """Create a study group"""
        invite_code = secrets.token_hex(3).upper()
        
        group = StudyGroup(
            name=name,
            description=description,
            subject=subject,
            created_by=created_by,
            invite_code=invite_code
        )
        db.add(group)
        db.commit()
        
        # Add creator
        member = StudyGroupMember(
            group_id=group.id,
            user_id=created_by,
            role="admin"
        )
        db.add(member)
        
        # Add other members
        if member_ids:
            for member_id in member_ids:
                if member_id != created_by:
                    m = StudyGroupMember(
                        group_id=group.id,
                        user_id=member_id,
                        role="member"
                    )
                    db.add(m)
        
        db.commit()
        return group
    
    def join_study_group(self, db: Session, group_id: int, user_id: int, invite_code: str = None) -> StudyGroupMember:
        """Join a study group"""
        query = db.query(StudyGroup).filter(StudyGroup.id == group_id)
        if invite_code:
            query = query.filter(StudyGroup.invite_code == invite_code)
        
        group = query.first()
        if not group:
            raise ValueError("Group not found or invalid invite code")
        
        # Check if already a member
        existing = db.query(StudyGroupMember).filter(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id
        ).first()
        
        if existing:
            raise ValueError("Already a member of this group")
        
        member = StudyGroupMember(
            group_id=group_id,
            user_id=user_id,
            role="member"
        )
        db.add(member)
        db.commit()
        return member
    
    def leave_study_group(self, db: Session, group_id: int, user_id: int) -> bool:
        """Leave a study group"""
        member = db.query(StudyGroupMember).filter(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id
        ).first()
        
        if not member:
            return False
        
        # If admin and there are other members, transfer admin
        if member.role == "admin":
            other_admin = db.query(StudyGroupMember).filter(
                StudyGroupMember.group_id == group_id,
                StudyGroupMember.user_id != user_id
            ).first()
            
            if other_admin:
                other_admin.role = "admin"
        
        db.delete(member)
        db.commit()
        return True
    
    def is_group_member(self, db: Session, group_id: int, user_id: int) -> bool:
        """Check if a user is a member of a group"""
        return db.query(StudyGroupMember).filter(
            StudyGroupMember.group_id == group_id,
            StudyGroupMember.user_id == user_id
        ).first() is not None
    
    # ============================================================
    # ACTIVITY
    # ============================================================
    
    def create_activity(self, db: Session, user_id: int, activity_type: str, message: str, data: Dict = None) -> Activity:
        """Create an activity entry"""
        activity = Activity(
            user_id=user_id,
            type=activity_type,
            message=message,
            data=data or {}
        )
        db.add(activity)
        db.commit()
        return activity
    
    def get_friend_activity(self, db: Session, user_id: int, limit: int = 20) -> List[Activity]:
        """Get activity feed from friends"""
        friendships = db.query(Friendship).filter(Friendship.user_id == user_id).all()
        friend_ids = [f.friend_id for f in friendships]
        
        return db.query(Activity).filter(
            Activity.user_id.in_(friend_ids)
        ).order_by(desc(Activity.created_at)).limit(limit).all()
    
    # ============================================================
    # CHALLENGES
    # ============================================================
    
    def create_challenge(self, db: Session, creator_id: int, challenge_type: str, friend_ids: List[int], duration: int = 7, stake: str = None) -> Challenge:
        """Create a new challenge"""
        challenge = Challenge(
            creator_id=creator_id,
            type=challenge_type,
            duration=duration,
            stake=stake,
            status="active",
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow() + timedelta(days=duration)
        )
        db.add(challenge)
        db.commit()
        
        # Add creator
        participant = ChallengeParticipant(
            challenge_id=challenge.id,
            user_id=creator_id
        )
        db.add(participant)
        
        # Add friends
        for friend_id in friend_ids:
            p = ChallengeParticipant(
                challenge_id=challenge.id,
                user_id=friend_id
            )
            db.add(p)
        
        db.commit()
        return challenge


# ============================================================
# INSTANCE
# ============================================================

social_service = SocialService()
