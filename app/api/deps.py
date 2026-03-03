from functools import lru_cache
from app.config.settings import Settings


@lru_cache
def get_settings() -> Settings:
    # Cached so we don't rebuild settings every request
    return Settings()