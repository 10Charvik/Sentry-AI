from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://sentry:sentry@localhost:5432/sentry"
    cors_origins: str = "*"

    # Auth — a single admin key protecting mutating "admin" actions
    # (PATCH /roads/{id}/status, POST /risk/recompute). Unset by default
    # so those endpoints refuse to work until you deliberately configure one.
    admin_api_key: Optional[str] = None

    # Background risk-recompute loop (see app/scheduler.py)
    risk_recompute_enabled: bool = True
    risk_recompute_interval_seconds: int = 300  # 5 minutes

    # Real IMD data ingestion (see app/ingestion/). Defaults to disabled —
    # it requires IP whitelisting with IMD and real station/district IDs
    # configured in app/ingestion/zone_mapping.py, so it stays off until
    # you've deliberately set both up. Otherwise it would just fail loudly
    # on every interval by default.
    imd_base_url: str = "https://api.imd.gov.in/api/v1"
    imd_ingest_enabled: bool = False
    imd_ingest_interval_seconds: int = 1800  # 30 minutes — be a polite API citizen

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
