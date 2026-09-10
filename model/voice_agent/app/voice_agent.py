"""Local microphone console or LiveKit room worker; all spoken output uses Rime."""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

from .config import ROOT, load, require


def main():
    load()
    # Let help/download-files work without credentials. Console needs provider
    # credentials only; dev/start also connect to a LiveKit server.
    command = sys.argv[1] if len(sys.argv) > 1 else "--help"
    if command in {"console", "dev", "start", "connect"}:
        try:
            require(room=command != "console")
        except ValueError as error:
            raise SystemExit(str(error)) from None

    from livekit import agents
    from livekit.agents import Agent, AgentSession, AgentServer, StopResponse
    from livekit.plugins import deepgram, rime, silero
    import aiohttp
    from .gemini_planner import GeminiPlanner
    from .orchestrator import Orchestrator
    from .inventory import FlightSearch
    from .live_playback import LiveKitPlayback

    server = AgentServer()

    @server.rtc_session(agent_name="rime-continuity")
    async def entrypoint(ctx: agents.JobContext):
        require(room=command != "console")
        folder = ROOT / "runs"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = folder / f"{stamp}-{os.getpid()}.jsonl"
        stream = path.open("a", encoding="utf-8")
        def record(event):
            if stream.closed:
                return
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush()

        client = aiohttp.ClientSession()
        tts = rime.TTS(model=os.environ["RIME_MODEL"], speaker=os.environ["RIME_VOICE"],
                       lang=os.environ["RIME_LANGUAGE"], use_websocket=False,
                       base_url=os.getenv("RIME_HTTP_URL", "https://users.rime.ai/v1/rime-tts"),
                       sample_rate=24000)
        session = AgentSession(
            stt=deepgram.STT(model=os.getenv("STT_MODEL", "nova-3"),
                            language=os.getenv("STT_LANGUAGE", "multi")),
            tts=tts, vad=silero.VAD.load(),
            turn_handling={"turn_detection": "vad",
                           "interruption": {"mode": "vad", "resume_false_interruption": False},
                           "preemptive_generation": {"enabled": False}},
        )
        playback = LiveKitPlayback(session)
        engine = Orchestrator(GeminiPlanner(client, os.environ["LLM_MODEL"], os.environ["GEMINI_API_KEY"], os.environ["RIME_LANGUAGE"]),
                              {"search": FlightSearch(float(os.getenv("DEMO_TOOL_DELAY", "4")), os.environ["RIME_LANGUAGE"])},
                              playback, event_sink=record, language=os.environ["RIME_LANGUAGE"])
        playback.event_sink = engine.log
        turns = set()

        class VoiceAgent(Agent):
            def __init__(self):
                super().__init__(instructions="Voice travel demo; external orchestrator owns replies.")

            async def on_user_turn_completed(self, turn_ctx, new_message):
                if new_message.text_content:
                    task = asyncio.create_task(engine.accept(new_message.text_content))
                    turns.add(task)
                    def completed(done):
                        turns.discard(done)
                        if not done.cancelled() and done.exception():
                            engine.log("turn_failed", error_type=type(done.exception()).__name__)
                    task.add_done_callback(completed)
                # No second implicit LLM response alongside the orchestrator.
                raise StopResponse()

        @session.on("user_state_changed")
        def user_state(event):
            if event.new_state == "speaking":
                engine.begin_input(barge_in=bool(playback.handles))

        @session.on("error")
        def provider_error(event):
            engine.log("provider_error", error_type=type(event.error).__name__)

        async def shutdown():
            for task in tuple(turns):
                task.cancel()
            await asyncio.gather(*tuple(turns), return_exceptions=True)
            await engine.close()
            await session.aclose()
            await client.close()
            stream.close()

        ctx.add_shutdown_callback(shutdown)
        engine.log("provider_configuration", tts="Rime", model=os.environ["RIME_MODEL"],
                   voice=os.environ["RIME_VOICE"], language=os.environ["RIME_LANGUAGE"],
                   endpoint=os.getenv("RIME_HTTP_URL", "https://users.rime.ai/v1/rime-tts"),
                   format="PCM signed 16-bit mono 24000 Hz", transport="LiveKit Rime streaming HTTP",
                   stt_model=os.getenv("STT_MODEL", "nova-3"), stt_language=os.getenv("STT_LANGUAGE", "multi"),
                   llm_provider="Gemini", llm_model=os.environ["LLM_MODEL"], cache_mode="uncached", inventory="synthetic")
        await session.start(room=ctx.room, agent=VoiceAgent(), record=False)
        engine._speak(engine.state.generation,
                      "नमस्ते। यह काल्पनिक उड़ानों की खोज का डेमो है। प्रस्थान का शहर, गंतव्य और दिन बताइए।"
                      if os.environ["RIME_LANGUAGE"] in {"hi", "hin"} else
                      "Hello. This is a synthetic flight search demo. Tell me your departure city, destination and day.")
        print(f"Rime voice session ready. Event log: {path}")

    agents.cli.run_app(server)


if __name__ == "__main__":
    main()
