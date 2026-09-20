from pydantic import Field, PositiveFloat 
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_prefix="LLMKIT_",
        env_file_encoding="utf-8", 
        extra="ignore", 
        frozen=True
    )
    provider_api_key: str
    base_url: str
    timeout_s: PositiveFloat = 30.0
    max_retries: int = Field(default=2, ge=0)

def get_settings() -> Settings:
    return Settings()