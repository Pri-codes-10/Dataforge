from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.agent import agent
from app.agent.state import ConversationState, Message
from app.voice.language import language_service

router = APIRouter(prefix="/api")

# Clean in-memory store for REST endpoints (no Redis dependency)
_conversations: Dict[str, Dict[str, Any]] = {}
_conversation_states: Dict[str, ConversationState] = {}


class ChatRequest(BaseModel):
    text: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    language: str
    is_code_switched: bool
    conversation_id: Optional[str] = None


class CreateConversationRequest(BaseModel):
    title: Optional[str] = "New Conversation"


class SendMessageRequest(BaseModel):
    content: str
    language: Optional[str] = None


@router.get("/status")
async def status():
    return {
        "status": "running",
        "service": "multilingual-voice-agent",
    }


@router.get("/conversations")
async def get_conversations() -> List[Dict[str, Any]]:
    """Retrieve all active conversations."""
    return list(_conversations.values())


@router.get("/conversations/recent")
async def get_recent_conversations() -> List[Dict[str, Any]]:
    """Retrieve grouped recent conversations for the sidebar."""
    items = []
    for c in sorted(_conversations.values(), key=lambda x: x.get("created_at", ""), reverse=True)[:10]:
        items.append({
            "id": c["id"],
            "title": c.get("title", "Conversation"),
            "time": c.get("time", "Just now"),
        })
    if not items:
        return []
    return [{"group": "Recent", "items": items}]


@router.post("/conversations")
async def create_conversation(request: Optional[CreateConversationRequest] = None) -> Dict[str, Any]:
    """Create a new conversation session."""
    cid = f"conv-{uuid4().hex[:8]}"
    title = request.title if request and request.title else "New Conversation"
    now_iso = datetime.utcnow().isoformat()
    record = {
        "id": cid,
        "title": title,
        "lastMessage": "Conversation started",
        "languages": "English",
        "status": "Running",
        "time": "Just now",
        "created_at": now_iso,
        "messages": [],
    }
    _conversations[cid] = record
    _conversation_states[cid] = ConversationState(session_id=cid)
    return record


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """Retrieve details, messages, and state for a single conversation."""
    conv = _conversations.get(conversation_id)
    if not conv:
        now_iso = datetime.utcnow().isoformat()
        conv = {
            "id": conversation_id,
            "title": "New Conversation",
            "lastMessage": "",
            "languages": "English",
            "status": "Running",
            "time": "Just now",
            "created_at": now_iso,
            "messages": [],
        }
        _conversations[conversation_id] = conv
        _conversation_states[conversation_id] = ConversationState(session_id=conversation_id)
    return conv


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, req: SendMessageRequest) -> Dict[str, Any]:
    """Append a message to a conversation and generate an assistant response."""
    conv = await get_conversation(conversation_id)
    state = _conversation_states.get(conversation_id)
    if not state:
        state = ConversationState(session_id=conversation_id)
        _conversation_states[conversation_id] = state

    lang_res = language_service.detect(req.content)
    user_msg = {
        "id": f"msg-{uuid4().hex[:8]}",
        "role": "user",
        "content": req.content,
        "language": req.language or lang_res.label,
        "timestamp": datetime.utcnow().isoformat(),
    }
    conv["messages"].append(user_msg)
    state.add_message(role="user", content=req.content, language=lang_res.label)

    assistant_text = await agent.respond(
        user_text=req.content,
        language=lang_res.primary_language,
        state=state,
    )

    assistant_msg = {
        "id": f"msg-{uuid4().hex[:8]}",
        "role": "assistant",
        "content": assistant_text,
        "language": lang_res.primary_language,
        "timestamp": datetime.utcnow().isoformat(),
    }
    conv["messages"].append(assistant_msg)
    state.add_message(role="assistant", content=assistant_text, language=lang_res.primary_language)

    conv["lastMessage"] = assistant_text[:60]
    return user_msg


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Text endpoint for direct conversation testing."""
    cid = request.conversation_id
    state = None
    if cid:
        if cid not in _conversation_states:
            _conversation_states[cid] = ConversationState(session_id=cid)
        state = _conversation_states[cid]

    language_result = language_service.detect(request.text)

    if state:
        state.add_message(role="user", content=request.text, language=language_result.label)

    response = await agent.respond(
        user_text=request.text,
        language=language_result.primary_language,
        state=state,
    )

    if state:
        state.add_message(role="assistant", content=response, language=language_result.primary_language)

    return ChatResponse(
        response=response,
        language=language_result.primary_language,
        is_code_switched=language_result.is_code_switched,
        conversation_id=cid,
    )