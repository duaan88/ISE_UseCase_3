import io
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch

from contract_v03 import SessionError
from customer_v03 import CustomerAgent, ExampleCustomerModel
from demo_v03 import TURNS
from orchestrator_v03 import Orchestrator
from training import Modellfehler


START = dict(
    contract_version="0.3", request_id="start", scenario_id="payout_missing",
    difficulty_preset="medium", usage_mode="anonymous", training_mode="training",
    coach_enabled=False, profile_id=None, consent_to_store=False,
)
RUBRIC = {"version": "fixture-rubric", "criteria": {"empathy": "Belastung anerkennen"}}


class RecordingCustomer(ExampleCustomerModel):
    def __init__(self):
        self.calls = []
        self.failure = None

    def antwort(self, role, prompt, data):
        self.calls.append((role, data))
        if isinstance(self.failure, Exception):
            raise self.failure
        if self.failure is not None:
            return self.failure
        return super().antwort(role, prompt, data)


def example_evaluation(evaluation_input):
    """Nachgebildete B-Funktion. Keine Bewertung durch A."""
    snapshot = evaluation_input["snapshot"]
    message = next(m for m in snapshot["messages"] if m["role"] == "trainee")
    evidence = [{"message_id": message["id"], "quote": message["text"],
                 "assisted": message["assisted"]}]
    return {
        "rubric_version": evaluation_input["rubric"]["version"],
        "snapshot_version": snapshot["snapshot_version"],
        "criteria": [{"criterion_id": "empathy", "level": "Gezeigt",
                      "rationale": "Belastung anerkannt.", "evidence": evidence}],
        "strengths": [{"criterion_id": "empathy", "text": "Konkrete Anerkennung.", "evidence": evidence}],
        "improvements": [], "next_practice": None,
    }


