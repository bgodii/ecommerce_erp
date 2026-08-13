from pydantic import BaseModel, Field, model_validator


class PricingIn(BaseModel):
    custo_unitario: float = Field(ge=0)
    qty: int = Field(default=1, gt=0)
    modo: str = "lucro"  # 'lucro' | 'preco'
    taxa_afiliado_pct: float = Field(default=0.0, ge=0)
    outros_custos: float = Field(default=0.0, ge=0)
    lucro_desejado: float | None = None
    preco_informado: float | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.modo not in ("lucro", "preco"):
            raise ValueError("modo deve ser 'lucro' ou 'preco'")
        return self
