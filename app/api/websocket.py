import asyncio
import base64
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.agent import agent
from app.agent.state import ConversationState, Message
from app.agent.tools import execute_tool
from app.voice.language import language_service, LanguageResult
from app.voice.rime import rime_service
from app.voice.stt import stt_service

logger = logging.getLogger("sutra.websocket")
websocket_router = APIRouter()


@websocket_router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    Main realtime communication endpoint for SUTRA.

    Handles:
    - Audio capture (16kHz WAV/webm binary) -> Sarvam STT -> transcript
    - Multilingual language detection (Hindi, English, Bengali, Hinglish)
    - Stable in-memory session lifecycle with task_version stale rejection
    - Non-destructive STOP: aborts active task/playback without disconnecting or clearing history
    - Clean RESET: resets working task state and returns to idle
    - Dynamic task pipeline reflecting actual request without fake tools
    - Rime TTS synthesis and audio dispatch
    """
    await websocket.accept()

    # Determine or generate conversation_id
    query_cid = websocket.query_params.get("conversation_id")
    conversation_id = query_cid.strip() if query_cid else f"conv-{uuid4().hex[:8]}"

    logger.info(f"[WebSocket] Client connected for conversation_id={conversation_id}")

    session_state = ConversationState(session_id=conversation_id)

    # Per-connection task tracking
    active_tool_task: Optional[asyncio.Task] = None
    active_task_info: Optional[Dict[str, Any]] = None

    async def safe_send(payload: dict) -> bool:
        """Safely send a JSON message to client, ignoring disconnect errors."""
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            return False

    async def send_state():
        """Emit current conversation state to the frontend."""
        lang_list = [session_state.language]
        if session_state.is_code_switched:
            lang_list = ["Hindi", "English"] if session_state.language == "hi" else ["Bengali", "English"]
        elif session_state.language == "hi":
            lang_list = ["Hindi"]
        elif session_state.language == "bn":
            lang_list = ["Bengali"]
        else:
            lang_list = ["English"]

        await safe_send({
            "type": "state",
            "conversation_id": conversation_id,
            "data": {
                "intent": session_state.intent,
                "language": lang_list,
                "codeSwitched": session_state.is_code_switched,
                "entities": {
                    "origin": str(session_state.constraints.get("origin", "")),
                    "destination": str(session_state.constraints.get("destination", "")),
                },
                "constraints": session_state.constraints,
                "activeTask": session_state.active_task_id,
                "stateVersion": session_state.task_version,
                "messages": session_state.get_messages(),
            },
        })

    def generate_pipeline_steps(
        intent: Optional[str],
        tool_required: bool = False,
        tool_status: str = "pending",
        response_status: str = "pending",
        rime_status: str = "pending",
    ) -> List[Dict[str, Any]]:
        """Generate dynamic pipeline steps reflecting the ACTUAL current task."""
        if not tool_required or not intent:
            # General conversation / knowledge query: no specialized tool needed
            return [
                {"id": "understand", "label": "Understand request", "status": "completed" if response_status != "pending" or rime_status != "pending" else "running"},
                {"id": "response", "label": "Generate response", "status": response_status},
                {"id": "rime", "label": "Rime voice output", "status": rime_status},
            ]

        origin = session_state.constraints.get("origin", "CCU")
        destination = session_state.constraints.get("destination", "DEL")
        date = session_state.constraints.get("date", "tomorrow")
        max_price = session_state.constraints.get("budget") or session_state.constraints.get("max_price")
        price_str = f" under {max_price}" if max_price else ""

        if intent == "flight_search":
            tool_label = f"Search flights: {origin} to {destination} ({date}){price_str}"
        elif intent == "hotel_search":
            tool_label = f"Search hotels in {destination or origin} ({date}){price_str}"
        elif intent == "web_search":
            tool_label = "Search current information"
        else:
            tool_label = f"Execute {intent.replace('_', ' ').title()}"

        return [
            {"id": "understand", "label": "Understand request", "status": "completed"},
            {"id": "tool", "label": tool_label, "status": tool_status},
            {"id": "response", "label": "Generate response", "status": response_status},
            {"id": "rime", "label": "Rime voice output", "status": rime_status},
        ]

    async def send_pipeline(
        tool_required: bool = False,
        tool_status: str = "pending",
        response_status: str = "pending",
        rime_status: str = "pending",
    ):
        """Broadcast dynamic pipeline steps to client."""
        steps = generate_pipeline_steps(
            session_state.intent,
            tool_required=tool_required,
            tool_status=tool_status,
            response_status=response_status,
            rime_status=rime_status,
        )
        await safe_send({
            "type": "pipeline",
            "steps": steps,
            "isRunning": tool_status == "running" or response_status == "running" or rime_status == "running",
        })

    async def run_pipeline_flow(
        task_id: str,
        task_version: int,
        transcript: str,
        language_result: LanguageResult,
        tool_name: Optional[str] = None,
        tool_label: Optional[str] = None,
    ):
        """
        Asynchronously runs tool execution, response generation, and TTS synthesis.
        Guarantees stale result rejection if task_version changes or Stop/Reset is pressed.
        """
        nonlocal active_task_info

        tool_result = {"result": ""}

        # 1. Tool execution (only if required)
        if tool_name:
            active_task_info = {
                "requestId": task_id,
                "toolName": tool_label,
                "taskVersion": task_version,
                "isCurrent": True,
                "elapsedSeconds": 0.0,
            }

            await safe_send({
                "type": "tool_event",
                "event": "TOOL_STARTED",
                "tool": tool_name,
                "toolName": tool_label,
                "requestId": task_id,
                "taskVersion": task_version,
                "label": f"{tool_label} ({task_id})",
                "status": "running",
                "isCurrent": True,
            })
            await send_pipeline(tool_required=True, tool_status="running")

            tool_args = {
                "origin": str(session_state.constraints.get("origin", "Kolkata")),
                "destination": str(session_state.constraints.get("destination", "Delhi")),
                "date": str(session_state.constraints.get("date", "tomorrow")),
                "max_price": str(session_state.constraints.get("budget") or session_state.constraints.get("max_price", "")),
                "city": str(session_state.constraints.get("destination") or session_state.constraints.get("origin", "Kolkata")),
                "query": transcript,
            }

            tool_result = await execute_tool(
                tool_name=tool_name,
                arguments=tool_args,
                task_id=task_id,
                task_version=task_version,
                state=session_state,
            )

            # Validate task version after tool completes
            if not session_state.is_task_current(task_id, task_version) or tool_result.get("stale"):
                logger.info(f"[Pipeline] Stale tool result rejected for {task_id} (v{task_version} vs current v{session_state.task_version})")
                await safe_send({
                    "type": "stale_result",
                    "requestId": task_id,
                    "isCurrent": False,
                    "message": "Stale result rejected",
                })
                await safe_send({
                    "type": "pipeline_event",
                    "event": "STALE_RESULT_REJECTED",
                    "requestId": task_id,
                    "label": f"Request #{task_id} stale result rejected",
                    "status": "stale",
                })
                return

            if tool_result.get("cancelled"):
                logger.info(f"[Pipeline] Task {task_id} was cancelled.")
                return

            await safe_send({
                "type": "tool_event",
                "event": "TOOL_COMPLETED",
                "tool": tool_name,
                "toolName": tool_label,
                "requestId": task_id,
                "result": tool_result.get("result", "Operation completed"),
                "status": "completed",
                "isCurrent": True,
            })
            await send_pipeline(tool_required=True, tool_status="completed", response_status="running")
        else:
            await send_pipeline(tool_required=False, response_status="running")

        # 2. LLM Spoken Response Generation
        await safe_send({
            "type": "pipeline_event",
            "event": "RESPONSE_STARTED",
            "label": "Generating response",
            "status": "running",
        })

        agent_response = await agent.respond(
            user_text=transcript,
            language=language_result.primary_language,
            tool_result=tool_result.get("result", ""),
            state=session_state,
        )

        # Check staleness after LLM call
        if not session_state.is_task_current(task_id, task_version):
            logger.info(f"[Pipeline] Task {task_id} became stale during LLM response generation.")
            return

        session_state.add_message(
            role="assistant",
            content=agent_response,
            language=language_result.primary_language,
        )

        await safe_send({
            "type": "response",
            "text": agent_response,
            "requestId": task_id,
        })

        await safe_send({
            "type": "pipeline_event",
            "event": "RESPONSE_GENERATED",
            "label": "Response generated",
            "status": "completed",
        })
        await send_pipeline(tool_required=bool(tool_name), tool_status="completed", response_status="completed", rime_status="running")

        # 3. Rime TTS Voice Synthesis
        await safe_send({
            "type": "pipeline_event",
            "event": "RIME_STARTED",
            "label": "Rime voice synthesis",
            "status": "running",
        })

        if language_result.primary_language in ["hi", "mixed"]:
            rime_lang = "hin"
        elif language_result.primary_language in ["bn", "ben"]:
            rime_lang = "ben"
        else:
            rime_lang = "eng"

        audio_bytes = await rime_service.synthesize(
            text=agent_response,
            language=rime_lang,
        )

        # Check staleness before dispatching audio
        if not session_state.is_task_current(task_id, task_version):
            logger.info(f"[Pipeline] Task {task_id} became stale before Rime audio dispatch.")
            return

        if audio_bytes:
            b64_audio = base64.b64encode(audio_bytes).decode("ascii")
            await safe_send({
                "type": "rime_audio",
                "format": "audio/wav",
                "language": rime_lang,
                "requestId": task_id,
                "data": b64_audio,
            })
            await safe_send({
                "type": "pipeline_event",
                "event": "RIME_COMPLETED",
                "label": "Rime audio ready",
                "status": "completed",
            })
            await send_pipeline(tool_required=bool(tool_name), tool_status="completed", response_status="completed", rime_status="completed")
        else:
            await safe_send({"type": "status", "status": "idle"})
            await send_pipeline(tool_required=bool(tool_name), tool_status="completed", response_status="completed", rime_status="completed")

        await send_state()

    async def process_user_utterance(
        transcript: str,
        is_final: bool = True,
        stt_lang_code: str = "",
    ):
        """Handle a transcribed user utterance or direct text message."""
        nonlocal active_tool_task, active_task_info

        clean_transcript = transcript.strip()
        if not clean_transcript:
            await safe_send({
                "type": "error",
                "message": "No speech recognized. Please try speaking again.",
            })
            await safe_send({"type": "status", "status": "idle"})
            return

        # 1. Dispatch transcript event
        await safe_send({
            "type": "transcript",
            "text": clean_transcript,
            "final": is_final,
        })

        if not is_final:
            return

        # 2. Multilingual detection
        lang_res = language_service.detect(clean_transcript, stt_lang_code=stt_lang_code)
        await safe_send({
            "type": "language",
            "language": lang_res.primary_language,
            "code_switched": lang_res.is_code_switched,
            "languages": lang_res.languages,
            "label": lang_res.label,
        })

        await safe_send({
            "type": "pipeline_event",
            "event": "LANGUAGE_DETECTED",
            "label": f"Language: {lang_res.label}",
            "status": "completed",
        })

        session_state.add_message(
            role="user",
            content=clean_transcript,
            language=lang_res.label,
        )

        # 3. Robust Intent & Constraint Detection (Phase 6 & 7)
        t_lower = clean_transcript.lower()

        # Check explicit flight keywords
        is_flight_intent = any(w in t_lower for w in [
            "flight", "flights", "ticket", "tickets", "udaan", "fly", "plane",
            "airplane", "airport", "airline", "airways"
        ])

        # Check travel constraint continuation (e.g., "Nahi, Mumbai jaana hai")
        is_flight_continuation = (
            session_state.intent == "flight_search"
            and any(w in t_lower for w in ["jaana", "chahiye", "delhi", "mumbai", "kolkata", "chennai", "bangalore", "saturday", "tomorrow", "kal", "budget", "6000", "rupees", "instead"])
        )

        is_hotel_intent = any(w in t_lower for w in ["hotel", "hotels", "room", "stay", "resort"])

        is_web_search_intent = any(w in t_lower for w in [
            "weather", "temperature", "rain", "forecast", "match", "cricket", "score", "news"
        ])

        if is_flight_intent or is_flight_continuation:
            session_state.intent = "flight_search"
            tool_name = "search_flights"
            tool_label = "Search flights"
        elif is_hotel_intent:
            session_state.intent = "hotel_search"
            tool_name = "search_hotels"
            tool_label = "Checking hotels"
        elif is_web_search_intent:
            session_state.intent = "web_search"
            tool_name = "search_information"
            tool_label = "Searching current weather" if any(w in t_lower for w in ["weather", "rain", "temperature"]) else "Searching web"
        else:
            # General knowledge / LLM chat / concepts: no tool needed
            session_state.intent = None
            tool_name = None
            tool_label = None

        # Update entities / constraints if flight or hotel
        if session_state.intent in ["flight_search", "hotel_search"]:
            has_new_constraint = False
            if "kolkata" in t_lower or "calcutta" in t_lower:
                session_state.update_constraint("origin", "Kolkata")
                has_new_constraint = True
            if "delhi" in t_lower:
                session_state.update_constraint("destination", "Delhi")
                has_new_constraint = True
            elif "mumbai" in t_lower or "bombay" in t_lower:
                session_state.update_constraint("destination", "Mumbai")
                has_new_constraint = True
            elif "bangalore" in t_lower or "bengaluru" in t_lower:
                session_state.update_constraint("destination", "Bangalore")
                has_new_constraint = True

            if "saturday" in t_lower or "shanivar" in t_lower or "shonibar" in t_lower:
                session_state.update_constraint("date", "Saturday")
                has_new_constraint = True
            elif "tomorrow" in t_lower or "kal" in t_lower or "agami" in t_lower:
                session_state.update_constraint("date", "Tomorrow")
                has_new_constraint = True

            if any(p in t_lower for p in ["6000", "six thousand", "6k", "hazaar", "hazar", "chhoy hajar", "che hazar"]):
                session_state.update_constraint("budget", "₹6,000")
                has_new_constraint = True

            if has_new_constraint:
                await safe_send({
                    "type": "pipeline_event",
                    "event": "CONSTRAINT_UPDATED",
                    "label": "Constraint updated",
                    "status": "completed",
                })

        # 4. Invalidate running task if a new utterance arrives (Stale Task Protection)
        if active_tool_task and not active_tool_task.done():
            old_req_id = (active_task_info or {}).get("requestId", "TASK-0001")
            logger.info(f"[Stale Protection] Active task {old_req_id} superseded by new utterance: '{clean_transcript}'")

            await safe_send({
                "type": "stale_result",
                "requestId": old_req_id,
                "isCurrent": False,
                "message": f"Request #{old_req_id} stale result rejected",
            })
            await safe_send({
                "type": "pipeline_event",
                "event": "STALE_RESULT_REJECTED",
                "requestId": old_req_id,
                "label": f"Request #{old_req_id} stale result rejected",
                "status": "stale",
            })

            try:
                active_tool_task.cancel()
            except Exception:
                pass

        # 5. Start new task version
        new_task_id = session_state.start_task()
        current_version = session_state.task_version

        await safe_send({
            "type": "pipeline_event",
            "event": "STATE_UPDATED",
            "label": f"State updated (v{current_version})",
            "status": "completed",
        })
        await send_state()
        await send_pipeline(
            tool_required=bool(tool_name),
            tool_status="running" if tool_name else "completed",
            response_status="running" if not tool_name else "pending",
        )

        # 6. Launch pipeline concurrently in background
        active_tool_task = asyncio.create_task(
            run_pipeline_flow(
                task_id=new_task_id,
                task_version=current_version,
                transcript=clean_transcript,
                language_result=lang_res,
                tool_name=tool_name,
                tool_label=tool_label,
            )
        )

    # Initial state on connection
    await send_state()
    await send_pipeline(tool_required=False)

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
                    "label": "Transcribing with Sarvam...",
                    "status": "running",
                })

                transcript, lang_code = await stt_service.send_audio(
                    audio_data=audio_data,
                    mime_type="audio/webm",
                )

                await process_user_utterance(transcript, is_final=True, stt_lang_code=lang_code)

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
                    mime_type = message.get("mimeType", "audio/wav")
                    if b64_str:
                        try:
                            audio_data = base64.b64decode(b64_str)
                            await safe_send({
                                "type": "pipeline_event",
                                "event": "REQUEST_RECEIVED",
                                "label": "Transcribing with Sarvam...",
                                "status": "running",
                            })
                            transcript, lang_code = await stt_service.send_audio(
                                audio_data=audio_data,
                                mime_type=mime_type,
                            )
                            await process_user_utterance(transcript, is_final=True, stt_lang_code=lang_code)
                        except Exception as e:
                            logger.error(f"[WebSocket Audio Decode Error] {e}")
                            await safe_send({
                                "type": "error",
                                "message": f"Audio processing error: {str(e)}",
                            })
                            await safe_send({"type": "status", "status": "idle"})

                # Text transcription directly sent
                elif message_type == "transcription":
                    await process_user_utterance(
                        transcript=message.get("text", ""),
                        is_final=message.get("final", True),
                    )

                # NON-DESTRUCTIVE STOP (Phase 2 & Phase 3):
                # Stops active task and playback WITHOUT disconnecting or creating a new conversation
                elif message_type == "stop":
                    logger.info(f"[WebSocket] Stop requested for conversation {conversation_id}")
                    if active_tool_task and not active_tool_task.done():
                        active_tool_task.cancel()
                    session_state.cancel_task()

                    await safe_send({
                        "type": "pipeline_event",
                        "event": "STOPPED",
                        "label": "Task stopped",
                        "status": "stopped",
                    })
                    await safe_send({"type": "status", "status": "idle"})
                    await send_pipeline(tool_required=False)
                    await send_state()

                # RESET SESSION (Phase 3):
                # Clears active task, constraints, and returns state to idle
                elif message_type == "reset":
                    logger.info(f"[WebSocket] Reset requested for conversation {conversation_id}")
                    if active_tool_task and not active_tool_task.done():
                        active_tool_task.cancel()
                    session_state.reset_active()

                    await safe_send({
                        "type": "reset_complete",
                        "conversation_id": conversation_id,
                        "task_version": session_state.task_version,
                    })
                    await safe_send({
                        "type": "pipeline_event",
                        "event": "SESSION_RESET",
                        "label": f"Session reset (v{session_state.task_version})",
                        "status": "completed",
                    })
                    await safe_send({"type": "status", "status": "idle"})
                    await send_pipeline(tool_required=False)
                    await send_state()

                # Task cancellation
                elif message_type == "cancel":
                    if active_tool_task and not active_tool_task.done():
                        active_tool_task.cancel()
                    session_state.cancel_task()

                    await safe_send({
                        "type": "pipeline_event",
                        "event": "CANCELLED",
                        "label": "Task cancelled",
                        "status": "cancelled",
                    })
                    await safe_send({"type": "status", "status": "idle"})
                    await send_pipeline(tool_required=False)
                    await send_state()

                # User interruption (Barge-in)
                elif message_type == "interrupt":
                    if active_tool_task and not active_tool_task.done():
                        active_tool_task.cancel()
                    session_state.cancel_task()

                    await safe_send({
                        "type": "pipeline_event",
                        "event": "USER_INTERRUPTED",
                        "label": "User interrupted",
                        "status": "completed",
                    })
                    await send_state()

                elif message_type == "ping":
                    await safe_send({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client disconnected for conversation {conversation_id}")
        if active_tool_task and not active_tool_task.done():
            active_tool_task.cancel()

    except Exception as exc:
        logger.error(f"[WebSocket Error] {exc}")
        await safe_send({
            "type": "error",
            "message": str(exc),
        })

    finally:
        logger.info(f"[WebSocket] Connection closed for conversation {conversation_id}")