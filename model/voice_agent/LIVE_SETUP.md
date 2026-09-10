# Run the live voice prototype

Gemini is now the active planner. Set `LLM_MODEL=gemini-3.6-flash` and obtain
`GEMINI_API_KEY` from https://aistudio.google.com/apikey. Put the key in `.env`
locally. OpenAI credentials are no longer required by the launcher or smoke test.
Run `python -m bench.provider_smoke` after configuration to validate live access.
Gemini adapter tests pass offline. A live mixed-text planner request and Rime
streaming smoke test also passed with gemini-3.6-flash; microphone testing remains.
Structured-output reference: https://ai.google.dev/gemini-api/docs/structured-output

Create a Python 3.11+ environment in this directory and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The complete
Windows/Python 3.12 dependency resolution is saved in `requirements.lock.txt`.

## Configure locally

From the project directory, copy `.env.example` to `.env` if `.env` does not exist.
Fill these fields in your editor:

- GEMINI_API_KEY and LLM_MODEL (gemini-3.6-flash)
- DEEPGRAM_API_KEY (default STT: nova-3, language: multi)
- RIME_API_KEY, RIME_MODEL, RIME_VOICE, RIME_LANGUAGE (compatible catalog values)

Do not paste keys in chat. `.env` is ignored by Git. No credentials are included in this repository.
The current Rime catalog must be checked and the chosen combination tested;
language support listings do not prove Hindi-English code-switch quality.

```powershell
.\.venv\Scripts\python.exe -m app.config
.\.venv\Scripts\python.exe -m app.voice_agent download-files
.\.venv\Scripts\python.exe -m app.voice_agent console
```

Console mode uses your microphone and speakers; use headphones to reduce echo.
Room mode additionally requires LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET:
run `python -m app.config --room`, then `python -m app.voice_agent dev` and connect
through a LiveKit client/playground. A custom browser client is not included.

## Microphone acceptance script

1. Say: "Kolkata se Delhi, Saturday flights dekho."
2. During the four-second lookup: "Budget chhe hazaar se kam, nonstop."
3. The latest synthetic result should be 5400 rupees, nonstop.
4. Interrupt spoken output with: "Actually Mumbai jaana hai."
5. During silent work ask: "Any update?" Verify the lookup is not cancelled.

All fares come from fixtures/flights.json; no real search or booking occurs.
DEMO_TOOL_DELAY sets delay from 0 to 20 seconds. Supported inventory is Kolkata
to Delhi/Mumbai on Saturday/Sunday only. This script has not been run with live
providers yet. With RIME_LANGUAGE=hi, greetings, planner text and synthetic results use Hindi.

## Evidence and limitations

Run `python -m bench.run_tests` and `python -m bench.analyze` for offline results.
The fixture replay `python -X utf8 -m app.demo` uses no providers. Provider tests
use mocks or construct SDK clients with dummy credentials without network calls.

Live runs write JSONL to ignored `runs/`, containing transcripts, generation
changes, tool and speech events and the active provider configuration. Automatic
LiveKit recording is disabled. Speech submission and handle completion are not
first-audible-response measurements. Physical playback latency, stale audio,
real STT accuracy and real LLM classification quality remain unmeasured.

VAD holds new output until a final utterance is processed. False VAD with no final
transcript may hold output until the next recognized utterance. Actual speech
barge-in cancels old-generation work; if a status question interrupts spoken
audio, a fresh search may be needed. Silent-work status preserves the lookup.
False-interruption speech resumption and preemptive generation are disabled.
LiveKit owns final device/WebRTC buffers; already transmitted audio needs a
physical stop-latency test before making the hard voice claim.

Missing settings fail before startup. Planner failure leaves constraints unchanged
and offers a retry response; tool failure only speaks if its generation is current.
Provider errors are logged and no alternate TTS silently takes over.
