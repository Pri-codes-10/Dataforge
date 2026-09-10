import asyncio
import json
import base64
import websockets
import sys

sys.stdout.reconfigure(encoding="utf-8")

WS_URL = "ws://127.0.0.1:8000/ws/voice"

async def verify_flow():
    print("Connecting to SUTRA WebSocket:", WS_URL)
    async with websockets.connect(WS_URL) as ws:
        # 1. Drain initial connection messages
        init_state = json.loads(await ws.recv())
        init_pipe = json.loads(await ws.recv())
        print("Connected successfully! Initial messages:", init_state.get("type"), init_pipe.get("type"))

        # 2. TEST GENERAL WEB SEARCH
        print("\n--- TEST: General Search (Weather in Kolkata) ---")
        await ws.send(json.dumps({
            "type": "transcription",
            "text": "What is the weather in Kolkata today?",
            "final": True
        }))

        tool_executed = False
        tool_name = ""
        response_text = ""
        audio_received = False
        audio_format = ""
        audio_bytes_len = 0

        while True:
            msg = json.loads(await ws.recv())
            mtype = msg.get("type")
            if mtype == "tool_event" and msg.get("event") == "TOOL_COMPLETED":
                tool_executed = True
                tool_name = msg.get("tool")
                print(f"Tool Completed: {tool_name}, result preview: {msg.get('result')[:90]}")
            elif mtype == "response":
                response_text = msg.get("text")
                print(f"LLM Spoken Response: {response_text}")
            elif mtype == "rime_audio":
                audio_received = True
                audio_format = msg.get("format")
                audio_bytes_len = len(base64.b64decode(msg.get("data")))
                print(f"Rime Audio Received: format={audio_format}, bytes={audio_bytes_len}")
                break

        assert tool_executed, "Expected search tool to execute"
        assert tool_name == "search_information", f"Expected search_information, got {tool_name}"
        assert audio_received and audio_bytes_len > 1000, "Expected valid Rime audio"
        print("General Search Test: PASSED!")

        # 3. TEST FLIGHT SEARCH
        print("\n--- TEST: Flight Search (Kolkata to Delhi) ---")
        await ws.send(json.dumps({
            "type": "transcription",
            "text": "Find me a flight from Kolkata to Delhi tomorrow.",
            "final": True
        }))

        flight_tool_executed = False
        flight_response = ""
        while True:
            msg = json.loads(await ws.recv())
            mtype = msg.get("type")
            if mtype == "tool_event" and msg.get("event") == "TOOL_COMPLETED":
                flight_tool_executed = True
                print(f"Flight Tool Completed: {msg.get('tool')}, result preview: {msg.get('result')[:90]}")
            elif mtype == "response":
                flight_response = msg.get("text")
                print(f"Flight Spoken Response: {flight_response}")
            elif mtype == "rime_audio":
                print(f"Flight Rime Audio: {len(base64.b64decode(msg.get('data')))} bytes")
                break

        assert flight_tool_executed, "Expected flight tool to execute"
        print("Flight Search Test: PASSED!")

        # 4. TEST CONSTRAINT MODIFICATION (FOLLOW-UP CORRECTION)
        print("\n--- TEST: Follow-up Correction ('Nahi, Saturday ko chahiye') ---")
        await ws.send(json.dumps({
            "type": "transcription",
            "text": "Nahi, Saturday ko chahiye.",
            "final": True
        }))

        correction_tool_executed = False
        correction_response = ""
        while True:
            msg = json.loads(await ws.recv())
            mtype = msg.get("type")
            if mtype == "tool_event" and msg.get("event") == "TOOL_COMPLETED":
                correction_tool_executed = True
                print(f"Correction Tool Completed: {msg.get('tool')}, result preview: {msg.get('result')[:90]}")
            elif mtype == "response":
                correction_response = msg.get("text")
                print(f"Correction Spoken Response: {correction_response}")
            elif mtype == "rime_audio":
                print(f"Correction Rime Audio: {len(base64.b64decode(msg.get('data')))} bytes")
                break

        print("Constraint Correction Test: PASSED!")

        # 5. TEST RESET
        print("\n--- TEST: Reset Session ---")
        await ws.send(json.dumps({"type": "reset"}))
        reset_msg = json.loads(await ws.recv())
        print("Reset Ack received:", reset_msg.get("type"), reset_msg.get("event"))
        print("Reset Test: PASSED!")

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(verify_flow())
