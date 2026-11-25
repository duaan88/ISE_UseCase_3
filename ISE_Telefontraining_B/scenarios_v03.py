"""Synthetische Fallprofile und die deterministische Gesprächsdynamik."""

import re
from dataclasses import asdict, dataclass

from contract_v03 import Difficulty
from faelle import FAELLE, Fall
from training import _zusage_beleg

RUNDENLIMIT = 6
VERSION = "synthetic-0.1"

DIFFICULTIES = {preset: Difficulty(preset, level, level, level, level, level)
                for level, preset in enumerate(("easy", "medium", "hard"), 1)}


@dataclass(frozen=True)
class Scenario:
    id: str
    card: Fall
    openings: tuple[str, str, str]
    public_facts: tuple[str, ...]
    issue_words: str
    clarification_words: str
    protected_words: str
    clue_id: str
    action: str
    reveal_when: str = "Passende Nachfrage nach dem letzten Kontakt oder relevanten Unterlagen."

    def reference(self) -> dict:
        """Vollständige Referenz für Bewertung, getrennt vom Kundenkontext."""
        facts = [{
            "id": self.clue_id,
            "text": self.card.interne_fakten[-1],
            "reveal_when": self.reveal_when,
        }]
        if self.card.termin_offen:
            facts.insert(0, {"id": "payout_date_open", "text": self.public_facts[-1]})
        return {
            "scenario_id": self.id, "title": self.card.titel,
            "scenario_version": VERSION, "knowledge_version": VERSION,
            "public_persona": self.card.persona, "public_facts": list(self.public_facts),
            "facts": facts,
            "allowed_next_step": self.card.erlaubte_schritte[0],
            "constraints": [
                "Keine neuen fachlichen Fakten oder tatsächlichen Serviceaktionen erfinden.",
                "Auswertung bezieht nur Informationen ein, die die Servicekraft im Dialog wissen konnte.",
            ],
        }


SCENARIOS = {
    "payout_missing": Scenario(
        "payout_missing", FAELLE["auszahlung"],
        (
            "Guten Tag, hier ist Petra Lindner. Meine angekündigte Auszahlung fehlt seit drei Wochen. Können Sie nachsehen?",
            "Hier ist Petra Lindner. Ich warte seit drei Wochen auf mein Geld und muss eine Rechnung bezahlen.",
            "Mit der angekündigten Sache stimmt etwas nicht. Seit drei Wochen warte ich! Können Sie mir sagen, was los ist?",
        ),
        ("Petra wartet seit drei Wochen auf eine angekündigte Auszahlung.",
         "Sie muss eine Rechnung bezahlen.", "Der Auszahlungstermin ist offen."),
        r"auszahlung|zahlung|geld",
        r"brief|nachricht|unterlag|formular|bankverbindung|(?:zuletzt|als letztes)\s+(?:erhalten|geschickt)",
        r"formular|bankverbindung|unterschrift|unterschrieben",
        "bank_form_missing",
        r"\bich\s+(?:sende|schicke)\b[^.!?;]*\bformular\b",
    ),
    "bereavement": Scenario(
        "bereavement",
        Fall("Todesfall eines Angehörigen", "Kundin",
             "Nora Beck hat ihren Vater verloren und sucht Orientierung für den ersten Kontakt.",
             "Mein Vater ist verstorben. Ich weiß nicht, wo ich anfangen soll.",
             "Eine kurze schriftliche Übersicht würde mir helfen. Am Telefon ist mir das gerade zu viel.",
             interne_fakten=("Nora wünscht eine kurze schriftliche Übersicht.",),
             erlaubte_schritte=("Auf Wunsch eine kurze Übersicht anbieten und die Rückmeldung abstimmen.",)),
        ("Mein Vater ist verstorben. Können Sie mir den ersten Schritt erklären?",
         "Hier ist Nora Beck. Mein Vater ist verstorben. Ich weiß nicht, wo ich anfangen soll.",
         "Es ist etwas passiert in meiner Familie. Es fällt mir schwer, darüber zu sprechen."),
        ("Noras Vater ist verstorben. Sie sucht Orientierung für den ersten Kontakt.",),
        r"passiert|geschehen|verstorben|verlust|anliegen|erzählen",
        r"was (?:würde|hilft|brauchen)|wie (?:kann|möchten|darf)|schriftlich|übersicht",
        r"schriftlich|übersicht", "written_orientation",
        r"\bich\s+(?:sende|schicke|schreibe)\b[^.!?;]*\bübersicht\b",
        "Behutsame Nachfrage nach gewünschter Unterstützung oder Kontaktform.",
    ),
    "missing_followup": Scenario(
        "missing_followup", FAELLE["rueckmeldung"],
        (
            "Guten Tag, hier ist Samir Yilmaz. Ich warte seit einer Woche auf eine Rückmeldung zu meiner Serviceanfrage.",
            FAELLE["rueckmeldung"].einstieg,
            "Ich habe mich schon gemeldet und komme nicht weiter. Seit einer Woche passiert nichts. Was soll ich jetzt tun?",
        ),
        ("Samir wartet seit einer Woche auf eine Antwort zu seiner fiktiven Serviceanfrage.",),
        r"rückmeldung|antwort|anfrage",
        r"adresse|nachricht|kontakt|e-?mail|empfänger",
        r"alt(?:e|en|er)\s+(?:e-?mail|adresse)|falsch(?:e|en|er)\s+(?:e-?mail|adresse)",
        "outdated_email",
        r"\bich\s+(?:prüfe|überprüfe|aktualisiere|korrigiere)\b[^.!?;]*\badresse\b",
    ),
}


