import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.agent import agent
from app.voice.language import language_service
from app.voice.stt import stt_service


websocket_router = APIRouter()


@websocket_router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    Main realtime communication endpoint.

    The frontend sends audio/transcription data through WebSocket.
    Your friend's voice model handles the actual STT.
    The backend handles language detection, agent processing,
    conversation state, and tool orchestration.
    """

    await websocket.accept()

    print("[WebSocket] Client connected")

    async def handle_transcript(
        transcript: str,
        is_final: bool = True,
    ):
        """Process a transcription received from the voice model."""

        if not transcript.strip():
            return

        await websocket.send_json({
            "type": "transcript",
            "text": transcript,
            "final": is_final,
        })

        # Do not send partial transcripts to the LLM.
        if not is_final:
            return

        # Detect language / Hinglish
        language_result = language_service.detect(transcript)

        await websocket.send_json({
            "type": "language",
            "language": language_result.primary_language,
            "code_switched": language_result.is_code_switched,
        })

        # Generate response
        response = await agent.respond(
            user_text=transcript,
            language=language_result.primary_language,
        )

        await websocket.send_json({
            "type": "response",
            "text": response,
        })

    stt_service.set_callback(handle_transcript)

    try:
        while True:
            data = await websocket.receive()

            # Binary data can be forwarded to the friend's
            # voice/STT model when its integration is connected.
            if data.get("bytes") is not None:
                audio_data = data["bytes"]

                await websocket.send_json({
                    "type": "audio_received",
                    "size": len(audio_data),
                })

            # JSON/text control messages
            elif data.get("text") is not None:
                try:
                    message = json.loads(data["text"])
                except json.JSONDecodeError:
                    message = {
                        "type": data["text"]
                    }

                message_type = message.get("type")

                # Your friend's model can send its transcription
                # directly to this backend.
                if message_type == "transcription":
                    await stt_service.process_transcription(
                        transcript=message.get("text", ""),
                        is_final=message.get("final", True),
                    )

                elif message_type == "ping":
                    await websocket.send_json({
                        "type": "pong"
                    })

                elif message_type == "stop":
                    break

    except WebSocketDisconnect:
        print("[WebSocket] Client disconnected")

    except Exception as exc:
        print(f"[WebSocket Error] {exc}")

        try:
            await websocket.send_json({
                "type": "error",
                "message": str(exc),
            })
        except Exception:
            pass

    finally:
        await stt_service.close()
        print("[WebSocket] Connection closed")