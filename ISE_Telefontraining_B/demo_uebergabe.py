"""Zustandsbeispiele für Person 2; keine HTTP-/Audiointegration.

python demo_uebergabe.py --datei beispiele/uebergabe.json
"""
import argparse
import json
from pathlib import Path

from training import (
    DEMO_ANTWORTEN, KRITERIEN, Uebungsmodell, feedback, naechste_runde,
    neu_formulieren, starte, verlauf, weiter,
)


def ansicht(gespraech) -> dict:
    """Fachlicher Ausschnitt; Sitzungs-ID und Version ergänzt der Transport."""
    return {
        "einschaetzung": gespraech.einschaetzung,
        "fokus": KRITERIEN[gespraech.fokus][0] if gespraech.fokus else "Fallstandard",
        "fokus_id": gespraech.fokus,
        "fokus_quelle": gespraech.fokus_quelle,
        "coaching": gespraech.coaching,
        "coach_hinweis": gespraech.coach_hinweis,
        "warte_auf_freigabe": gespraech.warte_auf_freigabe,
        "entwurf": gespraech.entwurf,
        "aerger": gespraech.aerger,
        "vertrauen": gespraech.vertrauen,
        "status": gespraech.status,
        "runden": verlauf(gespraech),
    }


def beispiele() -> dict:
    modell = Uebungsmodell()
    start = starte("auszahlung")
    bestaetigt = naechste_runde(start, DEMO_ANTWORTEN[0], modell)
    ende = naechste_runde(bestaetigt, DEMO_ANTWORTEN[1], modell)
    entwurf = naechste_runde(
        starte("auszahlung", coaching="kritisch"), "Das Geld ist morgen garantiert da", modell,
    )
    fortgesetzt = weiter(entwurf, modell)
    neu = naechste_runde(neu_formulieren(entwurf), DEMO_ANTWORTEN[0], modell)
    return {
        "direktstart": ansicht(start),
        "bestaetigte_runde": ansicht(bestaetigt),
        "coach_entwurf": ansicht(entwurf),
        "nach_weiter": ansicht(fortgesetzt),
        "nach_neu_formulieren": ansicht(neu),
        "bericht": feedback(ende, modell),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datei", type=Path)
    args = parser.parse_args()
    text = json.dumps(beispiele(), ensure_ascii=False, indent=2) + "\n"
    if args.datei:
        args.datei.parent.mkdir(parents=True, exist_ok=True)
        args.datei.write_text(text, encoding="utf-8")
        print(f"Übergabebeispiele geschrieben: {args.datei}")
    else:
        print(text, end="")
