from datetime import date

from pydantic import BaseModel, Field


class AdSpendIn(BaseModel):
    data: date
    canal: str | None = Field(default=None, max_length=120)
    valor: float = Field(ge=0)
    observacao: str | None = None


class AdSpendUpdate(BaseModel):
    data: date | None = None
    canal: str | None = Field(default=None, max_length=120)
    valor: float | None = Field(default=None, ge=0)
    observacao: str | None = None
