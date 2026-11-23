"""Streamlit mit As Orchestrator und nachgebildetem Blablador-Transport."""

import json
from pathlib import Path
import unittest
from unittest.mock import patch

from contract_v03 import SessionError
from customer_v03 import ExampleCustomerModel
from demo_v03 import TURNS
from test_person_b_v03 import AppTest, button


@unittest.skipIf(AppTest is None, "requirements-streamlit.txt installieren")
class CoreIntegrationTests(unittest.TestCase):
    def test_both_live_flows_with_simulated_models(self):
        for scenario, turns in TURNS.items():
            with self.subTest(scenario=scenario):
                calls = []
                def answer(role, prompt, data):
                    calls.append(role)
                    if role == "Kunde":
                        if len(calls) == 1:
                            raise TimeoutError()
                        return ExampleCustomerModel().antwort(role, prompt, data)
                    self.assertEqual(data["scenario_reference"]["scenario_id"], scenario)
                    messages = data["snapshot"]["messages"]
                    criteria = [
                        {"criterion_id": criterion, "level": "Gezeigt", "rationale": "Beispielbeobachtung.",
                         "evidence_ids": [messages[index]["id"]]}
                        for criterion, index in (("empathy", 1), ("clarification", 1), ("next_step", -2))
                    ]
                    return json.dumps(dict(criteria=criteria, strengths=[], improvements=[], next_practice=None))

                with patch.dict("os.environ", BLABLADOR_API_KEY="test"), patch("training.Blablador.antwort", side_effect=answer):
                    app = AppTest.from_file(str(Path(__file__).with_name("streamlit_app.py"))).run()
                    app.radio[0].set_value("Live-Gespräch").run()
                    app.selectbox[0].set_value(scenario).run()
                    button(app, "Übung starten").click().run()
                    core = app.session_state.core
                    with patch.object(core, "submit_turn", wraps=core.submit_turn) as submit:
                        for index, turn in enumerate(turns):
                            app.text_area[0].set_value(turn)
                            button(app, "Antwort senden").click().run()
                            if index == 0:
                                self.assertEqual(app.text_area[0].value, turn)
                                self.assertEqual(app.session_state.view["version"], 0)
                                button(app, "Antwort senden").click().run()
                                self.assertEqual(submit.call_args_list[0], submit.call_args_list[1])
                            self.assertFalse(app.exception)
                    view = app.session_state.view
                    self.assertEqual(view["end_reason"], "agreement")
                    self.assertEqual(view["snapshot_version"], len(turns))
                    self.assertNotIn("Bewertung", calls)
                    button(app, "Feedback ansehen").click().run()
                    report = app.session_state.view["feedback"]
                    self.assertEqual(report["snapshot_version"], len(turns))
                    self.assertEqual(report["criteria"][-1]["evidence"][0]["quote"], turns[-1])
                    self.assertEqual(calls.count("Bewertung"), 1)
                    button(app, "Neue Übung").click().run()
                    with self.assertRaises(SessionError):
                        core.get_session(view["session_id"])
