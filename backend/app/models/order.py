from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Status normalizado dos pedidos importados (qualquer canal).
ORDER_STATUSES = (
    "nao_pago",
    "a_enviar",
    "enviado",
    "entregue",
    "concluido",
    "cancelado",
    "devolucao",
)


class Order(Base, TimestampMixin):
    """Pedido importado do marketplace (ex.: export Order.all da Shopee).

    Guarda o financeiro REAL por pedido (taxas efetivamente cobradas) e o status,
    que alimenta a visão de caixa (recebido × a receber). Sem PII do comprador.
    """

    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "channel_id", "order_sn", name="uq_order_org_channel_sn"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("channels.id", ondelete="SET NULL"), index=True, nullable=True
    )
    order_sn: Mapped[str] = mapped_column(String(60), nullable=False)

    status_raw: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)

    created_at_channel: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Financeiro do pedido (soma dos itens; zerado em cancelados)
    valor_bruto: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    desconto_vendedor: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    taxa_comissao: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    taxa_servico: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    taxa_transacao: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # "Total global" do export (payout estimado do canal)
    valor_liquido: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(Base):
    """Item de um pedido importado. product_id/kit_id são resolvidos via sku_mappings."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku_main: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sku_var: Mapped[str | None] = mapped_column(String(120), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    variation_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kit_id: Mapped[int | None] = mapped_column(
        ForeignKey("kits.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # 'auto' (heurística), 'manual' (via tela de vínculo) ou 'pendente'
    mapping_status: Mapped[str] = mapped_column(String(10), default="pendente", nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
