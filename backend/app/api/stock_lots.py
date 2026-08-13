from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep
from app.models.product import Product
from app.models.stock_lot import StockLot
from app.schemas.stock_lot import StockLotIn, StockLotUpdate
from app.services import engine
from app.services.loader import load_snapshot

router = APIRouter(prefix="/stock-lots", tags=["entradas"])


def _status(consumed: int, qty_in: int) -> str:
    if consumed <= 0:
        return "Disponível"
    if consumed >= qty_in:
        return "Esgotado"
    return "Parcial"


def _out(lot: StockLot, lot_state: dict | None, product_name: str) -> dict:
    remaining = lot_state.get("remaining", lot.qty_in) if lot_state else lot.qty_in
    consumed = lot_state.get("consumed", 0) if lot_state else 0
    return {
        "id": lot.id,
        "product_id": lot.product_id,
        "produto": product_name,
        "lote_code": lot.lote_code,
        "data_entrada": lot.data_entrada,
        "qty_in": lot.qty_in,
        "unit_cost": lot.unit_cost,
        "custo_total": lot.qty_in * lot.unit_cost,
        "consumed": consumed,
        "remaining": remaining,
        "valor_saldo": remaining * lot.unit_cost,
        "status": _status(consumed, lot.qty_in),
    }


async def _get_owned(session, org_id: int, lot_id: int) -> StockLot:
    lot = await session.get(StockLot, lot_id)
    if lot is None or lot.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lote não encontrado")
    return lot


async def _product_names(session, org_id: int) -> dict[int, str]:
    res = await session.execute(select(Product).where(Product.organization_id == org_id))
    return {p.id: p.dropdown_name for p in res.scalars().all()}


def _lot_states(snap) -> dict[int, dict]:
    states: dict[int, dict] = {}
    for ps in engine.product_states(snap).values():
        for lot in ps["lots"]:
            states[lot["lot_id"]] = lot
    return states


@router.get("")
async def list_lots(user: CurrentUser, session: SessionDep):
    snap = await load_snapshot(session, user.organization_id)
    lot_states = _lot_states(snap)
    names = await _product_names(session, user.organization_id)
    res = await session.execute(
        select(StockLot)
        .where(StockLot.organization_id == user.organization_id)
        .order_by(StockLot.data_entrada, StockLot.id)
    )
    return [_out(lot, lot_states.get(lot.id), names.get(lot.product_id, "")) for lot in res.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_lot(data: StockLotIn, user: CurrentUser, session: SessionDep):
    product = await session.get(Product, data.product_id)
    if product is None or product.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto inválido")
    lot = StockLot(
        organization_id=user.organization_id,
        product_id=data.product_id,
        lote_code=data.lote_code,
        data_entrada=data.data_entrada,
        qty_in=data.qty_in,
        unit_cost=data.unit_cost,
    )
    session.add(lot)
    await session.commit()
    await session.refresh(lot)
    return _out(lot, None, product.dropdown_name)


@router.patch("/{lot_id}")
async def update_lot(lot_id: int, data: StockLotUpdate, user: CurrentUser, session: SessionDep):
    lot = await _get_owned(session, user.organization_id, lot_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lot, field, value)
    await session.commit()
    await session.refresh(lot)
    return _out(lot, None, "")


@router.delete("/{lot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lot(lot_id: int, user: CurrentUser, session: SessionDep):
    lot = await _get_owned(session, user.organization_id, lot_id)
    await session.delete(lot)
    await session.commit()
