from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import hash_token
from app.models import User, UserSession


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    token = request.cookies.get("rohobot_session")
    if not token:
        raise HTTPException(status_code=401, detail="Sign-in is required.")

    session = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(token),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
    )
    user = db.get(User, session.user_id) if session else None
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return user


def require_role(*roles: str):
    def role_dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You are not allowed to perform this action.")
        return user

    return role_dependency
