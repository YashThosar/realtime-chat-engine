import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Room, RoomMember, User
from app.schemas import RoomCreate, RoomMemberOut, RoomOut

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = Room(name=payload.name, created_by=current_user.id)
    db.add(room)
    db.flush()  # room.id generate ho jata hai commit se pehle

    membership = RoomMember(room_id=room.id, user_id=current_user.id)
    db.add(membership)

    db.commit()
    db.refresh(room)
    return room


@router.get("", response_model=list[RoomOut])
def list_my_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rooms = (
        db.query(Room)
        .join(RoomMember, RoomMember.room_id == Room.id)
        .filter(RoomMember.user_id == current_user.id)
        .all()
    )
    return rooms


@router.post("/{room_id}/join", status_code=status.HTTP_204_NO_CONTENT)
def join_room(
    room_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    existing = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == current_user.id)
        .first()
    )
    if existing:
        return  # already a member, silently succeed

    membership = RoomMember(room_id=room_id, user_id=current_user.id)
    db.add(membership)
    db.commit()


@router.get("/{room_id}/members", response_model=list[RoomMemberOut])
def list_room_members(
    room_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_member = (
        db.query(RoomMember)
        .filter(RoomMember.room_id == room_id, RoomMember.user_id == current_user.id)
        .first()
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this room")

    rows = (
        db.query(RoomMember, User)
        .join(User, User.id == RoomMember.user_id)
        .filter(RoomMember.room_id == room_id)
        .all()
    )
    return [
        RoomMemberOut(user_id=user.id, username=user.username, joined_at=member.joined_at)
        for member, user in rows
    ]