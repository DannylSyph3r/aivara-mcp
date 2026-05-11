import logging

import httpx

logger = logging.getLogger(__name__)

FHIR_REQUEST_TIMEOUT = 30.0


class FhirClient:
    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def _get(self, path: str, params: dict | None = None) -> dict | None:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        url = self._build_url(path)
        async with httpx.AsyncClient(timeout=FHIR_REQUEST_TIMEOUT) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 404:
                logger.debug("fhir_404 url=%s", url)
                return None
            response.raise_for_status()
            return response.json()

    async def read(self, path: str) -> dict | None:
        return await self._get(path)

    async def search(self, resource_type: str, params: dict | None = None) -> dict | None:
        return await self._get(resource_type, params=params)