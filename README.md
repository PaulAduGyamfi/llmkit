# llmkit

Typed async foundations for LLM services: an HTTP client with retries and
timeouts, environment-driven settings, and structured JSON logging with
correlation IDs.

## Install

Requires Python 3.12+.

```bash
uv add git+https://github.com/PaulAduGyamfi/llmkit
```

## Configuration

Settings are read from environment variables (or a `.env` file) with the
`LLMKIT_` prefix.

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLMKIT_PROVIDER_API_KEY` | yes | — | Sent as `Authorization: Bearer <key>` on every request |
| `LLMKIT_BASE_URL` | yes | — | Base URL all request paths are relative to |
| `LLMKIT_TIMEOUT_S` | no | `30.0` | **Read** timeout in seconds. Connect timeout is fixed at 5s |
| `LLMKIT_MAX_RETRIES` | no | `2` | Retries after the first attempt (`2` means 3 attempts total) |

Missing or invalid values raise a `pydantic.ValidationError` naming the field
when `get_settings()` is called. Call it once at application startup so a
misconfigured service fails on boot rather than on its first request.

## Usage

```python
import asyncio

from llmkit.client import LLMClient
from llmkit.logging import configure, request_id
from llmkit.settings import get_settings


async def main() -> None:
    configure()  # JSON logs to stdout
    request_id.set("req-123")  # tags every log line in this task

    settings = get_settings()  # validates the environment
    async with LLMClient(settings) as client:
        response = await client.request("GET", "/health")
        print(response.status_code)


asyncio.run(main())
```

`request()` returns the raw `httpx.Response` and does not raise on error
statuses; check `response.status_code` yourself.

### Retry behaviour

| Outcome | Retried |
|---|---|
| 429, 500, 502, 503, 504 | yes |
| `httpx.TimeoutException`, `httpx.ConnectError` | yes |
| Any other status, including 400, 401, 404 | no, returned immediately |

Retries use exponential backoff (0.5s, 1s, 2s, …) with up to 25% random
jitter. After the final attempt, a retryable status is returned to the
caller and a transport error is re-raised.

Each attempt logs one JSON line with `method`, `path`, `status` (or `error`),
`attempt`, `elapsed_ms` and `request_id`. Libraries should not call
`configure()`; applications should, once.

### Testing code that uses llmkit

Pass an `httpx.MockTransport` to avoid the network:

```python
import httpx
from llmkit.client import LLMClient
from llmkit.settings import Settings

transport = httpx.MockTransport(lambda req: httpx.Response(200, json={"ok": True}))
settings = Settings(provider_api_key="test", base_url="http://test")

async with LLMClient(settings, transport=transport) as client:
    response = await client.request("GET", "/anything")
```

## Development

```bash
uv sync
uv run pre-commit install
uv run pytest -v
uv run pyright
uv run ruff check .
```

CI runs all of the above on every push and pull request.