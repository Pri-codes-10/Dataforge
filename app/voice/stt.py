from typing import Callable, Optional


class STTService:
    """
    Adapter for the friend's voice/STT model.

    The friend's model is responsible for:
        Audio -> Transcription

    This class provides a simple interface for the backend to
    receive those transcriptions.
    """

    def __init__(self):
        self.on_transcript: Optional[
            Callable[[str, bool], None]
        ] = None

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
        Receive transcription from the friend's model.

        The friend's model should call this method after
        converting speech to text.
        """

        if not transcript.strip():
            return

        if self.on_transcript:
            result = self.on_transcript(
                transcript,
                is_final,
            )

            # Support both normal and async callbacks.
            if hasattr(result, "__await__"):
                await result

    async def send_audio(self, audio_data: bytes) -> None:
        """
        Placeholder interface for the friend's model.

        Audio processing itself is NOT implemented here.
        The friend's voice model handles audio -> text.
        """

        raise NotImplementedError(
            "Audio processing is handled by the friend's voice model."
        )

    async def close(self) -> None:
        """
        Close the STT integration.
        """

        self.on_transcript = None


stt_service = STTService()