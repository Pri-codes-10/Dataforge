import httpx

from app.core.config import settings
from app.agent.state import conversation_state


class VoiceAgent:
    """
    LLM agent for the voice assistant.

    Handles:
    - Conversation understanding
    - Hindi / English / Hinglish
    - Context continuity
    - Response generation
    """

    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.api_url = settings.SARVAM_API_URL
        self.model = settings.SARVAM_MODEL
        self.client = None

        if self.api_key:
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                },
            )

    async def respond(
        self,
        user_text: str,
        language: str = "en",
    ) -> str:
        """
        Generate a response using the current conversation state.
        """

        # Store the latest user message
        conversation_state.add_message(
            role="user",
            content=user_text,
        )

        # Update language information
        conversation_state.update_language(
            language=language,
            is_code_switched=(language == "mixed"),
        )

        api_key = settings.SARVAM_API_KEY or self.api_key

        if not api_key:
            assistant_text = (
                f"I heard you: '{user_text}'. Note: Please set SARVAM_API_KEY in your .env file."
            )
            conversation_state.add_message(
                role="assistant",
                content=assistant_text,
            )
            return assistant_text

        if not self.client or self.api_key != api_key:
            self.api_key = api_key
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                },
            )


        messages = [
            {
                "role": "system",
                "content": self._system_prompt(language),
            }
        ]

        # Include conversation history
        messages.extend(
            conversation_state.get_messages()
        )

        response = await self.client.post(
            self.api_url,
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
                "reasoning_effort": None,
            },
        )
        response.raise_for_status()
        response_data = response.json()

        assistant_text = (
            response_data["choices"][0]["message"].get("content") or ""
        )

        # Store assistant response
        conversation_state.add_message(
            role="assistant",
            content=assistant_text,
        )

        return assistant_text

    def _system_prompt(self, language: str) -> str:
        return f"""
You are a real-time multilingual voice assistant.

Current language:
{language}

Your responsibilities:

1. Understand the user's complete request.
2. Maintain context across multiple turns.
3. Understand English, Hindi, and Hinglish.
4. If the user changes a requirement, use the latest
   requirement instead of the previous one.
5. Do not forget information provided earlier in the
   conversation.
6. Keep responses short and natural because the response
   will be converted into speech.
7. Ask for clarification when required information is missing.
8. Do not invent tool results.
9. When a task changes, the latest instruction has priority.
"""

    
agent = VoiceAgent()