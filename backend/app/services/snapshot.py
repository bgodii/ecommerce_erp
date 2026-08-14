"""Snapshot em memória de uma loja — dataclasses puras.

O motor de cálculo (engine.py) opera exclusivamente sobre estas estruturas, sem
tocar no banco. A camada de API converte linhas ORM -> snapshot e chama o engine.
Isso mantém as regras de negócio puras, determinísticas e testáveis (testes golden
comparam contra os valores da própria planilha).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class SProduct:
    id: int
    sku: str
    nome: str
    dropdown_name: str
    variacao: str | None = None
    ativo: bool = True


@dataclass
class SLot:
    id: int
    product_id: int
    data_entrada: date
    qty_in: int
    unit_cost: float
    lote_code: str | None = None


@dataclass
class SKitComponent:
    product_id: int
    qty: int


@dataclass
class SKit:
    id: int
    sku: str
    nome: str
    components: list[SKitComponent] = field(default_factory=list)
    ativo: bool = True
    preco_referencia: float | None = None


@dataclass
class SSale:
    id: int
    data_venda: date
    item_type: str  # 'product' | 'kit'
    qty: int
    preco_unitario: float
    taxa_shopee_pct: float
    taxa_fixa: float
    taxa_afiliado_pct: float = 0.0
    outras_taxas: float = 0.0
    product_id: int | None = None
    kit_id: int | None = None
    pedido: str | None = None
    channel_id: int | None = None
    channel_name: str | None = None
    # 'manual' (lançada na tela) ou 'importado' (veio de um pedido do marketplace)
    origem: str = "manual"
    status: str | None = None


@dataclass
class SAd:
    id: int
    data: date
    valor: float
    canal: str | None = None


@dataclass
class Snapshot:
    products: list[SProduct] = field(default_factory=list)
    lots: list[SLot] = field(default_factory=list)
    kits: list[SKit] = field(default_factory=list)
    sales: list[SSale] = field(default_factory=list)
    ads: list[SAd] = field(default_factory=list)
