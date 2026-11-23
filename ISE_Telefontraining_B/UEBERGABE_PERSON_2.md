# Übergabe Person 1 → Person 2

Der Trainingskern und die Profilfunktionen sind lokal implementiert. `app.py`, `index.html` und `requirements.txt` bleiben unverändert. Ihr bisheriger Umfrage-/Textpfad funktioniert weiter. Neue HTTP-Aktionen, Direktstart im Browser und Audio sind noch in den Transport zu integrieren.

## Öffentliche Funktionen

```python
starte(fall_id, einschaetzung=None, fokus=None, *, profil_fokus=None, coaching="aus") -> Gespraech
naechste_runde(gespraech, aussage, modell) -> Gespraech
hinweis_anfordern(gespraech, modell) -> Gespraech
weiter(gespraech, modell) -> Gespraech
neu_formulieren(gespraech) -> Gespraech
beende(gespraech, abbrechen=False) -> Gespraech
feedback_moeglich(gespraech) -> bool
feedback(gespraech, modell) -> dict
verlauf(gespraech) -> list[dict]

profil_vorschlag(profil_id, *, db_pfad=None) -> dict
fortschritt_speichern(profil_id, uebung_id, gespraech, bericht, *, db_pfad=None) -> dict
```

`Modell.antwort(rolle, auftrag, daten) -> str`, `FAELLE`, `KRITERIEN`, `NACHFRAGEN`, `Fall`, `Blablador` und `Uebungsmodell` bleiben importierbar. `ValueError` bedeutet ungültige Aktion/Eingabe, `Modellfehler` ungültige Modellausgabe oder Fehler des Blablador-Adapters. SQLite-Fehler sind `sqlite3.Error` und sollten im Transport eine Fehlermeldung ohne Erfolgsmeldung ergeben.

Die Zustände sind unveränderliche Dataclasses: erst nach erfolgreichem Funktionsaufruf `sitzung.gespraech` ersetzen. Beim Fehler bleibt das bisherige Objekt gültig. Sitzungs-Lock, Version und Idempotenz wiederholter HTTP-Aktionen bleiben Transportaufgaben; eine veraltete Version darf `weiter` nicht nochmals ausführen.

## Start und freiwilliger Profilabruf

```python
# Ausschließlich nach „Lernprofil nutzen“:
vorschlag = profil_vorschlag(profil_id)
g = starte("auszahlung", profil_fokus=vorschlag["fokus"], coaching="kritisch")

# Direktstart ohne Profilzugriff:
g = starte("auszahlung")
```

Priorität: manuell → vollständige Umfrage → übergebener Profilfokus → Fallstandard. Auch unterlegene Eingaben werden validiert. Ohne Umfrage `einschaetzung=None`; ohne gewählten Fokus `fokus=None`, Quelle `fallstandard`. Ein leerer Profilvorschlag enthält `fokus=None` und eine Begründung. Start liest oder speichert selbst kein Profil.

## Ansicht und Aktionen

Für das bisherige Transportfeld `fokus` den Anzeigetext absichern: `KRITERIEN[g.fokus][0] if g.fokus else "Fallstandard"`. Zusätzlich `fokus_id=g.fokus`, `fokus_quelle`, `coaching`, `coach_hinweis` und `warte_auf_freigabe` abbilden. `entwurf` kann zur Bearbeitung des eigenen Beitrags mitgegeben werden. `verlauf(g)` behält `runde`, `servicekraft`, `kunde`, `ärger` und ergänzt `nachfrage`, `unterstuetzt`.

| HTTP-Aktion laut gemeinsamem Vertrag | Kernaufruf / Verhalten |
|---|---|
| Start | Umfrage optional; `fokus`, `coaching` übernehmen; nur bei gewählter `profil_id` Profil lesen |
| `hinweis` | `hinweis_anfordern(g, modell)`; kein Kundenaufruf, keine bestätigte Runde |
| `antwort` | `naechste_runde(g, aussage, modell)`; Rückgabe kann Entwurf oder bestätigte Runde sein |
| `weiter` | `weiter(g, modell)`; gespeicherten Entwurf einmal bestätigen, neuer Regie- und Kundenaufruf |
| `neu_formulieren` | `neu_formulieren(g)`; Entwurf löschen, nächste bestätigte Runde bleibt unterstützt |
| `beenden` / `abbrechen` | `beende(g, abbrechen=...)`; offenen Entwurf und Coach-Anzeige entfernen |
| `feedback` | Nur auf Anforderung; vorhandenen `sitzung.bericht` wiederverwenden |
| `fortschritt_merken` | Ausdrücklich gewählte Profil-ID, Sitzungs-ID als `uebung_id`, vorhandener Sitzungsbericht; niemals Bericht aus Clientdaten übernehmen |
| Profil-GET | `profil_vorschlag(id)` auf freiwilligen Abruf; Speichern und Lesen unabhängig |

