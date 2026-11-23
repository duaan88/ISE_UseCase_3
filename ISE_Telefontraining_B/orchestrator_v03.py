"""Flüchtige, versionierte Sitzungen für den anonymen Textablauf v0.3."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from secrets import token_urlsafe
from threading import Lock
from time import monotonic

from contract_v03 import (
    CONTRACT_VERSION, CompletedSessionSnapshot, Difficulty, EndReason, Evaluator,
    Feedback, FeedbackStatus, Message, SessionError, SessionView, TrainingMode,
)
from customer_v03 import CustomerAgent
from scenarios_v03 import (
    DIFFICULTIES, RUNDENLIMIT, SCENARIOS, VERSION, Conversation, Scenario,
    evaluate_turn, start_context,
)
from training import Modellausgabefehler


@dataclass
class _Session:
    id: str
    start_request: str
    scenario: Scenario
    difficulty: Difficulty
    training_mode: TrainingMode
    messages: tuple[Message, ...]
    context: Conversation
    last_activity: float
    lock: Lock = field(default_factory=Lock)
    version: int = 0
    status: str = "active"
    end_reason: EndReason | None = None
    snapshot: CompletedSessionSnapshot | None = None
    requests: dict[str, tuple] = field(default_factory=dict)
    completed_requests: set[str] = field(default_factory=set)
    feedback_status: FeedbackStatus = "not_requested"
    feedback: Feedback | None = None
    discarded: bool = False

    def view(self) -> SessionView:
        return {
            "contract_version": CONTRACT_VERSION, "session_id": self.id,
            "version": self.version, "usage_mode": "anonymous",
            "training_mode": self.training_mode, "scenario_id": self.scenario.id,
            "scenario_version": VERSION, "knowledge_version": VERSION,
            "difficulty": asdict(self.difficulty), "coach_enabled": False,
            "profile_id": None, "consent_to_store": False,
            "status": self.status, "end_reason": self.end_reason,
            "snapshot_version": self.snapshot.snapshot_version if self.snapshot else None,
            "messages": [asdict(message) for message in self.messages],
            "feedback_status": self.feedback_status, "feedback": deepcopy(self.feedback),
        }

    def finish(self, reason: EndReason) -> None:
        self.status = "aborted" if reason == "user_aborted" else "completed"
        self.end_reason = reason
        if self.status == "completed" and len(self.messages) > 1:
            self.snapshot = CompletedSessionSnapshot(
                CONTRACT_VERSION, self.id, self.version, "anonymous",
                self.training_mode, self.scenario.id, VERSION, VERSION,
                self.difficulty, reason, self.messages,
            )


class Orchestrator:
    """Prozesslokaler Gesprächskern. B bindet optional Rubrik und Bewertungsfunktion ein."""

    def __init__(self, customer: CustomerAgent, *, evaluator: Evaluator | None = None,
                 rubric: dict | None = None, idle_seconds: float = 1800,
                 clock: Callable[[], float] = monotonic):
        if (evaluator is None) != (rubric is None) or rubric is not None and (
            not isinstance(rubric.get("version"), str) or not rubric["version"].strip()
        ):
            raise ValueError("Bewertungsfunktion und Rubrik mit version gemeinsam konfigurieren.")
        if idle_seconds <= 0:
            raise ValueError("Die Inaktivitätsfrist muss positiv sein.")
        self._customer = customer
        self._evaluator = evaluator
        self._rubric = deepcopy(rubric)
        self._clock = clock
        self._idle_seconds = idle_seconds
        self._registry = Lock()
        self._sessions: dict[str, _Session] = {}
        self._starts: dict[str, tuple[tuple, str]] = {}

    def start_session(self, *, contract_version: str, request_id: str, scenario_id: str,
                      difficulty_preset: str, usage_mode: str, training_mode: TrainingMode,
                      coach_enabled: bool, profile_id: str | None,
                      consent_to_store: bool) -> SessionView:
        _check_id(request_id)
        if contract_version != CONTRACT_VERSION:
            raise SessionError("VALIDATION_ERROR", "Erwartete Vertragsversion: 0.3.")
        if (usage_mode != "anonymous" or profile_id is not None or coach_enabled is not False
                or consent_to_store is not False or training_mode not in ("training", "testing")):
            raise SessionError("VALIDATION_ERROR", "Der Textablauf erwartet eine anonyme Sitzung ohne Coach.")
        if not isinstance(scenario_id, str) or scenario_id not in SCENARIOS:
            raise SessionError("VALIDATION_ERROR", "Unbekanntes Szenario.")
        if not isinstance(difficulty_preset, str) or difficulty_preset not in DIFFICULTIES:
            raise SessionError("VALIDATION_ERROR", "Unbekannte Schwierigkeit.")

        self.cleanup_expired()
        fingerprint = (scenario_id, difficulty_preset, training_mode)
        with self._registry:
            previous = self._starts.get(request_id)
            if previous:
                if previous[0] != fingerprint:
                    raise _request_conflict()
                session_id = previous[1]
            else:
                session_id = token_urlsafe(18)
                scenario, difficulty = SCENARIOS[scenario_id], DIFFICULTIES[difficulty_preset]
                opening = scenario.openings[difficulty.ambiguity - 1]
                state = _Session(
                    session_id, request_id, scenario, difficulty, training_mode,
                    (Message(f"{session_id}-m001", "customer", 0, opening),),
                    start_context(difficulty), self._clock(),
                )
                state.requests[request_id] = ("start", *fingerprint)
                state.completed_requests.add(request_id)
                self._sessions[session_id] = state
                self._starts[request_id] = fingerprint, session_id
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> SessionView:
        with self._locked(session_id) as state:
            return state.view()

    def submit_turn(self, session_id: str, *, expected_version: int, request_id: str,
                    text: str) -> SessionView:
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            raise SessionError("VALIDATION_ERROR", "Gib einen Beitrag mit 1 bis 2.000 Zeichen ein.")
        # Wiederholungen erkennen, ohne unbestätigte Beiträge im Zustand zu behalten.
        fingerprint = sha256(text.encode("utf-8")).digest()
        with self._locked(session_id) as state:
            if self._begin(state, expected_version, request_id, ("turn", fingerprint)):
                return state.view()
            self._require_active(state)
            context, eligible_step = evaluate_turn(state.scenario, state.difficulty, state.context, text.strip())
            turn = len(state.messages) // 2 + 1
            escalation = state.context.anger == context.anger == 5 and turn > 1
            try:
                reply = self._customer.reply(
                    state.scenario, state.difficulty, context, state.messages, text.strip(),
                    eligible_step=eligible_step and not escalation,
                    escalation=escalation, turn_limit=turn >= RUNDENLIMIT,
                )
            except SessionError as exc:
                exc.current = state.view()
                raise
            finally:
                state.last_activity = self._clock()

            customer_text = reply.text
            if context.clue_revealed and not state.context.clue_revealed:
                clue = state.scenario.card.hinweis
                if clue not in customer_text:
                    customer_text = f"{clue} {customer_text}"
            state.messages += (
                Message(f"{state.id}-m{2 * turn:03d}", "trainee", turn, text.strip()),
                Message(f"{state.id}-m{2 * turn + 1:03d}", "customer", turn, customer_text),
            )
            state.context = context
            state.version += 1
            if escalation:
                state.finish("escalation")
            elif eligible_step and reply.accepts_step:
                state.finish("agreement")
            elif turn >= RUNDENLIMIT:
                state.finish("turn_limit")
            state.completed_requests.add(request_id)
            return state.view()

    def end_conversation(self, session_id: str, *, expected_version: int, request_id: str,
                         action: str) -> SessionView:
        if action not in ("finish", "abort"):
            raise SessionError("VALIDATION_ERROR", "Unbekannte Abschlussaktion.")
        with self._locked(session_id) as state:
            if self._begin(state, expected_version, request_id, (action,)):
                return state.view()
            self._require_active(state)
            state.version += 1
            state.finish("user_finished" if action == "finish" else "user_aborted")
            state.completed_requests.add(request_id)
            return state.view()

    def get_completed_snapshot(self, session_id: str) -> CompletedSessionSnapshot:
        with self._locked(session_id) as state:
            return self._require_snapshot(state)

    def request_feedback(self, session_id: str, *, expected_version: int,
                         request_id: str) -> SessionView:
        with self._locked(session_id) as state:
            if self._begin(state, expected_version, request_id, ("feedback",)):
                return state.view()
            snapshot = self._require_snapshot(state)
            if state.feedback_status in ("ready", "running"):
                state.completed_requests.add(request_id)
                return state.view()
            if self._evaluator is None or self._rubric is None:
                raise SessionError("INVALID_STATE", "Die Bewertung ist für diese Anwendung noch nicht eingerichtet.",
                                   current=state.view())

            state.feedback_status = "running"
            state.version += 1
            state.completed_requests.add(request_id)
            evaluation_input = {
                "snapshot": snapshot.to_dict(), "rubric": deepcopy(self._rubric),
                "scenario_reference": state.scenario.reference(),
            }

        # Während des Modellaufrufs kann die UI 'running' lesen oder verwerfen.
        try:
            report = deepcopy(self._evaluator(evaluation_input))
            self._validate_report(report, snapshot)
        except Exception as exc:
            if isinstance(exc, SessionError) and exc.code in ("MODEL_UNAVAILABLE", "MODEL_OUTPUT_INVALID"):
                code = exc.code
            elif isinstance(exc, (Modellausgabefehler, ValueError, TypeError, KeyError)):
                code = "MODEL_OUTPUT_INVALID"
            else:
                code = "MODEL_UNAVAILABLE"
            with self._locked(session_id) as current:
                current.feedback_status = "failed"
                current.version += 1
                current.last_activity = self._clock()
                view = current.view()
            raise SessionError(code, "Feedback konnte nicht erstellt werden.", retryable=True, current=view) from exc

        with self._locked(session_id) as current:
            current.feedback = report
            current.feedback_status = "ready"
            current.version += 1
            current.last_activity = self._clock()
            return current.view()

    def discard_session(self, session_id: str) -> None:
        _check_id(session_id)
        with self._registry:
            state = self._sessions.get(session_id)
        if state is not None:
            with state.lock:
                self._remove(state)

    def cleanup_expired(self) -> int:
        """Entfernt abgelaufene Sitzungen ohne laufende gesperrte Gesprächsrunden."""
        with self._registry:
            states = tuple(self._sessions.values())
        count = 0
        for state in states:
            if state.lock.acquire(blocking=False):
                try:
                    if not state.discarded and self._expired(state):
                        self._remove(state)
                        count += 1
                finally:
                    state.lock.release()
        return count

    @contextmanager
    def _locked(self, session_id: str) -> Iterator[_Session]:
        _check_id(session_id)
        with self._registry:
            state = self._sessions.get(session_id)
        if state is not None:
            with state.lock:
                if not state.discarded and not self._expired(state):
                    yield state
                    return
                if not state.discarded:
                    self._remove(state)
        raise SessionError("SESSION_NOT_FOUND", "Die Übung ist nicht mehr verfügbar.")

    def _remove(self, state: _Session) -> None:
        with self._registry:
            state.discarded = True
            self._sessions.pop(state.id, None)
            if self._starts.get(state.start_request, (None, None))[1] == state.id:
                self._starts.pop(state.start_request, None)

    def _expired(self, state: _Session) -> bool:
        return self._clock() - state.last_activity >= self._idle_seconds

    def _begin(self, state: _Session, version: int, request_id: str, action: tuple) -> bool:
        _check_id(request_id)
        if type(version) is not int or version < 0:
            raise SessionError("VALIDATION_ERROR", "Die erwartete Version ist ungültig.")
        fingerprint = (version, *action)
        previous = state.requests.get(request_id)
        if previous is not None and previous != fingerprint:
            raise _request_conflict()
        if request_id in state.completed_requests:
            state.last_activity = self._clock()
            return True
        if version != state.version:
            raise SessionError("VERSION_CONFLICT", "Die Sitzung wurde bereits aktualisiert.",
                               current=state.view())
        state.requests[request_id] = fingerprint
        state.last_activity = self._clock()
        return False

    @staticmethod
    def _require_active(state: _Session) -> None:
        if state.status != "active":
            raise SessionError("INVALID_STATE", "Diese Übung ist bereits beendet.", current=state.view())

    @staticmethod
    def _require_snapshot(state: _Session) -> CompletedSessionSnapshot:
        if state.snapshot is None:
            raise SessionError("INVALID_STATE", "Für diese Übung ist kein Feedback verfügbar.",
                               current=state.view())
        return state.snapshot

    def _validate_report(self, report: Feedback, snapshot: CompletedSessionSnapshot) -> None:
        if not isinstance(report, dict) or (
            report.get("rubric_version") != self._rubric["version"]
            or type(report.get("snapshot_version")) is not int
            or report["snapshot_version"] != snapshot.snapshot_version
            or any(not isinstance(report.get(name), list) for name in ("criteria", "strengths", "improvements"))
            or "next_practice" not in report
            or report["next_practice"] is not None and not isinstance(report["next_practice"], str)
        ):
            raise ValueError("Das Feedback entspricht nicht dem Abschluss-Snapshot oder dem Vertrag.")


def _check_id(value: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 160 or value != value.strip():
        raise SessionError("VALIDATION_ERROR", "Erwartet wird eine nichtleere ID.")


def _request_conflict() -> SessionError:
    return SessionError("VALIDATION_ERROR", "Diese Anforderungs-ID gehört bereits zu einer anderen Aktion.")
