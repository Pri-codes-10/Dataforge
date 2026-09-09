import logging
import httpx

from app.core.config import settings

logger = logging.getLogger("sutra.rime")


import io
import wave

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 22050) -> bytes:
    if not pcm_data:
        return b""
    if pcm_data.startswith(b"RIFF"):
        return pcm_data
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


class RimeTTS:
    """
    Rime Text-to-Speech service.

    Converts the agent's text response into spoken audio.
    """

    def __init__(self):
        self.base_url = "https://users.rime.ai/v1/rime-tts"

    async def synthesize(
        self,
        text: str,
        language: str = "eng",
    ) -> bytes:
        """
        Convert text to audio using Rime TTS.
        Returns WAV audio bytes, or b"" if unconfigured.
        """
        if not text or not text.strip():
            return b""

        api_key = settings.RIME_API_KEY
        if not api_key:
            logger.warning("RIME_API_KEY is not configured in .env. TTS synthesis skipped.")
            return b""

        voice = settings.RIME_VOICE or "astra"
        if voice.lower() in ["aria", ""]:
            voice = "astra"

        payload = {
            "text": text,
            "speaker": voice,
            "modelId": "coda",
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return _pcm_to_wav(response.content, 22050)
        except Exception as exc:
            logger.error(f"Rime TTS synthesis failed: {exc}")
            return b""


rime_service = RimeTTS()