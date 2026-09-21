import httpx
import pytest
from llmkit.client import LLMClient
from llmkit.settings import Settings

async def test_200_succeedes(settings: Settings) -> None:
    calls = { "count" : 0 }

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with LLMClient(settings, transport=transport) as client:
        result = await client.request("GET", "/anything")

    assert result.status_code == 200
    assert result.json() == {"ok": True}
    assert calls["count"] == 1

async def test_retries_on_503_then_succeeds(settings: Settings) -> None:
    calls = { "count": 0 }

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})
    
    transport = httpx.MockTransport(handler)
    async with LLMClient(settings, transport=transport) as client:
        result = await client.request("GET", "/anything")

    assert calls["count"] == 2
    assert result.status_code == 200

async def test_retries_on_503_exhausted(settings: Settings) -> None:
    calls = { "count" : 0 }

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(503, json={"retry": True})

    transport = httpx.MockTransport(handler)
    async with LLMClient(settings, transport=transport) as client:
        result = await client.request("GET", "/anything")

    assert result.status_code == 503
    assert calls["count"] == settings.max_retries + 1

async def test_400_returns_immediately_with_no_retry(settings: Settings) -> None:
    calls = { "count" : 0 }

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(400, json={"bad request": True})

    transport = httpx.MockTransport(handler)
    async with LLMClient(settings, transport=transport) as client:
        result = await client.request("GET", "/anything")
    
    assert calls["count"] == 1
    assert result.status_code == 400

async def test_request_outside_context_manager_raises(settings: Settings) -> None:
    client = LLMClient(settings)
    with pytest.raises(RuntimeError):
        await client.request("GET", "/anything")

async def test_timeout_retries_then_raises(settings: Settings) -> None:
    calls = { "count" : 0 }

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectTimeout("simulated")

    transport = httpx.MockTransport(handler)
    with pytest.raises(httpx.ConnectTimeout):
        async with LLMClient(settings, transport=transport) as client:
            await client.request("GET", "/anything")
    
    assert calls["count"] == settings.max_retries + 1