class TextFlowTests(unittest.TestCase):
    def setUp(self):
        self.model = RecordingCustomer()
        self.orchestrator = Orchestrator(CustomerAgent(self.model))

    def start(self, **overrides):
        return self.orchestrator.start_session(**(START | overrides))

    def turn(self, view, text, request_id=None):
        return self.orchestrator.submit_turn(
            view["session_id"], expected_version=view["version"],
            request_id=request_id or f"turn-{view['version']}", text=text,
        )

    def run_case(self, scenario_id):
        view = self.start(scenario_id=scenario_id)
        for text in TURNS[scenario_id]:
            view = self.turn(view, text)
        return view

    def test_petra_agreement_at_turn_three_without_regie_or_early_clue(self):
        view0 = self.start()
        self.assertEqual(view0, self.start())
        self.assertEqual(view0["version"], 0)
        view1 = self.turn(view0, TURNS["payout_missing"][0])
        self.assertNotIn("Formular", view1["messages"][-1]["text"])
        self.assertIsNone(self.model.calls[0][1]["fallhinweis"])
        view2 = self.turn(view1, TURNS["payout_missing"][1])
        self.assertIn("unterschriebene Formular", view2["messages"][-1]["text"])
        view3 = self.turn(view2, TURNS["payout_missing"][2])
        self.assertEqual((view3["end_reason"], view3["snapshot_version"]), ("agreement", 3))
        self.assertEqual(view3["feedback_status"], "not_requested")
        self.assertEqual([role for role, _ in self.model.calls], ["Kunde"] * 3)
        self.assertEqual([data["aerger"] for _, data in self.model.calls], [2, 2, 2])
        self.assertEqual(view0["messages"][0], view3["messages"][0])
        self.assertEqual([m["turn"] for m in view3["messages"]], [0, 1, 1, 2, 2, 3, 3])
        self.assertEqual(len({m["id"] for m in view3["messages"]}), 7)

    def test_second_scenario_has_own_clue_and_agreement(self):
        view = self.run_case("missing_followup")
        self.assertIn("alte E-Mail-Adresse", view["messages"][2]["text"])
        self.assertEqual(view["end_reason"], "agreement")
        self.assertNotIn("Petra", json.dumps(self.model.calls))
        reference = self.orchestrator.get_completed_snapshot(view["session_id"])
        self.assertEqual(reference.scenario_id, "missing_followup")

    def test_hard_case_starts_unresolved_and_can_escalate(self):
        view = self.start(difficulty_preset="hard", training_mode="testing")
        self.assertEqual(view["difficulty"]["ambiguity"], 3)
        self.assertFalse(view["coach_enabled"])
        self.assertNotIn("Auszahlung", view["messages"][0]["text"])
        view = self.turn(view, "Da müssen Sie sich gedulden.")
        self.assertEqual(view["status"], "active")
        self.assertEqual(self.model.calls[-1][1]["aerger"], 5)
        self.assertFalse(self.model.calls[-1][1]["anliegen_offengelegt"])
        view = self.turn(view, "Da müssen Sie sich gedulden.")
        self.assertEqual(view["end_reason"], "escalation")

    def test_clarification_unlocks_issue_then_clue(self):
        view = self.start(difficulty_preset="hard")
        view = self.turn(view, "Geht es um eine ausstehende Zahlung oder um eine Rückmeldung?")
        self.assertIn("Auszahlung", view["messages"][-1]["text"])
        self.assertIsNone(self.model.calls[-1][1]["fallhinweis"])
        view = self.turn(view, "Haben Sie einen Brief erhalten?")
        self.assertIn("Formular", view["messages"][-1]["text"])

    def test_case_limits_and_unallowed_promise(self):
        view = self.start()
        view = self.turn(view, TURNS["payout_missing"][1])
        view = self.turn(view, "Ich sende Ihnen das Formular. Ich melde mich morgen. Das Geld ist morgen garantiert da.")
        self.assertFalse(self.model.calls[-1][1]["angebot_zulaessig"])
        for _ in range(4):
            view = self.turn(view, "Bitte erzählen Sie weiter.")
        self.assertEqual((view["version"], view["end_reason"]), (6, "turn_limit"))

    def test_model_failures_leave_state_and_replayed_turn_is_once_only(self):
        view = self.start()
        sid = view["session_id"]
        for failure, code in [
            (Modellfehler("Timeout"), "MODEL_UNAVAILABLE"),
            ("defektes JSON", "MODEL_OUTPUT_INVALID"),
            ('{"text":"Ich bestätige das.", "accepts_step":true}', "MODEL_OUTPUT_INVALID"),
        ]:
            with self.subTest(code=code):
                self.model.failure = failure
                with self.assertRaises(SessionError) as raised:
                    self.turn(view, TURNS["payout_missing"][1], "same")
                self.assertEqual(raised.exception.code, code)
                self.assertEqual(self.orchestrator.get_session(sid), view)
        self.model.failure = None
        confirmed = self.turn(view, TURNS["payout_missing"][1], "same")
        self.assertEqual(self.turn(view, TURNS["payout_missing"][1], "same"), confirmed)
        self.assertEqual(len(self.model.calls), 4)
        self.assertTrue(all(d["verlauf"] == self.model.calls[0][1]["verlauf"] for _, d in self.model.calls))
        with self.assertRaises(SessionError) as conflict:
            self.turn(view, "Neue Formulierung", "other")
        self.assertEqual(conflict.exception.code, "VERSION_CONFLICT")
        self.assertEqual(conflict.exception.current, confirmed)
        with self.assertRaises(SessionError) as reused:
            self.turn(view, "Geänderter Inhalt unter alter ID", "same")
        self.assertEqual(reused.exception.code, "VALIDATION_ERROR")

    def test_early_model_hint_is_rejected_without_committing(self):
        view = self.start()
        self.model.failure = '{"text":"Das unterschriebene Formular fehlt.", "accepts_step":false}'
        with self.assertRaises(SessionError) as raised:
            self.turn(view, "Guten Tag.")
        self.assertEqual(raised.exception.code, "MODEL_OUTPUT_INVALID")
        self.assertEqual(self.orchestrator.get_session(view["session_id"]), view)

    def test_incompatible_start_options_are_rejected(self):
        for args in ({"profile_id": "p"}, {"consent_to_store": True}, {"usage_mode": "personalized"},
                     {"coach_enabled": True, "training_mode": "testing"}, {"contract_version": "0.2"}):
            with self.subTest(args=args), self.assertRaises(SessionError):
                self.start(**args)

    def test_live_adapter_sends_only_customer_context(self):
        body = io.BytesIO(json.dumps({"choices": [{"message": {"content":
            '{"text":"Ich brauche Klarheit.", "accepts_step":false}'}}]}).encode())
        with patch.dict("os.environ", {"BLABLADOR_API_KEY": "fixture", "BLABLADOR_MODEL": "fixture-model"}):
            self.orchestrator = Orchestrator(CustomerAgent.from_environment())
        view = self.start()
        with patch("training.urlopen", return_value=body) as request:
            completed = self.turn(view, "Guten Tag.")
        self.assertEqual(completed["version"], 1)
        self.assertEqual(request.call_args.kwargs["timeout"], 30)
        payload = json.loads(request.call_args.args[0].data)
        self.assertEqual(payload["model"], "fixture-model")
        sent = payload["messages"][-1]["content"]
        self.assertNotIn(view["session_id"], sent)
        self.assertNotIn("unterschriebene", sent)
        self.assertNotIn("profile_id", sent)


