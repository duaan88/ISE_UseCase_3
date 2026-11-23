# Arbeitsstand Person 1

## Geprüfter Ausgangsstand

- ZIP in eigenen Ordner `ISE_Telefontraining_B` entpackt; kein Git-Checkout und keine AGENTS.md vorhanden.
- Sieben bestehende Tests mit `python -m unittest -v` erfolgreich.
- `training.py`: vier Rollen bereits über `Modell.antwort`, atomare Runde und Abschlussregeln vorhanden; Umfrage Pflicht, Fokus nicht nullable, Fallregeln teilweise hart codiert, keine Dialog-Coach-Aktionen, keine SQLite-Persistenz.
- `app.py` / `index.html` gelesen: bisherige verpflichtende Startumfrage und alte Aktionsmenge; Person 2 verantwortet deren Erweiterung. Der bestehende Transportpfad mit Umfrage muss kompatibel bleiben.
- Workshop-.env nicht übernommen; lokale Beispiele benötigen keinen Schlüssel.

## Arbeitsschritte

1. Optionaler Start, Fokuspriorität und konfigurierbare Fallkarte; direkte Petra-Runde und bisherige Tests prüfen.
2. Regie/Kundin validieren, Coach-Modi und atomaren Entwurf einführen; gezielte Fehler- und Zustandsprüfungen.
3. Beleggestützte Bewertung mit Hilfemarkierung und abschließender Coach; Feedback prüfen.
4. Freiwilliges SQLite-Lernprofil samt zwei Beispielübungen und Persistenztests.
5. Schnittstellenübergabe, Morphologische Box anhand Originalquellen und gemeinsame Abnahme; auslieferbares ZIP.

Ergebnisse, Befehle und erwartete Ausgaben stehen nach jedem Schritt unten; ausschließlich lokale Regeln und nachgebildete Modellantworten sind als geprüft zu behandeln. Live-Blablador ist gesondert zu validieren.

## Abgeschlossene Schritte

### 1 · Direktstart und Fallkarten

Geändert: `training.py`, neu `faelle.py`, erweitert `test_training.py`.
Umfrage optional, vollständige Skalenprüfung, Fokusquelle und Priorität; Standardfragen, interne Fakten, erlaubte Schritte und Abschlussgrenzen in Fallkarten. `FAELLE`, `KRITERIEN`, `NACHFRAGEN` und bisherige Funktionen bleiben importierbar. Ein neuer Versandfall wurde allein über Konfiguration geprüft.

Start: `python training.py`. Erwartet und beobachtet: `Fallstandard (fallstandard)`, erste Runde Ärger 3, Formularhinweis, nach zweiter Runde `gelöst`.
Tests: sieben unveränderte Tests aus dem ZIP zuerst isoliert gegen den erweiterten Kern ausgeführt → `Ran 7 tests ... OK`; sie sind weiterhin in `python -m unittest -v test_training` enthalten. Start-/Fallprüfungen lassen sich gezielt mit `python -m unittest -v test_training.StartUndFallkartenTest` ausführen → `OK`.

### 2 · Regie und Kundin

Geändert: `training.py`, `faelle.py`, `test_training.py`.
Regie erhält interne Fallfakten, Kunde sichtbaren Kontext und neue Stimmung. Text-/JSON-Typen und Grenzen werden geprüft; pro Runde maximal ±1 und Skala 1–5. Hinweis, Stimmung und Transkript werden atomar übernommen. Neutrale Fragen verraten keine privaten Fakten. Lokale Handlungsanker sind fallbezogen; ein Werbeangebot löst den Auszahlungsfall nicht.

Prüfbefehl: `python -m unittest -v test_training.RundenUndModellgrenzenTest test_training.TelefontrainingTest` → `OK` (im vollständigen Kerntestlauf ebenfalls geprüft). Fehlermodelle hinterlassen den alten bestätigten Stand. Eskalation, Rundenlimit, Abbruch und reguläre Lösung bleiben erhalten.

### 3 · Coach und Entwurf

Geändert: `training.py`, `test_training.py`; neue Aktionssignaturen in `UEBERGABE_PERSON_2.md`.
Abruf nur bei aktiviertem Coach. Abgesicherter Eingriff nur bei offener Auszahlung, richtiger Regel-ID, wörtlichem Beleg mit eindeutigem Auszahlungs-/Terminbezug. Regie-Markierung alleine genügt nicht. Negative Proben umfassen Rückmeldezeit, Negation, Vermutung, berichtete Rede und abgelehnte Zitate. Die enge Demo-Regel behandelt unklare Formulierungen regulär und ersetzt keine allgemeine Sprachanalyse.

