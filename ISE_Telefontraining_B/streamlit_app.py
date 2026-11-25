"""Anonymer Textablauf für Person B mit Streamlit und Vertrag v0.3."""

from functools import partial
import importlib.util
import os
from uuid import uuid4
from time import perf_counter

import streamlit as st

from evaluation_v03 import evaluate, load_knowledge
from fixture_v03 import LABELS, FixtureOrchestrator, load_fixture


PRESETS = {"easy": "Leicht", "medium": "Mittel", "hard": "Schwer"}
DIMENSIONS = {
    "emotional_intensity": "Emotionale Intensität",
    "technical_complexity": "Fachliche Komplexität",
    "ambiguity": "Unklarheit",
    "conversational_dynamics": "Gesprächsdynamik",
    "information_load": "Umfang und Informationslast",
}
CRITERIA = {"empathy": "Empathie", "clarification": "Anliegen klären", "next_step": "Nächster Schritt"}
CORE_MODULES = ("orchestrator_v03", "customer_v03", "scenarios_v03", "contract_v03")


def build_core(customer_model, evaluation_model, *, scenario_id=None):
    """Bs Anschluss an As Orchestrator. Beide Modelle werden explizit gewählt."""
    from customer_v03 import CustomerAgent
    from orchestrator_v03 import Orchestrator

    rubric, _ = load_knowledge(scenario_id=scenario_id)
    return Orchestrator(CustomerAgent(customer_model),
                        evaluator=partial(evaluate, model=evaluation_model), rubric=rubric)


def start_form(state):
    has_core = all(importlib.util.find_spec(name) for name in CORE_MODULES)
    key = os.environ.get("BLABLADOR_API_KEY", "").strip()
    modes = ["Testgespräch"]
    if has_core and key:
        modes.extend(["Gesprächskern", "Live-Gespräch"])
    mode = st.radio("Ablauf", modes,
                    horizontal=True)
    if mode == "Testgespräch":
        title = "Mein Geld ist noch nicht da"
        fixture = st.selectbox("Testgespräch für „Mein Geld ist noch nicht da“", LABELS,
                               format_func=LABELS.__getitem__)
        sample = load_fixture(fixture)
        scenario_id = sample["scenario_id"]
        preset = sample["difficulty"]["preset"]
        training_mode = sample["training_mode"]
        st.caption("Feste Kundenantworten und nachgebildete Bewertung. Es werden keine Modellanfragen gesendet.")
    else:
        from scenarios_v03 import scenario_options

        options = scenario_options()
        scenario_id = st.selectbox("Übungsfall", list(options), format_func=options.__getitem__)
        title = options[scenario_id]
        preset = st.selectbox("Schwierigkeit", PRESETS, index=1, format_func=PRESETS.__getitem__)
        modes = {"training": "Training", "testing": "Testing"}
        training_mode = st.radio("Übungsmodus", modes, horizontal=True, format_func=modes.__getitem__)
        if mode == "Live-Gespräch":
            st.caption("Blablador erzeugt die Kundenantworten und auf Wunsch das Feedback. Nur fiktive Angaben eingeben.")
        else:
            st.caption("Lokales Kundenmodell. Erst für angefordertes Feedback wird das fiktive Gespräch an Blablador gesendet.")

    if not st.button("Übung starten", type="primary"):
        return
    if mode == "Testgespräch":
        core = FixtureOrchestrator(fixture)
    else:
        from customer_v03 import ExampleCustomerModel
        from training import Blablador

        backend = Blablador(key, timeout=30)
        core = build_core(backend if mode == "Live-Gespräch" else ExampleCustomerModel(),
                          Blablador(key, timeout=90), scenario_id=scenario_id)
    try:
        view = core.start_session(
            contract_version="0.3", request_id=uuid4().hex, scenario_id=scenario_id,
            difficulty_preset=preset, usage_mode="anonymous", training_mode=training_mode,
            coach_enabled=False, profile_id=None, consent_to_store=False,
        )
    except Exception as exc:
        report_error(state, exc)
        st.rerun()
    state.update(core=core, view=view, scenario_title=title,
                 fixture_mode=mode == "Testgespräch", reset_draft=True)
    st.rerun()


def report_error(state, error):
    to_dict = getattr(error, "to_dict", None)
    if not callable(to_dict):
        raise error
    details = to_dict()
    current = getattr(error, "current", None)
    if current is not None:
        state.view = current
    if details.get("code") == "SESSION_NOT_FOUND":
        state.pop("view", None)
        state.pop("core", None)
        state["reset_draft"] = True
    state.error = details.get("message") or "Die Aktion konnte nicht ausgeführt werden."


def act(state, operation, **fields):
    view = state.view
    signature = (view["session_id"], view["version"], operation, fields)
    previous = state.get("pending_action")
    if previous is None or previous[0] != signature:
        state.pending_action = (signature, uuid4().hex)
    started = perf_counter()
    try:
        state.view = getattr(state.core, operation)(
            view["session_id"], expected_version=view["version"], request_id=state.pending_action[1], **fields)
    except Exception as exc:
        report_error(state, exc)
        if operation == "request_feedback" or exc.to_dict()["code"] in ("SESSION_NOT_FOUND", "VERSION_CONFLICT"):
            state.pop("pending_action", None)
    else:
        state.pop("pending_action", None)
        if operation in ("submit_turn", "request_feedback"):
            state[operation + "_seconds"] = perf_counter() - started
        if operation in ("submit_turn", "end_conversation"):
            state.reset_draft = True
    st.rerun()


