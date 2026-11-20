from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.schemas import CampaignCreate, CampaignOut, OfferAdd, OfferPin
from app.services import campaign_service, stream_service
from app.services.keitaro import KeitaroClient, KeitaroError

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def get_keitaro(settings: Settings = Depends(get_settings)) -> KeitaroClient:
    return KeitaroClient(settings)


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> CampaignOut:
    try:
        async with client:
            return await campaign_service.create_campaign(db, client, payload)
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(db: AsyncSession = Depends(get_db)) -> list[CampaignOut]:
    return await campaign_service.list_campaigns(db)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    try:
        return await campaign_service.get_campaign(db, campaign_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{campaign_id}/fetch-streams", response_model=CampaignOut)
async def fetch_streams(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> CampaignOut:
    try:
        record = await stream_service.load_campaign(db, campaign_id)
        async with client:
            return stream_service.campaign_out(
                await stream_service.sync_streams_from_keitaro(db, client, record)
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/{campaign_id}/streams/{stream_id}/offers", response_model=CampaignOut)
async def add_offer(
    campaign_id: int,
    stream_id: int,
    payload: OfferAdd,
    db: AsyncSession = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> CampaignOut:
    try:
        async with client:
            return await stream_service.add_offer(
                db, client, campaign_id, stream_id, payload.offer_id
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post(
    "/{campaign_id}/streams/{stream_id}/offers/{offer_id}/remove",
    response_model=CampaignOut,
)
async def remove_offer(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    try:
        return await stream_service.remove_offer(db, campaign_id, stream_id, offer_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{campaign_id}/streams/{stream_id}/offers/{offer_id}/bring-back",
    response_model=CampaignOut,
)
async def bring_back_offer(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    try:
        return await stream_service.bring_back_offer(db, campaign_id, stream_id, offer_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{campaign_id}/streams/{stream_id}/offers/{offer_id}/pin",
    response_model=CampaignOut,
)
async def pin_offer(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    payload: OfferPin,
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    try:
        return await stream_service.pin_offer(
            db, campaign_id, stream_id, offer_id, payload.pinned, payload.share
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{campaign_id}/streams/{stream_id}/push", response_model=CampaignOut)
async def push_stream(
    campaign_id: int,
    stream_id: int,
    db: AsyncSession = Depends(get_db),
    client: KeitaroClient = Depends(get_keitaro),
) -> CampaignOut:
    try:
        async with client:
            return await stream_service.push_stream(db, client, campaign_id, stream_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.post("/{campaign_id}/streams/{stream_id}/cancel", response_model=CampaignOut)
async def cancel_stream(
    campaign_id: int,
    stream_id: int,
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    try:
        return await stream_service.cancel_stream(db, campaign_id, stream_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
