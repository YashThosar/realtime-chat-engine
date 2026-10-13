import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models import Message, RoomMember
from app.ws.manager import manager
from app.ws.pubsub import publish_to_room

router = APIRouter()


@router.websocket("/ws/rooms/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: uuid.UUID, token: str = Query(...)):
    # Step 1: verify the JWT BEFORE accepting the connection
    user_id = decode_access_token(token)
    if user_id is None:
        await websocket.close(code=4401)  # custom code: unauthorized
        return

    user_id = uuid.UUID(user_id)

    # Step 2: verify this user is actually a member of this room
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user_id)
        )
        if result.scalar_one_or_none() is None:
            await websocket.close(code=4403)  # custom code: forbidden
            return

    # Step 3: handshake complete, accept and register the connection
    await manager.connect(room_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content")
            client_msg_id = data.get("client_msg_id")

            if not content or not client_msg_id:
                await websocket.send_json({"error": "content and client_msg_id are required"})
                continue

            async with AsyncSessionLocal() as db:
                # idempotency check — same as the REST endpoint
                result = await db.execute(
                    select(Message).where(
                        Message.room_id == room_id, Message.client_msg_id == client_msg_id
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    message = existing
                else:
                    result = await db.execute(
                        select(func.max(Message.seq)).where(Message.room_id == room_id)
                    )
                    max_seq = result.scalar()
                    next_seq = (max_seq or 0) + 1

                    message = Message(
                        room_id=room_id,
                        sender_id=user_id,
                        content=content,
                        seq=next_seq,
                        client_msg_id=client_msg_id,
                    )
                    db.add(message)
                    try:
                        await db.commit()
                        await db.refresh(message)
                    except IntegrityError:
                        await db.rollback()
                        result = await db.execute(
                            select(Message).where(
                                Message.room_id == room_id, Message.client_msg_id == client_msg_id
                            )
                        )
                        message = result.scalar_one_or_none()

                        payload = {
                "id": str(message.id),
                "room_id": str(message.room_id),
                "sender_id": str(message.sender_id),
                "content": message.content,
                "seq": message.seq,
                "created_at": message.created_at.isoformat(),
            }
            try:
                await publish_to_room(room_id, payload)
            except Exception:
                # message DB mein safe hai, sirf live delivery fail hui
                await websocket.send_json(
                    {"error": "saved, but live delivery failed", "seq": message.seq}
                )

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)