import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    """
    Application configuration loaded from environment variables.
    """

    SARVAM_API_KEY: str = os.getenv(
        "SARVAM_API_KEY",
        "",
    )

    SARVAM_API_URL: str = os.getenv(
        "SARVAM_API_URL",
        "https://api.sarvam.ai/v1/chat/completions",
    )

    SARVAM_MODEL: str = os.getenv(
        "SARVAM_MODEL",
        "sarvam-105b-conversations",
    )

    RIME_API_KEY: str = os.getenv(
        "RIME_API_KEY",
        "",
    )

    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379",
    )

    APP_ENV: str = os.getenv(
        "APP_ENV",
        "development",
    )

    DEBUG: bool = os.getenv(
        "DEBUG",
        "true",
    ).lower() == "true"


settings = Settings()