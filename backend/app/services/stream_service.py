from __future__ import annotations

import json
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes, selectinload

from app.models import CampaignRecord, StreamOfferRecord, StreamRecord
from app.schemas import CampaignOut, StreamOfferOut, StreamOut
from app.services.keitaro import KeitaroClient, KeitaroError
from app.services.shares import active_share_total, recalculate_shares


def _offers_collection(stream: StreamRecord) -> list:
    """Access stream.offers without triggering async lazy-load after flush."""
    state = attributes.instance_state(stream)
    if "offers" not in state.dict:
        attributes.set_committed_value(stream, "offers", [])
    return stream.offers


def _snapshot_offers(stream: StreamRecord) -> str:
    payload = [
        {
            "offer_id": o.offer_id,
            "offer_name": o.offer_name,
            "share": o.share,
            "pinned": o.pinned,
            "status": o.status,
        }
        for o in _offers_collection(stream)
    ]
    return json.dumps(payload)


def _offer_out(o: StreamOfferRecord) -> StreamOfferOut:
    return StreamOfferOut(
        id=o.id,
        offer_id=o.offer_id,
        offer_name=o.offer_name,
        share=o.share,
        pinned=o.pinned,
        status=o.status,
    )


def _stream_out(s: StreamRecord) -> StreamOut:
    return StreamOut(
        id=s.id,
        keitaro_stream_id=s.keitaro_stream_id,
        name=s.name,
        stream_type=s.stream_type,
        has_offers=s.has_offers,
        is_dirty=s.is_dirty,
        offers=[_offer_out(o) for o in s.offers] if s.has_offers else [],
    )


def campaign_out(record: CampaignRecord) -> CampaignOut:
    return CampaignOut(
        id=record.id,
        name=record.name,
        geo=record.geo,
        keitaro_campaign_id=record.keitaro_campaign_id,
        offer_stream_id=record.offer_stream_id,
        google_stream_id=record.google_stream_id,
        domain_id=record.domain_id,
        group_id=record.group_id,
        traffic_source_id=record.traffic_source_id,
        alias=record.alias,
        created_at=record.created_at,
        streams=[_stream_out(s) for s in record.streams],
    )


