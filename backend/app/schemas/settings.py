from pydantic import BaseModel, Field


class SettingsOut(BaseModel):
    taxa_shopee_pct: float
    taxa_fixa: float
    taxa_afiliado_pct: float

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    taxa_shopee_pct: float | None = Field(default=None, ge=0, le=1)
    taxa_fixa: float | None = Field(default=None, ge=0)
    taxa_afiliado_pct: float | None = Field(default=None, ge=0, le=1)