Prüfbefehl: `python -m unittest -v test_training.CoachUndEntwurfTest` → `OK` (im vollständigen Kerntestlauf geprüft). Erwartet: keine Kundenantwort und unveränderter Fachzustand während Pause; `weiter` genau eine unterstützte Runde; `neu_formulieren` verwirft Entwurf und markiert erst die nächste bestätigte Runde unterstützt; Abschluss/Abbruch räumt auf.

### 4 · Bewertung und abschließender Coach

Geändert: `training.py`, `test_training.py`.
Genau drei Kriterien, vier erlaubte Stufen und gültige bestätigte Rundennummern. Originalzitat und Hilfemarkierung stammen aus der Runde. Direktstart priorisiert belegten Übungsbedarf, bei gleichem Bedarf eigenständige Belege, dann Kriterienreihenfolge. Bei vorhandenem Fokus richtet sich der Tipp danach. Der Selbstabgleich zeigt Sicherheitswert und Beobachtungsstufe nebeneinander; ohne Umfrage bleibt er leer. Abschlussfeedback ist unabhängig vom Dialog-Coach.

Prüfbefehl: `python -m unittest -v test_training.BewertungsVertragTest` → `OK` (im vollständigen Kerntestlauf geprüft). Erwartet: falsche/boolesche Belegstellen und fremde Kriterien werden abgewiesen, vom Modell erfundene Zitate werden durch den Originaltext ersetzt.

### 5 · Freiwilliges Lernprofil

Neu: `lernprofil.py`, `test_lernprofil.py`, `demo_lernprofil.py`.
SQLite speichert nur kompakte Beobachtungen, Zeitpunkt und Hilfe je Beleg und Übung. Profil + Übung ist eindeutig. Schreiben nach vorhandenem Bericht, Lesen separat; keine automatische Nutzung. Wiederkehrender Bedarf der letzten fünf Beobachtungen je Kriterium wird priorisiert. Keine Gelegenheit ist fehlende Beobachtung. Leerer Zustand ergibt keinen Fokus.

Tests: `python -m unittest -q test_lernprofil` → `Ran 19 tests ... OK`. Geprüft sind Berichtbindung, Profiltrennung, parallele Wiederholung, Neustart-Lesbarkeit, leeres Profil und die Hilfemarkierung auch dann, wenn eine unterstützte Runde nicht zitiert wird.
Demo: `python demo_lernprofil.py` → zwei bestätigte Speicherungen, Vorschlag `empathie` mit 2× Übungsbedarf, neuer Start mit Quelle `lernprofil`. Standardmäßig temporär; `--db PFAD` erlaubt einen dauerhaften Durchlauf.

### 6 · Übergabe und Abnahme

Neu/aktualisiert: `README.md`, `UEBERGABE_PERSON_2.md`, `ISE_EINORDNUNG.md`, `demo_uebergabe.py`, `beispiele/uebergabe.json`, dieser Arbeitsstand.
Die ISE-Einordnung ordnet alle elf Dimensionen den Aufgaben-, Agenten- und Gruppenbezugspunkten zu und belegt die Auswahl anhand der Originalbox, der Erläuterungen, Kickoff, Workshop und Architektur. Signaturen, bestätigte Runde und Coach-Entwurf stehen in der Übergabe.

Befehle: `python demo_uebergabe.py --datei beispiele/uebergabe.json` → Datei geschrieben; JSON separat mit erneut ausgeführten Beispielen abgeglichen. `python -m unittest -q` → **Ran 61 tests ... OK** (42 Kern, 19 Profil). `python training.py` und `python demo_lernprofil.py` erfolgreich ausgeführt.

Zusätzlich geprüft: bestehender FastAPI-TestClient-Pfad Start mit Umfrage → zwei Antworten → gelöst → Feedback mit Originalzitat → Löschen. `app.py`, `index.html`, `requirements.txt` sind bytegleich zum ZIP-Ausgangsstand. Der FastAPI-TestClient war in der Arbeitsumgebung vorhanden; zusätzliche Pakete wurden nicht installiert.

## Prüfgrenzen und verbleibende Parallelentwicklung

**Geprüft:** lokaler Regelmodus, nachgebildete Modellausgaben/HTTP-Antworten, Persistenz, Fachzustand und bisheriger Texttransport. Laufzeiten der Unittests sind kein Nachweis für Modellantwortzeit.

**Noch zu prüfen:** echtes Blablador-Modell (Falltreue, Formate, Bewertungsqualität, Antwortzeit), Audio und neue Browseraktionen. Person 2 muss optionale Umfrage, Profilaktionen und Coach-Zustände im Transport ergänzen. Die bestehende Browser-Demo fordert die Umfrage weiterhin an. Der konkrete Implementierungsplan dafür steht in `UEBERGABE_PERSON_2.md`. Keine Schlüssel oder Workshop-.env im Ergebnis.
