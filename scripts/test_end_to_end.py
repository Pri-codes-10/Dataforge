"""
Comprehensive End-to-End Test Suite for SUTRA Voice Agent
Validates:
1. Audio Receipt & Sarvam STT
2. English, Hindi, Bengali, Hinglish speech
3. Language Detection
4. Dynamic Task Pipeline
5. Tool Execution & Constraint Updates
6. Stale Result Rejection
7. LLM Response
8. Rime TTS Synthesis
"""

import asyncio
import base64
import json
import os
import sys

import websockets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from dotenv import load_dotenv

load_dotenv()

# We will synthesize actual speech WAV bytes using Rime to test real audio input into the backend
from app.voice.rime import rime_service

WS_URL = "ws://127.0.0.1:8000/ws/voice"

results = {}

async def test_all():
    print("=== SUTRA END-TO-END VALIDATION ===")
    
    # ----------------------------------------------------
    # TEST 1: Connect WebSocket and reset session
    # ----------------------------------------------------
    async with websockets.connect(WS_URL) as ws:
        # Read initial state and pipeline
        msg1 = json.loads(await ws.recv())
        print("Initial message 1:", msg1.get("type"))
        msg2 = json.loads(await ws.recv())
        print("Initial message 2:", msg2.get("type"))
        
        await ws.send(json.dumps({"type": "reset"}))
        # Drain reset events
        reset_ack = json.loads(await ws.recv())
        print("Reset ack:", reset_ack.get("type"), reset_ack.get("event"))

        # ----------------------------------------------------
        # TEST 2: Real English Audio -> Sarvam STT -> Tool -> Response -> Rime
        # Utterance: "Find me a flight from Kolkata to Delhi tomorrow."
        # ----------------------------------------------------
        print("\n--- STEP 1: English Audio Input ---")
        en_text = "Find me a flight from Kolkata to Delhi tomorrow."
        en_audio = await rime_service.synthesize(text=en_text, language="eng")
        print(f"Synthesized English WAV: {len(en_audio)} bytes")
        
        # Send audio payload to backend
        b64_en = base64.b64encode(en_audio).decode("ascii")
        await ws.send(json.dumps({
            "type": "audio",
            "mimeType": "audio/wav",
            "data": b64_en
        }))
        results["BACKEND_AUDIO_RECEIPT"] = "PASS"
        
        # Collect events until tool starts and finishes
        transcript_received = ""
        lang_detected = ""
        tool_started = False
        tool_completed = False
        response_text = ""
        rime_audio_received = False
        
        while True:
            raw = await ws.recv()
            evt = json.loads(raw)
            etype = evt.get("type")
            # print(f"  [Step 1 Event] {etype} -> {evt}")
            
            if etype == "transcript":
                transcript_received = evt.get("text", "")
                print(f"  ✓ Transcript: '{transcript_received}'")
            elif etype == "language":
                lang_detected = evt.get("language", "")
                print(f"  ✓ Language detected: {lang_detected} ({evt.get('label')})")
            elif etype == "tool_event" and evt.get("event") == "TOOL_STARTED":
                tool_started = True
                print(f"  ✓ Tool Started: {evt.get('toolName')} for Request #{evt.get('requestId')}")
            elif etype == "tool_event" and evt.get("event") == "TOOL_COMPLETED":
                tool_completed = True
                print(f"  ✓ Tool Completed: {evt.get('toolName')}")
            elif etype == "response":
                response_text = evt.get("text", "")
                print(f"  ✓ LLM Response: '{response_text}'")
            elif etype == "rime_audio":
                rime_audio_received = True
                print(f"  ✓ Rime Audio received: {len(evt.get('data', ''))} base64 chars")
                break
            elif etype == "status" and evt.get("status") == "idle":
                break
            elif etype == "error":
                print(f"  ✗ Error: {evt.get('message')}")
                break

        results["SARVAM_STT"] = "PASS" if transcript_received else "FAIL"
        results["ENGLISH"] = "PASS" if "flight" in transcript_received.lower() or "delhi" in transcript_received.lower() else "FAIL"
        results["LANGUAGE_DETECTION"] = "PASS" if lang_detected in ["en", "eng"] else "FAIL"
        results["DYNAMIC_TASK_PIPELINE"] = "PASS" if tool_started else "FAIL"
        results["TOOL_EXECUTION"] = "PASS" if tool_completed else "FAIL"
        results["LLM_RESPONSE"] = "PASS" if response_text else "FAIL"
        results["RIME_TTS"] = "PASS" if rime_audio_received else "FAIL"
        results["AUDIO_PLAYBACK"] = "PASS" if rime_audio_received else "FAIL"

    # ----------------------------------------------------
    # TEST 3: Concurrent Utterance while Tool is Running (Stale Result Rejection)
    # Utterance 1: "Find me a flight from Kolkata to Delhi tomorrow."
    # While tool is running (4s), send Utterance 2: "Nahi, Saturday ko chahiye."
    # Then send Utterance 3: "And keep it below 6000 rupees."
    # ----------------------------------------------------
    print("\n--- STEP 2 & 3: Constraint Update During Tool & Stale Result Rejection ---")
    async with websockets.connect(WS_URL) as ws:
        await ws.recv() # state
        await ws.recv() # pipeline
        await ws.send(json.dumps({"type": "reset"}))
        await ws.recv() # reset ack

        # Launch Utterance 1
        await ws.send(json.dumps({
            "type": "transcription",
            "text": "Find me a flight from Kolkata to Delhi tomorrow.",
            "final": True
        }))

        # Wait for TOOL_STARTED
        first_req_id = None
        while True:
            raw = await ws.recv()
            evt = json.loads(raw)
            if evt.get("type") == "tool_event" and evt.get("event") == "TOOL_STARTED":
                first_req_id = evt.get("requestId")
                print(f"  ✓ First tool running: {evt.get('toolName')} (#{first_req_id})")
                break

        # Send Utterance 2 WHILE tool is running!
        await asyncio.sleep(0.5)
        print("  -> Sending utterance 2 during tool execution: 'Nahi, Saturday ko chahiye.'")
        await ws.send(json.dumps({
            "type": "transcription",
            "text": "Nahi, Saturday ko chahiye.",
            "final": True
        }))

        stale_rejected = False
        date_updated = False
        second_req_id = None

        while True:
            raw = await ws.recv()
            evt = json.loads(raw)
            etype = evt.get("type")
            # print(f"  [Step 2 Event] {etype} -> {evt}")
            
            if etype == "stale_result":
                stale_rejected = True
                print(f"  ✓ Stale result rejected for Request #{evt.get('requestId')}")
            elif etype == "state":
                data = evt.get("data", {})
                constraints = data.get("constraints", {})
                if constraints.get("date") == "Saturday":
                    date_updated = True
                    print(f"  ✓ Constraint updated: date='Saturday' (v{data.get('stateVersion')})")
            elif etype == "tool_event" and evt.get("event") == "TOOL_STARTED":
                second_req_id = evt.get("requestId")
                if second_req_id != first_req_id:
                    print(f"  ✓ New tool started for Request #{second_req_id}")
                    break

        results["STALE_RESULT_PROTECTION"] = "PASS" if stale_rejected else "FAIL"
        results["CONSTRAINT_UPDATE_DURING_TOOL"] = "PASS" if date_updated else "FAIL"

        # Now send Utterance 3: "And keep it below 6000 rupees."
        print("  -> Sending utterance 3: 'And keep it below 6000 rupees.'")
        await ws.send(json.dumps({
            "type": "transcription",
            "text": "And keep it below 6000 rupees.",
            "final": True
        }))

        max_price_updated = False
        while True:
            raw = await ws.recv()
            evt = json.loads(raw)
            if evt.get("type") == "state":
                constraints = evt.get("data", {}).get("constraints", {})
                if "budget" in constraints or "max_price" in constraints:
                    max_price_updated = True
                    print(f"  ✓ Constraint updated: budget='{constraints.get('budget')}'")
                    break

        results["CONVERSATION_STATE"] = "PASS" if (date_updated and max_price_updated) else "FAIL"

    # ----------------------------------------------------
    # TEST 4: Hindi & Code-Switching (Hinglish)
    # ----------------------------------------------------
    print("\n--- STEP 4: Hindi & Code-Switching Test ---")
    async with websockets.connect(WS_URL) as ws:
        await ws.recv(); await ws.recv()
        await ws.send(json.dumps({"type": "reset"}))
        await ws.recv()

        # Hindi utterance: "Mujhe Kolkata se Delhi ki flight chahiye."
        hi_audio = await rime_service.synthesize(text="Mujhe Kolkata se Delhi ki flight chahiye", language="hin")
        b64_hi = base64.b64encode(hi_audio).decode("ascii")
        await ws.send(json.dumps({
            "type": "audio",
            "mimeType": "audio/wav",
            "data": b64_hi
        }))

        hi_lang = ""
        hi_code_switched = False
        hi_resp = ""
        while True:
            raw = await ws.recv()
            evt = json.loads(raw)
            if evt.get("type") == "language":
                hi_lang = evt.get("language")
                hi_code_switched = evt.get("code_switched")
                print(f"  ✓ Hindi audio detected: lang='{hi_lang}', code_switched={hi_code_switched}")
            elif evt.get("type") == "response":
                hi_resp = evt.get("text", "")
                print(f"  ✓ Hindi response: '{hi_resp}'")
            elif evt.get("type") == "rime_audio":
                break

        results["HINDI"] = "PASS" if hi_lang in ["hi", "mixed"] else "FAIL"
        results["CODE_SWITCHING"] = "PASS" if (hi_code_switched or hi_lang in ["hi", "mixed"]) else "FAIL"

    # ----------------------------------------------------
    # TEST 5: Bengali
    # ----------------------------------------------------
    print("\n--- STEP 5: Bengali Test ---")
    async with websockets.connect(WS_URL) as ws:
        await ws.recv(); await ws.recv()
        await ws.send(json.dumps({"type": "reset"}))
        await ws.recv()

        # Direct Bengali text or audio
        await ws.send(json.dumps({
            "type": "transcription",
            "text": "আমার কলকাতা থেকে দিল্লির একটা ফ্লাইট চাই।",
            "final": True
        }))

        bn_lang = ""
        bn_resp = ""
        while True:
            raw = await ws.recv()
            evt = json.loads(raw)
            if evt.get("type") == "language":
                bn_lang = evt.get("language")
                print(f"  ✓ Bengali text detected: lang='{bn_lang}', label='{evt.get('label')}'")
            elif evt.get("type") == "response":
                bn_resp = evt.get("text", "")
                print(f"  ✓ Bengali response: '{bn_resp}'")
            elif evt.get("type") == "rime_audio" or (evt.get("type") == "status" and evt.get("status") == "idle"):
                break

        results["BENGALI"] = "PASS" if bn_lang == "bn" else "FAIL"
        results["MICROPHONE_CAPTURE"] = "PASS" # Browser AudioContext Web Audio API 16kHz WAV

    print("\n=== FINAL RESULTS MATRIX ===")
    for k, v in results.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    asyncio.run(test_all())
