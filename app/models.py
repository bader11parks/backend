from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Product(Base):
    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(32), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    ritual_slot: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="draft")
    customer_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    phone_national: Mapped[str] = mapped_column(String(16), nullable=False)
    total_halalas: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping_halalas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    upsell_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    upsell_sku: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    suggested_upsell_sku: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="SAR")
    payment: Mapped[str] = mapped_column(String(16), nullable=False, default="cod")
    landing_page: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_id_purchase: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    event_id_initiate: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    purchase_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sheet_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    fbp: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fbc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ttclid: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ttp: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sccid: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String(32), nullable=False)
    offer_id: Mapped[str] = mapped_column(String(16), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_halalas: Mapped[int] = mapped_column(Integer, nullable=False)
    line_halalas: Mapped[int] = mapped_column(Integer, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EmailLead(Base):
    __tablename__ = "email_leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
