from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://chat:chat@localhost:5432/chat"
    async_database_url: str = "postgresql+asyncpg://chat:chat@localhost:5432/chat"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-this-in-production-please"
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()