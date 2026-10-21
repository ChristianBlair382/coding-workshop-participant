from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:<password>@localhost:5432/<db_name>"
    secret_key: str
    frontend_origin: str = "http://localhost:3000"
    access_token_expire_time: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()