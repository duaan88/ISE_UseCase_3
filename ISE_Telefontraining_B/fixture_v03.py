"""Nur für den Testmodus: feste Gespräche aus dem abgestimmten v0.3-Handoff."""

from copy import deepcopy
from functools import partial
import json
from pathlib import Path
from uuid import uuid4

from evaluation_v03 import evaluate, load_knowledge

DIRECTORY = Path(__file__).with_name("beispiele") / "person_b_v03"
LABELS = {
    "regular": "Regulär · Einigung",
    "emotional": "Emotional · manuell beenden",
    "unclear": "Unklar · manuell beenden",
}


def load_fixture(name):
    if name not in LABELS:
        raise ValueError("Unbekanntes Testgespräch.")
    return json.loads((DIRECTORY / f"{name}.json").read_text(encoding="utf-8"))


def _observation(criterion_id, level, rationale, *ids):
    return dict(criterion_id=criterion_id, level=level, rationale=rationale, evidence_ids=list(ids))


def _suggestion(criterion_id, text, *ids):
    return dict(criterion_id=criterion_id, text=text, evidence_ids=list(ids))


def fixture_model_output(name):
    """Synthetische Modellantworten, deren Belege der echte Validator auflöst."""
    shown, partial_level, practice, no_chance = (
        "Gezeigt", "Teilweise gezeigt", "Übungsbedarf", "Keine Gelegenheit")
    if name == "regular":
        return dict(criteria=[
            _observation("empathy", shown, "Die Wartezeit wird als Belastung anerkannt.", "regular-m002"),
            _observation("clarification", shown, "Die gezielte Frage erschließt die fehlende Unterlage.", "regular-m004"),
            _observation("next_step", shown, "Formularversand, Zuständigkeit und Rückmeldezeit sind konkret.", "regular-m006"),
        ], strengths=[_suggestion("next_step", "Der nächste Schritt ist klar vereinbart.", "regular-m006")],
            improvements=[], next_practice=None)
    if name == "emotional":
        return dict(criteria=[
            _observation("empathy", partial_level, "Auf die Abweisung folgt eine konkrete Korrektur.", "emotional-m002", "emotional-m004"),
            _observation("clarification", shown, "Die Frage nach der Nachricht erschließt das fehlende Formular.", "emotional-m004"),
            _observation("next_step", practice, "Das Formular ist bekannt. Die Antwort vereinbart keinen Schritt.", "emotional-m006"),
        ], strengths=[_suggestion("empathy", "Die Abweisung wird angesprochen und korrigiert.", "emotional-m004")],
            improvements=[_suggestion("next_step", "Biete den Formularversand an und vereinbare eine Rückmeldezeit.", "emotional-m006")],
            next_practice="Formuliere einen konkreten Zwischenstand mit Uhrzeit.")
    if name == "unclear":
        return dict(criteria=[
            _observation("empathy", practice, "Die erste Antwort grenzt das Anliegen ein und greift die geäußerte Ratlosigkeit nicht auf.", "unclear-m002"),
            _observation("clarification", shown, "Das Anliegen wird eingegrenzt und die Unterlage erfragt.", "unclear-m002", "unclear-m004"),
            _observation("next_step", no_chance, "Der Formularhinweis steht im letzten Kundenbeitrag. Danach folgt keine Serviceantwort."),
        ], strengths=[_suggestion("clarification", "Die gezielte Eingrenzung klärt das anfangs unklare Anliegen.", "unclear-m002", "unclear-m004")],
            improvements=[], next_practice=None)
    raise ValueError("Unbekanntes Testgespräch.")


class FixtureModel:
    def __init__(self, name):
        self.name = name

    def antwort(self, rolle, auftrag, daten):
        return json.dumps(fixture_model_output(self.name), ensure_ascii=False)


class FixtureError(ValueError):
    def __init__(self, code, message, *, current=None, retryable=False):
        super().__init__(message)
        self.current = current
        self.error = dict(code=code, message=message, retryable=retryable)

    def to_dict(self):
        return self.error.copy()


