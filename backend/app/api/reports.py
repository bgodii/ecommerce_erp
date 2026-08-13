from datetime import date

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, SessionDep
from app.services import engine
from app.services.loader import load_snapshot

router = APIRouter(prefix="/reports", tags=["relatorios"])


@router.get("/dashboard")
async def dashboard(user: CurrentUser, session: SessionDep):
    snap = await load_snapshot(session, user.organization_id)
    return engine.dashboard(snap)


@router.get("/balanco-diario")
async def balanco_diario(
    user: CurrentUser,
    session: SessionDep,
    dt_from: date | None = Query(default=None, alias="from"),
    dt_to: date | None = Query(default=None, alias="to"),
):
    snap = await load_snapshot(session, user.organization_id)
    return engine.balanco_diario(snap, dt_from, dt_to)


@router.get("/estoque-diario")
async def estoque_diario(
    user: CurrentUser,
    session: SessionDep,
    data: date = Query(..., description="Data analisada (YYYY-MM-DD)"),
):
    snap = await load_snapshot(session, user.organization_id)
    return engine.estoque_diario(snap, data)


@router.get("/estoque-diario-range")
async def estoque_diario_range(
    user: CurrentUser,
    session: SessionDep,
    dt_from: date | None = Query(default=None, alias="from"),
    dt_to: date | None = Query(default=None, alias="to"),
):
    snap = await load_snapshot(session, user.organization_id)
    return engine.estoque_diario_range(snap, dt_from, dt_to)
