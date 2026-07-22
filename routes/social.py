# ============================================================
# routes/social.py — Complete Social Features
# Friends, Messages, Duel Invites, Study Groups, Challenges
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import random

from database import get_db
from models import (
    User, FriendRequest, Friendship, Message, DuelInvite,
    StudyGroup, StudyGroupMember, StudyGroupMessage,
    Challenge, ChallengeParticipant, Activity, UserStats, Duel
)
from dependencies import get_current_user
from services.social import social_service

router = APIRouter(prefix="/social", tags=["Social"])


# ============================================================
# 1. USER SEARCH
# ============================================================

@router.get("/users/search")
async def search_users(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for users by username, name, or school"""
    users = db.query(User).filter(
        or_(
            User.username.ilike(f"%{q}%"),
            User.first_name.ilike(f"%{q}%"),
            User.last_name.ilike(f"%{q}%"),
            User.school.ilike(f"%{q}%")
        ),
        User.id != current_user.id,
        User.is_active == True
    ).limit(limit).all()
    
    # Get friend status for each user
    result = []
    friend_ids = [f.friend_id for f in db.query(Friendship).filter(Friendship.user_id == current_user.id).all()]
    request_ids = [r.sender_id for r in db.query(FriendRequest).filter(
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).all()]
    
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "avatar": user.avatar_url,
            "school": user.school,
            "exam": user.exam,
            "streak": user.stats.streak if user.stats else 0,
            "xp": user.stats.xp if user.stats else 0,
            "level": user.stats.level if user.stats else 1,
            "accuracy": user.stats.accuracy if user.stats else 0,
            "isFriend": user.id in friend_ids,
            "friendRequestSent": user.id in request_ids,
            "isOnline": user.last_login and (datetime.utcnow() - user.last_login).seconds < 300
        })
    
    return {
        "success": True,
        "data": {
            "users": result,
            "total": len(result),
            "limit": limit
        }
    }


# ============================================================
# 2. FRIENDS SYSTEM
# ============================================================

@router.get("/friends")
async def get_friends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all friends with online status"""
    friendships = db.query(Friendship).filter(
        Friendship.user_id == current_user.id
    ).all()
    
    friend_ids = [f.friend_id for f in friendships]
    friends = db.query(User).filter(User.id.in_(friend_ids)).all()
    
    # Get unread message counts
    unread_counts = {}
    for f in friends:
        unread = db.query(Message).filter(
            Message.sender_id == f.id,
            Message.receiver_id == current_user.id,
            Message.is_read == False
        ).count()
        unread_counts[f.id] = unread
    
    return {
        "success": True,
        "data": {
            "friends": [
                {
                    "id": f.id,
                    "username": f.username,
                    "firstName": f.first_name,
                    "lastName": f.last_name,
                    "avatar": f.avatar_url,
                    "school": f.school,
                    "exam": f.exam,
                    "streak": f.stats.streak if f.stats else 0,
                    "xp": f.stats.xp if f.stats else 0,
                    "level": f.stats.level if f.stats else 1,
                    "accuracy": f.stats.accuracy if f.stats else 0,
                    "isOnline": f.last_login and (datetime.utcnow() - f.last_login).seconds < 300,
                    "lastSeen": f.last_login,
                    "unreadMessages": unread_counts.get(f.id, 0),
                    "friendSince": next((fs.created_at for fs in friendships if fs.friend_id == f.id), None)
                }
                for f in friends
            ],
            "total": len(friends),
            "online": sum(1 for f in friends if f.last_login and (datetime.utcnow() - f.last_login).seconds < 300)
        }
    }


@router.post("/friends/request")
async def send_friend_request(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a friend request"""
    receiver_id = data.get("userId")
    if not receiver_id:
        raise HTTPException(400, "userId is required")
    
    if receiver_id == current_user.id:
        raise HTTPException(400, "Cannot send friend request to yourself")
    
    # Check if already friends
    existing = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == receiver_id),
            and_(Friendship.user_id == receiver_id, Friendship.friend_id == current_user.id)
        )
    ).first()
    if existing:
        raise HTTPException(400, "Already friends")
    
    # Check if request already sent
    existing_request = db.query(FriendRequest).filter(
        FriendRequest.sender_id == current_user.id,
        FriendRequest.receiver_id == receiver_id,
        FriendRequest.status == "pending"
    ).first()
    if existing_request:
        raise HTTPException(400, "Friend request already sent")
    
    # Check if request already received
    received_request = db.query(FriendRequest).filter(
        FriendRequest.sender_id == receiver_id,
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()
    if received_request:
        # Auto-accept if request already exists from them
        received_request.status = "accepted"
        friendship1 = Friendship(user_id=current_user.id, friend_id=receiver_id)
        friendship2 = Friendship(user_id=receiver_id, friend_id=current_user.id)
        db.add_all([friendship1, friendship2])
        db.commit()
        return {
            "success": True,
            "data": {
                "requestId": received_request.id,
                "status": "accepted",
                "message": "Friend request automatically accepted"
            }
        }
    
    new_request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        status="pending"
    )
    db.add(new_request)
    db.commit()
    
    return {
        "success": True,
        "data": {
            "requestId": new_request.id,
            "status": "pending",
            "sentAt": new_request.created_at
        }
    }


@router.get("/friends/requests")
async def get_friend_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending friend requests"""
    requests = db.query(FriendRequest).filter(
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).all()
    
    return {
        "success": True,
        "data": {
            "requests": [
                {
                    "id": r.id,
                    "fromUser": {
                        "id": r.sender.id,
                        "username": r.sender.username,
                        "firstName": r.sender.first_name,
                        "lastName": r.sender.last_name,
                        "avatar": r.sender.avatar_url
                    },
                    "sentAt": r.created_at
                }
                for r in requests
            ],
            "total": len(requests)
        }
    }


@router.put("/friends/accept/{request_id}")
async def accept_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a friend request"""
    request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()
    
    if not request:
        raise HTTPException(404, "Friend request not found")
    
    request.status = "accepted"
    request.updated_at = datetime.utcnow()
    
    # Create bidirectional friendships
    friendship1 = Friendship(user_id=request.sender_id, friend_id=request.receiver_id)
    friendship2 = Friendship(user_id=request.receiver_id, friend_id=request.sender_id)
    db.add_all([friendship1, friendship2])
    db.commit()
    
    return {
        "success": True,
        "data": {
            "friendId": request.sender_id,
            "friendUsername": request.sender.username,
            "acceptedAt": request.updated_at
        }
    }


@router.delete("/friends/reject/{request_id}")
async def reject_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a friend request"""
    request = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()
    
    if not request:
        raise HTTPException(404, "Friend request not found")
    
    request.status = "rejected"
    request.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Friend request rejected"}


@router.delete("/friends/{friend_id}")
async def remove_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a friend"""
    friendships = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == friend_id),
            and_(Friendship.user_id == friend_id, Friendship.friend_id == current_user.id)
        )
    ).all()
    
    if not friendships:
        raise HTTPException(404, "Friend not found")
    
    for f in friendships:
        db.delete(f)
    db.commit()
    
    return {"success": True, "message": "Friend removed"}


# ============================================================
# 3. PRIVATE MESSAGES
# ============================================================

@router.get("/messages/{friend_id}")
async def get_messages(
    friend_id: int,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation with a friend"""
    # Check if they are friends
    is_friend = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == friend_id),
            and_(Friendship.user_id == friend_id, Friendship.friend_id == current_user.id)
        )
    ).first()
    
    if not is_friend:
        raise HTTPException(403, "You can only message friends")
    
    query = db.query(Message).filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == friend_id),
            and_(Message.sender_id == friend_id, Message.receiver_id == current_user.id)
        )
    )
    
    if before:
        query = query.filter(Message.id < before)
    
    messages = query.order_by(desc(Message.id)).limit(limit).all()
    messages.reverse()
    
    # Mark messages from friend as read
    db.query(Message).filter(
        Message.sender_id == friend_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()
    
    return {
        "success": True,
        "data": {
            "messages": [
                {
                    "id": m.id,
                    "senderId": m.sender_id,
                    "receiverId": m.receiver_id,
                    "message": m.message,
                    "isRead": m.is_read,
                    "createdAt": m.created_at
                }
                for m in messages
            ],
            "nextCursor": messages[0].id if len(messages) == limit else None
        }
    }


@router.post("/messages/send")
async def send_message(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a private message"""
    recipient_id = data.get("recipientId")
    message_text = data.get("message")
    
    if not recipient_id or not message_text:
        raise HTTPException(400, "recipientId and message are required")
    
    # Check if they are friends
    is_friend = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == recipient_id),
            and_(Friendship.user_id == recipient_id, Friendship.friend_id == current_user.id)
        )
    ).first()
    
    if not is_friend:
        raise HTTPException(403, "You can only message friends")
    
    # Check if recipient exists
    recipient = db.query(User).filter(User.id == recipient_id).first()
    if not recipient:
        raise HTTPException(404, "Recipient not found")
    
    message = Message(
        sender_id=current_user.id,
        receiver_id=recipient_id,
        message=message_text,
        is_read=False
    )
    db.add(message)
    db.commit()
    
    # Create activity
    activity = Activity(
        user_id=current_user.id,
        type="message",
        message=f"Sent a message to {recipient.username}",
        data={"recipient_id": recipient_id, "message_id": message.id}
    )
    db.add(activity)
    db.commit()
    
    return {
        "success": True,
        "data": {
            "message": {
                "id": message.id,
                "senderId": message.sender_id,
                "receiverId": message.receiver_id,
                "message": message.message,
                "isRead": message.is_read,
                "createdAt": message.created_at
            }
        }
    }


@router.put("/messages/{friend_id}/read")
async def mark_messages_read(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all messages from a friend as read"""
    result = db.query(Message).filter(
        Message.sender_id == friend_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()
    
    return {
        "success": True,
        "data": {
            "markedCount": result,
            "updatedAt": datetime.utcnow()
        }
    }


@router.get("/messages/unread")
async def get_unread_counts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get unread message counts per conversation"""
    # Get all unread messages
    unread = db.query(Message).filter(
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).all()
    
    # Group by sender
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
        # Update last message if newer
        if msg.created_at > conversations[msg.sender_id]["lastMessageAt"]:
            conversations[msg.sender_id]["lastMessage"] = msg.message
            conversations[msg.sender_id]["lastMessageAt"] = msg.created_at
    
    return {
        "success": True,
        "data": {
            "totalUnread": len(unread),
            "conversations": list(conversations.values())
        }
    }


# ============================================================
# 4. DUEL INVITES
# ============================================================

@router.post("/duel/invite")
async def send_duel_invite(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a duel invite to a friend"""
    friend_id = data.get("friendId")
    subject = data.get("subject")
    topic = data.get("topic")
    question_count = data.get("questionCount", 10)
    time_limit = data.get("timeLimit", 300)
    
    if not friend_id or not subject:
        raise HTTPException(400, "friendId and subject are required")
    
    # Check if they are friends
    is_friend = db.query(Friendship).filter(
        or_(
            and_(Friendship.user_id == current_user.id, Friendship.friend_id == friend_id),
            and_(Friendship.user_id == friend_id, Friendship.friend_id == current_user.id)
        )
    ).first()
    
    if not is_friend:
        raise HTTPException(403, "You can only invite friends")
    
    friend = db.query(User).filter(User.id == friend_id).first()
    if not friend:
        raise HTTPException(404, "Friend not found")
    
    # Create invite
    invite = DuelInvite(
        sender_id=current_user.id,
        receiver_id=friend_id,
        subject=subject,
        topic=topic,
        question_count=question_count,
        time_limit=time_limit,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db.add(invite)
    db.commit()
    
    return {
        "success": True,
        "data": {
            "inviteId": invite.id,
            "friendId": friend.id,
            "friendUsername": friend.username,
            "status": invite.status,
            "invitedAt": invite.invited_at,
            "expiresAt": invite.expires_at
        }
    }


@router.get("/duel/invites")
async def get_duel_invites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pending duel invites"""
    invites = db.query(DuelInvite).filter(
        DuelInvite.receiver_id == current_user.id,
        DuelInvite.status == "pending"
    ).order_by(DuelInvite.invited_at.desc()).all()
    
    return {
        "success": True,
        "data": {
            "invites": [
                {
                    "id": i.id,
                    "fromUser": {
                        "id": i.sender.id,
                        "username": i.sender.username,
                        "avatar": i.sender.avatar_url
                    },
                    "subject": i.subject,
                    "topic": i.topic,
                    "questionCount": i.question_count,
                    "timeLimit": i.time_limit,
                    "status": i.status,
                    "invitedAt": i.invited_at,
                    "expiresAt": i.expires_at
                }
                for i in invites
            ]
        }
    }


@router.post("/duel/invite/{invite_id}/respond")
async def respond_duel_invite(
    invite_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept or reject a duel invite"""
    accept = data.get("accept", False)
    
    invite = db.query(DuelInvite).filter(
        DuelInvite.id == invite_id,
        DuelInvite.receiver_id == current_user.id,
        DuelInvite.status == "pending"
    ).first()
    
    if not invite:
        raise HTTPException(404, "Invite not found or already responded")
    
    if invite.expires_at < datetime.utcnow():
        invite.status = "expired"
        db.commit()
        raise HTTPException(400, "Invite has expired")
    
    if not accept:
        invite.status = "rejected"
        db.commit()
        return {"success": True, "message": "Duel invite rejected"}
    
    # ACCEPT — Create the duel using existing duel endpoint logic
    # Generate questions (simplified — reuse your existing logic)
    from routes.duel import create_duel_from_invite  # You'll need to extract this logic
    
    # For now, create a simple duel
    import secrets
    code = secrets.token_hex(3).upper()
    
    duel = Duel(
        challenger_id=invite.sender_id,
        opponent_id=current_user.id,
        code=code,
        subject=invite.subject,
        topic=invite.topic,
        questions_data=[],  # Will be populated by frontend
        question_ids=[],
        status="active",
        is_public=False,
        time_limit=invite.time_limit,
        challenger_score=0,
        opponent_score=0
    )
    db.add(duel)
    db.commit()
    
    invite.status = "accepted"
    invite.duel_id = duel.id
    db.commit()
    
    return {
        "success": True,
        "data": {
            "duelId": duel.id,
            "status": duel.status,
            "questionCount": invite.question_count,
            "timeLimit": invite.time_limit,
            "startsAt": datetime.utcnow().isoformat()
        }
    }


# ============================================================
# 5. STUDY GROUPS
# ============================================================

@router.get("/groups")
async def get_study_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all study groups the user is a member of"""
    memberships = db.query(StudyGroupMember).filter(
        StudyGroupMember.user_id == current_user.id
    ).all()
    
    group_ids = [m.group_id for m in memberships]
    groups = db.query(StudyGroup).filter(StudyGroup.id.in_(group_ids)).all()
    
    return {
        "success": True,
        "data": {
            "groups": [
                {
                    "id": g.id,
                    "name": g.name,
                    "description": g.description,
                    "subject": g.subject,
                    "memberCount": db.query(StudyGroupMember).filter(StudyGroupMember.group_id == g.id).count(),
                    "isMember": True,
                    "createdBy": g.created_by,
                    "createdAt": g.created_at,
                    "lastActivity": g.updated_at
                }
                for g in groups
            ]
        }
    }


@router.post("/groups/create")
async def create_study_group(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a study group"""
    name = data.get("name")
    description = data.get("description")
    subject = data.get("subject")
    member_ids = data.get("memberIds", [])
    
    if not name:
        raise HTTPException(400, "name is required")
    
    # Generate invite code
    invite_code = secrets.token_hex(3).upper()
    
    group = StudyGroup(
        name=name,
        description=description,
        subject=subject,
        created_by=current_user.id,
        invite_code=invite_code
    )
    db.add(group)
    db.commit()
    
    # Add creator as member
    member = StudyGroupMember(
        group_id=group.id,
        user_id=current_user.id,
        role="admin"
    )
    db.add(member)
    
    # Add other members
    for member_id in member_ids:
        if member_id != current_user.id:
            m = StudyGroupMember(
                group_id=group.id,
                user_id=member_id,
                role="member"
            )
            db.add(m)
    
    db.commit()
    
    return {
        "success": True,
        "data": {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "subject": group.subject,
            "memberCount": len(member_ids) + 1,
            "isMember": True,
            "createdAt": group.created_at,
            "inviteCode": invite_code
        }
    }


@router.post("/groups/{group_id}/join")
async def join_study_group(
    group_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Join a study group"""
    invite_code = data.get("inviteCode")
    
    query = db.query(StudyGroup).filter(StudyGroup.id == group_id)
    if invite_code:
        query = query.filter(StudyGroup.invite_code == invite_code)
    
    group = query.first()
    
    if not group:
        raise HTTPException(404, "Group not found or invalid invite code")
    
    # Check if already a member
    existing = db.query(StudyGroupMember).filter(
        StudyGroupMember.group_id == group_id,
        StudyGroupMember.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(400, "Already a member of this group")
    
    member = StudyGroupMember(
        group_id=group_id,
        user_id=current_user.id,
        role="member"
    )
    db.add(member)
    db.commit()
    
    return {
        "success": True,
        "data": {
            "groupId": group.id,
            "joinedAt": member.joined_at
        }
    }


@router.post("/groups/{group_id}/leave")
async def leave_study_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Leave a study group"""
    member = db.query(StudyGroupMember).filter(
        StudyGroupMember.group_id == group_id,
        StudyGroupMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(404, "Not a member of this group")
    
    db.delete(member)
    db.commit()
    
    return {"success": True, "message": "Left group successfully"}


@router.get("/groups/{group_id}/messages")
async def get_group_messages(
    group_id: int,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages from a study group"""
    # Check membership
    member = db.query(StudyGroupMember).filter(
        StudyGroupMember.group_id == group_id,
        StudyGroupMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(403, "You are not a member of this group")
    
    messages = db.query(StudyGroupMessage).filter(
        StudyGroupMessage.group_id == group_id
    ).order_by(desc(StudyGroupMessage.id)).limit(limit).all()
    messages.reverse()
    
    return {
        "success": True,
        "data": {
            "messages": [
                {
                    "id": m.id,
                    "sender": {
                        "id": m.sender.id,
                        "username": m.sender.username,
                        "avatar": m.sender.avatar_url
                    },
                    "message": m.message,
                    "isPinned": m.is_pinned,
                    "isAnnouncement": m.is_announcement,
                    "createdAt": m.created_at
                }
                for m in messages
            ]
        }
    }


@router.post("/groups/{group_id}/message")
async def send_group_message(
    group_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a study group"""
    message_text = data.get("message")
    if not message_text:
        raise HTTPException(400, "message is required")
    
    # Check membership
    member = db.query(StudyGroupMember).filter(
        StudyGroupMember.group_id == group_id,
        StudyGroupMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(403, "You are not a member of this group")
    
    is_announcement = data.get("isAnnouncement", False) and member.role == "admin"
    
    message = StudyGroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        message=message_text,
        is_announcement=is_announcement
    )
    db.add(message)
    
    # Update group activity
    group = db.query(StudyGroup).filter(StudyGroup.id == group_id).first()
    group.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "data": {
            "id": message.id,
            "sender": {
                "id": current_user.id,
                "username": current_user.username
            },
            "message": message.message,
            "isAnnouncement": message.is_announcement,
            "createdAt": message.created_at
        }
    }


@router.put("/groups/{group_id}/pin/{message_id}")
async def pin_group_message(
    group_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pin a message in the group"""
    # Check if user is admin
    member = db.query(StudyGroupMember).filter(
        StudyGroupMember.group_id == group_id,
        StudyGroupMember.user_id == current_user.id,
        StudyGroupMember.role == "admin"
    ).first()
    
    if not member:
        raise HTTPException(403, "Only admins can pin messages")
    
    # Unpin previous pinned message
    db.query(StudyGroupMessage).filter(
        StudyGroupMessage.group_id == group_id,
        StudyGroupMessage.is_pinned == True
    ).update({"is_pinned": False})
    
    # Pin new message
    message = db.query(StudyGroupMessage).filter(
        StudyGroupMessage.id == message_id,
        StudyGroupMessage.group_id == group_id
    ).first()
    
    if not message:
        raise HTTPException(404, "Message not found")
    
    message.is_pinned = True
    db.commit()
    
    return {"success": True, "message": "Message pinned"}


@router.post("/groups/{group_id}/announcement")
async def send_announcement(
    group_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send an announcement to the group (admins only)"""
    message_text = data.get("message")
    if not message_text:
        raise HTTPException(400, "message is required")
    
    # Check if user is admin
    member = db.query(StudyGroupMember).filter(
        StudyGroupMember.group_id == group_id,
        StudyGroupMember.user_id == current_user.id,
        StudyGroupMember.role == "admin"
    ).first()
    
    if not member:
        raise HTTPException(403, "Only admins can send announcements")
    
    message = StudyGroupMessage(
        group_id=group_id,
        sender_id=current_user.id,
        message=message_text,
        is_announcement=True
    )
    db.add(message)
    db.commit()
    
    return {
        "success": True,
        "data": {
            "id": message.id,
            "message": message.message,
            "createdAt": message.created_at
        }
    }


@router.get("/groups/{group_id}/members")
async def get_group_members(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all members of a study group"""
    members = db.query(StudyGroupMember).filter(
        StudyGroupMember.group_id == group_id
    ).all()
    
    user_ids = [m.user_id for m in members]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    
    # Create role mapping
    role_map = {m.user_id: m.role for m in members}
    
    return {
        "success": True,
        "data": {
            "members": [
                {
                    "id": u.id,
                    "username": u.username,
                    "firstName": u.first_name,
                    "lastName": u.last_name,
                    "avatar": u.avatar_url,
                    "role": role_map.get(u.id, "member"),
                    "joinedAt": next((m.joined_at for m in members if m.user_id == u.id), None)
                }
                for u in users
            ],
            "total": len(users)
        }
    }


# ============================================================
# 6. ACTIVITY FEED
# ============================================================

@router.get("/activity/friends")
async def get_friend_activity(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get activity feed from friends"""
    # Get friends' IDs
    friendships = db.query(Friendship).filter(
        Friendship.user_id == current_user.id
    ).all()
    
    friend_ids = [f.friend_id for f in friendships]
    
    # Get activities from friends
    activities = db.query(Activity).filter(
        Activity.user_id.in_(friend_ids)
    ).order_by(desc(Activity.created_at)).limit(limit).all()
    
    return {
        "success": True,
        "data": {
            "activities": [
                {
                    "id": a.id,
                    "type": a.type,
                    "friend": {
                        "id": a.user.id,
                        "username": a.user.username,
                        "avatar": a.user.avatar_url
                    },
                    "message": a.message,
                    "details": a.data,
                    "createdAt": a.created_at
                }
                for a in activities
            ]
        }
    }


@router.get("/activity/global")
async def get_global_activity(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get global activity feed"""
    activities = db.query(Activity).order_by(
        desc(Activity.created_at)
    ).limit(limit).all()
    
    stats = {
        "totalUsers": db.query(User).filter(User.is_active == True).count(),
        "onlineNow": db.query(User).filter(
            User.last_login > (datetime.utcnow() - timedelta(minutes=5))
        ).count(),
        "sessionsToday": db.query(Activity).filter(
            Activity.type == "session",
            Activity.created_at > datetime.utcnow().replace(hour=0, minute=0, second=0)
        ).count()
    }
    
    return {
        "success": True,
        "data": {
            "recent": [
                {
                    "user": a.user.username,
                    "action": a.message,
                    "details": a.data,
                    "timeAgo": (datetime.utcnow() - a.created_at).seconds // 60
                }
                for a in activities
            ],
            "stats": stats
        }
    }


# ============================================================
# 7. CHALLENGES
# ============================================================

@router.post("/challenges/create")
async def create_challenge(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new challenge"""
    challenge_type = data.get("type")
    friend_ids = data.get("friendIds", [])
    duration = data.get("duration", 7)
    stake = data.get("stake")
    
    if not challenge_type or not friend_ids:
        raise HTTPException(400, "type and friendIds are required")
    
    challenge = Challenge(
        creator_id=current_user.id,
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
        user_id=current_user.id
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
    
    return {
        "success": True,
        "data": {
            "challengeId": challenge.id,
            "type": challenge.type,
            "participants": [current_user.id] + friend_ids,
            "duration": challenge.duration,
            "stake": challenge.stake,
            "status": challenge.status,
            "startsAt": challenge.starts_at,
            "endsAt": challenge.ends_at
        }
    }


@router.get("/challenges")
async def get_challenges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all challenges the user is part of"""
    participants = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.user_id == current_user.id
    ).all()
    
    challenge_ids = [p.challenge_id for p in participants]
    challenges = db.query(Challenge).filter(
        Challenge.id.in_(challenge_ids)
    ).order_by(desc(Challenge.created_at)).all()
    
    return {
        "success": True,
        "data": {
            "challenges": [
                {
                    "id": c.id,
                    "type": c.type,
                    "creator": c.creator_id,
                    "participants": [
                        {"id": p.user_id, "username": p.user.username}
                        for p in db.query(ChallengeParticipant).filter(
                            ChallengeParticipant.challenge_id == c.id
                        ).all()
                    ],
                    "status": c.status,
                    "startsAt": c.starts_at,
                    "endsAt": c.ends_at
                }
                for c in challenges
            ]
        }
    }


@router.post("/challenges/{challenge_id}/accept")
async def accept_challenge(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a challenge invitation"""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    
    # Check if already participating
    existing = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id,
        ChallengeParticipant.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(400, "Already participating in this challenge")
    
    participant = ChallengeParticipant(
        challenge_id=challenge_id,
        user_id=current_user.id
    )
    db.add(participant)
    db.commit()
    
    return {
        "success": True,
        "data": {
            "challengeId": challenge.id,
            "joinedAt": participant.joined_at
        }
    }


@router.get("/challenges/{challenge_id}")
async def get_challenge_status(
    challenge_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get challenge status with progress"""
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    
    participants = db.query(ChallengeParticipant).filter(
        ChallengeParticipant.challenge_id == challenge_id
    ).all()
    
    # Calculate progress for each participant (simplified)
    results = []
    for p in participants:
        # Get user stats
        stats = db.query(UserStats).filter(UserStats.user_id == p.user_id).first()
        progress = stats.streak if challenge.type == "streak" else stats.xp // 100
        results.append({
            "id": p.user_id,
            "username": p.user.username,
            "progress": progress or 0,
            "rank": 0  # Will be calculated after sorting
        })
    
    # Sort by progress and assign ranks
    results.sort(key=lambda x: x["progress"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    
    return {
        "success": True,
        "data": {
            "id": challenge.id,
            "type": challenge.type,
            "status": challenge.status,
            "participants": results,
            "timeRemaining": (challenge.ends_at - datetime.utcnow()).seconds // 3600
        }
    }
