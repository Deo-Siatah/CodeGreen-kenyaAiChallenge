from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str

    NEO4J_URI: str
    NEO4J_USERNAME: str
    NEO4J_PASSWORD: str
    NEO4J_DATABASE: str
    USSD_WEBHOOK_URL: str
    SMS_WEBHOOK_URL: str
    BACKEND_URL: str
    AFRICASTALKING_API_KEY: str
    AFRICASTALKING_USERNAME: str    
    
    GEMINI_API_KEY: str 

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()


print("Loaded AT username:", settings.AFRICASTALKING_USERNAME)
print("Loaded AT API key:", settings.AFRICASTALKING_API_KEY)

