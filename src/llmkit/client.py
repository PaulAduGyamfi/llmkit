import asyncio, httpx, random, time
import logging
from typing import Any
from llmkit.settings import Settings

log = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset[int]({429, 500, 502, 503, 504})

class LLMClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
    
    async def __aenter__(self):
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.base_url,
                timeout=httpx.Timeout(connect=5.0,read=self._settings.timeout_s,write=10.0,pool=5.0),
                headers={"Authorization": f"Bearer {self._settings.provider_api_key}"},
                transport=self._transport,
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
            started = time.perf_counter()
            try:
                response = await self._client.request(method, path, json=json)
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                log.warning("request failed", extra={"ctx": {
                    "method": method,
                    "path": path,
                    "attempt": attempt,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
                    "error": type(e).__name__,
                }})
                if attempt == self._settings.max_retries:
                    raise
                await self._sleep(attempt)
                continue
            else:
                log.info("request attempt", extra={"ctx": {
                    "method": method,
                    "path": path,
                    "status": response.status_code,
                    "attempt": attempt,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}})

            if response.status_code not in RETRYABLE_STATUS:
                return response
            if attempt == self._settings.max_retries:
                return response
            await self._sleep(attempt)
            
        raise AssertionError("unreachable: loop always returns or raises")

    async def _sleep(self, attempt: int) -> None:
        delay = 0.5 * 2 ** attempt
        delay += random.uniform(0, delay * 0.25)
        await asyncio.sleep(delay)