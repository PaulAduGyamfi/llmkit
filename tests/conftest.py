import pytest

from llmkit.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(provider_api_key="test-key", base_url="http://test", max_retries=2)
