import base64
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.agent import agent
from app.agent.state import conversation_state
from app.agent.tools import execute_tool
from app.voice.language import language_service
from app.voice.rime import rime_service
from app.voice.stt import stt_service

logger = logging.getLogger("sutra.websocket")
websocket_router = APIRouter()


@websocket_router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    Main realtime communication endpoint for SUTRA.

    Handles:
    - Audio capture / binary stream -> Sarvam STT -> transcript
    - Text transcriptions from client or model
    - Multilingual language detection (Hindi, English, Hinglish)
    - Conversation state synchronization
    - Tool execution & pipeline lifecycle events
    - Rime TTS synthesis and audio dispatch
    """

    await websocket.accept()
    logger.info("[WebSocket] Client connected")

    async def safe_send(payload: dict) -> bool:
        """Safely send a JSON message to client, ignoring disconnect errors."""
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            return False

    async def send_state():
        """Emit current conversation state to the frontend."""
        await safe_send({
            "type": "state",
            "data": {
                "intent": conversation_state.intent,
                "language": [conversation_state.language],
                "codeSwitched": conversation_state.is_code_switched,
                "entities": {
                    "origin": conversation_state.constraints.get("origin", ""),
                    "destination": conversation_state.constraints.get("destination", ""),
                },
                "constraints": conversation_state.constraints,
                "activeTask": conversation_state.active_task_id or (f"TASK-{conversation_state.task_version:04d}" if conversation_state.task_version > 0 else None),
                "stateVersion": conversation_state.task_version,
                "messages": conversation_state.get_messages(),
            },
        })

    async def handle_transcript(
        transcript: str,
        is_final: bool = True,
    ):
        """Process a transcription received from audio STT or client."""
        if not transcript or not transcript.strip():
            return

        # 1. Send user transcript
        await safe_send({
            "type": "transcript",
            "text": transcript,
            "final": is_final,
        })

        if not is_final:
            return

        # 2. Detect language (Hindi, English, Mixed/Hinglish)
        language_result = language_service.detect(transcript)
        await safe_send({
            "type": "language",
            "language": language_result.primary_language,
            "code_switched": language_result.is_code_switched,
        })

        await safe_send({
            "type": "pipeline_event",
            "event": "LANGUAGE_DETECTED",
            "label": f"Language: {language_result.primary_language.upper()}",
            "status": "completed",
        })

        # 3. Extract intent and constraints dynamically
        t_lower = transcript.lower()
        has_new_constraint = False

        if any(w in t_lower for w in ["flight", "ticket", "hotel", "travel", "jaana", "udaan", "search"]):
            if not conversation_state.intent:
                conversation_state.intent = "flight_search"
                await safe_send({
                    "type": "pipeline_event",
                    "event": "INTENT_EXTRACTED",
                    "label": "Intent extracted: Flight Search",
                    "status": "completed",
                })

        # Update entities / constraints from utterance
        if "kolkata" in t_lower:
            conversation_state.update_constraint("origin", "Kolkata")
            has_new_constraint = True
        if "delhi" in t_lower:
            conversation_state.update_constraint("destination", "Delhi")
            has_new_constraint = True
        if "mumbai" in t_lower:
            conversation_state.update_constraint("destination", "Mumbai")
            has_new_constraint = True
        if "saturday" in t_lower or "shanivar" in t_lower:
            conversation_state.update_constraint("date", "Saturday")
            has_new_constraint = True
        elif "tomorrow" in t_lower or "kal" in t_lower:
            conversation_state.update_constraint("date", "Tomorrow")
            has_new_constraint = True

        if any(p in t_lower for p in ["6000", "six thousand", "6k", "hazaar", "hazar"]):
            conversation_state.update_constraint("budget", "₹6,000")
            has_new_constraint = True

        if has_new_constraint:
            await safe_send({
                "type": "pipeline_event",
                "event": "CONSTRAINT_UPDATED",
                "label": "Constraint updated",
                "status": "completed",
            })

        await safe_send({
            "type": "pipeline_event",
            "event": "STATE_UPDATED",
            "label": f"State updated (v{conversation_state.task_version})",
            "status": "completed",
        })

        # Emit updated state
        await send_state()

        # 4. Optional Tool Execution for demo
        task_id = conversation_state.active_task_id or f"TASK-{conversation_state.task_version:04d}"
        if conversation_state.intent:
            await safe_send({
                "type": "pipeline_event",
                "event": "TOOL_STARTED",
                "label": "Flight Search API",
                "tool": "search_information",
                "requestId": task_id,
                "status": "running",
            })

        # 5. Generate agent response
        response = await agent.respond(
            user_text=transcript,
            language=language_result.primary_language,
        )

        await safe_send({
            "type": "response",
            "text": response,
        })

        await safe_send({
            "type": "pipeline_event",
            "event": "RESPONSE_GENERATED",
            "label": "Response generated",
            "status": "completed",
        })

        if conversation_state.intent:
            await safe_send({
                "type": "pipeline_event",
                "event": "TOOL_COMPLETED",
                "label": "Flight Search API complete",
                "status": "completed",
            })

        # 6. Rime TTS Voice Output
        await safe_send({
            "type": "pipeline_event",
            "event": "RIME_STARTED",
            "label": "Rime voice output synthesis",
            "status": "running",
        })

        rime_lang = "hin" if language_result.primary_language == "hi" else "eng"
        audio_bytes = await rime_service.synthesize(
            text=response,
            language=rime_lang,
        )

        if audio_bytes:
            b64_audio = base64.b64encode(audio_bytes).decode("ascii")
            await safe_send({
                "type": "rime_audio",
                "format": "audio/wav",
                "language": rime_lang,
                "request_id": task_id,
                "data": b64_audio,
            })
            await safe_send({
                "type": "pipeline_event",
                "event": "RIME_COMPLETED",
                "label": "Rime audio ready",
                "status": "completed",
            })

        # Send final state
        await send_state()

    stt_service.set_callback(handle_transcript)

    # Send initial state on connection
    await send_state()

    try:
        while True:
            data = await websocket.receive()

            # Binary audio data from microphone
            if data.get("bytes") is not None:
                audio_data = data["bytes"]
                logger.info(f"[WebSocket] Received {len(audio_data)} audio bytes")

                await safe_send({
                    "type": "pipeline_event",
                    "event": "REQUEST_RECEIVED",
                    "label": "Processing audio input",
                    "status": "running",
                })

                transcript, lang_code = await stt_service.send_audio(
                    audio_data=audio_data,
                    mime_type="audio/webm",
                )

            # JSON text control messages
            elif data.get("text") is not None:
                try:
                    message = json.loads(data["text"])
                except json.JSONDecodeError:
                    message = {"type": data["text"]}

                message_type = message.get("type")

                # Audio transmitted as base64 string
                if message_type == "audio":
                    b64_str = message.get("data", "")
                    mime_type = message.get("mimeType", "audio/webm")
                    if b64_str:
                        audio_data = base64.b64decode(b64_str)
                        await safe_send({
                            "type": "pipeline_event",
                            "event": "REQUEST_RECEIVED",
                            "label": "Audio received",
                            "status": "running",
                        })
                        await stt_service.send_audio(
                            audio_data=audio_data,
                            mime_type=mime_type,
                        )

                # Text transcription directly sent
                elif message_type == "transcription":
                    await stt_service.process_transcription(
                        transcript=message.get("text", ""),
                        is_final=message.get("final", True),
                    )

                # Task cancellation
                elif message_type == "cancel":
                    conversation_state.cancel_task()
                    await safe_send({
                        "type": "pipeline_event",
                        "event": "CANCELLED",
                        "label": "Task cancelled",
                        "status": "cancelled",
                    })
                    await send_state()

                # User interruption
                elif message_type == "interrupt":
                    await safe_send({
                        "type": "pipeline_event",
                        "event": "USER_INTERRUPTED",
                        "label": "User interrupted",
                        "status": "completed",
                    })

                elif message_type == "ping":
                    await safe_send({"type": "pong"})

                elif message_type == "stop":
                    break

    except WebSocketDisconnect:
        logger.info("[WebSocket] Client disconnected")

    except Exception as exc:
        logger.error(f"[WebSocket Error] {exc}")
        await safe_send({
            "type": "error",
            "message": str(exc),
        })

    finally:
        await stt_service.close()
        logger.info("[WebSocket] Connection closed")