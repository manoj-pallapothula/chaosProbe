"""Central configuration via pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Database
    database_url: str = Field(
        default="postgresql://chaosuser:chaospass@localhost:5432/chaosdb",
        alias="DATABASE_URL",
    )
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    # Prometheus
    prometheus_url: str = Field(
        default="http://localhost:9090",
        alias="PROMETHEUS_URL",
    )
    # App
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    secret_key: str = Field(default="changeme", alias="SECRET_KEY")

    model_config = {"env_file": ".env", "populate_by_name": True}


settings = Settings()