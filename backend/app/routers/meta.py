from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.schemas import MetaItem
from app.services.keitaro import KeitaroClient, KeitaroError

router = APIRouter(prefix="/api/meta", tags=["meta"])


def get_keitaro(settings: Settings = Depends(get_settings)) -> KeitaroClient:
    return KeitaroClient(settings)


def _to_meta(items: list[dict]) -> list[MetaItem]:
    result: list[MetaItem] = []
    for item in items:
        if "id" not in item:
            continue
        name = item.get("name") or item.get("domain") or f"#{item['id']}"
        result.append(MetaItem(id=int(item["id"]), name=str(name)))
    return result


@router.get("/domains", response_model=list[MetaItem])
async def list_domains(client: KeitaroClient = Depends(get_keitaro)) -> list[MetaItem]:
    try:
        async with client:
            return _to_meta(await client.list_domains())
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("/groups", response_model=list[MetaItem])
async def list_groups(client: KeitaroClient = Depends(get_keitaro)) -> list[MetaItem]:
    try:
        async with client:
            return _to_meta(await client.list_groups("campaigns"))
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("/traffic-sources", response_model=list[MetaItem])
async def list_traffic_sources(client: KeitaroClient = Depends(get_keitaro)) -> list[MetaItem]:
    try:
        async with client:
            return _to_meta(await client.list_traffic_sources())
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("/offers", response_model=list[MetaItem])
async def list_offers(client: KeitaroClient = Depends(get_keitaro)) -> list[MetaItem]:
    try:
        async with client:
            return _to_meta(await client.list_offers())
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc


@router.get("/offers/{offer_id}", response_model=MetaItem)
async def get_offer(offer_id: int, client: KeitaroClient = Depends(get_keitaro)) -> MetaItem:
    try:
        async with client:
            offer = await client.get_offer(offer_id)
            return MetaItem(
                id=int(offer["id"]),
                name=str(offer.get("name") or f"#{offer['id']}"),
            )
    except KeitaroError as exc:
        raise HTTPException(status_code=exc.status_code or 404, detail=str(exc)) from exc
