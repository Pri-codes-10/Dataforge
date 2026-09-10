# Evidence ledger

## Microphone-run repair

A real console run received STT transcripts but recorded a Rime WebSocket closing
transport error. The active launcher now uses the official plugin's streaming
HTTP endpoint, https://users.rime.ai/v1/rime-tts, avoiding pooled WebSocket reuse.
Gemini extraction and HTTP audio generation passed the live smoke check. An
incomplete trailing audio-frame warning remains; listening quality and physical
interruption latency need rechecking after restart. Hindi configuration now
selects Hindi greeting, planner text, error prompts and synthetic search results.

## Gemini migration live check

The live mixed-text planner smoke test passed with `gemini-3.6-flash`, and Rime
returned streaming audio in the same run. Google rejected `gemini-2.5-flash` for
new users and named 3.6 Flash as its replacement. All 24 offline tests passed.
This single text request verifies basic provider access and constraint extraction,
not microphone transcription, physical playback or broad multilingual accuracy.

## Target claim

The completed voice agent should preserve constraints across language switches
and prevent superseded tool results and queued audio from being spoken.

## Predefined acceptance scenarios

1. Normal request: extracted constraints reach search and current result reaches output.
2. Code-switch: structured deltas preserve destination/date when budget changes.
3. Constraint change during work: obsolete cooperative task is cancelled.
4. Stress: a task that returns despite cancellation is dropped before output.
5. Barge-in: queue is cleared and late old-generation output is rejected.

## Procedure and current results

Run `python -m bench.run_tests` and inspect `bench/results/acceptance.csv`.
The numbered cases correspond to the handoff's five scenarios at the engine level.
Additional tests cover status, pending planner interruption, invalid tools and
constraint removal. `python -X utf8 -m app.demo` reproduces a three-turn fixture.

These are offline simulations, including predefined actions, mocked OpenAI
Responses calls, playback-handle fakes, synthetic inventory, and actual SDK
construction without network calls. They test concurrency, validation and adapter
contracts, not multilingual recognition, language understanding, Rime synthesis,
actual playback or end-to-end voice performance. The CSV is the authoritative
run result; skipped tests are explicitly reported.

## Live implementation milestone

`app/voice_agent.py` connects Deepgram, the structured Gemini planner and the
official LiveKit Rime WebSocket plugin. `app.config` checks settings before launch.
The local console is the first target; a room client is still external.
`runs/` logs contain server-side stage events and provider configuration, not
physical playback timestamps. Real provider tests remain pending credentials.
See LIVE_SETUP.md for microphone steps and integration limitations.

## Still unmeasured

Actual audible stale-result rate; real STT/LLM constraint-retention accuracy;
microphone barge-in stop latency; time to first audible response median/p90;
cold versus cached audio latency. No numbers are claimed for these metrics.
Required next evidence: recorded code-switched audio, real LiveKit/Rime session,
client playback telemetry, exact provider configuration, and 4-5 minute demo.