def evidence_rows(evidence, messages):
    for item in evidence:
        message = messages[item["message_id"]]
        help_label = " · mit Coach-Hilfe" if item["assisted"] else ""
        st.caption(f"Runde {message['turn']} · {item['message_id']}{help_label}")
        st.text(item["quote"])


def render_feedback(report, messages):
    st.header("Feedback zur Übung")
    st.caption(f"Rubrik {report['rubric_version']} · Gesprächsversion {report['snapshot_version']}")
    st.subheader("Kritische Befunde")
    if report["critical_findings"]:
        for finding in report["critical_findings"]:
            st.write("Unbelegte Auszahlungszusage")
            st.text(finding["reason"])
            evidence_rows(finding["evidence"], messages)
    else:
        st.caption("Keine eindeutige terminierte Auszahlungszusage erkannt." if
                   st.session_state.view["scenario_id"] == "payout_missing" else
                   "Für diesen Fall ist keine kritische Prüfregel hinterlegt.")
    st.subheader("Kriterienbewertung")
    for item in report["criteria"]:
        st.write(CRITERIA.get(item["criterion_id"], item["criterion_id"]), "·", item["level"])
        st.text(item["rationale"])
        evidence_rows(item["evidence"], messages)
    for key, heading in (("strengths", "Stärken"), ("improvements", "Verbesserungsvorschläge")):
        if report[key]:
            st.subheader(heading)
            for item in report[key]:
                st.caption(CRITERIA.get(item["criterion_id"], item["criterion_id"]))
                st.text(item["text"])
                evidence_rows(item["evidence"], messages)
    if report["next_practice"]:
        st.subheader("Nächster Übungsschritt")
        st.text(report["next_practice"])


def render_session(state):
    try:
        view = state.core.get_session(state.view["session_id"])
    except Exception as exc:
        report_error(state, exc)
        st.rerun()
    state.view = view
    difficulty = view["difficulty"]
    st.subheader(state.scenario_title)
    if not state.fixture_mode:
        for operation, label in (("submit_turn", "Letzte Gesprächsrunde"), ("request_feedback", "Bewertung")):
            if (seconds := state.get(operation + "_seconds")) is not None:
                st.caption(f"{label} · {seconds:.1f} s")
    st.caption(("Testgespräch · " if state.fixture_mode else "") +
               ("Training" if view["training_mode"] == "training" else "Testing"))
    with st.expander(f"Szenarioschwierigkeit · {PRESETS[difficulty['preset']]}"):
        for key, label in DIMENSIONS.items():
            st.write(f"{label} · {difficulty[key]} von 3")
    messages = {message["id"]: message for message in view["messages"]}
    for message in messages.values():
        is_trainee = message["role"] == "trainee"
        with st.chat_message("user" if is_trainee else "assistant",
                             avatar="👤" if is_trainee else "☎️"):
            st.caption("Servicekraft" if is_trainee else "Kunde")
            st.text(message["text"])

    if view["status"] == "active":
        sample = state.core.next_sample() if state.fixture_mode else None
        if sample is not None:
            with st.expander("Beispielantwort für diesen Test", expanded=True):
                st.text(sample)
                st.button("Beispielantwort übernehmen", on_click=lambda: state.update(draft=sample))
        with st.form("turn"):
            text = st.text_area("Deine Antwort", key="draft", max_chars=2000)
            send = st.form_submit_button("Antwort senden", type="primary",
                                         disabled=state.fixture_mode and sample is None)
        if send:
            if not text.strip():
                st.warning("Gib eine Antwort ein.")
            else:
                act(state, "submit_turn", text=text.strip())
        finish, abort = st.columns(2)
        if finish.button("Gespräch beenden"):
            act(state, "end_conversation", action="finish")
        if abort.button("Übung abbrechen"):
            act(state, "end_conversation", action="abort")
        return

    st.write("Übung abgebrochen." if view["status"] == "aborted" else "Gespräch beendet.")
    if view["status"] == "completed" and view["snapshot_version"] is not None:
        status = view["feedback_status"]
        if status == "ready":
            render_feedback(view["feedback"], messages)
        elif status == "running":
            st.info("Feedback wird erstellt.")
            if st.button("Feedbackstatus aktualisieren"):
                try:
                    state.view = state.core.get_session(view["session_id"])
                except Exception as exc:
                    report_error(state, exc)
                st.rerun()
        elif st.button("Feedback erneut versuchen" if status == "failed" else "Feedback ansehen", type="primary"):
            with st.spinner("Feedback wird erstellt …"):
                act(state, "request_feedback")
    elif view["status"] == "completed":
        st.caption("Für Feedback ist mindestens eine bestätigte Serviceantwort nötig.")

    if st.button("Neue Übung"):
        try:
            state.core.discard_session(view["session_id"])
        except Exception as exc:
            report_error(state, exc)
        else:
            state.pop("view", None)
            state.pop("core", None)
            state.reset_draft = True
        st.rerun()


def main():
    st.set_page_config(page_title="ISE Telefontraining", page_icon="☎️")
    st.title("Telefontraining")
    st.caption("Anonyme Textübung mit fiktiven Fällen · kein Lernprofil")
    state = st.session_state
    if state.pop("reset_draft", False):
        state.pop("draft", None)
    if error := state.pop("error", None):
        st.error(error)
    if "view" in state:
        render_session(state)
    else:
        for key in ("pending_action", "submit_turn_seconds", "request_feedback_seconds"):
            state.pop(key, None)
        start_form(state)


if __name__ == "__main__":
    main()
