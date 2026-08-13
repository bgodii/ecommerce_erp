from pydantic import BaseModel, Field


class ProductIn(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    nome: str = Field(min_length=1, max_length=160)
    variacao: str | None = Field(default=None, max_length=120)
    dropdown_name: str | None = Field(default=None, max_length=200)
    ativo: bool = True


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=80)
    nome: str | None = Field(default=None, max_length=160)
    variacao: str | None = Field(default=None, max_length=120)
    dropdown_name: str | None = Field(default=None, max_length=200)
    ativo: bool | None = None
