import httpx

from app.core.config import settings


class RimeTTS:
    """
    Rime Text-to-Speech service.

    Converts the agent's text response into spoken audio.
    """

    def __init__(self):
        self.api_key = settings.RIME_API_KEY
        self.base_url = "https://users.rime.ai/v1/rime-tts"

        # Keep the voice configurable from .env
        self.voice = settings.RIME_VOICE

    async def synthesize(
        self,
        text: str,
        language: str = "eng",
    ) -> bytes:
        """
        Convert text to audio using Rime TTS.
        """

        if not text.strip():
            return b""

        if not self.api_key:
            raise ValueError(
                "RIME_API_KEY is not configured."
            )

        payload = {
            "text": text,
            "speaker": self.voice,
            "lang": language,
            "modelId": "arcana",
            "samplingRate": 22050,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            return response.content


rime_service = RimeTTS()