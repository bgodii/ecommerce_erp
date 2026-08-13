from datetime import date

from pydantic import BaseModel, Field


class StockLotIn(BaseModel):
    product_id: int
    data_entrada: date
    qty_in: int = Field(gt=0)
    unit_cost: float = Field(ge=0)
    lote_code: str | None = Field(default=None, max_length=40)


class StockLotUpdate(BaseModel):
    data_entrada: date | None = None
    qty_in: int | None = Field(default=None, gt=0)
    unit_cost: float | None = Field(default=None, ge=0)
    lote_code: str | None = Field(default=None, max_length=40)
