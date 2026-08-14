from datetime import date

from pydantic import BaseModel, Field


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=160)
    variacao: str | None = Field(default=None, max_length=120)
    dropdown_name: str | None = Field(default=None, max_length=200)
    ativo: bool = True


class StockAdjustIn(BaseModel):
    """Acerto de estoque: informe quanto você TEM hoje e quanto pagou por unidade."""

    estoque_atual: int = Field(ge=0)
    custo_unitario: float = Field(gt=0)
    data_entrada: date | None = None


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=80)
    nome: str | None = Field(default=None, max_length=160)
    variacao: str | None = Field(default=None, max_length=120)
    dropdown_name: str | None = Field(default=None, max_length=200)
    ativo: bool | None = None
