from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class KeitaroError(Exception):
    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class KeitaroClient:
    def __init__(self, settings: Settings):
        self.base_url = settings.keitaro_base_url.rstrip("/")
        self.api_key = settings.keitaro_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> KeitaroClient:
        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/admin_api/v1",
            headers={
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
            # Ignore HTTP(S)_PROXY from the environment (e.g. Cursor sandbox).
            trust_env=False,
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("KeitaroClient must be used as an async context manager")
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = await self.client.request(method, path, json=json, params=params)
        except httpx.HTTPError as exc:
            raise KeitaroError(f"Keitaro request failed: {exc}", status_code=502) from exc
        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise KeitaroError(
                f"Keitaro API error {response.status_code}: {body}",
                status_code=response.status_code,
                body=body,
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def list_campaigns(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/campaigns")
        return data if isinstance(data, list) else []

    async def get_campaign(self, campaign_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/campaigns/{campaign_id}")

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/campaigns", json=payload)

    async def list_campaign_streams(self, campaign_id: int) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/campaigns/{campaign_id}/streams")
        return data if isinstance(data, list) else []

    async def get_stream(self, stream_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/streams/{stream_id}")

    async def create_stream(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/streams", json=payload)

    async def update_stream(self, stream_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("PUT", f"/streams/{stream_id}", json=payload)

    async def list_domains(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/domains")
        return data if isinstance(data, list) else []

    async def list_groups(self, group_type: str = "campaigns") -> list[dict[str, Any]]:
        data = await self._request("GET", "/groups", params={"type": group_type})
        return data if isinstance(data, list) else []

    async def list_traffic_sources(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/traffic_sources")
        return data if isinstance(data, list) else []

    async def list_offers(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/offers")
        return data if isinstance(data, list) else []

    async def get_offer(self, offer_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/offers/{offer_id}")