def scenario_options() -> dict[str, str]:
    """Fall-IDs und Titel für die Streamlit-Auswahl."""
    return {scenario_id: scenario.card.titel for scenario_id, scenario in SCENARIOS.items()}


_EMPLOYEE_FOLLOWUP = re.compile(r"\b(?:melde\s+mich|gebe\s+ihnen\b.*\b(?:rückmeldung|zwischenstand|antwort))\b")
_TIME = re.compile(r"\b(?:heute|morgen|übermorgen|montag|dienstag|mittwoch|donnerstag|"
                   r"freitag|samstag|sonntag|\d{1,2}\s*uhr)\b")
_DISMISSAL = re.compile(r"gedulden|nicht mein problem|selbst schuld|müssen sie (?:eben |wohl )?(?:noch (?:etwas )?)?warten")
_EMPATHY = re.compile(r"ich verstehe|nachvollzieh|tut mir leid|ärgerlich|wartezeit belastet")
_NEGATION = re.compile(r"\b(?:nicht|kein\w*|nie|vielleicht|falls|würde\w*|könnte\w*|sobald)\b")


@dataclass(frozen=True)
class Conversation:
    anger: int
    trust: int = 2
    issue_known: bool = True
    clue_revealed: bool = False


def start_context(difficulty: Difficulty) -> Conversation:
    return Conversation(difficulty.emotional_intensity + 1, issue_known=difficulty.ambiguity < 3)


def evaluate_turn(scenario: Scenario, difficulty: Difficulty, context: Conversation,
                  text: str) -> tuple[Conversation, bool]:
    """Kleine, fallgebundene Heuristik. Unsichere Schritte bleiben offen."""
    words = text.casefold()
    questions = [part for part in re.split(r"(?<=[.!?;])", words) if part.endswith("?")]
    issue = context.issue_known or any(re.search(scenario.issue_words, part) for part in questions)
    clue = context.clue_revealed or bool(
        issue and any(re.search(scenario.clarification_words, part) for part in questions)
    )

    statements = [part.strip() for part in re.split(r"[.!?;]+", words)]
    # In einem Angebot müssen Handlung und Rückmeldung beide in Verantwortung
    # der Servicekraft liegen. Eine Negation im separaten Auszahlungssatz ist erlaubt.
    action = any(re.search(scenario.action, part) and not _NEGATION.search(part)
                 for part in statements)
    followup = any(_EMPLOYEE_FOLLOWUP.search(part) and _TIME.search(part)
                   and not _NEGATION.search(part) for part in statements)
    payout_promise = scenario.card.termin_offen and any(
        _zusage_beleg(part) for part in statements if part
    )
    valid_step = context.clue_revealed and action and followup and not payout_promise

    dismissed = bool(_DISMISSAL.search(words))
    empathic = bool(_EMPATHY.search(words)) and not re.search(r"\b(?:ich verstehe|nachvollziehen)\b[^.!?]*\bnicht\b", words)
    # Schwerere Dialoge beruhigen sich bei konkreter Anerkennung und Fachbezug.
    calmer = empathic and (
        difficulty.conversational_dynamics < 3
        or bool(re.search(r"wart|belast|ärger|rechnung|sorge", words))
    )
    engaged = calmer or valid_step or (clue and not context.clue_revealed)
    anger = min(5, max(1, context.anger + (1 if dismissed else -1 if calmer else 0)))
    trust = min(5, max(1, context.trust + (-1 if dismissed else 1 if engaged else 0)))
    return Conversation(anger, trust, issue, clue), valid_step and not dismissed


def visible_case(scenario: Scenario, difficulty: Difficulty, context: Conversation) -> dict:
    return {
        "persona": scenario.card.persona if context.issue_known else "Eine wartende Person benötigt Auskunft.",
        "sichtbare_fakten": scenario.public_facts if context.issue_known else (),
        "fallhinweis": scenario.card.hinweis if context.clue_revealed else None,
        "schwierigkeit": asdict(difficulty),
        "aerger": context.anger,
        "vertrauen": context.trust,
        "anliegen_offengelegt": context.issue_known,
    }
