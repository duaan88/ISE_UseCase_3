# Person B · Anonymer Textablauf nach v0.3

## Start

Im Projektordner mit Python 3.10 oder neuer. Geprüft mit Python 3.12 und Streamlit 1.67.

```sh
python -m pip install -r requirements-streamlit.txt
python -m streamlit run streamlit_app.py --browser.gatherUsageStats false
```

Unter PowerShell dieselben Befehle verwenden. Bei einer bestehenden virtuellen Umgebung lässt sich `python` durch deren Python ersetzen, etwa `.\.venv\Scripts\python.exe`. Streamlit zeigt die lokale URL an (Standardport 8501).

Für die reguläre Übung „Übung starten“ wählen, dreimal „Beispielantwort übernehmen“ und „Antwort senden“ anklicken. Petra nimmt den nächsten Schritt an. „Feedback ansehen“ zeigt danach Rubrik, Begründungen und Originalzitate. Die separate Szenarioschwierigkeit lässt sich ausklappen. Bei den emotionalen und unklaren Testgesprächen am Ende „Gespräch beenden“ wählen. Die Texte und Modellantworten im Testmodus sind synthetisch. Der Testmodus sendet keine Modellanfragen.

## Umsetzung und Prüfung

| Schritt | Dateien | Befehl und erwartete Ausgabe |
|---|---|---|
| Wissenspaket und Bewertungs-Agent | `wissen/synthetisch_v03.json`, `evaluation_v03.py` | `python -m unittest test_person_b_v03.EvaluationTests -v` · Drei Tests prüfen die drei Fixtures, Belegfehler und Modell-Eingabedaten. |
| Vertragstreue Testgespräche | `beispiele/person_b_v03/*.json`, `fixture_v03.py` | Startbefehl oben · Reguläres Gespräch endet nach drei Runden mit Snapshot-Version 3. Die zwei anderen Fixtures enden auf Klick. |
| Streamlit und freiwilliges Feedback | `streamlit_app.py`, `requirements-streamlit.txt`, `test_person_b_v03.py` | `python -m unittest test_person_b_v03 -v` · Sechs Tests, einschließlich drei Streamlit AppTests. Abruf ist freiwillig, Retry behält die Snapshot-Version, Verwerfen entfernt die Sitzung. |
| Regression | bestehende Tests und neue Tests | `python -m unittest discover -q` · Alle Backend- und Person-B-Tests bestehen mit installierten Abhängigkeiten. |

Zusätzlich in Chromium bei 430 px geprüft: drei bestätigte Runden, Feedback erst auf Klick, sichtbare Beleg-ID `regular-m006` und Rückkehr zum Start über „Neue Übung“.

Die Fixture-JSONs sind die drei in v0.3 vereinbarten Sollverläufe. Der simulierte Orchestrator dient nur dem UI-Test mit genau diesen Texten. Er ersetzt keine freie Kundensimulation. Die Wissensquelle ist als eigene JSON-Datei mit Rubrik- und Fallversion angelegt. `load_knowledge(path)` kann denselben Aufbau aus einer anderen Quelle laden. Für freigegebenes Wissen sind Wissens- und Rubrikversion mit A abzugleichen.

Der Validator verlangt pro Rubrikkriterium genau eine Beobachtung und prüft auch Kriterien- und Nachrichten-IDs von Stärken und Verbesserungen. Er ergänzt ausschließlich Zitate und Hilfemarkierungen aus den bestätigten Servicebeiträgen. Für „Keine Gelegenheit“ bleibt die Belegliste leer. Eine ungültige Ausgabe erzeugt einen Fehler statt eines teilweise gültigen Berichts.

## Anschluss an Person A

As Phase-B-Übergabe beschreibt `contract_v03.py`, `customer_v03.py`, `scenarios_v03.py` und `orchestrator_v03.py`. Diese Module sind im Branch `person-a/backend-v03` vorhanden. `build_core(customer_model, evaluation_model)` in `streamlit_app.py` nutzt die dokumentierte Schnittstelle `Orchestrator(CustomerAgent(...), evaluator=..., rubric=...)`. Streamlit hält den Orchestrator je Browser-Sitzung und gibt bei einer Aktion nur Sitzungs-ID, aktuelle Revision, Anforderungs-ID und Aktionsdaten weiter.

Mit serverseitig gesetztem `BLABLADOR_API_KEY` stehen zwei weitere Abläufe zur Auswahl. „Gesprächskern“ verwendet As lokales Kundenmodell und Blablador für freiwilliges Feedback. „Live-Gespräch“ verwendet Blablador für beide Agenten. Die App zeigt die Dauer der letzten erfolgreichen Runde und des Feedbackabrufs separat. Ohne Schlüssel stehen die drei festen Testgespräche zur Verfügung.

Im gemeinsamen Checkout wurden unter Windows mit Python 3.13.9 und Streamlit 1.51.0 alle 82 Tests mit `python -m unittest discover -q` erfolgreich ausgeführt. Der Integrationstest `python -m unittest -v test_streamlit_core_v03` bedient die Live-Option mit ausgetauschtem Modelltransport. Er durchläuft Petra (drei Runden) und Samir (zwei Runden) über Streamlit und As Orchestrator, provoziert einen Timeout, prüft Entwurf und identische Wiederholungsanfrage, den freiwilligen Abruf, Originalbeleg und das Verwerfen. Die älteren SQLite-Tests schließen ihre eigenen Verbindungen vor dem Entfernen temporärer Dateien unter Windows.

Ein externer Modellaufruf und reale Antwortzeiten stehen mangels Teamzugang aus. Die Bereinigung verlassener Browsersitzungen ist noch gemeinsam abzunehmen. Der zuvor dokumentierte Chromium-Lauf stammt aus dem früheren Workspace.

Dieser Schritt deckt den anonymen Textmeilenstein ab. Lernprofil, Personalisierung und Sprache folgen nach der gemeinsamen Kernabnahme.
