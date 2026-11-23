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

Sobald As Module im Projektordner liegen und `BLABLADOR_API_KEY` im Backend gesetzt ist, bietet Streamlit „Gesprächskern“ an. Diese Option verwendet ausdrücklich As lokales `ExampleCustomerModel` und ruft Blablador erst für angefordertes Feedback auf. Für die gemeinsame Live-Abnahme beider Agenten kann A sein Live-Kundenmodell an `build_core` übergeben. Der Anschluss an As Backend wurde für beide Fälle mit lokaler Kundensimulation und nachgebildeter Bewertungsantwort geprüft. Der echte Modellzugang und die Bereinigung verlassener Live-Sitzungen bleiben separat zu prüfen. In der lokalen Testansicht entfernt „Neue Übung“ sowohl den simulierten Backend-Zustand als auch die Streamlit-Ansicht.

Dieser Schritt deckt den anonymen Textmeilenstein ab. Lernprofil, Personalisierung und Sprache folgen nach der gemeinsamen Kernabnahme.
