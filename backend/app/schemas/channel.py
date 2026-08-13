from pydantic import BaseModel, Field


class ChannelIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    taxa_pct: float = Field(default=0.0, ge=0, le=1)
    taxa_fixa: float = Field(default=0.0, ge=0)
    taxa_afiliado_pct: float = Field(default=0.0, ge=0, le=1)
    ativo: bool = True


class ChannelUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    taxa_pct: float | None = Field(default=None, ge=0, le=1)
    taxa_fixa: float | None = Field(default=None, ge=0)
    taxa_afiliado_pct: float | None = Field(default=None, ge=0, le=1)
    ativo: bool | None = None
