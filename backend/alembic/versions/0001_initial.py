"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="owner"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "org_settings",
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("taxa_shopee_pct", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("taxa_fixa", sa.Float(), nullable=False, server_default="4"),
        sa.Column("taxa_afiliado_pct", sa.Float(), nullable=False, server_default="0"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("variacao", sa.String(120), nullable=True),
        sa.Column("dropdown_name", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.UniqueConstraint("organization_id", "sku", name="uq_product_org_sku"),
    )
    op.create_index("ix_products_organization_id", "products", ["organization_id"])

    op.create_table(
        "stock_lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lote_code", sa.String(40), nullable=True),
        sa.Column("data_entrada", sa.Date(), nullable=False),
        sa.Column("qty_in", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    )
    op.create_index("ix_stock_lots_organization_id", "stock_lots", ["organization_id"])
    op.create_index("ix_stock_lots_product_id", "stock_lots", ["product_id"])

    op.create_table(
        "kits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preco_referencia", sa.Float(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.UniqueConstraint("organization_id", "sku", name="uq_kit_org_sku"),
    )
    op.create_index("ix_kits_organization_id", "kits", ["organization_id"])

    op.create_table(
        "kit_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "kit_id", sa.Integer(), sa.ForeignKey("kits.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_kit_components_kit_id", "kit_components", ["kit_id"])
    op.create_index("ix_kit_components_product_id", "kit_components", ["product_id"])

    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("data_venda", sa.Date(), nullable=False),
        sa.Column("pedido", sa.String(60), nullable=True),
        sa.Column("item_type", sa.String(10), nullable=False),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "kit_id", sa.Integer(), sa.ForeignKey("kits.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("preco_unitario", sa.Float(), nullable=False),
        sa.Column("taxa_shopee_pct", sa.Float(), nullable=False),
        sa.Column("taxa_fixa", sa.Float(), nullable=False),
        sa.Column("taxa_afiliado_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("outras_taxas", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    )
    op.create_index("ix_sales_organization_id", "sales", ["organization_id"])
    op.create_index("ix_sales_product_id", "sales", ["product_id"])
    op.create_index("ix_sales_kit_id", "sales", ["kit_id"])

    op.create_table(
        "ad_spends",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("canal", sa.String(120), nullable=True),
        sa.Column("valor", sa.Float(), nullable=False, server_default="0"),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
    )
    op.create_index("ix_ad_spends_organization_id", "ad_spends", ["organization_id"])


def downgrade() -> None:
    op.drop_table("ad_spends")
    op.drop_table("sales")
    op.drop_table("kit_components")
    op.drop_table("kits")
    op.drop_table("stock_lots")
    op.drop_table("products")
    op.drop_table("org_settings")
    op.drop_table("users")
    op.drop_table("organizations")
