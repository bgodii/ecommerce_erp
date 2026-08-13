from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, SessionDep
from app.models.channel import Channel
from app.schemas.channel import ChannelIn, ChannelUpdate

router = APIRouter(prefix="/channels", tags=["canais"])


def _out(c: Channel) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "taxa_pct": c.taxa_pct,
        "taxa_fixa": c.taxa_fixa,
        "taxa_afiliado_pct": c.taxa_afiliado_pct,
        "ativo": c.ativo,
    }


async def _get_owned(session, org_id: int, channel_id: int) -> Channel:
    c = await session.get(Channel, channel_id)
    if c is None or c.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Canal não encontrado")
    return c


@router.get("")
async def list_channels(user: CurrentUser, session: SessionDep):
    res = await session.execute(
        select(Channel).where(Channel.organization_id == user.organization_id).order_by(Channel.id)
    )
    return [_out(c) for c in res.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_channel(data: ChannelIn, user: CurrentUser, session: SessionDep):
    c = Channel(organization_id=user.organization_id, **data.model_dump())
    session.add(c)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um canal com esse nome")
    await session.refresh(c)
    return _out(c)


@router.patch("/{channel_id}")
async def update_channel(
    channel_id: int, data: ChannelUpdate, user: CurrentUser, session: SessionDep
):
    c = await _get_owned(session, user.organization_id, channel_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um canal com esse nome")
    await session.refresh(c)
    return _out(c)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(channel_id: int, user: CurrentUser, session: SessionDep):
    c = await _get_owned(session, user.organization_id, channel_id)
    # vendas ficam com channel_id nulo (ON DELETE SET NULL)
    await session.delete(c)
    await session.commit()
