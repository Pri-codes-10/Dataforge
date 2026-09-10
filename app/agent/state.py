from dataclasses import dataclass, field
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ConversationState:
    """
    Maintains the current conversation.

    This is responsible for:
    - Conversation history
    - Current task
    - User constraints
    - Language information
    - Task versioning
    """

    session_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    messages: List[Message] = field(
        default_factory=list
    )

    intent: Optional[str] = None

    constraints: Dict[str, str] = field(
        default_factory=dict
    )

    language: str = "en"

    is_code_switched: bool = False

    active_task_id: Optional[str] = None

    task_version: int = 0

    def add_message(
        self,
        role: str,
        content: str,
    ) -> None:
        """Store a conversation message."""

        self.messages.append(
            Message(
                role=role,
                content=content,
            )
        )

    def get_messages(self) -> List[dict]:
        """Return conversation history for the LLM."""

        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in self.messages
        ]

    def update_language(
        self,
        language: str,
        is_code_switched: bool = False,
    ) -> None:
        """Update the current language."""

        self.language = language
        self.is_code_switched = is_code_switched

    def update_constraint(
        self,
        key: str,
        value: str,
    ) -> None:
        """
        Update a task constraint.

        Changing a constraint creates a new task version.
        """

        self.constraints[key] = value
        self.task_version += 1

    def reset(self) -> None:
        """Reset conversation state for a fresh session."""
        self.session_id = str(uuid4())
        self.messages.clear()
        self.intent = None
        self.constraints.clear()
        self.language = "en"
        self.is_code_switched = False
        self.active_task_id = None
        self.task_version = 0

    def start_task(self, custom_id: Optional[str] = None) -> str:
        """Start a new task with version bump."""
        self.task_version += 1
        self.active_task_id = custom_id or f"TASK-{self.task_version:04d}"
        return self.active_task_id

    def cancel_task(self) -> None:
        """Cancel the current task."""
        self.active_task_id = None
        self.task_version += 1

    def is_task_current(
        self,
        task_id: str,
        task_version: int,
    ) -> bool:
        """
        Check whether a result belongs to the
        latest version of the task.
        """
        return (
            self.active_task_id == task_id
            and self.task_version == task_version
        )


conversation_state = ConversationState()