async def load_campaign(db: AsyncSession, campaign_id: int) -> CampaignRecord:
    result = await db.execute(
        select(CampaignRecord)
        .where(CampaignRecord.id == campaign_id)
        .options(
            selectinload(CampaignRecord.streams).selectinload(StreamRecord.offers)
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise LookupError(f"Campaign {campaign_id} not found")
    return record


async def _offer_names(client: KeitaroClient) -> Dict[int, str]:
    try:
        offers = await client.list_offers()
    except KeitaroError:
        return {}
    return {int(o["id"]): o.get("name") or f"Offer #{o['id']}" for o in offers if "id" in o}


def _normalize_keitaro_offers(raw: Optional[List[dict]]) -> List[dict]:
    result = []
    for item in raw or []:
        offer_id = item.get("offer_id")
        if offer_id is None:
            continue
        result.append(
            {
                "offer_id": int(offer_id),
                "share": int(item.get("share") or 0),
                "state": item.get("state") or "active",
            }
        )
    return result


async def sync_streams_from_keitaro(
    db: AsyncSession,
    client: KeitaroClient,
    campaign: CampaignRecord,
) -> CampaignRecord:
    """Fetch streams from Keitaro and merge into local draft state."""
    remote_streams = await client.list_campaign_streams(campaign.keitaro_campaign_id)
    names = await _offer_names(client)
    by_keitaro_id = {s.keitaro_stream_id: s for s in campaign.streams}

    seen = set()
    for remote in remote_streams:
        keitaro_id = int(remote["id"])
        seen.add(keitaro_id)
        raw_offers = _normalize_keitaro_offers(remote.get("offers"))
        existing = by_keitaro_id.get(keitaro_id)
        # Video: streams without offers are listed but not parsed.
        # Default / previously-known offer streams stay editable.
        has_offers = (
            len(raw_offers) > 0
            or (existing.has_offers if existing else False)
            or remote.get("type") == "default"
        )

        if existing is None:
            existing = StreamRecord(
                campaign_id=campaign.id,
                keitaro_stream_id=keitaro_id,
                name=remote.get("name") or f"Stream #{keitaro_id}",
                stream_type=remote.get("type") or "regular",
                has_offers=has_offers,
                is_dirty=False,
            )
            db.add(existing)
            await db.flush()
            # flush expires relationship loaders; seed empty collection for async safety
            attributes.set_committed_value(existing, "offers", [])
            campaign.streams.append(existing)
            by_keitaro_id[keitaro_id] = existing
        else:
            existing.name = remote.get("name") or existing.name
            existing.stream_type = remote.get("type") or existing.stream_type
            existing.has_offers = has_offers or existing.has_offers

        offers = _offers_collection(existing)

        if not existing.has_offers:
            offers.clear()
            existing.is_dirty = False
            existing.published_snapshot = "[]"
            continue

        # If local draft is dirty, don't overwrite local edits — only mark missing remote as removed?
        # Video: Fetch Streams syncs from Keitaro. We'll merge:
        # - If not dirty: full replace from Keitaro + mark locally-known missing as removed
        # - If dirty: skip overwrite of this stream (keep draft)
        if existing.is_dirty:
            continue

        remote_ids = {o["offer_id"] for o in raw_offers}
        local_by_id = {o.offer_id: o for o in offers}

        for remote_offer in raw_offers:
            oid = remote_offer["offer_id"]
            local = local_by_id.get(oid)
            if local is None:
                local = StreamOfferRecord(
                    stream_id=existing.id,
                    offer_id=oid,
                    offer_name=names.get(oid),
                    share=remote_offer["share"],
                    pinned=False,
                    status="active",
                )
                db.add(local)
                offers.append(local)
            else:
                local.status = "active"
                local.share = remote_offer["share"]
                if not local.offer_name:
                    local.offer_name = names.get(oid)

        for local in list(offers):
            if local.offer_id not in remote_ids and local.status == "active":
                # Disappeared in Keitaro → archive as removed, already matches remote
                local.status = "removed"
                local.share = 0
                local.pinned = False

        existing.is_dirty = False
        await db.flush()
        existing.published_snapshot = _snapshot_offers(existing)

    # Keep local streams that vanished from Keitaro (rare)
    for stream in campaign.streams:
        if stream.keitaro_stream_id not in seen and stream.has_offers:
            # leave as-is
            pass

    await db.commit()
    return await load_campaign(db, campaign.id)


async def add_offer(
    db: AsyncSession,
    client: KeitaroClient,
    campaign_id: int,
    stream_id: int,
    offer_id: int,
) -> CampaignOut:
    campaign = await load_campaign(db, campaign_id)
    stream = _get_offer_stream(campaign, stream_id)

    existing = next((o for o in stream.offers if o.offer_id == offer_id), None)
    if existing and existing.status == "active":
        raise ValueError(f"Offer {offer_id} is already in the stream")

    try:
        remote_offer = await client.get_offer(offer_id)
        name = remote_offer.get("name")
    except KeitaroError as exc:
        raise ValueError(f"Offer {offer_id} not found in Keitaro") from exc

    if existing and existing.status == "removed":
        existing.status = "active"
        existing.pinned = False
        existing.offer_name = name or existing.offer_name
    else:
        row = StreamOfferRecord(
            stream_id=stream.id,
            offer_id=offer_id,
            offer_name=name,
            share=0,
            pinned=False,
            status="active",
        )
        db.add(row)
        stream.offers.append(row)

    recalculate_shares(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return campaign_out(await load_campaign(db, campaign_id))


async def remove_offer(
    db: AsyncSession,
    campaign_id: int,
    stream_id: int,
    offer_id: int,
) -> CampaignOut:
    campaign = await load_campaign(db, campaign_id)
    stream = _get_offer_stream(campaign, stream_id)
    offer = next((o for o in stream.offers if o.offer_id == offer_id), None)
    if offer is None:
        raise LookupError(f"Offer {offer_id} not found in stream")
    if offer.status == "removed":
        return campaign_out(campaign)

    active_count = sum(1 for o in stream.offers if o.status == "active")
    if active_count <= 1:
        raise ValueError("Cannot remove the last active offer from the stream")

    offer.status = "removed"
    offer.share = 0
    offer.pinned = False
    recalculate_shares(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return campaign_out(await load_campaign(db, campaign_id))


async def bring_back_offer(
    db: AsyncSession,
    campaign_id: int,
    stream_id: int,
    offer_id: int,
) -> CampaignOut:
    campaign = await load_campaign(db, campaign_id)
    stream = _get_offer_stream(campaign, stream_id)
    offer = next((o for o in stream.offers if o.offer_id == offer_id), None)
    if offer is None:
        raise LookupError(f"Offer {offer_id} not found in stream")
    if offer.status != "removed":
        return campaign_out(campaign)

    offer.status = "active"
    offer.pinned = False
    recalculate_shares(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return campaign_out(await load_campaign(db, campaign_id))


async def pin_offer(
    db: AsyncSession,
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    pinned: bool,
    share: Optional[int] = None,
) -> CampaignOut:
    campaign = await load_campaign(db, campaign_id)
    stream = _get_offer_stream(campaign, stream_id)
    offer = next((o for o in stream.offers if o.offer_id == offer_id), None)
    if offer is None:
        raise LookupError(f"Offer {offer_id} not found in stream")
    if offer.status != "active":
        raise ValueError("Only active offers can be pinned")

    offer.pinned = pinned
    if pinned:
        if share is None:
            raise ValueError("Share is required when pinning an offer")
        offer.share = share
    recalculate_shares(stream.offers)
    stream.is_dirty = True
    await db.commit()
    return campaign_out(await load_campaign(db, campaign_id))


async def push_stream(
    db: AsyncSession,
    client: KeitaroClient,
    campaign_id: int,
    stream_id: int,
) -> CampaignOut:
    campaign = await load_campaign(db, campaign_id)
    stream = _get_offer_stream(campaign, stream_id)
    if not stream.is_dirty:
        return campaign_out(campaign)

    payload_offers = [
        {
            "offer_id": o.offer_id,
            "share": o.share,
            "state": "active",
        }
        for o in stream.offers
        if o.status == "active"
    ]
    if not payload_offers:
        raise ValueError("Cannot push a stream with no active offers")

    total = active_share_total(stream.offers)
    if total != 100:
        raise ValueError(f"Active offer shares must sum to 100 (now {total})")

    await client.update_stream(stream.keitaro_stream_id, {"offers": payload_offers})
    stream.is_dirty = False
    stream.published_snapshot = _snapshot_offers(stream)
    await db.commit()
    return campaign_out(await load_campaign(db, campaign_id))


async def cancel_stream(
    db: AsyncSession,
    campaign_id: int,
    stream_id: int,
) -> CampaignOut:
    campaign = await load_campaign(db, campaign_id)
    stream = _get_offer_stream(campaign, stream_id)
    if not stream.is_dirty:
        return campaign_out(campaign)

    snapshot_raw = stream.published_snapshot or "[]"
    snapshot = json.loads(snapshot_raw)
    stream.offers.clear()
    await db.flush()

    for item in snapshot:
        db.add(
            StreamOfferRecord(
                stream_id=stream.id,
                offer_id=int(item["offer_id"]),
                offer_name=item.get("offer_name"),
                share=int(item.get("share") or 0),
                pinned=bool(item.get("pinned")),
                status=item.get("status") or "active",
            )
        )
    stream.is_dirty = False
    await db.commit()
    return campaign_out(await load_campaign(db, campaign_id))


def _get_offer_stream(campaign: CampaignRecord, stream_id: int) -> StreamRecord:
    stream = next((s for s in campaign.streams if s.id == stream_id), None)
    if stream is None:
        raise LookupError(f"Stream {stream_id} not found")
    if not stream.has_offers:
        raise ValueError("This stream has no offers to edit")
    return stream
