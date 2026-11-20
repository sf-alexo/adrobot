from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CampaignRecord(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    geo: Mapped[str] = mapped_column(String(8), nullable=False)
    keitaro_campaign_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    offer_stream_id: Mapped[int] = mapped_column(Integer, nullable=False)
    google_stream_id: Mapped[int] = mapped_column(Integer, nullable=False)
    domain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    group_id: Mapped[int] = mapped_column(Integer, nullable=False)
    traffic_source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    streams: Mapped[List["StreamRecord"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="StreamRecord.id",
    )


class StreamRecord(Base):
    __tablename__ = "streams"
    __table_args__ = (
        UniqueConstraint("campaign_id", "keitaro_stream_id", name="uq_campaign_keitaro_stream"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    keitaro_stream_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stream_type: Mapped[str] = mapped_column(String(32), nullable=False, default="regular")
    has_offers: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_dirty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    campaign: Mapped[CampaignRecord] = relationship(back_populates="streams")
    offers: Mapped[List["StreamOfferRecord"]] = relationship(
        back_populates="stream",
        cascade="all, delete-orphan",
        order_by="StreamOfferRecord.id",
    )


class StreamOfferRecord(Base):
    __tablename__ = "stream_offers"
    __table_args__ = (
        UniqueConstraint("stream_id", "offer_id", name="uq_stream_offer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), nullable=False)
    offer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    offer_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    share: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")  # active | removed

    stream: Mapped[StreamRecord] = relationship(back_populates="offers")
