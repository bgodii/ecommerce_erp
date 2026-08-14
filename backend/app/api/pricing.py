from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep
from app.models.channel import Channel
from app.schemas.pricing import PricingIn
from app.services import pricing
from app.services.orgsettings import get_or_create_settings

router = APIRouter(prefix="/pricing", tags=["precificacao"])


@router.post("/simulate")
async def simulate(data: PricingIn, user: CurrentUser, session: SessionDep):
    """Precificação com custo unitário informado. As taxas Shopee/fixa vêm do e-commerce
    escolhido (ou do primeiro canal ativo); afiliado e outros custos são do formulário."""
    org_id = user.organization_id
    shopee_pct: float
    taxa_fixa: float
    channel_name: str | None = None

    if data.channel_id is not None:
        ch = await session.get(Channel, data.channel_id)
        if ch is None or ch.organization_id != org_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "E-commerce não encontrado")
        shopee_pct, taxa_fixa, channel_name = ch.taxa_pct, ch.taxa_fixa, ch.name
    else:
        ch = (
            await session.execute(
                select(Channel)
                .where(Channel.organization_id == org_id, Channel.ativo.is_(True))
                .order_by(Channel.id)
            )
        ).scalars().first()
        if ch is not None:
            shopee_pct, taxa_fixa, channel_name = ch.taxa_pct, ch.taxa_fixa, ch.name
        else:
            settings = await get_or_create_settings(session, org_id)
            await session.commit()
            shopee_pct, taxa_fixa = settings.taxa_shopee_pct, settings.taxa_fixa

    result = pricing.simulate(
        custo_unitario=data.custo_unitario,
        qty=data.qty,
        modo=data.modo,
        taxa_shopee_pct=shopee_pct,
        taxa_fixa=taxa_fixa,
        taxa_afiliado_pct=data.taxa_afiliado_pct,
        outros_custos=data.outros_custos,
        lucro_desejado=data.lucro_desejado,
        preco_informado=data.preco_informado,
    )
    return {**result, "custo_unitario": data.custo_unitario, "channel": channel_name}
