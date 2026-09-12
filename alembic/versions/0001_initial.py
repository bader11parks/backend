"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("sku", sa.String(32), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name_ar", sa.String(255), nullable=False),
        sa.Column("ritual_slot", sa.String(64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("customer_name", sa.String(80), nullable=False),
        sa.Column("phone_e164", sa.String(20), nullable=False),
        sa.Column("phone_national", sa.String(16), nullable=False),
        sa.Column("total_halalas", sa.Integer(), nullable=False),
        sa.Column("shipping_halalas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("upsell_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("upsell_sku", sa.String(32), nullable=True),
        sa.Column("suggested_upsell_sku", sa.String(32), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="SAR"),
        sa.Column("payment", sa.String(16), nullable=False, server_default="cod"),
        sa.Column("landing_page", sa.Text(), nullable=True),
        sa.Column("event_id_purchase", sa.String(64), nullable=True, unique=True),
        sa.Column("event_id_initiate", sa.String(64), nullable=True),
        sa.Column("purchase_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sheet_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fbp", sa.Text(), nullable=True),
        sa.Column("fbc", sa.Text(), nullable=True),
        sa.Column("ttclid", sa.Text(), nullable=True),
        sa.Column("ttp", sa.Text(), nullable=True),
        sa.Column("sccid", sa.Text(), nullable=True),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_medium", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("utm_content", sa.String(255), nullable=True),
        sa.Column("utm_term", sa.String(255), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_orders_phone_e164", "orders", ["phone_e164"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.String(32), nullable=False),
        sa.Column("offer_id", sa.String(16), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_halalas", sa.Integer(), nullable=False),
        sa.Column("line_halalas", sa.Integer(), nullable=False),
        sa.Column("name_ar", sa.String(255), nullable=False),
    )
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("leads")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("products")
