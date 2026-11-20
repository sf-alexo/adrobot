from __future__ import annotations

import re
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CampaignRecord, StreamRecord
from app.schemas import CampaignCreate, CampaignOut
from app.services import stream_service
from app.services.keitaro import KeitaroClient

GOOGLE_URL = "https://www.google.com"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    suffix = secrets.token_hex(3)
    base = (slug or "campaign")[:40]
    return f"{base}-{suffix}"


async def create_campaign(
    db: AsyncSession,
    client: KeitaroClient,
    data: CampaignCreate,
) -> CampaignOut:
    geo = data.geo.upper().strip()
    alias = _slugify(data.name)

    campaign = await client.create_campaign(
        {
            "name": data.name,
            "alias": alias,
            "domain_id": data.domain_id,
            "group_id": str(data.group_id),
            "traffic_source_id": data.traffic_source_id,
            "state": "active",
            "type": "position",
        }
    )
    campaign_id = int(campaign["id"])

    google_stream = await client.create_stream(
        {
            "campaign_id": campaign_id,
            "name": f"Geo {geo} → Google",
            "type": "regular",
            "schema": "action",
            "action_type": "http",
            "action_payload": GOOGLE_URL,
            "collect_clicks": True,
            "state": "active",
            "filters": [
                {
                    "name": "country",
                    "mode": "accept",
                    "payload": [geo],
                }
            ],
        }
    )

    offer_stream = await client.create_stream(
        {
            "campaign_id": campaign_id,
            "name": "Offer stream",
            "type": "default",
            "schema": "landings",
            "action_type": "http",
            "action_payload": "",
            "collect_clicks": True,
            "state": "active",
            "landings": [],
            "offers": [
                {
                    "offer_id": data.offer_id,
                    "share": 100,
                    "state": "active",
                }
            ],
        }
    )

    record = CampaignRecord(
        name=data.name,
        geo=geo,
        keitaro_campaign_id=campaign_id,
        offer_stream_id=int(offer_stream["id"]),
        google_stream_id=int(google_stream["id"]),
        domain_id=data.domain_id,
        group_id=data.group_id,
        traffic_source_id=data.traffic_source_id,
        alias=campaign.get("alias") or alias,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return await stream_service.sync_streams_from_keitaro(db, client, record)


async def list_campaigns(db: AsyncSession) -> list[CampaignOut]:
    result = await db.execute(
        select(CampaignRecord)
        .options(selectinload(CampaignRecord.streams).selectinload(StreamRecord.offers))
        .order_by(CampaignRecord.id.desc())
    )
    return [stream_service.campaign_out(r) for r in result.scalars().all()]


async def get_campaign(db: AsyncSession, campaign_id: int) -> CampaignOut:
    record = await stream_service.load_campaign(db, campaign_id)
    return stream_service.campaign_out(record)
