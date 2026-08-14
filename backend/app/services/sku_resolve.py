"""Resolução de SKU do marketplace → produto/kit do ERP.

Ordem de resolução por item importado:
1. `sku_mappings` (vínculos salvos — manuais ou automáticos anteriores)
2. Heurísticas: SKU exato do produto/kit; nomes normalizados (dropdown/nome)
3. Sem match → 'pendente' (aparece na tela Vincular SKUs)

Sempre que uma heurística acerta, um mapping 'auto' é salvo para estabilidade.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kit import Kit
from app.models.product import Product
from app.models.sku_mapping import SkuMapping
from app.services.shopee_import import norm_key

# Sufixos de tamanho a remover para AGREGAR por cor/modelo (decisão do usuário):
# 'Blusa-Branco-M' -> 'Blusa-Branco' ; 'Azul Marinho e Marrom, G' -> 'Azul Marinho e Marrom'
_SIZE_TOKEN = r"(PP|P|M|G|GG|XG|XGG|XXG|\d{2})"
_RE_VESTE = re.compile(r"\s*-?\s*veste\b.*$", re.IGNORECASE)
_RE_SIZE_SUFFIX = re.compile(rf"\s*[,\-/]\s*{_SIZE_TOKEN}\s*$", re.IGNORECASE)


def strip_size(name: str | None) -> str:
    """Remove marcações de tamanho do fim do nome/SKU da variação."""
    s = " ".join(str(name or "").split()).strip()
    s = _RE_VESTE.sub("", s).strip()
    prev = None
    while prev != s:  # remove sufixos encadeados (ex.: ',M' depois de tirar o 'Veste 38/40')
        prev = s
        s = _RE_SIZE_SUFFIX.sub("", s).strip().rstrip(",-/").strip()
    return s


def _slug(s: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return out[:70] or "produto"


def auto_product_identity(item: dict) -> tuple[str, str]:
    """(sku, nome) do produto a auto-criar a partir de um item do marketplace.

    Agrega por cor/modelo: variações que só diferem no tamanho geram a MESMA identidade.
    """
    if item.get("sku_var"):
        base = strip_size(item["sku_var"])
        return _slug(base), base
    variacao = strip_size(item.get("variation_name"))
    prod = " ".join(str(item.get("product_name") or "").split()[:4])
    nome = f"{prod} — {variacao}" if variacao else (prod or "Produto importado")
    return _slug(f"{prod}-{variacao}"), nome


@dataclass
class Resolution:
    product_id: int | None = None
    kit_id: int | None = None
    status: str = "pendente"  # 'auto' | 'manual' | 'pendente'


def item_match_key(item: dict) -> str:
    """Chave canônica do item: sku_var se existir, senão nome+variação."""
    if item.get("sku_var"):
        return norm_key(item["sku_var"])
    return norm_key(item.get("product_name"), item.get("variation_name"))


class SkuResolver:
    """Carrega o contexto da org uma vez e resolve N itens em memória."""

    def __init__(self, mappings: dict[str, SkuMapping], products: list[Product], kits: list[Kit]):
        self._mappings = mappings
        self._by_product_sku = {norm_key(p.sku): p for p in products}
        self._by_product_name = {}
        for p in products:
            self._by_product_name.setdefault(norm_key(p.dropdown_name), p)
            self._by_product_name.setdefault(norm_key(p.nome), p)
        self._by_kit_sku = {norm_key(k.sku): k for k in kits}
        self._by_kit_name = {norm_key(k.nome): k for k in kits}
        self.new_mappings: list[SkuMapping] = []

    @classmethod
    async def load(cls, session: AsyncSession, org_id: int, channel_id: int | None) -> "SkuResolver":
        mappings = {
            m.match_key: m
            for m in (
                await session.execute(
                    select(SkuMapping).where(
                        SkuMapping.organization_id == org_id,
                        SkuMapping.channel_id == channel_id,
                    )
                )
            ).scalars()
        }
        products = (
            (await session.execute(select(Product).where(Product.organization_id == org_id)))
            .scalars()
            .all()
        )
        kits = (
            (await session.execute(select(Kit).where(Kit.organization_id == org_id))).scalars().all()
        )
        return cls(mappings, list(products), list(kits))

    def resolve(self, item: dict, org_id: int, channel_id: int | None) -> Resolution:
        key = item_match_key(item)
        if not key:
            return Resolution()

        m = self._mappings.get(key)
        if m is not None:
            return Resolution(product_id=m.product_id, kit_id=m.kit_id, status="manual")

        # Heurísticas (nesta ordem de confiança)
        candidates = [
            norm_key(item.get("sku_var")),
            norm_key(item.get("sku_main")),
            norm_key(item.get("variation_name")),
            norm_key(item.get("product_name")),
        ]
        hit_product = hit_kit = None
        for c in candidates:
            if not c:
                continue
            if c in self._by_product_sku:
                hit_product = self._by_product_sku[c]
                break
            if c in self._by_kit_sku:
                hit_kit = self._by_kit_sku[c]
                break
            if c in self._by_product_name:
                hit_product = self._by_product_name[c]
                break
            if c in self._by_kit_name:
                hit_kit = self._by_kit_name[c]
                break

        if hit_product is None and hit_kit is None:
            return Resolution()

        # registra mapping automático (persistido pelo chamador via new_mappings)
        mapping = SkuMapping(
            organization_id=org_id,
            channel_id=channel_id,
            match_key=key,
            product_id=hit_product.id if hit_product else None,
            kit_id=hit_kit.id if hit_kit else None,
        )
        self._mappings[key] = mapping
        self.new_mappings.append(mapping)
        return Resolution(
            product_id=hit_product.id if hit_product else None,
            kit_id=hit_kit.id if hit_kit else None,
            status="auto",
        )

    def register_product(self, product: Product, item: dict, org_id: int, channel_id: int | None) -> None:
        """Registra um produto auto-criado nos caches e cria o mapping do item."""
        self._by_product_sku[norm_key(product.sku)] = product
        self._by_product_name.setdefault(norm_key(product.dropdown_name), product)
        key = item_match_key(item)
        if key and key not in self._mappings:
            mapping = SkuMapping(
                organization_id=org_id, channel_id=channel_id, match_key=key, product_id=product.id
            )
            self._mappings[key] = mapping
            self.new_mappings.append(mapping)

    def find_product_by_sku(self, sku: str) -> Product | None:
        return self._by_product_sku.get(norm_key(sku))
