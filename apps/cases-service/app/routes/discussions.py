from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.case import CaseDB
from app.models.discussion import (
    DiscussionMessageDB,
    DiscussionMessage,
    DiscussionMessageCreate,
    DiscussionMessageUpdate,
)
from app.utils.database import get_db
from app.routes.cases import get_current_user_override, can_access_case, _user_role, _user_identities

router = APIRouter(prefix="/discussions", tags=["Discussions"])


def _to_message_response(db_message: DiscussionMessageDB) -> DiscussionMessage:
    return DiscussionMessage(
        id=db_message.id,
        case_id=db_message.case_id,
        user_id=db_message.user_id,
        content=db_message.content,
        created_at=db_message.created_at,
        updated_at=db_message.updated_at,
    )


async def _get_case_or_404(db: AsyncSession, case_id: str) -> CaseDB:
    result = await db.execute(select(CaseDB).where(CaseDB.id == case_id))
    db_case = result.scalar_one_or_none()

    if not db_case:
        raise HTTPException(status_code=404, detail="Case not found")

    return db_case


@router.get("/case/{case_id}", response_model=List[DiscussionMessage])
async def list_case_messages(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_override),
):
    db_case = await _get_case_or_404(db, case_id)

    if not can_access_case(current_user, db_case):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(DiscussionMessageDB)
        .where(DiscussionMessageDB.case_id == case_id)
        .order_by(DiscussionMessageDB.created_at.asc())
    )
    messages = result.scalars().all()

    return [_to_message_response(message) for message in messages]


@router.post("/case/{case_id}", response_model=DiscussionMessage, status_code=status.HTTP_201_CREATED)
async def create_case_message(
    case_id: str,
    payload: DiscussionMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_override),
):
    db_case = await _get_case_or_404(db, case_id)

    if not can_access_case(current_user, db_case):
        raise HTTPException(status_code=403, detail="Access denied")

    possible_user_ids = list(_user_identities(current_user))
    if not possible_user_ids:
        raise HTTPException(status_code=401, detail="Unable to resolve current user")

    user_id = (
        current_user.get("email")
        or current_user.get("sub")
        or current_user.get("username")
        or possible_user_ids[0]
    )

    db_message = DiscussionMessageDB(
        case_id=case_id,
        user_id=user_id,
        content=payload.content.strip(),
    )

    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)

    return _to_message_response(db_message)


@router.put("/{message_id}", response_model=DiscussionMessage)
async def update_message(
    message_id: str,
    payload: DiscussionMessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_override),
):
    result = await db.execute(
        select(DiscussionMessageDB).where(DiscussionMessageDB.id == message_id)
    )
    db_message = result.scalar_one_or_none()

    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")

    db_case = await _get_case_or_404(db, db_message.case_id)

    if not can_access_case(current_user, db_case):
        raise HTTPException(status_code=403, detail="Access denied")

    role = _user_role(current_user)
    identities = _user_identities(current_user)

    if role != "admin" and db_message.user_id.strip().lower() not in identities:
        raise HTTPException(status_code=403, detail="You can only edit your own messages")

    db_message.content = payload.content.strip()

    await db.commit()
    await db.refresh(db_message)

    return _to_message_response(db_message)


@router.delete("/{message_id}")
async def delete_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user_override),
):
    result = await db.execute(
        select(DiscussionMessageDB).where(DiscussionMessageDB.id == message_id)
    )
    db_message = result.scalar_one_or_none()

    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")

    db_case = await _get_case_or_404(db, db_message.case_id)

    if not can_access_case(current_user, db_case):
        raise HTTPException(status_code=403, detail="Access denied")

    role = _user_role(current_user)
    identities = _user_identities(current_user)

    if role != "admin" and db_message.user_id.strip().lower() not in identities:
        raise HTTPException(status_code=403, detail="You can only delete your own messages")

    await db.delete(db_message)
    await db.commit()

    return {"detail": "Message deleted", "id": message_id}


from pydantic import BaseModel

class ExternalDiscussionCreate(BaseModel):
    author: str
    message: str


@router.post("/external/case/{case_id}")
async def create_external_discussion(
    case_id: str,
    payload: ExternalDiscussionCreate,
    db: AsyncSession = Depends(get_db),
):
    discussion = DiscussionMessageDB(
        case_id=case_id,
        author_name=payload.author,
        message=payload.message,
    )

    db.add(discussion)

    await db.commit()
    await db.refresh(discussion)

    return {
        "id": str(discussion.id),
        "status": "created",
    }


@router.get("/external/case/{case_id}")
async def get_external_discussion(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DiscussionMessageDB)
        .where(DiscussionMessageDB.case_id == case_id)
        .order_by(DiscussionMessageDB.created_at.asc())
    )

    messages = result.scalars().all()

    return [
        {
            "id": str(msg.id),
            "case_id": msg.case_id,
            "author": msg.author_name,
            "role": msg.author_role,
            "message": msg.message,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]