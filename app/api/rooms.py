import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Room, RoomMember, User
from app.schemas import RoomCreate, RoomMemberOut, RoomOut

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = Room(name=payload.name, created_by=current_user.id)
    db.add(room)
    await db.flush()

    membership = RoomMember(room_id=room.id, user_id=current_user.id)
    db.add(membership)

    await db.commit()
    await db.refresh(room)
    return room


@router.get("", response_model=list[RoomOut])
async def list_my_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Room).join(RoomMember, RoomMember.room_id == Room.id).where(RoomMember.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/{room_id}/join", status_code=status.HTTP_204_NO_CONTENT)
async def join_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == current_user.id)
    )
    if result.scalar_one_or_none():
        return

    membership = RoomMember(room_id=room_id, user_id=current_user.id)
    db.add(membership)
    await db.commit()


@router.get("/{room_id}/members", response_model=list[RoomMemberOut])
async def list_room_members(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not a member of this room")

    result = await db.execute(
        select(RoomMember, User).join(User, User.id == RoomMember.user_id).where(RoomMember.room_id == room_id)
    )
    rows = result.all()
    return [
        RoomMemberOut(user_id=user.id, username=user.username, joined_at=member.joined_at)
        for member, user in rows
    ]