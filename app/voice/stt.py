import logging
from typing import Callable, Optional, Tuple
import httpx

from app.core.config import settings

logger = logging.getLogger("sutra.stt")


class STTService:
    """
    Speech-to-Text Service using Sarvam AI's Saarika model.

    Handles:
    - Audio bytes -> Transcription
    - Automatic multilingual detection (Hindi, English, Bengali, etc.)
    - Code-switched Hinglish transcription
    """

    def __init__(self):
        self.on_transcript: Optional[Callable[[str, bool], None]] = None

    def set_callback(
        self,
        callback: Callable[[str, bool], None],
    ) -> None:
        """
        Register a callback that receives transcriptions.
        callback(transcript, is_final)
        """
        self.on_transcript = callback

    async def process_transcription(
        self,
        transcript: str,
        is_final: bool = True,
    ) -> None:
        """
        Notify listener/WebSocket of a transcription.
        """
        if not transcript.strip():
            return

        if self.on_transcript:
            result = self.on_transcript(
                transcript,
                is_final,
            )
            if hasattr(result, "__await__"):
                await result

    async def send_audio(
        self,
        audio_data: bytes,
        mime_type: str = "audio/webm",
    ) -> Tuple[str, str]:
        """
        Send raw audio bytes to Sarvam STT API (Saarika model) and return
        (transcript, detected_language).
        """
        if not audio_data:
            return "", "unknown"

        api_key = settings.SARVAM_API_KEY
        if not api_key:
            logger.warning("SARVAM_API_KEY is not configured in .env. STT call bypassed.")
            placeholder = "Audio received (SARVAM_API_KEY is not configured in backend .env)"
            await self.process_transcription(placeholder, is_final=True)
            return placeholder, "unknown"

        stt_url = settings.SARVAM_STT_URL
        headers = {
            "api-subscription-key": api_key,
        }

        last_error = ""

        # Determine audio extension and strictly valid MIME type for Sarvam upload
        clean_mime = mime_type.split(";")[0].strip().lower() if mime_type else "audio/webm"
        if audio_data.startswith(b"RIFF") or "wav" in clean_mime:
            ext = "wav"
            upload_mime = "audio/wav"
        elif "mp3" in clean_mime or "mpeg" in clean_mime or audio_data.startswith(b"ID3") or audio_data[:2] == b"\xff\xfb":
            ext = "mp3"
            upload_mime = "audio/mp3"
        elif "ogg" in clean_mime or "opus" in clean_mime:
            ext = "ogg"
            upload_mime = "audio/ogg"
        elif "mp4" in clean_mime or "m4a" in clean_mime:
            ext = "mp4"
            upload_mime = "audio/mp4"
        else:
            ext = "webm"
            upload_mime = "audio/webm"

        filename = f"audio.{ext}"

        # Try latest model saaras:v3 first, fallback to saarika:v2.5
        transcript = ""
        lang_code = "unknown"
        stt_success = False

        for model in ["saaras:v3", "saarika:v2.5"]:
            try:
                files = {
                    "file": (filename, audio_data, upload_mime),
                }
                data = {
                    "model": model,
                    "language_code": "unknown",
                }

                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        stt_url,
                        headers=headers,
                        files=files,
                        data=data,
                    )

                    if response.status_code == 200:
                        res_json = response.json()
                        transcript = res_json.get("transcript", "").strip()
                        lang_code = res_json.get("language_code", "unknown")
                        stt_success = True
                        break

                    elif response.status_code in [400, 404] and model == "saaras:v3":
                        last_error = f"Model {model} returned {response.status_code}: {response.text}"
                        continue
                    else:
                        last_error = f"Sarvam STT returned HTTP {response.status_code}: {response.text}"
                        logger.error(last_error)
            except Exception as e:
                last_error = f"Error calling Sarvam STT ({model}): {str(e)}"
                logger.error(last_error)

        if stt_success:
            if transcript:
                try:
                    await self.process_transcription(transcript, is_final=True)
                except Exception as exc:
                    logger.debug(f"Transcription callback error: {exc}")
                return transcript, lang_code
            return "", lang_code

        if last_error:
            logger.warning(f"[STT Failure] {last_error}")
            err_notice = f"[Sarvam STT Error: {last_error}]"
            try:
                await self.process_transcription(err_notice, is_final=True)
            except Exception:
                pass
            return err_notice, "unknown"

        return "", "unknown"

    async def close(self) -> None:
        """
        Close the STT integration.
        """
        self.on_transcript = None


stt_service = STTService()