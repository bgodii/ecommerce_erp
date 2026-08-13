from pydantic import BaseModel, Field


class KitComponentIn(BaseModel):
    product_id: int
    qty: int = Field(default=1, gt=0)


class KitIn(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=200)
    ativo: bool = True
    preco_referencia: float | None = Field(default=None, ge=0)
    observacao: str | None = None
    components: list[KitComponentIn] = Field(default_factory=list)


class KitUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=80)
    nome: str | None = Field(default=None, max_length=200)
    ativo: bool | None = None
    preco_referencia: float | None = Field(default=None, ge=0)
    observacao: str | None = None
    components: list[KitComponentIn] | None = None
