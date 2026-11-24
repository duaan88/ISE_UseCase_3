"""Vertragstests ohne Schlüssel und ohne As Kunden-Agenten."""

from pathlib import Path
import unittest
from unittest.mock import Mock

from evaluation_v03 import InvalidEvaluation, evaluate, load_knowledge, validate_feedback
from fixture_v03 import FixtureModel, fixture_model_output, load_fixture

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


class EvaluationTests(unittest.TestCase):
    def test_petra_transfer_without_disclosure_keeps_solution_out_of_model_input(self):
        rubric, cases = load_knowledge()
        fixture = load_fixture("regular")
        fixture.update(end_reason="user_finished", snapshot_version=4)
        dialogue = [
            fixture["messages"][0]["text"],
            "Hallo Petra, das kann ich verstehen. Leider kann ich dir nicht weiter helfen",
            "Das ist wirklich ärgerlich, ich brauche das Geld dringend für die Rechnung. "
            "Drei Wochen warten ist zu lange. Bitte prüfen Sie den Status sofort.",
            "Okay, ich prüfe den Status, aber ich bin selbst ein neuer Mitarbeiter und weiß nicht ganz was ich tun soll.",
            "Das ist wirklich unakzeptabel, ich brauche das Geld sofort für die Rechnung. "
            "Bitte leiten Sie das an jemanden weiter, der den Status prüfen kann.",
            "Okay, ich leite Sie weiter.",
            "Ich verstehe, dass Sie das Geld dringend für die Rechnung benötigen, jedoch kann ich die Weiterleitung nicht veranlassen.",
        ]
        for message, text in zip(fixture["messages"], dialogue, strict=True):
            message["text"] = text
        # Capture the request at the model boundary, independently of a simulated rating.
        model = Mock()
        model.antwort.side_effect = TimeoutError
        with self.assertRaises(TimeoutError):
            evaluate({"snapshot": fixture, "rubric": rubric,
                      "scenario_reference": cases["payout_missing"]}, model)
        _, instruction, data = model.antwort.call_args.args
        self.assertEqual([msg["text"] for msg in data["snapshot"]["messages"]], dialogue)
        self.assertEqual(set(data), {"snapshot", "rubric"})
        for hidden in ("Bankverbindung", "Formular", "bank_form_missing"):
            self.assertNotIn(hidden.casefold(), (instruction + str(data)).casefold())

    def test_three_fixtures_resolve_original_quotes_and_differentiate_opportunity(self):
        rubric, cases = load_knowledge()
        expected = {
            "regular": ("Gezeigt", ["regular-m006"]),
            "emotional": ("Übungsbedarf", ["emotional-m006"]),
            "unclear": ("Keine Gelegenheit", []),
        }
        for name, (level, ids) in expected.items():
            with self.subTest(fixture=name):
                fixture = load_fixture(name)
                report = evaluate({
                    "snapshot": fixture, "rubric": rubric,
                    "scenario_reference": cases[fixture["scenario_id"]],
                }, FixtureModel(name))
                observation = next(item for item in report["criteria"] if item["criterion_id"] == "next_step")
                self.assertEqual(observation["level"], level)
                self.assertEqual([proof["message_id"] for proof in observation["evidence"]], ids)
                self.assertEqual(report["snapshot_version"], fixture["snapshot_version"])
                messages = {msg["id"]: msg for msg in fixture["messages"]}
                for item in report["criteria"] + report["strengths"] + report["improvements"]:
                    for proof in item["evidence"]:
                        self.assertEqual(messages[proof["message_id"]]["role"], "trainee")
                        self.assertEqual(proof["quote"], messages[proof["message_id"]]["text"])

    def test_bad_ids_in_suggestions_and_missing_evidence_are_rejected(self):
        rubric, _ = load_knowledge()
        fixture = load_fixture("emotional")
        for evidence_ids in (["emotional-m005"], ["unknown-id"], []):
            with self.subTest(evidence_ids=evidence_ids):
                raw = fixture_model_output("emotional")
                raw["improvements"][0]["evidence_ids"] = evidence_ids
                with self.assertRaises(InvalidEvaluation):
                    validate_feedback(raw, fixture, rubric)
        raw = fixture_model_output("emotional")
        raw["strengths"][0]["criterion_id"] = "unknown-criterion"
        with self.assertRaises(InvalidEvaluation):
            validate_feedback(raw, fixture, rubric)

    def test_model_does_not_receive_session_or_profile_fields(self):
        rubric, cases = load_knowledge()
        fixture = load_fixture("regular")
        fixture["profile_id"] = "private"
        model = Mock(wraps=FixtureModel("regular"))
        evaluate({"snapshot": fixture, "rubric": rubric,
                  "scenario_reference": cases["payout_missing"]}, model)
        sent = model.antwort.call_args.args[2]["snapshot"]
        self.assertEqual(set(sent), {"difficulty", "end_reason", "messages"})


