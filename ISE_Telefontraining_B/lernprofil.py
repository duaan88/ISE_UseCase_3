"""Freiwilliges, anwendungsseitiges Long-Term Memory für fiktive Profile.

Nur die expliziten Aufrufe dieses Moduls greifen auf SQLite zu. ``starte`` liest
kein Profil. Nach Freigabe ruft die App ``profil_vorschlag(profil_id)`` auf und
übergibt dessen ``fokus`` als ``profil_fokus`` an den Trainingskern. Speichern
erfolgt separat nach „Fortschritt merken“ mit dem vorhandenen Feedbackbericht.

Auswahlregel: je Kriterium die letzten fünf tatsächlich beobachteten Übungen
betrachten (neueste zuerst; „Keine Gelegenheit“ überspringen). Zuerst zählt die
Anzahl „Übungsbedarf“, dann „Teilweise gezeigt“, zuletzt die Reihenfolge in
KRITERIEN. So hat wiederkehrender Übungsbedarf Vorrang. Gibt es nur „Gezeigt“
oder noch keine Beobachtung, bleibt der Fokus leer und der Fallstandard greift.
Genutzte Hilfe bleibt gespeichert; sie verändert diese einfache Regel nicht.
Das ist eine Inhaltsauswahl, kein Training eines Sprachmodells.

SQLite enthält ausschließlich Profil-/Übungs-ID, UTC-Zeitpunkt, Kriterien-ID,
Bewertungsstufe und Hilfekennzeichnung (je Übung sowie je Beleg). Transkript, Zitate, Tipp und Umfrage
bleiben in der flüchtigen Übung. Die App verantwortet die freiwilligen Aktionen
und die Zuordnung ihrer Sitzungs-ID zur ``uebung_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3

from training import BEWERTUNGSSTUFEN, KRITERIEN, feedback_moeglich


FENSTER = 5
_STANDARD_DB = Path(__file__).with_name("lernprofile.sqlite3")


def _kennung(wert: str, bezeichnung: str) -> str:
    if not isinstance(wert, str) or not 1 <= len(wert) <= 128 or wert != wert.strip():
        raise ValueError(f"{bezeichnung} muss eine nichtleere ID mit höchstens 128 Zeichen sein.")
    return wert


def _db_pfad(db_pfad: str | os.PathLike | None) -> Path:
    return Path(db_pfad if db_pfad is not None else os.environ.get("ISE_LERNPROFIL_DB", _STANDARD_DB))


def _verbindung(pfad: Path) -> sqlite3.Connection:
    verbindung = sqlite3.connect(pfad, timeout=10)
    verbindung.execute("PRAGMA foreign_keys = ON")
    return verbindung


def _schema(verbindung: sqlite3.Connection) -> None:
    verbindung.execute("""
        CREATE TABLE IF NOT EXISTS uebungen (
            profil_id TEXT NOT NULL,
            uebung_id TEXT NOT NULL,
            zeitpunkt TEXT NOT NULL,
            unterstuetzt INTEGER NOT NULL CHECK (unterstuetzt IN (0, 1)),
            PRIMARY KEY (profil_id, uebung_id)
        )
    """)
    verbindung.execute("""
        CREATE TABLE IF NOT EXISTS beobachtungen (
            profil_id TEXT NOT NULL,
            uebung_id TEXT NOT NULL,
            kriterium TEXT NOT NULL,
            stufe TEXT NOT NULL,
            unterstuetzt INTEGER NOT NULL CHECK (unterstuetzt IN (0, 1)),
            PRIMARY KEY (profil_id, uebung_id, kriterium),
            FOREIGN KEY (profil_id, uebung_id)
                REFERENCES uebungen(profil_id, uebung_id)
        )
    """)
    # Früh angelegte PoC-Dateien hatten die Kennzeichnung nur pro Beobachtung.
    # Eine separate Übungsmarkierung bewahrt auch Hilfe in einer nicht zitierten
    # Runde. Vorhandene Daten bleiben lesbar; bekannte Hilfen werden übernommen.
    spalten = {zeile[1] for zeile in verbindung.execute("PRAGMA table_info(uebungen)")}
    if "unterstuetzt" not in spalten:
        verbindung.execute(
            "ALTER TABLE uebungen ADD COLUMN unterstuetzt INTEGER NOT NULL DEFAULT 0 "
            "CHECK (unterstuetzt IN (0, 1))"
        )
        verbindung.execute(
            "UPDATE uebungen SET unterstuetzt = EXISTS ("
            "SELECT 1 FROM beobachtungen AS b WHERE b.profil_id = uebungen.profil_id "
            "AND b.uebung_id = uebungen.uebung_id AND b.unterstuetzt = 1)"
        )


def _beobachtungen_pruefen(gespraech, bericht: dict) -> list[tuple[str, str, int]]:
    if not feedback_moeglich(gespraech):
        raise ValueError("Fortschritt ist erst nach einer auswertbaren, abgeschlossenen Übung speicherbar.")
    if not isinstance(bericht, dict) or not isinstance(bericht.get("tipp"), str) or not bericht["tipp"].strip():
        raise ValueError("Fordere vor dem Speichern den Feedbackbericht an.")
    beobachtungen = bericht.get("beobachtungen")
    if not isinstance(beobachtungen, dict) or set(beobachtungen) != set(KRITERIEN):
        raise ValueError("Der Feedbackbericht muss alle drei Kriterien enthalten.")
    kompakt = []
    for kriterium in KRITERIEN:
        beobachtung = beobachtungen[kriterium]
        if not isinstance(beobachtung, dict) or beobachtung.get("stufe") not in BEWERTUNGSSTUFEN:
            raise ValueError("Der Feedbackbericht enthält eine ungültige Bewertungsstufe.")
        stufe = beobachtung["stufe"]
        runde = beobachtung.get("runde")
        zitat = beobachtung.get("zitat")
        hilfe = beobachtung.get("unterstuetzt")
        if type(hilfe) is not bool:
            raise ValueError("Der Feedbackbericht muss genutzte Hilfe ausdrücklich kennzeichnen.")
        if stufe == "Keine Gelegenheit":
            if runde is not None or zitat is not None or hilfe:
                raise ValueError("Ohne Beobachtungsgelegenheit darf kein Beleg angegeben sein.")
        elif type(runde) is not int or not 1 <= runde <= len(gespraech.runden):
            raise ValueError("Der Feedbackbericht verweist auf eine ungültige bestätigte Runde.")
        else:
            bestaetigt = gespraech.runden[runde - 1]
            if zitat != bestaetigt.servicekraft or hilfe != getattr(bestaetigt, "unterstuetzt", False):
                raise ValueError("Der Beleg und die Hilfekennzeichnung müssen zur bestätigten Runde passen.")
        kompakt.append((kriterium, stufe, int(hilfe)))
    return kompakt


def fortschritt_speichern(
    profil_id: str,
    uebung_id: str,
    gespraech,
    bericht: dict,
    *,
    db_pfad: str | os.PathLike | None = None,
) -> dict:
    """Speichere auf Aktion einmal je Profil/Übung, auch bei parallelen Requests.

    ``bericht`` muss der bereits angeforderte Bericht zu ``gespraech`` sein.
    Die Form- und Belegprüfung ersetzt keine Authentifizierung: fiktive Profil-
    IDs und Sitzung gehören der Anwendung. Ein wiederholter Aufruf überschreibt
    nichts und liefert ebenfalls ``gespeichert=True``.
    """
    profil_id = _kennung(profil_id, "Profil-ID")
    uebung_id = _kennung(uebung_id, "Übungs-ID")
    kompakt = _beobachtungen_pruefen(gespraech, bericht)
    pfad = _db_pfad(db_pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    verbindung = _verbindung(pfad)
    try:
        with verbindung:
            # Ein Schreib-Lock umfasst Schemaänderung und Einfügen gemeinsam,
            # damit parallele Wiederholungen auch eine alte DB sicher migrieren.
            verbindung.execute("BEGIN IMMEDIATE")
            _schema(verbindung)
            neu = verbindung.execute(
                "INSERT OR IGNORE INTO uebungen (profil_id, uebung_id, zeitpunkt, unterstuetzt) VALUES (?, ?, ?, ?)",
                (profil_id, uebung_id, datetime.now(timezone.utc).isoformat(),
                 int(any(getattr(runde, "unterstuetzt", False) for runde in gespraech.runden))),
            ).rowcount == 1
            if neu:
                verbindung.executemany(
                    "INSERT INTO beobachtungen (profil_id, uebung_id, kriterium, stufe, unterstuetzt) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [(profil_id, uebung_id, kriterium, stufe, hilfe) for kriterium, stufe, hilfe in kompakt],
                )
    finally:
        verbindung.close()
    return {"gespeichert": True, "bereits_vorhanden": not neu, "profil_id": profil_id, "uebung_id": uebung_id}


def profil_vorschlag(profil_id: str, *, db_pfad: str | os.PathLike | None = None) -> dict:
    """Lies nur nach separater Lesefreigabe einen nachvollziehbaren Vorschlag.

    Der leere Zustand legt keine Datei an. Kein Transkript und keine Umfrage
    werden in die nächste Übung übernommen. Die feste Kriterienreihenfolge
    löst Gleichstände auf.
    """
    profil_id = _kennung(profil_id, "Profil-ID")
    pfad = _db_pfad(db_pfad)
    leer = {"fokus": None, "begruendung": "Noch keine Lernbeobachtungen vorhanden. Der Fallstandard ist verfügbar."}
    if not pfad.exists():
        return leer
    verbindung = _verbindung(pfad)
    try:
        if not verbindung.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'beobachtungen'"
        ).fetchone():
            return leer
        zeilen = verbindung.execute(
            "SELECT b.kriterium, b.stufe FROM beobachtungen AS b "
            "JOIN uebungen AS u ON u.profil_id = b.profil_id AND u.uebung_id = b.uebung_id "
            "WHERE b.profil_id = ? ORDER BY u.zeitpunkt DESC, u.rowid DESC",
            (profil_id,),
        ).fetchall()
    finally:
        verbindung.close()
    beobachtet = {kriterium: [] for kriterium in KRITERIEN}
    for kriterium, stufe in zeilen:
        if kriterium in beobachtet and stufe != "Keine Gelegenheit" and len(beobachtet[kriterium]) < FENSTER:
            beobachtet[kriterium].append(stufe)
    if not any(beobachtet.values()):
        return leer
    wertung = {
        kriterium: (stufen.count("Übungsbedarf"), stufen.count("Teilweise gezeigt"))
        for kriterium, stufen in beobachtet.items()
    }
    fokus = max(KRITERIEN, key=wertung.__getitem__)
    bedarf, teilweise = wertung[fokus]
    if bedarf == 0 and teilweise == 0:
        return {"fokus": None, "begruendung": "Die vorhandenen Beobachtungen zeigen keinen Übungsbedarf. Der Fallstandard ist verfügbar."}
    anzahl = len(beobachtet[fokus])
    begruendung = (
        f"{KRITERIEN[fokus][0]}: {bedarf}× Übungsbedarf und {teilweise}× Teilweise gezeigt "
        f"in den letzten {anzahl} beobachteten Übungen (höchstens {FENSTER} je Kriterium). "
        "Übungsbedarf hat Vorrang, bei Gleichstand teilweise gezeigtes Verhalten und danach die Kriterienreihenfolge. "
        "Keine Gelegenheit wird ausgelassen; genutzte Hilfe bleibt gekennzeichnet."
    )
    return {"fokus": fokus, "begruendung": begruendung}
