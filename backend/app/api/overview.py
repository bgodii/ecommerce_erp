from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.services.insights import build_overview, roas_marginal

router = APIRouter(prefix="/reports", tags=["visao-geral"])


@router.get("/visao-geral")
async def visao_geral(
    user: CurrentUser,
    session: SessionDep,
    dt_from: date | None = Query(default=None, alias="from"),
    dt_to: date | None = Query(default=None, alias="to"),
):
    """Visão geral da loja (home): KPIs, caixa, custos, insights, tops e vereditos de ADS.

    Sem parâmetros, usa os últimos 30 dias.
    """
    if dt_to is None:
        dt_to = date.today()
    if dt_from is None:
        dt_from = dt_to - timedelta(days=29)
    return await build_overview(session, user.organization_id, dt_from, dt_to)


@router.get("/roas-marginal")
async def roas_marginal_endpoint(
    user: CurrentUser,
    session: SessionDep,
    dias: int = Query(default=7, ge=1, le=90),
    ate: date | None = Query(default=None),
):
    """Compara os últimos N dias com os N anteriores: o ROAS marginal diz se o aumento
    de investimento ainda vale a pena (deve ficar acima do ROAS even)."""
    return await roas_marginal(session, user.organization_id, dias, ate)
