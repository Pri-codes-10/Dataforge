from fastapi import APIRouter
from pydantic import BaseModel

from app.agent.agent import agent
from app.voice.language import language_service


router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    response: str
    language: str
    is_code_switched: bool


@router.get("/status")
async def status():
    return {
        "status": "running",
        "service": "multilingual-voice-agent",
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Text endpoint for testing the backend
    without using the voice frontend.
    """

    language_result = language_service.detect(
        request.text
    )

    response = await agent.respond(
        user_text=request.text,
        language=language_result.primary_language,
    )

    return ChatResponse(
        response=response,
        language=language_result.primary_language,
        is_code_switched=language_result.is_code_switched,
    )