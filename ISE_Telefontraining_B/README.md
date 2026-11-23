# ISE Telefontraining · Variante B · Person 1

Trainingskern für den fiktiven Petra-Fall: Direktstart ohne Umfrage, vier spezialisierte Agentenrollen, freiwilliger Fokus, Gesprächsgedächtnis, Coach und optionales SQLite-Lernprofil. Der Python-/FastAPI-Stack bleibt erhalten. Alle Fallfakten, Auszahlungen, Formulare und Fristen sind Übungsbeispiele.

## Phase B · Anonyme Streamlit-Textübung nach Vertrag v0.3

Im Projektordner installieren und starten:

```bash
python -m pip install -r requirements-streamlit.txt
python -m streamlit run streamlit_app.py --browser.gatherUsageStats false
```

„Testgespräch“ nutzt feste fiktive Dialoge und nachgebildete Bewertungen ohne API-Key. Mit gesetztem `BLABLADOR_API_KEY` bietet „Gesprächskern“ beide Fälle aus Person As Backend an. Dabei antwortet das lokale Kundenmodell. Erst „Feedback ansehen“ sendet das fiktive Transkript zur Bewertung an Blablador. Der Bericht belegt seine Beobachtungen mit Originalaussagen aus bestätigten Runden und zeigt die Schwierigkeit separat.

[Startanleitung, Tests und Anschluss an Person A](docs/PERSON_B_V03.md) · [Backend-Übergabe von Person A](PHASE_B_PERSON_A.md)

## Direkt starten und prüfen

Der Kern braucht Python 3.10 oder neuer und ausschließlich die Standardbibliothek. Lokal geprüft mit Python 3.12. Alle Befehle im entpackten Projektordner ausführen:

```bash
python training.py
python -m unittest -v
python demo_lernprofil.py
python demo_uebergabe.py --datei beispiele/uebergabe.json
```

Unter Windows kann `python` durch `py -3.12` ersetzt werden. Erwartet: Direktstart mit `Fallstandard (fallstandard)`, Ärger 4 → 3, Formularhinweis, nach zwei Antworten `gelöst` und ein Coach-Tipp. Die Tests enden mit `Ran 61 tests ... OK`. Die Profildemo zeigt zwei vorbereitete Übungen und den Vorschlag `empathie`, Quelle `lernprofil`. Ohne `--db` nutzt sie eine temporäre Datenbank.

Die enthaltenen Transportdateien `app.py` und `index.html` zeigen weiterhin die ursprüngliche Browser-Demo mit Pflichtumfrage. Sie wurden für die parallele Arbeit von Person 2 unverändert gelassen; die neuen Kernaktionen sind dort noch anzuschließen. Der bisherige HTTP-Textpfad wurde auf Kompatibilität geprüft.

Für die bestehende Browser-Demo die Abhängigkeiten aus `requirements.txt` in einer virtuellen Umgebung installieren und Uvicorn starten:

