from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.services.insights import build_overview

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
