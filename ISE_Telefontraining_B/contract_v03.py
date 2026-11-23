"""Gemeinsame Python-Schnittstelle v0.3 für Gesprächskern und Streamlit."""

from dataclasses import asdict, dataclass
from typing import Literal, Protocol, TypedDict

CONTRACT_VERSION = "0.3"
EndReason = Literal["agreement", "user_finished", "turn_limit", "escalation", "user_aborted"]
TrainingMode = Literal["training", "testing"]
FeedbackStatus = Literal["not_requested", "running", "ready", "failed"]


@dataclass(frozen=True, slots=True)
class Difficulty:
    preset: str
    emotional_intensity: int
    technical_complexity: int
    ambiguity: int
    conversational_dynamics: int
    information_load: int


@dataclass(frozen=True, slots=True)
class Message:
    id: str
    role: Literal["customer", "trainee"]
    turn: int
    text: str
    assisted: bool = False


@dataclass(frozen=True, slots=True)
class CompletedSessionSnapshot:
    contract_version: str
    session_id: str
    snapshot_version: int
    usage_mode: Literal["anonymous"]
    training_mode: TrainingMode
    scenario_id: str
    scenario_version: str
    knowledge_version: str
    difficulty: Difficulty
    end_reason: EndReason
    messages: tuple[Message, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["messages"] = list(data["messages"])
        return data


class Evidence(TypedDict):
    message_id: str
    quote: str
    assisted: bool


class Observation(TypedDict):
    criterion_id: str
    level: Literal["Gezeigt", "Teilweise gezeigt", "Übungsbedarf", "Keine Gelegenheit"]
    rationale: str
    evidence: list[Evidence]


class Finding(TypedDict):
    criterion_id: str
    text: str
    evidence: list[Evidence]


class Feedback(TypedDict):
    rubric_version: str
    snapshot_version: int
    criteria: list[Observation]
    strengths: list[Finding]
    improvements: list[Finding]
    next_practice: str | None


class EvaluationInput(TypedDict):
    snapshot: dict
    rubric: dict
    scenario_reference: dict


class Evaluator(Protocol):
    """Von B implementiert: Rubrik auswerten, Beleg-IDs in Originalzitate auflösen."""

    def __call__(self, evaluation_input: EvaluationInput, /) -> Feedback: ...


class SessionView(TypedDict):
    contract_version: str
    session_id: str
    version: int
    usage_mode: Literal["anonymous"]
    training_mode: TrainingMode
    scenario_id: str
    scenario_version: str
    knowledge_version: str
    difficulty: dict
    coach_enabled: bool
    profile_id: None
    consent_to_store: bool
    status: Literal["active", "completed", "aborted"]
    end_reason: EndReason | None
    snapshot_version: int | None
    messages: list[dict]
    feedback_status: FeedbackStatus
    feedback: Feedback | None


class SessionError(Exception):
    """Fehler gemäß Vertrag, optional mit der aktuellen SessionView."""

    def __init__(self, code: str, message: str, *, retryable: bool = False,
                 current: SessionView | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.current = current

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}
