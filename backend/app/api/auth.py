from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, OwnerUser, SessionDep
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.channel import Channel
from app.models.organization import Organization
from app.models.settings import OrgSettings
from app.models.user import User
from app.schemas.auth import (
    InviteIn,
    LoginIn,
    PasswordResetIn,
    RefreshIn,
    RegisterIn,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _email_exists(session, email: str) -> bool:
    res = await session.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none() is not None


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, session: SessionDep):
    if await _email_exists(session, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")

    org = Organization(name=data.org_name or f"Loja de {data.name}")
    session.add(org)
    await session.flush()

    user = User(
        organization_id=org.id,
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        role="owner",
    )
    session.add(user)
    session.add(OrgSettings(organization_id=org.id))
    # canal padrão "Shopee" com as taxas default da loja
    session.add(
        Channel(organization_id=org.id, name="Shopee", taxa_pct=0.20, taxa_fixa=4.0, ativo=True)
    )
    await session.flush()
    await session.commit()

    return TokenOut(
        access_token=create_access_token(user.id, org.id),
        refresh_token=create_refresh_token(user.id, org.id),
    )


@router.post("/login", response_model=TokenOut)
async def login(data: LoginIn, session: SessionDep):
    res = await session.execute(select(User).where(User.email == data.email))
    user = res.scalar_one_or_none()
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha inválidos")
    return TokenOut(
        access_token=create_access_token(user.id, user.organization_id),
        refresh_token=create_refresh_token(user.id, user.organization_id),
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn, session: SessionDep):
    try:
        payload = decode_token(data.refresh_token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    if payload.get("type") != REFRESH:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    user = await session.get(User, int(payload.get("sub", 0)))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    return TokenOut(
        access_token=create_access_token(user.id, user.organization_id),
        refresh_token=create_refresh_token(user.id, user.organization_id),
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(user: CurrentUser, session: SessionDep):
    res = await session.execute(
        select(User).where(User.organization_id == user.organization_id).order_by(User.id)
    )
    return list(res.scalars().all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def invite_user(data: InviteIn, owner: OwnerUser, session: SessionDep):
    if await _email_exists(session, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail já cadastrado")
    role = "owner" if data.role == "owner" else "member"
    user = User(
        organization_id=owner.organization_id,
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _get_org_user(session, owner: User, user_id: int) -> User:
    target = await session.get(User, user_id)
    if target is None or target.organization_id != owner.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado")
    return target


@router.patch("/users/{user_id}/password", response_model=UserOut)
async def reset_user_password(
    user_id: int, data: PasswordResetIn, owner: OwnerUser, session: SessionDep
):
    """Owner define uma nova senha para um usuário da própria loja (inclui a si mesmo)."""
    target = await _get_org_user(session, owner, user_id)
    target.password_hash = hash_password(data.password)
    await session.commit()
    await session.refresh(target)
    return target


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, owner: OwnerUser, session: SessionDep):
    target = await _get_org_user(session, owner, user_id)
    if target.id == owner.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Você não pode excluir a própria conta")
    if target.role == "owner":
        owners = await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.organization_id == owner.organization_id, User.role == "owner")
        )
        if (owners or 0) <= 1:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Não é possível excluir o único dono da loja"
            )
    await session.delete(target)
    await session.commit()
