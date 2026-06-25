from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str

    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str
    
    GEMINI_API_KEY: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()