from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    geo: str = Field(min_length=2, max_length=8, description="ISO country code, e.g. DE")
    offer_id: int
    domain_id: int
    group_id: int
    traffic_source_id: int


class StreamOfferOut(BaseModel):
    id: int
    offer_id: int
    offer_name: Optional[str] = None
    share: int
    pinned: bool
    status: str

    model_config = {"from_attributes": True}


class StreamOut(BaseModel):
    id: int
    keitaro_stream_id: int
    name: str
    stream_type: str
    has_offers: bool
    is_dirty: bool
    offers: List[StreamOfferOut] = []

    model_config = {"from_attributes": True}


class CampaignOut(BaseModel):
    id: int
    name: str
    geo: str
    keitaro_campaign_id: int
    offer_stream_id: int
    google_stream_id: int
    domain_id: int
    group_id: int
    traffic_source_id: int
    alias: str
    created_at: datetime
    streams: List[StreamOut] = []

    model_config = {"from_attributes": True}


class OfferAdd(BaseModel):
    offer_id: int


class OfferPin(BaseModel):
    pinned: bool
    share: Optional[int] = Field(default=None, ge=0, le=100)


class MetaItem(BaseModel):
    id: int
    name: str
