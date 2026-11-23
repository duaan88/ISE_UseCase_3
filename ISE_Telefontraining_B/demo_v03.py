"""Mehrzügiger Textlauf beider Fallkarten, lokal oder ausdrücklich mit Blablador."""

import argparse

from contract_v03 import CONTRACT_VERSION, SessionError
from customer_v03 import CustomerAgent, ExampleCustomerModel
from orchestrator_v03 import Orchestrator

TURNS = {
    "payout_missing": (
        "Ich verstehe, dass die Wartezeit Sie belastet. Was wurde Ihnen zuletzt zur Auszahlung mitgeteilt?",
        "Haben Sie einen Brief oder eine Nachricht zu den benötigten Unterlagen erhalten?",
        "Ich sende Ihnen das Formular zu und melde mich morgen bis 12 Uhr mit einem Zwischenstand. "
        "Einen Auszahlungstermin kann ich noch nicht bestätigen. Passt das für Sie?",
    ),
    "missing_followup": (
        "Ich verstehe, dass die Wartezeit Sie belastet. An welche Adresse ging die letzte Nachricht?",
        "Ich prüfe Ihre Adresse und melde mich morgen bis 12 Uhr mit einem Zwischenstand. Passt das für Sie?",
    ),
}


def demo(customer: CustomerAgent, scenario_id: str) -> None:
    orchestrator = Orchestrator(customer)
    view = orchestrator.start_session(
        contract_version=CONTRACT_VERSION, request_id="demo-start",
        scenario_id=scenario_id, difficulty_preset="medium", usage_mode="anonymous",
        training_mode="training", coach_enabled=False, profile_id=None, consent_to_store=False,
    )
    session_id = view["session_id"]
    print(f"Fall: {view['scenario_id']} ({view['difficulty']['preset']})")
    print(f"Kunde: {view['messages'][0]['text']}")
    for number, text in enumerate(TURNS[scenario_id], 1):
        view = orchestrator.submit_turn(
            session_id, expected_version=view["version"], request_id=f"demo-turn-{number}", text=text,
        )
        print(f"Service: {view['messages'][-2]['text']}")
        print(f"Kunde: {view['messages'][-1]['text']}")
        if view["status"] != "active":
            break
    if view["status"] == "active":
        view = orchestrator.end_conversation(
            session_id, expected_version=view["version"], request_id="demo-finish", action="finish",
        )
    snapshot = orchestrator.get_completed_snapshot(session_id)
    print(f"Abschluss: {view['end_reason']} | Snapshot: {snapshot.snapshot_version} | "
          f"Nachrichten: {len(snapshot.messages)} | Feedback: {view['feedback_status']}")
    orchestrator.discard_session(session_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=TURNS, default="payout_missing")
    parser.add_argument("--live", action="store_true", help="Blablador mit synthetischen Beiträgen verwenden")
    args = parser.parse_args()
    try:
        agent = CustomerAgent.from_environment() if args.live else CustomerAgent(ExampleCustomerModel())
        print("Modus:", "Blablador" if args.live else "Lokales Beispielmodell")
        demo(agent, args.scenario)
    except SessionError as exc:
        parser.exit(1, f"{exc.code}: {exc.message}\n")
