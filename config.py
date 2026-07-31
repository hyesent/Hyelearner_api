from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database - Supabase
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI - Gemini 2.5 Flash
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # Paystack
    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str
    PAYSTACK_CALLBACK_URL: str

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # ============================================================
    # HYESCRIPTURES — Separate Supabase Project
    # ============================================================
    HYESCRIPTURES_SUPABASE_URL: Optional[str] = None
    HYESCRIPTURES_SUPABASE_KEY: Optional[str] = None

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