def button(app, label):
    return next(widget for widget in app.button if widget.label == label)


@unittest.skipIf(AppTest is None, "Optional: requirements-streamlit.txt installieren")
class StreamlitTests(unittest.TestCase):
    def start(self, fixture="regular"):
        app = AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py"))).run()
        app.selectbox[0].set_value(fixture).run()
        button(app, "Übung starten").click().run()
        self.assertFalse(app.exception)
        return app

    def round(self, app):
        button(app, "Beispielantwort übernehmen").click().run()
        button(app, "Antwort senden").click().run()
        self.assertFalse(app.exception)

    def test_regular_feedback_is_voluntary_and_discard_removes_session(self):
        app = self.start()
        core = app.session_state.core
        core.evaluate = Mock(wraps=core.evaluate)
        for _ in range(3):
            self.round(app)
        view = app.session_state.view
        self.assertEqual(view["end_reason"], "agreement")
        self.assertEqual(len(view["messages"]), 7)
        self.assertIsNone(view["profile_id"])
        self.assertFalse(view["consent_to_store"])
        self.assertEqual(view["feedback_status"], "not_requested")
        core.evaluate.assert_not_called()
        button(app, "Feedback ansehen").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state.view["feedback"]["snapshot_version"], 3)
        self.assertEqual(len(app.header), 1)
        self.assertTrue(any("Szenarioschwierigkeit" in item.label for item in app.expander))
        self.assertTrue(any("Ich sende Ihnen das Formular" in item.value for item in app.text))
        app.run()
        core.evaluate.assert_called_once()
        button(app, "Neue Übung").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(core.view)
        self.assertNotIn("view", app.session_state)

    def test_empty_finish_and_abort_do_not_offer_feedback(self):
        for label in ("Gespräch beenden", "Übung abbrechen"):
            with self.subTest(action=label):
                app = self.start()
                if label == "Übung abbrechen":
                    self.round(app)
                button(app, label).click().run()
                self.assertFalse(app.exception)
                self.assertIsNone(app.session_state.view["snapshot_version"])
                self.assertNotIn("Feedback ansehen", [widget.label for widget in app.button])

    def test_invalid_draft_stays_and_failed_feedback_reuses_snapshot(self):
        app = self.start("unclear")
        app.text_area[0].set_value("Anderer Text")
        button(app, "Antwort senden").click().run()
        self.assertEqual(app.text_area[0].value, "Anderer Text")
        self.assertEqual(len(app.session_state.view["messages"]), 1)
        for _ in range(2):
            self.round(app)
        button(app, "Gespräch beenden").click().run()
        core = app.session_state.core
        evaluator = core.evaluate
        attempts = []

        def fail_once(data):
            attempts.append(data["snapshot"]["snapshot_version"])
            if len(attempts) == 1:
                raise InvalidEvaluation("Testfehler")
            return evaluator(data)

        core.evaluate = fail_once
        button(app, "Feedback ansehen").click().run()
        self.assertEqual(app.session_state.view["feedback_status"], "failed")
        self.assertTrue(app.error)
        button(app, "Feedback erneut versuchen").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(attempts, [3, 3])
        report = app.session_state.view["feedback"]
        observation = next(item for item in report["criteria"] if item["criterion_id"] == "next_step")
        self.assertEqual((observation["level"], observation["evidence"]), ("Keine Gelegenheit", []))


if __name__ == "__main__":
    unittest.main()
