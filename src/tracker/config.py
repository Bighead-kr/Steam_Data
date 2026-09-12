from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# The SteamSpy genre lists the pipeline collects from, most-specific-first:
# the first list an app appears in becomes its cohort (see collect_games),
# and "Simulation" says more about a game than "Indie", which is really a
# budget bracket.
#
# "roguelike" and "management" used to be in this list and silently
# contributed nothing - SteamSpy's genre index has no such genres and
# answered both with {} (verified live, alongside Indie=61,504 and
# Simulation=17,764). They are Steam *tags*, and are reachable as such now
# that the collector stores per-app tags.
TARGET_GENRES = ["Simulation", "Indie"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    steam_api_key: str
    bayesian_prior_strength: float = 50.0
    min_cohort_size: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
