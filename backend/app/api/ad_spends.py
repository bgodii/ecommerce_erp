from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep
from app.models.ad_spend import AdSpend
from app.schemas.ad_spend import AdSpendIn, AdSpendUpdate

router = APIRouter(prefix="/ad-spends", tags=["ads"])


def _out(a: AdSpend) -> dict:
    return {
        "id": a.id,
        "data": a.data,
        "canal": a.canal,
        "valor": a.valor,
        "observacao": a.observacao,
    }


async def _get_owned(session, org_id: int, ad_id: int) -> AdSpend:
    a = await session.get(AdSpend, ad_id)
    if a is None or a.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lançamento não encontrado")
    return a


@router.get("")
async def list_ads(user: CurrentUser, session: SessionDep):
    res = await session.execute(
        select(AdSpend)
        .where(AdSpend.organization_id == user.organization_id)
        .order_by(AdSpend.data.desc(), AdSpend.id.desc())
    )
    return [_out(a) for a in res.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ad(data: AdSpendIn, user: CurrentUser, session: SessionDep):
    a = AdSpend(organization_id=user.organization_id, **data.model_dump())
    session.add(a)
    await session.commit()
    await session.refresh(a)
    return _out(a)


@router.patch("/{ad_id}")
async def update_ad(ad_id: int, data: AdSpendUpdate, user: CurrentUser, session: SessionDep):
    a = await _get_owned(session, user.organization_id, ad_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(a, field, value)
    await session.commit()
    await session.refresh(a)
    return _out(a)


@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ad(ad_id: int, user: CurrentUser, session: SessionDep):
    a = await _get_owned(session, user.organization_id, ad_id)
    await session.delete(a)
    await session.commit()
