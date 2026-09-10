from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass
class Message:
    role: str
    content: str
    language: Optional[str] = None
    was_interruption: bool = False
    timestamp: Optional[str] = None
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id or f"msg-{uuid4().hex[:8]}",
            "role": self.role,
            "content": self.content,
            "language": self.language or ("English" if self.role == "user" else "SUTRA"),
            "wasInterruption": self.was_interruption,
            "timestamp": self.timestamp or "",
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            language=data.get("language"),
            was_interruption=data.get("wasInterruption", False),
            timestamp=data.get("timestamp"),
            id=data.get("id"),
        )


@dataclass
class ConversationState:
    """
    Maintains the current conversation state.

    Responsible for:
    - Conversation history
    - Current task & tool tracking
    - User constraints
    - Language information
    - Task versioning for stale-result rejection
    """

    session_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    messages: List[Message] = field(
        default_factory=list
    )

    intent: Optional[str] = None

    constraints: Dict[str, Any] = field(
        default_factory=dict
    )

    language: str = "en"

    is_code_switched: bool = False

    active_task_id: Optional[str] = None

    task_version: int = 0

    tool_results: Dict[str, str] = field(
        default_factory=dict
    )

    def add_message(
        self,
        role: str,
        content: str,
        language: Optional[str] = None,
        was_interruption: bool = False,
    ) -> Message:
        """Store a conversation message."""
        msg = Message(
            role=role,
            content=content,
            language=language,
            was_interruption=was_interruption,
        )
        self.messages.append(msg)
        return msg

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Record latest tool result in conversation state."""
        self.tool_results[tool_name] = result

    def get_messages(self) -> List[dict]:
        """Return conversation history formatted for LLM and UI."""
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
        value: Any,
    ) -> None:
        """
        Update a task constraint.
        Changing a constraint creates a new task version.
        """
        self.constraints[key] = value
        self.task_version += 1

    def reset_active(self) -> None:
        """
        Reset active state for fresh turn/task while strictly
        preserving messages and session_id (Part 9 & Part 11).
        """
        self.intent = None
        self.constraints.clear()
        self.active_task_id = None
        self.tool_results.clear()
        self.task_version += 1

    def reset(self) -> None:
        """Full reset (clears active state and bumps task_version)."""
        self.reset_active()

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
        Check whether a result belongs to the latest version of the task.
        """
        return (
            self.active_task_id == task_id
            and self.task_version == task_version
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for Redis storage."""
        return {
            "session_id": self.session_id,
            "intent": self.intent,
            "constraints": self.constraints,
            "language": self.language,
            "is_code_switched": self.is_code_switched,
            "active_task_id": self.active_task_id,
            "task_version": self.task_version,
            "tool_results": self.tool_results,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], messages: Optional[List[Message]] = None) -> "ConversationState":
        """Deserialize state from Redis data."""
        return cls(
            session_id=data.get("session_id") or str(uuid4()),
            messages=messages or [],
            intent=data.get("intent"),
            constraints=data.get("constraints") or {},
            language=data.get("language", "en"),
            is_code_switched=data.get("is_code_switched", False),
            active_task_id=data.get("active_task_id"),
            task_version=data.get("task_version", 0),
            tool_results=data.get("tool_results") or {},
        )


conversation_state = ConversationState()