class FixtureOrchestrator:
    """Simuliert für eine Browser-Sitzung die dokumentierte A-Schnittstelle."""

    def __init__(self, name, evaluator=None):
        self.fixture = load_fixture(name)
        self.evaluate = evaluator or partial(evaluate, model=FixtureModel(name))
        self.rubric, self.scenarios = load_knowledge()
        self.view = None
        self.requests = {}

    def start_session(self, **request):
        self.view = {
            **self.fixture,
            **{key: request[key] for key in ("usage_mode", "training_mode", "coach_enabled", "profile_id", "consent_to_store")},
            "session_id": uuid4().hex, "version": 0, "status": "active",
            "end_reason": None, "snapshot_version": None, "messages": self.fixture["messages"][:1],
        }
        self.requests.clear()
        return deepcopy(self.view)

    def get_session(self, session_id):
        if not self.view or self.view["session_id"] != session_id:
            raise FixtureError("SESSION_NOT_FOUND", "Die Sitzung wurde verworfen.")
        return deepcopy(self.view)

    def next_sample(self):
        messages = self.fixture["messages"]
        index = len(self.view["messages"])
        return messages[index]["text"] if index < len(messages) else None

    def _check(self, session_id, expected_version, request_id, action):
        current = self.get_session(session_id)
        signature = (expected_version, action)
        if request_id in self.requests:
            if self.requests[request_id] != signature:
                raise FixtureError("VALIDATION_ERROR", "Die Anfrage-ID wurde bereits verwendet.")
            return None
        if expected_version != current["version"]:
            raise FixtureError("VERSION_CONFLICT", "Der aktuelle Gesprächsstand wurde geladen.", current=current)
        return signature

    def _commit(self, request_id, signature):
        self.requests[request_id] = signature
        self.view["version"] += 1
        return deepcopy(self.view)

    def submit_turn(self, session_id, *, expected_version, request_id, text):
        signature = self._check(session_id, expected_version, request_id, ("turn", text))
        if signature is None:
            return self.get_session(session_id)
        if self.view["status"] != "active" or text.strip() != self.next_sample():
            raise FixtureError("VALIDATION_ERROR", "Im Testgespräch bitte die vorgegebene Beispielantwort verwenden.")
        index = len(self.view["messages"])
        self.view["messages"] = self.fixture["messages"][:index + 2]
        if len(self.view["messages"]) == len(self.fixture["messages"]) and self.fixture["end_reason"] == "agreement":
            self.view.update(status="completed", end_reason="agreement", snapshot_version=self.view["version"] + 1)
        return self._commit(request_id, signature)

    def end_conversation(self, session_id, *, expected_version, request_id, action):
        signature = self._check(session_id, expected_version, request_id, ("end", action))
        if signature is None:
            return self.get_session(session_id)
        if self.view["status"] != "active" or action not in ("finish", "abort"):
            raise FixtureError("INVALID_STATE", "Diese Übung ist bereits abgeschlossen.")
        if action == "finish" and len(self.view["messages"]) not in (1, len(self.fixture["messages"])):
            raise FixtureError("INVALID_STATE", "Für das feste Testfeedback zuerst das Beispielgespräch zu Ende führen.")
        aborted = action == "abort"
        self.view.update(status="aborted" if aborted else "completed",
                         end_reason="user_aborted" if aborted else "user_finished")
        if not aborted and len(self.view["messages"]) > 1:
            self.view["snapshot_version"] = self.view["version"] + 1
        return self._commit(request_id, signature)

    def request_feedback(self, session_id, *, expected_version, request_id):
        signature = self._check(session_id, expected_version, request_id, ("feedback",))
        if signature is None or self.view["feedback_status"] == "ready":
            return self.get_session(session_id)
        if self.view["snapshot_version"] is None:
            raise FixtureError("INVALID_STATE", "Für diese Übung ist kein Feedback verfügbar.")
        keys = ("contract_version", "session_id", "snapshot_version", "usage_mode", "training_mode",
                "scenario_id", "scenario_version", "knowledge_version", "difficulty", "end_reason", "messages")
        snapshot = {key: self.view[key] for key in keys}
        try:
            report = self.evaluate(deepcopy({
                "snapshot": snapshot, "rubric": self.rubric,
                "scenario_reference": self.scenarios[snapshot["scenario_id"]],
            }))
        except ValueError as exc:
            self.view.update(feedback_status="failed", feedback=None)
            current = self._commit(request_id, signature)
            raise FixtureError("MODEL_OUTPUT_INVALID", "Bewertung fehlgeschlagen. Erneut versuchen.",
                               current=current, retryable=True) from exc
        self.view.update(feedback_status="ready", feedback=report)
        return self._commit(request_id, signature)

    def discard_session(self, session_id):
        self.get_session(session_id)
        self.view = None
        self.requests.clear()
