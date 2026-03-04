from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "bayer-ai"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"


    from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "bayer-ai"
    documents_dir: str = "documents"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

