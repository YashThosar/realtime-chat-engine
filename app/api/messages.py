import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Message, RoomMember, User
from app.schemas import MessageCreate, MessageOut

router = APIRouter(prefix="/rooms/{room_id}/messages", tags=["messages"])


async def ensure_member(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="You are not a member of this room")


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: uuid.UUID,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ensure_member(db, room_id, current_user.id)

    # idempotency check: same client_msg_id already exists in this room?
    result = await db.execute(
        select(Message).where(
            Message.room_id == room_id, Message.client_msg_id == payload.client_msg_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing  # retry — return the original, don't create a duplicate

    # next sequence number for this room
    result = await db.execute(select(func.max(Message.seq)).where(Message.room_id == room_id))
    max_seq = result.scalar()
    next_seq = (max_seq or 0) + 1

    message = Message(
        room_id=room_id,
        sender_id=current_user.id,
        content=payload.content,
        seq=next_seq,
        client_msg_id=payload.client_msg_id,
    )
    db.add(message)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # race condition: two requests grabbed the same seq at once — check if it was a retry
        result = await db.execute(
            select(Message).where(
                Message.room_id == room_id, Message.client_msg_id == payload.client_msg_id
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        raise HTTPException(status_code=409, detail="Could not save message, please retry")

    await db.refresh(message)
    return message


@router.get("", response_model=list[MessageOut])
async def get_messages(
    room_id: uuid.UUID,
    after_seq: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ensure_member(db, room_id, current_user.id)

    result = await db.execute(
        select(Message)
        .where(Message.room_id == room_id, Message.seq > after_seq)
        .order_by(Message.seq.asc())
        .limit(limit)
    )
    return result.scalars().all()