"""Zwei fiktive Übungen und ein freiwilliger Profilabruf, ohne Netz.

``python demo_lernprofil.py`` nutzt eine temporäre SQLite-Datei und hinterlässt
keine Profildaten. ``python demo_lernprofil.py --db /tmp/ise-demo.sqlite3``
verwendet absichtlich eine dauerhafte Datei; ein zweiter Aufruf bestätigt die
beiden bereits gespeicherten Übungen, statt sie doppelt zu zählen.
"""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from lernprofil import fortschritt_speichern, profil_vorschlag
from training import Uebungsmodell, beende, feedback, naechste_runde, starte


def demo(db_pfad: Path) -> None:
    profil_id = "fiktiv-demo-petra-training"
    modell = Uebungsmodell()
    print("Ohne Lesefreigabe: Direktstart mit Fallstandard, kein Profilabruf.")
    for nummer in (1, 2):
        gespraech = starte("auszahlung")
        for aussage in (
            "Haben Sie einen Brief oder eine Nachricht zu den Unterlagen erhalten?",
            "Ich sende Ihnen das Formular und melde mich bis morgen um 12 Uhr mit einem Zwischenstand.",
        ):
            gespraech = naechste_runde(gespraech, aussage, modell)
        if gespraech.status == "läuft":
            gespraech = beende(gespraech)
        bericht = feedback(gespraech, modell)
        print(f"Übung {nummer}: Feedback ausdrücklich angefordert; erst danach Fortschritt merken.")
        print(json.dumps(fortschritt_speichern(profil_id, f"vorbereitete-uebung-{nummer}", gespraech, bericht, db_pfad=db_pfad), ensure_ascii=False))
    print("Neue Übung: Lernprofil nutzen wurde separat freigegeben.")
    vorschlag = profil_vorschlag(profil_id, db_pfad=db_pfad)
    print(json.dumps(vorschlag, ensure_ascii=False))
    neu = starte("auszahlung", profil_fokus=vorschlag["fokus"])
    print(f"Fokus: {neu.fokus}; Quelle: {neu.fokus_quelle}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Dauerhafte SQLite-Datei, sonst temporäre Demo")
    args = parser.parse_args()
    if args.db:
        demo(args.db)
    else:
        with TemporaryDirectory() as verzeichnis:
            demo(Path(verzeichnis) / "demo.sqlite3")
