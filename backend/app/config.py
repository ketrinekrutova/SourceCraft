from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/repo_health"

    sourcecraft_api_base_url: str = "https://api.sourcecraft.tech"
    sourcecraft_service_pat: str = ""  # для публичного (кронового) конвейера

    # Гипотеза, не подтверждена организаторами — см. CHECK.md A3.
    scs_security_api_base_url: str = "https://appsec.sourcecraft.tech"

    ya_id_client_id: str = ""
    ya_id_client_secret: str = ""
    ya_id_redirect_uri: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
