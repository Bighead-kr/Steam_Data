from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    steam_api_key: str
    bayesian_prior_strength: float = 50.0
    min_cohort_size: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
