"""pedidos importados, listings, ad_stats e sku_mappings

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("order_sn", sa.String(60), nullable=False),
        sa.Column("status_raw", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at_channel", sa.DateTime(), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("valor_bruto", sa.Float(), nullable=False, server_default="0"),
        sa.Column("desconto_vendedor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("taxa_comissao", sa.Float(), nullable=False, server_default="0"),
        sa.Column("taxa_servico", sa.Float(), nullable=False, server_default="0"),
        sa.Column("taxa_transacao", sa.Float(), nullable=False, server_default="0"),
        sa.Column("valor_liquido", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_file", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.UniqueConstraint("organization_id", "channel_id", "order_sn", name="uq_order_org_channel_sn"),
    )
    op.create_index("ix_orders_organization_id", "orders", ["organization_id"])
    op.create_index("ix_orders_channel_id", "orders", ["channel_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("sku_main", sa.String(120), nullable=True),
        sa.Column("sku_var", sa.String(120), nullable=True),
        sa.Column("product_name", sa.String(300), nullable=True),
        sa.Column("variation_name", sa.String(200), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("kit_id", sa.Integer(), sa.ForeignKey("kits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mapping_status", sa.String(10), nullable=False, server_default="pendente"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"])
    op.create_index("ix_order_items_kit_id", "order_items", ["kit_id"])

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("listing_id", sa.String(40), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column(
            "product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("kit_id", sa.Integer(), sa.ForeignKey("kits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.UniqueConstraint("organization_id", "channel_id", "listing_id", name="uq_listing_org_channel"),
    )
    op.create_index("ix_listings_organization_id", "listings", ["organization_id"])

    op.create_table(
        "ad_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("report_type", sa.String(12), nullable=False),
        sa.Column("listing_ref", sa.String(40), nullable=False, server_default="-"),
        sa.Column("detail_key", sa.String(200), nullable=False, server_default="-"),
        sa.Column("ad_name", sa.String(300), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_sold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gmv", sa.Float(), nullable=False, server_default="0"),
        sa.Column("spend", sa.Float(), nullable=False, server_default="0"),
        sa.Column("roas", sa.Float(), nullable=False, server_default="0"),
        sa.Column("acos", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source_file", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "channel_id",
            "report_type",
            "listing_ref",
            "detail_key",
            "period_start",
            "period_end",
            name="uq_adstat_scope",
        ),
    )
    op.create_index("ix_ad_stats_organization_id", "ad_stats", ["organization_id"])

    op.create_table(
        "sku_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_id", sa.Integer(), sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("match_key", sa.String(400), nullable=False),
        sa.Column(
            "product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("kit_id", sa.Integer(), sa.ForeignKey("kits.id", ondelete="CASCADE"), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.UniqueConstraint("organization_id", "channel_id", "match_key", name="uq_mapping_key"),
    )
    op.create_index("ix_sku_mappings_organization_id", "sku_mappings", ["organization_id"])


def downgrade() -> None:
    op.drop_table("sku_mappings")
    op.drop_table("ad_stats")
    op.drop_table("listings")
    op.drop_table("order_items")
    op.drop_table("orders")
