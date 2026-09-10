# Voice-agent prototype

The [Gemini/LiveKit voice agent](voice_agent/README.md) provides conversation continuity, interruptible playback, and synthetic flight search. It runs independently of the root FastAPI backend and React frontend.

Start in `model/voice_agent` and follow [live setup](voice_agent/LIVE_SETUP.md). Copy `.env.example` to a local `.env` and configure provider credentials. Never commit `.env`.

Run offline checks from that directory with `python -m bench.run_tests`.
