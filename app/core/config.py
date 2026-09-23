from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database Settings
    POSTGRE_HOST: str = "localhost"
    POSTGRE_PORT: int = 5432
    POSTGRE_USERNAME: str = "postgres"
    POSTGRE_PASSWORD: str = "postgres"
    POSTGRE_DATABASE: str = "postgres"

    # JWT Settings
    SECRET_KEY: str = "YkADFlDGKADDbz9OX9dGAMKeq_bUoNS88kLc72MHG4Q"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # OAuth Settings (e.g., Google)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_CONF_URL: str = "https://accounts.google.com/.well-known/openid-configuration"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.POSTGRE_USERNAME}:{self.POSTGRE_PASSWORD}@{self.POSTGRE_HOST}:{self.POSTGRE_PORT}/{self.POSTGRE_DATABASE}"


settings = Settings()
