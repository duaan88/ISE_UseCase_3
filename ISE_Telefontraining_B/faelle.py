"""Fiktive Fallkarten: neue Fälle als Konfiguration in FAELLE ergänzen.

Persona und Einstieg sind öffentlich. interne_fakten und hinweis gehen nur an
Regie/Bewertung; die Anwendung gibt den Hinweis gezielt im Kundentext frei.
Abschlussregeln und lokale Testauslöser liegen je Fall in dieser Konfiguration.
"""
from dataclasses import dataclass

NACHFRAGEN = {
    "empathie": (
        "Können Sie verstehen, warum mich die lange Wartezeit so verärgert?",
        "Wie würden Sie sich fühlen, wenn Sie so lange warten müssten?",
    ),
    "klaerung": (
        "Welche Information brauchen Sie von mir, um den Grund zu finden?",
        "Was bedeutet das für meinen Fall?",
    ),
    "naechster_schritt": (
        "Was passiert jetzt konkret mit meinem Anliegen?",
        "Wer meldet sich bis wann bei mir?",
    ),
}
@dataclass(frozen=True)
class Fall:
    titel: str
    rolle: str
    persona: str
    einstieg: str
    hinweis: str
    standardfragen: tuple[str, str] = (
        "Welche Information brauchen Sie von mir?", "Wie geht es jetzt weiter?",
    )
    interne_fakten: tuple[str, ...] = ()
    erlaubte_schritte: tuple[str, ...] = ()
    hinweis_ausloeser: tuple[str, ...] = ("brief", "nachricht", "unterlag", "grund")
    schritt_woerter: tuple[str, ...] = ("prüfe", "sende", "schaue", "leite")
    schritt_gegenstaende: tuple[str, ...] = ()
    termin_offen: bool = False
    kritische_regel: str | None = None
    start_aerger: int = 4
    start_vertrauen: int = 2
    loesung_braucht_hinweis: bool = True
    loesung_max_aerger: int = 3
    eskalations_aerger: int = 5
    rundenlimit: int = 6
    stimme: str = "standard"


FAELLE = {
    "auszahlung": Fall(
        "Mein Geld ist noch nicht da",
        "Kundin",
        "Petra Lindner, 58 Jahre, wartet seit drei Wochen auf eine angekündigte Auszahlung. "
        "Sie braucht das Geld für eine Rechnung. Der Auszahlungstermin ist offen.",
        "Guten Tag, hier ist Petra Lindner. Ich warte seit drei Wochen auf mein Geld und muss eine Rechnung bezahlen.",
        "Im letzten Brief stand, dass das unterschriebene Formular zur Bankverbindung noch fehlt.",
        standardfragen=("Haben Sie schon einen Hinweis zu meiner Auszahlung gefunden?", "Wie geht es jetzt mit meiner Auszahlung weiter?"),
        interne_fakten=("Der Auszahlungstermin ist offen.", "Das unterschriebene Formular zur Bankverbindung fehlt."),
        erlaubte_schritte=("Formular zur Bankverbindung zusenden und Rückmeldung mit Zwischenstand vereinbaren.",),
        termin_offen=True,
        kritische_regel="auszahlung_termin_offen",
        schritt_gegenstaende=("formular", "unterlag", "vorgang", "bankverbindung"),
        stimme="petra",
    ),
    "rueckmeldung": Fall(
        "Ich habe keine Rückmeldung bekommen",
        "Kunde",
        "Samir Yilmaz wartet seit einer Woche auf eine Antwort zu seiner fiktiven Serviceanfrage.",
        "Guten Tag, ich warte seit einer Woche auf eine Rückmeldung. Können Sie mir weiterhelfen?",
        "Beim letzten Kontakt ist mir aufgefallen, dass die Nachricht an meine alte E-Mail-Adresse geschickt wurde.",
        standardfragen=("Können Sie nachsehen, wohin Ihre Nachricht geschickt wurde?", "Wie erhalte ich die Rückmeldung an meine aktuelle Adresse?"),
        interne_fakten=("Die letzte Nachricht ging an eine alte E-Mail-Adresse.",),
        erlaubte_schritte=("Adresse prüfen oder aktualisieren und eine erneute Rückmeldung vereinbaren.",),
        hinweis_ausloeser=("adresse", "nachricht", "kontakt", "grund"),
        schritt_woerter=("prüfe", "aktualisier", "sende", "leite"),
        schritt_gegenstaende=("adresse", "nachricht", "anfrage", "vorgang"),
        stimme="samir",
    ),
}
