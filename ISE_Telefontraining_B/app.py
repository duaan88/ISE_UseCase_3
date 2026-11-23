"""Lokale Browser-Oberfläche. Jede Übung hat einen eigenen Zustand im Arbeitsspeicher."""

from dataclasses import dataclass, field
import os
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from training import (
    Blablador, FAELLE, Gespraech, KRITERIEN, Modell, Modellfehler, Uebungsmodell,
    beende, feedback, feedback_moeglich, naechste_runde, starte, verlauf,
)

app = FastAPI(title="ISE Telefontraining")
Rating = Annotated[int, Field(strict=True, ge=1, le=5)]


class Startdaten(BaseModel):
    fall: str
    einschaetzung: dict[str, Rating]
    fokus: str | None = None
    modus: Literal["demo", "ki"] = "demo"


class Aktion(BaseModel):
    aktion: Literal["antwort", "beenden", "abbrechen", "feedback"]
    version: Annotated[int, Field(strict=True, ge=0)]
    aussage: str = Field(default="", max_length=600)


@dataclass
class Sitzung:
    gespraech: Gespraech
    modell: Modell
    einschaetzung: dict[str, int]
    modus: str
    version: int = 0
    bericht: dict | None = None
    sperre: Lock = field(default_factory=Lock)


_sitzungen: dict[str, Sitzung] = {}
_sitzungsliste = Lock()


def _ansicht(kennung: str, sitzung: Sitzung) -> dict:
    gespraech = sitzung.gespraech
    fall = FAELLE[gespraech.fall_id]
    return {
        "id": kennung,
        "version": sitzung.version,
        "titel": fall.titel,
        "einstieg": fall.einstieg,
        "kundenrolle": fall.rolle,
        "modus": sitzung.modus,
        "einschaetzung": sitzung.einschaetzung,
        "fokus": KRITERIEN[gespraech.fokus][0],
        "aerger": gespraech.aerger,
        "status": gespraech.status,
        "runden": verlauf(gespraech),
        "feedback_moeglich": feedback_moeglich(gespraech),
        "bericht": sitzung.bericht,
    }


@app.get("/")
def startseite():
    return FileResponse(Path(__file__).with_name("index.html"))


@app.get("/api/optionen")
def optionen():
    return {
        "faelle": {kennung: fall.titel for kennung, fall in FAELLE.items()},
        "kriterien": {kennung: {"titel": titel, "frage": frage} for kennung, (titel, frage, _) in KRITERIEN.items()},
        "ki_verfuegbar": bool(os.environ.get("BLABLADOR_API_KEY", "").strip()),
    }


@app.post("/api/training", status_code=201)
def neues_training(daten: Startdaten):
    try:
        gespraech = starte(daten.fall, daten.einschaetzung, daten.fokus)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    modell: Modell = Uebungsmodell()
    if daten.modus == "ki":
        api_key = os.environ.get("BLABLADOR_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(400, "Für den KI-Modus fehlt der Blablador-API-Key.")
        modell = Blablador(api_key)
    kennung = token_urlsafe(20)
    sitzung = Sitzung(gespraech, modell, daten.einschaetzung, daten.modus)
    with _sitzungsliste:
        _sitzungen[kennung] = sitzung
    return _ansicht(kennung, sitzung)


@app.post("/api/training/{kennung}")
def aktion(kennung: str, daten: Aktion):
    with _sitzungsliste:
        sitzung = _sitzungen.get(kennung)
    if sitzung is None:
        raise HTTPException(404, "Starte eine neue Übung. Diese Sitzung ist nicht mehr verfügbar.")
    with sitzung.sperre:
        if daten.version != sitzung.version:
            # Ein wiederholter Request kann den letzten Stand abrufen, ohne den Zug erneut auszuführen.
            return _ansicht(kennung, sitzung)
        try:
            if daten.aktion == "antwort":
                sitzung.gespraech = naechste_runde(sitzung.gespraech, daten.aussage, sitzung.modell)
            elif daten.aktion in ("beenden", "abbrechen"):
                sitzung.gespraech = beende(sitzung.gespraech, abbrechen=daten.aktion == "abbrechen")
            elif sitzung.bericht is None:
                sitzung.bericht = feedback(sitzung.gespraech, sitzung.modell)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Modellfehler as exc:
            raise HTTPException(502, str(exc)) from exc
        sitzung.version += 1
        return _ansicht(kennung, sitzung)


@app.delete("/api/training/{kennung}", status_code=204)
def training_entfernen(kennung: str):
    with _sitzungsliste:
        _sitzungen.pop(kennung, None)
