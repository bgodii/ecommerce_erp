from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import ACCESS, decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Credenciais inválidas",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    session: SessionDep,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise _credentials_error
    try:
        payload = decode_token(token)
    except Exception:
        raise _credentials_error
    if payload.get("type") != ACCESS:
        raise _credentials_error
    user_id = payload.get("sub")
    if user_id is None:
        raise _credentials_error
    user = await session.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_owner(user: CurrentUser) -> User:
    if user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o dono da loja pode fazer isso",
        )
    return user


OwnerUser = Annotated[User, Depends(require_owner)]
