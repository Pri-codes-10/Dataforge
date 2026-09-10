import os
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initial load from all candidate locations
load_dotenv(os.path.join(base_dir, ".env"))
load_dotenv(os.path.join(base_dir, "backend", ".env"))
load_dotenv()


class Settings:
    """
    Application configuration dynamically loaded from environment variables.
    Properties ensure any updates to .env are immediately reflected without stale cache.
    """

    def reload(self) -> None:
        """Reload environment variables from .env files."""
        load_dotenv(os.path.join(base_dir, ".env"), override=True)
        load_dotenv(os.path.join(base_dir, "backend", ".env"), override=True)
        load_dotenv(override=True)

    @property
    def SARVAM_API_KEY(self) -> str:
        key = os.getenv("SARVAM_API_KEY", "").strip()
        if not key:
            self.reload()
            key = os.getenv("SARVAM_API_KEY", "").strip()
        return key

    @property
    def SARVAM_API_URL(self) -> str:
        return os.getenv("SARVAM_API_URL", "https://api.sarvam.ai/v1/chat/completions").strip()

    @property
    def SARVAM_MODEL(self) -> str:
        return os.getenv("SARVAM_MODEL", "sarvam-105b-conversations").strip()

    @property
    def SARVAM_STT_URL(self) -> str:
        return os.getenv("SARVAM_STT_URL", "https://api.sarvam.ai/speech-to-text").strip()

    @property
    def RIME_API_KEY(self) -> str:
        key = os.getenv("RIME_API_KEY", "").strip()
        if not key:
            self.reload()
            key = os.getenv("RIME_API_KEY", "").strip()
        return key

    @property
    def RIME_VOICE(self) -> str:
        return os.getenv("RIME_VOICE", "vespera").strip()

    @property
    def WEB_SEARCH_API_KEY(self) -> str:
        return os.getenv("WEB_SEARCH_API_KEY", "").strip()

    @property
    def FLIGHT_API_KEY(self) -> str:
        return os.getenv("FLIGHT_API_KEY", "").strip()

    @property
    def APP_ENV(self) -> str:
        return os.getenv("APP_ENV", "development").strip()

    @property
    def DEBUG(self) -> bool:
        return os.getenv("DEBUG", "true").lower().strip() == "true"


settings = Settings()