Bei einer Coach-Pause bleibt `status="läuft"`, `warte_auf_freigabe=True`, die Rundenzahl und Stimmung bleiben unverändert. Erst eine neue bestätigte Rundennummer erlaubt automatische Kundenausgabe. Wiederholte Anzeige eines Hinweises spielt kein Audio ab. `weiter` und `neu_formulieren` ohne Entwurf ergeben `ValueError`. Im Modus `aus` ist der Abruf unzulässig; `auf_abruf` stoppt nie automatisch. Abschlussfeedback bleibt bei jedem Coach-Modus verfügbar.

## Geprüfte Zustandsbeispiele

Vollständige Beispiele: [beispiele/uebergabe.json](beispiele/uebergabe.json). Reproduzierbar mit:

```bash
python demo_uebergabe.py --datei beispiele/uebergabe.json
```

Bestätigte Runde: `naechste_runde(starte("auszahlung"), DEMO_ANTWORTEN[0], Uebungsmodell())` liefert Ärger 3, eine Runde, den Formularhinweis und `unterstuetzt=False`. `fokus_id` ist `null`, Quelle `fallstandard`.

Coach-Entwurf: `naechste_runde(starte("auszahlung", coaching="kritisch"), "Das Geld ist morgen garantiert da", Uebungsmodell())` liefert Ärger 4, Vertrauen 2, keine Runde, `warte_auf_freigabe=True` und `coach_hinweis={"typ":"kritisch", "text":...}`. Nach `weiter` entsteht eine unterstützte Runde. Nach `neu_formulieren` und neuer Antwort wird nur deren bestätigte Runde unterstützt.

Der Bericht behält `beobachtungen` und `tipp`. Je Kriterium: `stufe`, `runde`, aus dem bestätigten Text gelesenes `zitat`, `unterstuetzt`. Bei „Keine Gelegenheit“ sind Runde/Zitat `null`, Unterstützung `false`. Zusätzliche Felder: `tipp_fokus`, `selbsteinschaetzung`, `vergleich` (Sicherheit und Beobachtungsstufe nebeneinander, ohne sie numerisch gleichzusetzen).

## Modell- und Audiovertrag

Regie liefert die bisherigen Felder und optional:

```json
{"kritisch": {"regel_id": "auszahlung_termin_offen", "beleg": "Das Geld ist morgen garantiert da"}}
```

Fehlend oder `null` bleibt mit dem alten Modellformat kompatibel. Python prüft Typen, Fallregel, offenen Termin, wörtliche Herkunft und eine eindeutige terminierte Auszahlungsaussage. Ein isoliertes „morgen“, Negation, Vermutung, Zitat oder bloße Rückmeldezeit reicht nicht. Die enge Demo-Regel deckt keine beliebige deutsche Formulierung ab; unklare Fälle werden regulär weitergeführt.

Regie erhält interne Fakten und erlaubte Schritte. Kunde und Dialog-Coach erhalten nur Persona und sichtbaren Kontext. Die Anwendung ergänzt den freigegebenen Hinweis. Neue Fallkarten konfigurieren unter anderem `standardfragen`, `hinweis_ausloeser`, `schritt_woerter`, `schritt_gegenstaende` und Abschlussgrenzen. Der lokale Modus nutzt diese Sprachanker; das Live-Modell muss fachlich separat geprüft werden.

`Fall.stimme` ist pro Fall stabil (`petra`, `samir`) und dient Person 2 als Auswahlkennung für die TTS-Stimme. Runden behalten den damaligen Ärgerwert. Sprechweise: 1–2 ruhig, 3 angespannt, 4–5 verärgert. Audiozugriff und Wiedergabe ändern den Kernzustand nicht. Die neuen Audioendpunkte sind hier nicht implementiert.

## Speicherung

Standarddatei: `lernprofile.sqlite3` neben dem Modul, alternativ `ISE_LERNPROFIL_DB`. Speicherbestätigung: `{"gespeichert":true,"bereits_vorhanden":false,"profil_id":"...","uebung_id":"..."}`; Wiederholung ergibt `bereits_vorhanden=true`. Der eindeutige Schlüssel ist Profil + Übung. Inhalt sind kompakte Kriterienbeobachtungen und Hilfenutzung je Beleg sowie je Übung; keine Texte, Umfragewerte oder Audiodaten. Die App ist für die Sitzungszuordnung zuständig.

Lokal geprüft: 42 Kerntests, 19 Profiltests, direkte Demos und bestehender FastAPI-Textpfad mit Umfrage. Noch zu prüfen: neue Browseraktionen, Audio und echtes Blablador einschließlich Antwortzeit und inhaltlicher Qualität.
