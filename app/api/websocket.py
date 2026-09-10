import asyncio
import base64
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agent.agent import agent
from app.agent.state import conversation_state
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
    - Audio capture / binary stream -> Sarvam STT -> transcript
    - Text transcriptions from client
    - Multilingual language detection (Hindi, English, Bengali, Hinglish)
    - Conversation state synchronization with task versioning
    - Non-blocking tool execution & dynamic pipeline lifecycle
    - Stale result rejection when task changes mid-execution
    - Rime TTS synthesis and audio dispatch
    """
    await websocket.accept()
    logger.info("[WebSocket] Client connected")

    # Per-connection state
    active_tool_task: Optional[asyncio.Task] = None
    active_task_info: Optional[Dict[str, Any]] = None
    last_stale_info: Optional[Dict[str, Any]] = None

    async def safe_send(payload: dict) -> bool:
        """Safely send a JSON message to client, ignoring disconnect errors."""
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            return False

    async def send_state():
        """Emit current conversation state to the frontend."""
        lang_list = [conversation_state.language]
        if conversation_state.is_code_switched:
            lang_list = ["Hindi", "English"] if conversation_state.language == "hi" else ["Bengali", "English"]
        elif conversation_state.language == "hi":
            lang_list = ["Hindi"]
        elif conversation_state.language == "bn":
            lang_list = ["Bengali"]
        else:
            lang_list = ["English"]

        await safe_send({
            "type": "state",
            "data": {
                "intent": conversation_state.intent,
                "language": lang_list,
                "codeSwitched": conversation_state.is_code_switched,
                "entities": {
                    "origin": conversation_state.constraints.get("origin", ""),
                    "destination": conversation_state.constraints.get("destination", ""),
                },
                "constraints": conversation_state.constraints,
                "activeTask": conversation_state.active_task_id,
                "stateVersion": conversation_state.task_version,
                "messages": conversation_state.get_messages(),
            },
        })

    def generate_pipeline_steps(
        intent: Optional[str],
        tool_status: str = "pending",
        response_status: str = "pending",
        rime_status: str = "pending",
    ) -> List[Dict[str, Any]]:
        """Generate dynamic pipeline steps reflecting current intent and task."""
        origin = conversation_state.constraints.get("origin", "Kolkata")
        destination = conversation_state.constraints.get("destination", "Delhi")
        date = conversation_state.constraints.get("date", "tomorrow")
        max_price = conversation_state.constraints.get("budget") or conversation_state.constraints.get("max_price")
        price_str = f" under {max_price}" if max_price else ""

        if intent == "flight_search":
            tool_label = f"Search flights: {origin} to {destination} ({date}){price_str}"
        elif intent == "hotel_search":
            tool_label = f"Search hotels in {origin or destination} ({date}){price_str}"
        elif intent:
            tool_label = f"Execute {intent.replace('_', ' ').title()}"
        else:
            tool_label = "Search information"

        return [
            {"id": "understand", "label": "Understand request", "status": "completed"},
            {"id": "tool", "label": tool_label, "status": tool_status},
            {"id": "response", "label": "Generate response", "status": response_status},
            {"id": "rime", "label": "Rime voice output", "status": rime_status},
        ]

    async def send_pipeline(
        tool_status: str = "pending",
        response_status: str = "pending",
        rime_status: str = "pending",
    ):
        """Broadcast dynamically generated pipeline steps to the client."""
        steps = generate_pipeline_steps(
            conversation_state.intent,
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
    ):
        """
        Asynchronously runs tool execution, response generation, and TTS synthesis.
        If task_version becomes stale during execution, tool result is rejected.
        """
        nonlocal active_task_info, last_stale_info

        tool_name = "search_flights" if conversation_state.intent == "flight_search" else "search_hotels" if conversation_state.intent == "hotel_search" else "search_information"
        tool_label = "Flight Search API" if conversation_state.intent == "flight_search" else "Hotel Search API" if conversation_state.intent == "hotel_search" else "Search API"

        active_task_info = {
            "requestId": task_id,
            "toolName": tool_label,
            "taskVersion": task_version,
            "isCurrent": True,
            "elapsedSeconds": 0.0,
        }

        # Step 2: Tool execution starts
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
        await send_pipeline(tool_status="running")

        # Execute tool
        tool_args = {
            "origin": conversation_state.constraints.get("origin", "Kolkata"),
            "destination": conversation_state.constraints.get("destination", "Delhi"),
            "date": conversation_state.constraints.get("date", "tomorrow"),
            "max_price": conversation_state.constraints.get("budget") or conversation_state.constraints.get("max_price", ""),
            "city": conversation_state.constraints.get("origin") or conversation_state.constraints.get("destination", "Kolkata"),
            "query": transcript,
        }

        tool_result = await execute_tool(
            tool_name=tool_name,
            arguments=tool_args,
            task_id=task_id,
            task_version=task_version,
        )

        # Check for stale result
        if not conversation_state.is_task_current(task_id, task_version) or tool_result.get("stale"):
            logger.info(f"[Pipeline] Stale tool result detected for {task_id} (v{task_version})")
            last_stale_info = {
                "requestId": task_id,
                "isCurrent": False,
                "message": "Stale result rejected",
            }
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
            # Do not proceed with outdated response
            return

        if tool_result.get("cancelled"):
            logger.info(f"[Pipeline] Task {task_id} was cancelled.")
            return

        # Tool Completed
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
        await send_pipeline(tool_status="completed", response_status="running")

        # Step 3: LLM Response Generation
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
        )

        # Re-check staleness after LLM call
        if not conversation_state.is_task_current(task_id, task_version):
            logger.info(f"[Pipeline] Task {task_id} became stale during response generation.")
            return

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
        await send_pipeline(tool_status="completed", response_status="completed", rime_status="running")

        # Step 4: Rime TTS Voice Output
        await safe_send({
            "type": "pipeline_event",
            "event": "RIME_STARTED",
            "label": "Rime voice synthesis",
            "status": "running",
        })

        rime_lang = "hin" if language_result.primary_language in ["hi", "mixed"] else "eng"
        audio_bytes = await rime_service.synthesize(
            text=agent_response,
            language=rime_lang,
        )

        # Re-check staleness before playing audio
        if not conversation_state.is_task_current(task_id, task_version):
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
            await send_pipeline(tool_status="completed", response_status="completed", rime_status="completed")
        else:
            # Rime synthesis skipped or empty; cleanly signal completion
            await safe_send({
                "type": "status",
                "status": "idle",
            })
            await send_pipeline(tool_status="completed", response_status="completed", rime_status="completed")

        await send_state()

    async def process_user_utterance(
        transcript: str,
        is_final: bool = True,
        stt_lang_code: str = "",
    ):
        """Handle a transcribed user utterance or direct text message."""
        nonlocal active_tool_task, active_task_info, last_stale_info

        clean_transcript = transcript.strip()
        if not clean_transcript:
            await safe_send({
                "type": "error",
                "message": "No speech recognized. Please try speaking again.",
            })
            await safe_send({
                "type": "status",
                "status": "idle",
            })
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

        # 3. Intent & Constraint Extraction
        t_lower = clean_transcript.lower()
        if any(w in t_lower for w in ["flight", "ticket", "travel", "jaana", "udaan", "flite", "fly"]):
            conversation_state.intent = "flight_search"
        elif any(w in t_lower for w in ["hotel", "room", "stay", "resort"]):
            conversation_state.intent = "hotel_search"
        elif not conversation_state.intent:
            conversation_state.intent = "flight_search"

        # Update entities / constraints
        has_new_constraint = False
        if "kolkata" in t_lower or "calcutta" in t_lower:
            conversation_state.update_constraint("origin", "Kolkata")
            has_new_constraint = True
        if "delhi" in t_lower:
            conversation_state.update_constraint("destination", "Delhi")
            has_new_constraint = True
        elif "mumbai" in t_lower or "bombay" in t_lower:
            conversation_state.update_constraint("destination", "Mumbai")
            has_new_constraint = True

        if "saturday" in t_lower or "shanivar" in t_lower or "shonibar" in t_lower:
            conversation_state.update_constraint("date", "Saturday")
            has_new_constraint = True
        elif "tomorrow" in t_lower or "kal" in t_lower or "agami" in t_lower:
            conversation_state.update_constraint("date", "Tomorrow")
            has_new_constraint = True

        if any(p in t_lower for p in ["6000", "six thousand", "6k", "hazaar", "hazar", "chhoy hajar", "che hazar"]):
            conversation_state.update_constraint("budget", "₹6,000")
            has_new_constraint = True

        if has_new_constraint:
            await safe_send({
                "type": "pipeline_event",
                "event": "CONSTRAINT_UPDATED",
                "label": "Constraint updated",
                "status": "completed",
            })

        # 4. Check if a previously running tool is now superseded/stale
        if active_tool_task and not active_tool_task.done():
            old_req_id = (active_task_info or {}).get("requestId", "TASK-0001")
            logger.info(f"[Stale Protection] Active task {old_req_id} superseded by new utterance: '{clean_transcript}'")

            last_stale_info = {
                "requestId": old_req_id,
                "isCurrent": False,
                "message": "Stale result rejected",
            }

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
        new_task_id = conversation_state.start_task()
        current_version = conversation_state.task_version

        await safe_send({
            "type": "pipeline_event",
            "event": "STATE_UPDATED",
            "label": f"State updated (v{current_version})",
            "status": "completed",
        })
        await send_state()
        await send_pipeline(tool_status="running")

        # 6. Launch pipeline concurrently in background so WebSocket receive loop is NEVER blocked
        active_tool_task = asyncio.create_task(
            run_pipeline_flow(
                task_id=new_task_id,
                task_version=current_version,
                transcript=clean_transcript,
                language_result=lang_res,
            )
        )

    # Send initial connection state and initial dynamic pipeline
    await send_state()
    await send_pipeline()

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
                    mime_type = message.get("mimeType", "audio/webm")
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

                # Reset session
                elif message_type == "reset":
                    if active_tool_task and not active_tool_task.done():
                        active_tool_task.cancel()
                    conversation_state.reset()
                    await safe_send({
                        "type": "pipeline_event",
                        "event": "SESSION_RESET",
                        "label": "Session reset",
                        "status": "completed",
                    })
                    await send_state()
                    await send_pipeline()

                # Task cancellation
                elif message_type == "cancel":
                    if active_tool_task and not active_tool_task.done():
                        active_tool_task.cancel()
                    conversation_state.cancel_task()
                    await safe_send({
                        "type": "pipeline_event",
                        "event": "CANCELLED",
                        "label": "Task cancelled",
                        "status": "cancelled",
                    })
                    await send_state()
                    await send_pipeline()

                # User interruption
                elif message_type == "interrupt":
                    if active_tool_task and not active_tool_task.done():
                        active_tool_task.cancel()
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
        if active_tool_task and not active_tool_task.done():
            active_tool_task.cancel()

    except Exception as exc:
        logger.error(f"[WebSocket Error] {exc}")
        await safe_send({
            "type": "error",
            "message": str(exc),
        })

    finally:
        logger.info("[WebSocket] Connection closed")