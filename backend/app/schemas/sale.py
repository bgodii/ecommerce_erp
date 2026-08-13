from datetime import date

from pydantic import BaseModel, Field, model_validator


class SaleIn(BaseModel):
    data_venda: date
    pedido: str | None = Field(default=None, max_length=60)
    item_type: str  # 'product' | 'kit'
    product_id: int | None = None
    kit_id: int | None = None
    channel_id: int | None = None
    qty: int = Field(gt=0)
    preco_unitario: float = Field(ge=0)
    # Taxas: se omitidas, o backend usa as configurações da loja.
    taxa_shopee_pct: float | None = Field(default=None, ge=0)
    taxa_fixa: float | None = Field(default=None, ge=0)
    taxa_afiliado_pct: float | None = Field(default=None, ge=0)
    outras_taxas: float | None = Field(default=None, ge=0)
    # Permite lançar mesmo sem saldo (ERP-002); default bloqueia.
    permitir_sem_estoque: bool = False

    @model_validator(mode="after")
    def _check_item(self):
        if self.item_type not in ("product", "kit"):
            raise ValueError("item_type deve ser 'product' ou 'kit'")
        if self.item_type == "product" and not self.product_id:
            raise ValueError("product_id é obrigatório para item_type='product'")
        if self.item_type == "kit" and not self.kit_id:
            raise ValueError("kit_id é obrigatório para item_type='kit'")
        return self


class SaleUpdate(BaseModel):
    data_venda: date | None = None
    pedido: str | None = Field(default=None, max_length=60)
    qty: int | None = Field(default=None, gt=0)
    preco_unitario: float | None = Field(default=None, ge=0)
    taxa_shopee_pct: float | None = Field(default=None, ge=0)
    taxa_fixa: float | None = Field(default=None, ge=0)
    taxa_afiliado_pct: float | None = Field(default=None, ge=0)
    outras_taxas: float | None = Field(default=None, ge=0)