```bash
python -m venv .venv
# Linux/macOS:
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Unter Windows dieselben Befehle mit dem Python unter `.venv/Scripts/python.exe` ausführen. Browser: [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Fachlicher Ablauf

1. `starte("auszahlung")` beginnt ohne Profilzugriff und ohne Umfrage. Optionaler Fokus: manuelle Wahl vor niedrigstem Umfragewert vor ausdrücklich übergebenem Profilvorschlag vor Fallstandard. Vollständige Umfragewerte müssen echte Ganzzahlen von 1–5 sein; Gleichstand: Empathie, Klärung, nächster Schritt.
2. Regie schlägt Stimmung, Hinweisfreigabe, Nachfrage und Vereinbarung vor. Python prüft Typen und begrenzt Ärger und Vertrauen auf 1–5 bei maximal ±1 pro Runde. Kunde formuliert mit sichtbarem Kontext; Python ergänzt freigegebenen Hinweis und Nachfrage. Erst danach wird die Runde gemeinsam übernommen.
3. Coach-Modi: `aus` (Standard), `auf_abruf`, `kritisch`. Im abgesicherten Modus hält die konkrete belegte Zusage eines Auszahlungstermins bei offenem Termin vor Petras Antwort an. „Weiter“ bestätigt den Entwurf einmal; „Neu formulieren“ verwirft ihn. Beide Wege markieren die nächste bestätigte Runde nach dem Tipp als unterstützt.
4. Die bisherigen Abschlussregeln bleiben: passende Vereinbarung nach Hinweis bei Ärger höchstens 3; zwei bestätigte Runden hintereinander mit Ärger 5; sechs Runden; manuelles Ende oder Abbruch. „Gelöst“ bedeutet eine Vereinbarung zum nächsten Schritt. Der Auszahlungstermin bleibt offen.
5. Nach einer auswertbaren abgeschlossenen Übung ruft die Anwendung auf Wunsch Bewertung → Coach auf. Stufe und Beleg-Rundennummer werden validiert; das Originalzitat liest Python aus dem bestätigten Text. Unterstützte Stellen sind gekennzeichnet. Ohne Fokus bestimmt vorrangig belegter Übungsbedarf den Tipp. Ein Selbstabgleich ist nur bei vorhandener Umfrage enthalten.
6. Erst „Fortschritt merken“ speichert den vorhandenen Bericht kompakt. Ein gesondertes „Lernprofil nutzen“ liest einen Vorschlag für eine neue Übung. Start, Runden und Feedback speichern nichts automatisch.

## Lernprofilregel und Daten

Je Kriterium zählen die letzten fünf tatsächlichen Beobachtungen. Die Anzahl `Übungsbedarf` hat Vorrang, danach `Teilweise gezeigt`, danach die feste Kriterienreihenfolge. Wiederkehrender Bedarf hat damit Vorrang vor einmaligem. `Keine Gelegenheit` wird übersprungen. Ein leeres Profil oder ausschließlich `Gezeigt` ergibt `fokus=None` und erlaubt den Fallstandard. Hilfe wird gespeichert, ändert diese einfache Auswahlregel aber nicht.

SQLite enthält Profil-/Übungs-ID, UTC-Zeitpunkt, Kriterium, Stufe und Hilfemarkierung je Beleg und Übung. Transkript, Originalzitate, Coach-Tipp und Umfrage stehen ausschließlich in der flüchtigen Übung. Der Schlüssel Profil + Übung verhindert doppelte Speicherung auch bei parallelen Wiederholungen. Fiktive Profile bleiben getrennt. Es findet kein Modelltraining statt.

Standarddatei: `lernprofile.sqlite3`, konfigurierbar über `ISE_LERNPROFIL_DB` oder `db_pfad=...`. Abruf eines nicht vorhandenen Profils legt keine Datei an. Ein dauerhafter Beispieldurchlauf lässt sich zweimal ausführen; beim zweiten Mal bestätigt er die vorhandenen Übungen:

```bash
python demo_lernprofil.py --db /tmp/ise-profil-demo.sqlite3
```

## Dateien und Übergabe

| Datei | Zweck |
|---|---|
| `training.py` | Zustand, Start, vier Rollen, Coach-Aktionen, atomare Runde und Bericht |
| `faelle.py` | Fiktive Fakten, lokale Sprachanker, Fragen, Stimmenkennungen und Abschlussregeln |
| `lernprofil.py` | Freiwillige SQLite-Persistenz und nachvollziehbare Fokusregel |
| `test_training.py`, `test_lernprofil.py` | 61 lokale Tests einschließlich sieben unveränderter Bestandstests |
| `demo_lernprofil.py`, `demo_uebergabe.py` | Reproduzierbare Profil- und Zustandsbeispiele |
| [UEBERGABE_PERSON_2.md](UEBERGABE_PERSON_2.md) | Signaturen, JSON-Beispiele und Transportintegration |
| [ISE_EINORDNUNG.md](ISE_EINORDNUNG.md) | Alle elf Dimensionen der Morphologischen Box mit Originalquellen |
| [ARBEITSSTAND.md](ARBEITSSTAND.md) | Ist-Stand, abgeschlossene Schritte, Prüfungen und verbleibende Integration |

Die Fachlogik kann durch Fallkonfiguration erweitert werden. Für den lokalen Regelmodus gehören Hinweiswörter, Handlungsverben und passende Gegenstände ebenfalls zur Karte. `FAELLE`, `KRITERIEN`, `NACHFRAGEN` und bisherige Funktionen bleiben über `training` importierbar.

## Geprüft und noch live zu prüfen

Geprüft sind regelbasierte Dialoge, nachgebildete Modellausgaben und Fehler, Fokuspriorität, private Hinweise, Coach-Entwürfe, Belegvalidierung, Wiederholung und Trennung der Profile, Neustart-Persistenz und die bisherige FastAPI-Textschnittstelle. Die enge kritische Python-Regel prüft den definierten Demo-Fall; sie ist kein vollständiger Parser jeder deutschen Zusage. Bei Zitaten und unsicherem Wortlaut unterbleibt der automatische Eingriff.

Ein echtes Blablador-Modell wurde nicht aufgerufen. Live zu prüfen sind Ausgabeformate, Falltreue, Garantiezusage und Gegenbeispiele, Qualität der Beobachtungen und Antwortzeit. Für den KI-Modus setzt Person 2 `BLABLADOR_API_KEY`, optional `BLABLADOR_MODEL` (Standard `alias-fast`). Die Workshop-`.env` wurde weder übernommen noch genutzt. Audio und neue Browseraktionen gehören zur anschließenden Person-2-Integration.
