import asyncio, httpx, random
from typing import Any
from llmkit.settings import Settings

RETRYABLE_STATUS = frozenset[int]({429, 500, 502, 503, 504})

class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None
    
    async def __aenter__(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=httpx.Timeout(connect=5.0,read=self._settings.timeout_s,write=10.0,pool=5.0),
                headers={"Authorization": f"Bearer {self._settings.provider_api_key}"}
            )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
        self._client = None

    async def request(self, method: str, path: str, *, json: dict[str, Any] | None = None ) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("LLMClient must be used as an async context manager")
        
        for attempt in range(self._settings.max_retries + 1):
            try:
                response = await self._client.request(method, path, json=json)
            except (httpx.TimeoutException, httpx.ConnectError):
                if attempt == self._settings.max_retries:
                    raise
                await self._sleep(attempt)
                continue
            if response.status_code not in RETRYABLE_STATUS:
                return response
            if attempt == self._settings.max_retries:
                return response
            await self._sleep(attempt)

        return response

    async def _sleep(self, attempt: int) -> None:
        delay = 0.5 * 2 ** attempt
        delay += random.uniform(0, delay * 0.25)
        await asyncio.sleep(delay)