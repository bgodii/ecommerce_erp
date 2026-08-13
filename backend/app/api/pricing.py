from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.schemas.pricing import PricingIn
from app.services import pricing
from app.services.orgsettings import get_or_create_settings

router = APIRouter(prefix="/pricing", tags=["precificacao"])


@router.post("/simulate")
async def simulate(data: PricingIn, user: CurrentUser, session: SessionDep):
    """Precificação com custo unitário informado manualmente.

    As taxas Shopee/fixa vêm das Configurações da loja; afiliado e outros custos são do formulário.
    """
    settings = await get_or_create_settings(session, user.organization_id)
    await session.commit()

    result = pricing.simulate(
        custo_unitario=data.custo_unitario,
        qty=data.qty,
        modo=data.modo,
        taxa_shopee_pct=settings.taxa_shopee_pct,
        taxa_fixa=settings.taxa_fixa,
        taxa_afiliado_pct=data.taxa_afiliado_pct,
        outros_custos=data.outros_custos,
        lucro_desejado=data.lucro_desejado,
        preco_informado=data.preco_informado,
    )
    return {**result, "custo_unitario": data.custo_unitario}