class FeedbackLifecycleTests(unittest.TestCase):
    def create(self, evaluator=example_evaluation, **kwargs):
        return Orchestrator(CustomerAgent(ExampleCustomerModel()), evaluator=evaluator, rubric=RUBRIC, **kwargs)

    def finish(self, core):
        view = core.start_session(**START)
        sid = view["session_id"]
        core.submit_turn(sid, expected_version=0, request_id="first", text=TURNS["payout_missing"][0])
        return core.end_conversation(sid, expected_version=1, request_id="finish", action="finish")

    def test_optional_feedback_reuses_immutable_snapshot_and_original_evidence(self):
        calls = []

        def evaluator(data):
            calls.append(data)
            if len(calls) == 1:
                data["snapshot"]["messages"][1]["text"] = "Mutierter Übergabewert"
                raise TimeoutError()
            return example_evaluation(data)

        core = self.create(evaluator)
        view = self.finish(core)
        sid = view["session_id"]
        snapshot = core.get_completed_snapshot(sid)
        self.assertEqual(calls, [])
        self.assertIsInstance(snapshot.messages, tuple)
        with self.assertRaises(SessionError) as failed:
            core.request_feedback(sid, expected_version=2, request_id="eval1")
        retry_view = failed.exception.current
        self.assertEqual(retry_view["feedback_status"], "failed")
        self.assertEqual(retry_view["version"], 4)
        ready = core.request_feedback(sid, expected_version=4, request_id="eval2")
        self.assertEqual(ready["snapshot_version"], 2)
        self.assertEqual(ready["version"], 6)
        self.assertEqual(ready["feedback_status"], "ready")
        evidence = ready["feedback"]["strengths"][0]["evidence"][0]
        self.assertEqual(evidence["message_id"], snapshot.messages[1].id)
        self.assertEqual(evidence["quote"], TURNS["payout_missing"][0])
        self.assertIn("bank_form_missing", str(calls[1]["scenario_reference"]))
        self.assertEqual(core.get_completed_snapshot(sid), snapshot)
        self.assertEqual(core.request_feedback(sid, expected_version=6, request_id="eval3"), ready)
        self.assertEqual(len(calls), 2)
        core.discard_session(sid)
        with self.assertRaises(SessionError) as gone:
            core.get_completed_snapshot(sid)
        self.assertEqual(gone.exception.code, "SESSION_NOT_FOUND")

    def test_active_aborted_and_empty_finish_have_no_snapshot(self):
        core = self.create()
        for i, action in enumerate(("abort", "finish")):
            view = core.start_session(**(START | {"request_id": f"start-{i}"}))
            sid = view["session_id"]
            with self.assertRaises(SessionError):
                core.request_feedback(sid, expected_version=0, request_id="early")
            if action == "abort":
                view = core.submit_turn(sid, expected_version=0, request_id="first", text="Guten Tag.")
            ended = core.end_conversation(sid, expected_version=view["version"], request_id="end", action=action)
            self.assertIsNone(ended["snapshot_version"])
            with self.assertRaises(SessionError):
                core.request_feedback(sid, expected_version=ended["version"], request_id="later")

    def test_inactivity_does_not_renew_on_read(self):
        now = [0.0]
        core = self.create(idle_seconds=10, clock=lambda: now[0])
        view = self.finish(core)
        now[0] = 9
        core.get_session(view["session_id"])
        now[0] = 10
        self.assertEqual(core.cleanup_expired(), 1)
        with self.assertRaises(SessionError):
            core.get_session(view["session_id"])

    def test_concurrent_feedback_request_does_not_evaluate_twice(self):
        entered, release = Event(), Event()
        calls = []

        def evaluator(data):
            calls.append(data)
            entered.set()
            if not release.wait(3):
                raise RuntimeError("Test wartet auf zweiten Abruf.")
            return example_evaluation(data)

        core = self.create(evaluator)
        sid = self.finish(core)["session_id"]
        with ThreadPoolExecutor() as pool:
            first = pool.submit(core.request_feedback, sid, expected_version=2, request_id="eval1")
            try:
                self.assertTrue(entered.wait(3))
                running = core.request_feedback(sid, expected_version=3, request_id="eval2")
                self.assertEqual(running["feedback_status"], "running")
            finally:
                release.set()
            self.assertEqual(first.result(timeout=3)["feedback_status"], "ready")
        self.assertEqual(len(calls), 1)


class FixturesTests(unittest.TestCase):
    def test_fixtures_match_v03_message_order_and_expected_beleg_ids(self):
        checks = {
            "regular": ("agreement", 3, ("regular-m002", "regular-m004", "regular-m006")),
            "emotional": ("user_finished", 4, ("emotional-m002", "emotional-m004", "emotional-m006")),
            "unclear": ("user_finished", 3, ("unclear-m002", "unclear-m004")),
        }
        fixture_dir = Path(__file__).with_name("beispiele") / "v03"
        for name, (reason, version, evidence) in checks.items():
            with self.subTest(name=name):
                view = json.loads((fixture_dir / f"{name}.json").read_text())
                self.assertEqual(view["contract_version"], "0.3")
                self.assertEqual((view["end_reason"], view["snapshot_version"]), (reason, version))
                self.assertEqual(view["feedback_status"], "not_requested")
                self.assertFalse(view["coach_enabled"])
                ids = [m["id"] for m in view["messages"]]
                self.assertEqual(len(set(ids)), len(ids))
                for index, message in enumerate(view["messages"]):
                    self.assertEqual(message["turn"], (index + 1) // 2)
                    self.assertEqual(message["role"], "trainee" if index % 2 else "customer")
                trainees = {m["id"] for m in view["messages"] if m["role"] == "trainee"}
                self.assertTrue(set(evidence).issubset(trainees))
