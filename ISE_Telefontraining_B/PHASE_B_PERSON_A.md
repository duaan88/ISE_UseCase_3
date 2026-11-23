# ISE Telefontraining – Phase B, Person A

Der anonyme Textablauf nach Vertrag v0.3 liegt im selben Projektordner wie der bisherige FastAPI-Prototyp. Person B kann den neuen Python-Kern direkt aus Streamlit aufrufen. Der bestehende Einstieg `app.py` verwendet weiterhin seinen bisherigen Vertrag.

## Umsetzung und Prüfschritte

| Schritt | Dateien | Befehl | Erwartetes und beobachtetes Ergebnis |
|---|---|---|---|
| Vertrag und Ausgangsstand | `contract_v03.py`, `beispiele/v03/*.json` | `python -m unittest -v test_v03.FixturesTests` | Drei v0.3-Ansichten mit eindeutigen Beleg-IDs und den Abschlussversionen 3, 4 und 3. Vor der Änderung waren alle 61 Bestandstests grün. |
| Kunden-Agent und LLM-Anbindung | `customer_v03.py`, `training.py` (optionaler Timeout und Fehlerklasse im bestehenden Adapter) | `python -m unittest -v test_v03.TextFlowTests.test_live_adapter_sends_only_customer_context` | Nachgebildeter HTTP-Aufruf verarbeitet Modellantwort mit einem 30-Sekunden-Timeout ohne Sitzungs-ID oder unveröffentlichte Fallfakten im Prompt. |
| Fälle und Gesprächskern | `scenarios_v03.py`, `orchestrator_v03.py`, `demo_v03.py` | `python demo_v03.py` und `python demo_v03.py --scenario missing_followup` | Petra erreicht `agreement` mit Snapshot-Version 3 und sieben Nachrichten. Samir erreicht `agreement` mit Snapshot-Version 2 und fünf Nachrichten. |
| Abschluss und Übergabe für Feedback | `orchestrator_v03.py`, `test_v03.py` | `python -m unittest -v test_v03.FeedbackLifecycleTests` | Feedback läuft erst auf Abruf. Nach Fehler und Retry verweist der Bericht auf denselben eingefrorenen Snapshot. Ein erfolgreicher Abruf ist wiederanzeigbar. Verwerfen entfernt die Sitzung. |

Alle Tests: `python -m unittest -q`. Der Kern benötigt Python 3.10+ und keine weiteren Pakete. Live-Demo bei konfiguriertem `BLABLADOR_API_KEY`: `python demo_v03.py --live`. `BLABLADOR_MODEL` ist optional, Standard ist `alias-fast`. Das lokale Beispielmodell braucht keinen Schlüssel. Mangels Schlüssel wurde Blablador hier mit nachgebildeten HTTP-Antworten geprüft. Teste im Live-Lauf Falltreue, Gesprächssprache und Antwortzeiten mit den synthetischen Beispielen. Anbieterbedingungen wurden für diesen Durchlauf nicht verifiziert.

## Übergabe an Person B

`scenarios_v03.scenario_options()` liefert Fall-ID und Titel für die Auswahl. Die Ausschnitte unten zeigen die Python-Schnittstelle. In Streamlit eine Orchestrator-Instanz je Browser-Sitzung über Reruns halten und eine zufällige `request_id` pro Aktion vergeben. Ein wiederholter Versand derselben Aktion verwendet ihre ursprüngliche ID und Version.

```python
from customer_v03 import CustomerAgent, ExampleCustomerModel
from orchestrator_v03 import Orchestrator

# bewerten(evaluation_input) und rubrik sind die Implementierung von Person B.
core = Orchestrator(CustomerAgent(ExampleCustomerModel()),
                    evaluator=bewerten, rubric=rubrik)

view = core.start_session(
    contract_version="0.3", request_id="start-001",
    scenario_id="payout_missing", difficulty_preset="medium",
    usage_mode="anonymous", training_mode="training", coach_enabled=False,
    profile_id=None, consent_to_store=False,
)
sid = view["session_id"]
view = core.submit_turn(sid, expected_version=view["version"],
                        request_id="turn-001", text="Haben Sie einen Brief erhalten?")
view = core.end_conversation(sid, expected_version=view["version"],
                             request_id="end-001", action="finish")
# Erst beim Klick auf „Feedback ansehen“ aufrufen:
view = core.request_feedback(sid, expected_version=view["version"],
                             request_id="feedback-001")
# Bei „Neue Übung“ oder „Sitzung verwerfen“:
core.discard_session(sid)
```

- `get_session(session_id)` liefert die aktuelle Ansicht. Automatisches Ende erscheint im Rundenergebnis.
- `get_completed_snapshot(session_id)` liefert einen unveränderlichen Snapshot. `to_dict()` erzeugt eine unabhängige, JSON-taugliche Kopie. Beim Abruf erhält `bewerten` ein Dictionary mit `snapshot`, `rubric` und `scenario_reference`. `rubric["version"]` und Snapshot-Version müssen im Bericht übereinstimmen.
- B liefert `Feedback` gemäß `contract_v03.py`. B prüft Kriterien und Beleg-IDs sowohl für Kriterienbeobachtungen als auch für Stärken und Verbesserungen. B liest Originalzitat und `assisted` aus dem referenzierten Servicebeitrag. A verwaltet Revisionen, optionalen Aufruf, Retry und Wiederanzeige.
- `SessionError.to_dict()` liefert `code`, `message` und `retryable`. `SessionError.current` enthält bei Versionskonflikt und Feedbackfehler den aktuellen Stand. Ein erneuter Feedbackversuch verwendet die aktuelle Ansichtsrevision und eine neue Anforderungs-ID. Die Snapshot-Version bleibt unverändert.
- Feedback anzeigen, wenn `status == "completed"` und `snapshot_version is not None`. Ein manueller Abschluss ohne Servicebeitrag sowie Abbruch bleiben ohne Bewertungs-Snapshot.
- Die JSON-Dateien in `beispiele/v03/` sind die vereinbarten Fixtures, keine Aufzeichnungen des Modellmodus. `unclear-m002` und `unclear-m004` belegen Klärung im unklaren Verlauf. Für den nächsten Schritt gilt dort „Keine Gelegenheit“. Im emotionalen Verlauf belegt `emotional-m006` den Übungsbedarf. A hat die Fixture-Struktur und referenzierte IDs geprüft. B prüft Bewertungsqualität und UI.

## Umfang des ersten gemeinsamen Meilensteins

Python steuert Reihenfolge, Stimmung, Informationsfreigabe und Abschluss. Der Kunden-Agent antwortet einmal pro Runde und kann einen zuvor von der Engine zugelassenen Schritt ausdrücklich annehmen. Eng gefasste Fallregeln erkennen Nachfragen, Stimmungssignale und zulässige Schritte. Bei freien Paraphrasen kann die Erkennung ausbleiben. Die Schwierigkeit wird separat ausgewiesen. Sie steuert Einstieg, anfänglichen Ärger und Gesprächsanforderungen im Kundenkontext.

Verlauf, Snapshot und Bericht bleiben im Arbeitsspeicher. Der Vorschlagswert für die Inaktivität beträgt 30 Minuten und lässt sich über `idle_seconds` ändern. Die Ablaufprüfung erfolgt beim Zugriff und die Bereinigung beim nächsten Start oder explizit über `cleanup_expired()`. Streamlit-Integration und Bereinigung für verlassene Browser-Sitzungen bleiben Teil der gemeinsamen Abnahme. Der isolierte Test mit nachgebildeter Bewertung ersetzt sie nicht.
