from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Utm(BaseModel):
    source: str = ""
    medium: str = ""
    campaign: str = ""
    content: str = ""
    term: str = ""


class DraftItem(BaseModel):
    sku: str
    offer_id: str


class DraftOrderIn(BaseModel):
    customer_name: str
    phone: str
    items: list[DraftItem]
    landing_page: str = ""
    event_source_url: str = ""
    user_agent: str = ""
    fbp: str = ""
    fbc: str = ""
    ttclid: str = ""
    ttp: str = ""
    sccid: str = ""
    event_id_initiate: str = ""
    utm: Utm = Field(default_factory=Utm)


class FinalizeIn(BaseModel):
    accept_upsell: bool = False
    event_id_purchase: str


class TrackUser(BaseModel):
    fbp: str = ""
    fbc: str = ""
    ttclid: str = ""
    ttp: str = ""
    sccid: str = ""
    phone: str = ""
    name: str = ""


class TrackContent(BaseModel):
    id: str
    quantity: int = 1
    item_price: float = 0


class TrackIn(BaseModel):
    event_name: str
    event_id: str
    event_source_url: str = ""
    value: Optional[float] = None
    currency: str = "SAR"
    contents: list[TrackContent] = Field(default_factory=list)
    user: TrackUser = Field(default_factory=TrackUser)


class LeadIn(BaseModel):
    name: str
    phone: str
    message: str


class EmailLeadIn(BaseModel):
    name: str
    email: str
    message: str
