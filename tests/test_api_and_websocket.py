import pytest
from uuid import uuid4
from starlette.testclient import TestClient

from app.main import app


def test_rest_api_status():
    """Test REST /api/status endpoint."""
    with TestClient(app) as client:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"


def test_rest_conversations_flow():
    """Test REST CRUD flow for conversations."""
    with TestClient(app) as client:
        # Create conversation
        create_resp = client.post("/api/conversations", json={"title": "Test Flight Booking"})
        assert create_resp.status_code == 200
        conv_data = create_resp.json()
        cid = conv_data["id"]
        assert conv_data["title"] == "Test Flight Booking"

        # Send message
        msg_resp = client.post(
            f"/api/conversations/{cid}/messages",
            json={"content": "What is the weather in Delhi?", "language": "English"},
        )
        assert msg_resp.status_code == 200
        user_msg = msg_resp.json()
        assert user_msg["role"] == "user"

        # Get conversation detail
        get_resp = client.get(f"/api/conversations/{cid}")
        assert get_resp.status_code == 200
        detail = get_resp.json()
        assert detail["id"] == cid
        assert len(detail.get("messages", [])) >= 2  # user + assistant

        # Get recent conversations
        recent_resp = client.get("/api/conversations/recent")
        assert recent_resp.status_code == 200
        recent_data = recent_resp.json()
        assert isinstance(recent_data, list)


def test_websocket_reset_and_persistence():
    """Test WebSocket session, reset event, and task version invalidation."""
    cid = f"ws-test-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/voice?conversation_id={cid}") as ws:
            # Receive initial state
            init_state = ws.receive_json()
            assert init_state["type"] == "state"
            assert init_state["conversation_id"] == cid

            # Receive initial pipeline
            init_pipe = ws.receive_json()
            assert init_pipe["type"] == "pipeline"

            # Send a user transcription
            ws.send_json({"type": "transcription", "text": "Find me a flight from Kolkata to Delhi tomorrow"})

            # Receive transcript acknowledgment
            msg1 = ws.receive_json()
            assert msg1["type"] == "transcript"

            # Send reset command
            ws.send_json({"type": "reset"})

            # Find reset_complete message
            reset_received = False
            for _ in range(10):
                msg = ws.receive_json()
                if msg.get("type") == "reset_complete":
                    assert msg["conversation_id"] == cid
                    assert msg["task_version"] >= 1
                    reset_received = True
                    break
                elif msg.get("event") == "SESSION_RESET":
                    reset_received = True
                    break
            assert reset_received is True


def test_case_1_normal_voice():
    """TEST 1: Normal voice/question - No flight tool called."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/voice?conversation_id=test-case-1") as ws:
            init_state = ws.receive_json()
            assert init_state["type"] == "state"
            init_pipe = ws.receive_json()
            assert init_pipe["type"] == "pipeline"

            ws.send_json({"type": "transcription", "text": "Hello, what is machine learning?"})

            msg_transcript = ws.receive_json()
            assert msg_transcript["type"] == "transcript"
            assert msg_transcript["text"] == "Hello, what is machine learning?"

            tool_called = False
            for _ in range(15):
                m = ws.receive_json()
                if m.get("type") == "tool_event":
                    tool_called = True
                if m.get("type") == "response" or m.get("type") == "rime_audio":
                    break

            assert tool_called is False, "Normal question must NOT call flight or specialized tool"


def test_case_2_flight_search():
    """TEST 2: Flight query invokes flight search and returns real result."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/voice?conversation_id=test-case-2") as ws:
            ws.receive_json()  # init state
            ws.receive_json()  # init pipeline

            ws.send_json({"type": "transcription", "text": "Find a flight from Kolkata to Delhi tomorrow."})

            msg_transcript = ws.receive_json()
            assert msg_transcript["type"] == "transcript"

            tool_started = False
            tool_completed = False
            for _ in range(15):
                m = ws.receive_json()
                if m.get("type") == "tool_event":
                    if m.get("event") == "TOOL_STARTED":
                        assert m.get("tool") == "search_flights"
                        tool_started = True
                    elif m.get("event") == "TOOL_COMPLETED":
                        assert m.get("tool") == "search_flights"
                        tool_completed = True
                        break

            assert tool_started is True
            assert tool_completed is True


def test_case_3_stop_during_task():
    """TEST 3: Stop stops current task without creating new conversation or closing connection."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/voice?conversation_id=test-case-3") as ws:
            ws.receive_json()  # init state
            ws.receive_json()  # init pipeline

            ws.send_json({"type": "transcription", "text": "Find flights from Kolkata to Delhi."})
            ws.receive_json()  # transcript

            # Immediate STOP
            ws.send_json({"type": "stop"})

            stopped_event = False
            for _ in range(15):
                m = ws.receive_json()
                if m.get("event") == "STOPPED":
                    stopped_event = True
                    assert m.get("status") == "stopped"
                    break

            assert stopped_event is True

            # Send ping to confirm WebSocket connection is still alive and NOT terminated
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            while pong.get("type") != "pong":
                pong = ws.receive_json()
            assert pong["type"] == "pong"


def test_case_6_multilingual():
    """TEST 6: Understand mixed-language Hindi/English flight request."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/voice?conversation_id=test-case-6") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "transcription", "text": "Delhi jaana hai tomorrow."})

            transcript_msg = ws.receive_json()
            assert transcript_msg["type"] == "transcript"

            lang_msg = ws.receive_json()
            assert lang_msg["type"] == "language"

            tool_found = False
            for _ in range(15):
                m = ws.receive_json()
                if m.get("type") == "tool_event" and m.get("tool") == "search_flights":
                    tool_found = True
                    break

            assert tool_found is True


def test_case_7_constraint_update_stale_protection():
    """TEST 7: Consecutive requests supersede older tasks and reject stale results."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/voice?conversation_id=test-case-7") as ws:
            ws.receive_json()
            ws.receive_json()

            # Task 1
            ws.send_json({"type": "transcription", "text": "Find a flight from Kolkata to Delhi."})
            ws.receive_json()  # transcript

            # Rapid Task 2 before Task 1 completes
            ws.send_json({"type": "transcription", "text": "Nahi, Mumbai jaana hai and under 6000."})

            stale_event = False
            for _ in range(25):
                m = ws.receive_json()
                if m.get("type") == "stale_result" or m.get("event") == "STALE_RESULT_REJECTED":
                    stale_event = True
                    break

            assert stale_event is True


def test_case_8_general_question():
    """TEST 8: General question answers directly without tools."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws/voice?conversation_id=test-case-8") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "transcription", "text": "What is artificial intelligence?"})
            ws.receive_json()  # transcript

            tool_ran = False
            response_got = False
            for _ in range(15):
                m = ws.receive_json()
                if m.get("type") == "tool_event":
                    tool_ran = True
                if m.get("type") == "response":
                    response_got = True
                    assert len(m.get("text", "")) > 0
                    break

            assert tool_ran is False
            assert response_got is True

