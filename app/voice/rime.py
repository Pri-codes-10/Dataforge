import io
import logging
import re
import wave
import httpx

from app.core.config import settings

logger = logging.getLogger("sutra.rime")


def preprocess_text_for_tts(text: str) -> str:
    """
    Clean raw LLM text for natural speech synthesis:
    - Removes markdown formatting, bullet points, headers, and code blocks
    - Removes internal debug info, task tags (TASK-0005), and API status messages
    - Removes UI symbols, checkmarks, arrows, and emojis
    - Normalizes pauses and ellipses to natural sentence rhythm
    - Preserves natural punctuation and multilingual scripts
    """
    if not text or not text.strip():
        return ""

    # 1. Remove markdown code blocks and inline code
    clean = re.sub(r"```(?:json|python|[a-zA-Z0-9_-]*)\s*[\s\S]*?```", " ", text)
    clean = re.sub(r"`[^`]+`", " ", clean)

    # 2. Remove internal task / tool / status headers & debug lines
    # e.g., "TASK-0005", "API status: Complete", "Tool Output:", "Status: Complete"
    clean = re.sub(r"(?im)^\s*(?:task[-_]\w+|api status\s*:\s*\w+|status\s*:\s*\w+|tool\s*(?:output|result|execution)\s*:.*)\s*$", " ", clean)
    clean = re.sub(r"\bTASK-[0-9A-Za-z]+\b", " ", clean)
    clean = re.sub(r"(?i)\bapi status:\s*\w+\b", " ", clean)

    # 3. Remove markdown links [text](url) -> text, and images ![alt](url) -> ""
    clean = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", clean)
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)

    # 4. Remove markdown headers, blockquotes, horizontal rules
    clean = re.sub(r"(?m)^#{1,6}\s+", " ", clean)
    clean = re.sub(r"(?m)^>\s+", " ", clean)
    clean = re.sub(r"(?m)^[-*_]{3,}\s*$", " ", clean)

    # 5. Remove bullet list markers at line starts: e.g. "* ", "- ", "1. ", "• "
    clean = re.sub(r"(?m)^[\s*•\-–—]+\s*", " ", clean)
    clean = re.sub(r"(?m)^\s*\d+[\.)]\s*", " ", clean)

    # 6. Remove bold/italic markdown formatting: **text**, *text*, __text__, _text_
    clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
    clean = re.sub(r"\*([^*]+)\*", r"\1", clean)
    clean = re.sub(r"__([^_]+)__", r"\1", clean)
    clean = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", clean)
    clean = re.sub(r"~~([^~]+)~~", r"\1", clean)

    # 7. Remove UI symbols, checkmarks, emojis, and symbols that shouldn't be read aloud
    ui_symbols = r"[✓✔✕✖✗→←↑↓➜➤►•●○■□★☆♦♠♣♥\u2022\u25aa\u25fe\u25cf\u25cb]"
    clean = re.sub(ui_symbols, " ", clean)
    # Remove emoji characters
    clean = re.sub(r"[\U00010000-\U0010ffff]", " ", clean)

    # 8. Pacing & punctuation normalization:
    # Ellipsis at end of sentence becomes period
    clean = re.sub(r"\s*\.{2,}\s*$", ".", clean.strip())
    # Ellipsis after common conversational openers becomes a comma pause
    clean = re.sub(r"(?i)\b(okay|sure|well|yes|no|yep|theek hai)\s*\.{2,}\s*", r"\1, ", clean)
    # Ellipsis between ordinary words becomes a single space to avoid unnatural pauses
    clean = re.sub(r"\s*\.{2,}\s*", " ", clean)
    # Replace multiple hyphens/dashes with a comma
    clean = re.sub(r"[-–—]{2,}", ", ", clean)
    clean = re.sub(r"\s+[-–—]\s+", ", ", clean)

    # 9. Clean up multiple spaces, line breaks into natural punctuation
    lines = [l.strip() for l in clean.splitlines() if l.strip()]
    rebuilt = []
    for line in lines:
        if line and line[-1] not in ".?!,:;।":
            rebuilt.append(line + ".")
        else:
            rebuilt.append(line)

    result = " ".join(rebuilt)
    result = re.sub(r",\s*,+", ", ", result)
    result = re.sub(r",\s*\.", ".", result)
    result = re.sub(r"\.\s*,", ".", result)
    result = re.sub(r"\s+", " ", result).strip()

    return result


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """
    Wrap signed 16-bit PCM audio into a standard RIFF/WAV container.
    Rime's coda model generates 24,000 Hz audio. Packaging it at 24,000 Hz
    ensures correct pitch, speed, and crystal-clear playback.
    """
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

    Synthesizes conversational, human-like voice responses.
    Configured for Rime's coda model with speaker 'vespera'.
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
        Returns 24kHz WAV audio bytes, or b"" if unconfigured.
        """
        if not text or not text.strip():
            return b""

        api_key = settings.RIME_API_KEY
        if not api_key:
            logger.warning("RIME_API_KEY is not configured in .env. TTS synthesis skipped.")
            return b""

        # Preprocess text for natural conversational speech
        clean_text = preprocess_text_for_tts(text)
        if not clean_text:
            return b""

        # Voice selection: default to vespera as requested
        voice = settings.RIME_VOICE or "vespera"
        if voice.lower() in ["aria", "astra", ""]:
            voice = "vespera"

        # Language mapping
        rime_lang = None
        if language in ["en", "eng"]:
            rime_lang = "eng"
        elif language in ["hi", "hin", "mixed"]:
            rime_lang = "hin"
        # Note: For Bengali ('bn'/'ben'), omitting lang allows native multilingual synthesis

        payload = {
            "text": clean_text,
            "speaker": voice,
            "modelId": "coda",
            "reduceLatency": True,
        }
        if rime_lang:
            payload["lang"] = rime_lang

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "audio/pcm",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                # Packaging 24kHz PCM from Rime coda model
                return _pcm_to_wav(response.content, 24000)
        except Exception as exc:
            logger.error(f"Rime TTS synthesis failed: {exc}")
            return b""


rime_service = RimeTTS()