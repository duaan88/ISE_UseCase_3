import io
import json
import os
import unittest
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from training import (
    Blablador, DEMO_ANTWORTEN, FAELLE, KRITERIEN, Modellfehler, Uebungsmodell, beende,
    feedback, feedback_moeglich, hinweis_anfordern, naechste_runde, neu_formulieren,
    starte, verlauf, weiter,
)


EINSCHAETZUNG = {"empathie": 4, "klaerung": 2, "naechster_schritt": 4}


class NachgebildetesModell:
    """Beobachtbare Rollengrenze ohne HTTP; einzelne Antworten sind gezielt ersetzbar."""

    def __init__(self, **antworten):
        self.antworten = antworten
        self.aufrufe = []
        self.lokal = Uebungsmodell()

    def antwort(self, rolle, auftrag, daten):
        self.aufrufe.append((rolle, auftrag, deepcopy(daten)))
        if rolle in self.antworten:
            antwort = self.antworten[rolle]
            return antwort(daten) if callable(antwort) else antwort
        return self.lokal.antwort(rolle, auftrag, daten)


def regie_antwort(**aenderungen):
    entscheidung = {
        "aerger_delta": 0, "vertrauen_delta": 0, "hinweis_freigeben": False,
        "schritt_vereinbart": False, "frage": 0,
    }
    entscheidung.update(aenderungen)
    return json.dumps(entscheidung, ensure_ascii=False)


def kritische_regie(beleg, regel_id="auszahlung_termin_offen"):
    return regie_antwort(
        aerger_delta=-1, vertrauen_delta=1, hinweis_freigeben=True,
        kritisch={"regel_id": regel_id, "beleg": beleg},
    )


class TelefontrainingTest(unittest.TestCase):
    def setUp(self):
        self.modell = Uebungsmodell()
        self.gespraech = starte("auszahlung", EINSCHAETZUNG)

    def test_fokus_aendert_nachfrage_bei_gleicher_antwort(self):
        andere_uebung = starte("auszahlung", EINSCHAETZUNG, fokus="naechster_schritt")
        klaerung = naechste_runde(self.gespraech, DEMO_ANTWORTEN[0], self.modell)
        naechster_schritt = naechste_runde(andere_uebung, DEMO_ANTWORTEN[0], self.modell)
        self.assertEqual(klaerung.fokus, "klaerung")
        self.assertEqual(klaerung.aerger, naechster_schritt.aerger)
        self.assertIn("Was bedeutet das", klaerung.runden[0].nachfrage)
        self.assertIn("Wer meldet sich", naechster_schritt.runden[0].nachfrage)

    def test_regulaer_und_feedback_mit_originalzitat(self):
        runde_eins = naechste_runde(self.gespraech, DEMO_ANTWORTEN[0], self.modell)
        self.assertEqual(runde_eins.aerger, 3)
        self.assertTrue(runde_eins.hinweis_bekannt)
        self.assertIn(FAELLE["auszahlung"].hinweis, runde_eins.runden[0].kunde)
        self.assertFalse(feedback_moeglich(runde_eins))
        ende = naechste_runde(runde_eins, DEMO_ANTWORTEN[1], self.modell)
        self.assertEqual(ende.status, "gelöst")
        bericht = feedback(ende, self.modell)
        verbindlichkeit = bericht["beobachtungen"]["naechster_schritt"]
        self.assertEqual(verbindlichkeit["runde"], 2)
        self.assertEqual(verbindlichkeit["zitat"], DEMO_ANTWORTEN[1])

    def test_abbruch_blockiert_weitere_antwort_und_feedback(self):
        laufend = naechste_runde(self.gespraech, "Worum geht es genau?", self.modell)
        abbruch = beende(laufend, abbrechen=True)
        self.assertEqual(abbruch.status, "abgebrochen")
        self.assertEqual(abbruch.runden, laufend.runden)
        self.assertFalse(feedback_moeglich(abbruch))
        with self.assertRaises(ValueError):
            naechste_runde(abbruch, DEMO_ANTWORTEN[0], self.modell)

    def test_zwei_runden_mit_aerger_fuenf_beenden_das_gespraech(self):
        for _ in range(2):
            self.gespraech = naechste_runde(self.gespraech, "Da müssen Sie sich gedulden.", self.modell)
        self.assertEqual(self.gespraech.aerger, 5)
        self.assertEqual(self.gespraech.status, "eskaliert")

    def test_kundenfehler_laesst_runde_erneut_senden(self):
        with patch.object(self.modell, "antwort", wraps=self.modell.antwort) as antwort:
            antwort.side_effect = [json.dumps({
                "aerger_delta": -1, "vertrauen_delta": 1, "hinweis_freigeben": True,
                "schritt_vereinbart": False, "frage": 0,
            }), Modellfehler("Timeout im Kunden-Agenten")]
            with self.assertRaises(Modellfehler):
                naechste_runde(self.gespraech, DEMO_ANTWORTEN[0], self.modell)
        self.assertEqual(self.gespraech.runden, ())
        self.assertEqual(self.gespraech.aerger, 4)
        self.assertFalse(self.gespraech.hinweis_bekannt)
        erneut = naechste_runde(self.gespraech, DEMO_ANTWORTEN[0], self.modell)
        self.assertEqual(len(erneut.runden), 1)

    def test_ungueltige_regieentscheidung_stoppt_vor_kundenaufruf(self):
        with patch.object(self.modell, "antwort", return_value='{"aerger_delta": 8}') as antwort:
            with self.assertRaises(Modellfehler):
                naechste_runde(self.gespraech, DEMO_ANTWORTEN[0], self.modell)
        self.assertEqual(antwort.call_count, 1)

    def test_blablador_http_vertrag_mit_lokaler_antwort(self):
        rueckgabe = {"choices": [{"message": {"content": "Guten Tag."}}]}
        with patch.dict(os.environ, {"BLABLADOR_MODEL": "alias-fast"}):
            modell = Blablador("test-key")
        with patch("training.urlopen", return_value=io.BytesIO(json.dumps(rueckgabe).encode())) as http:
            self.assertEqual(modell.antwort("Kunde", "Spiele den Kunden.", {"aerger": 3}), "Guten Tag.")
        request = http.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/v1/chat/completions"))
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(json.loads(request.data)["model"], "alias-fast")
        with patch("training.urlopen", side_effect=ConnectionResetError("Unterbrochene Verbindung")):
            with self.assertRaises(Modellfehler):
                modell.antwort("Kunde", "Spiele den Kunden.", {"aerger": 3})


class StartUndFallkartenTest(unittest.TestCase):
    def test_direktstart_ohne_umfrage_mit_funktionierender_runde(self):
        gespraech = starte("auszahlung")
        self.assertIsNone(gespraech.fokus)
        self.assertIsNone(gespraech.einschaetzung)
        self.assertEqual(gespraech.fokus_quelle, "fallstandard")
        self.assertEqual(gespraech.coaching, "aus")
        self.assertEqual((gespraech.aerger, gespraech.vertrauen), (4, 2))
        bestaetigt = naechste_runde(gespraech, DEMO_ANTWORTEN[0], Uebungsmodell())
        self.assertEqual(len(bestaetigt.runden), 1)
        self.assertEqual(bestaetigt.aerger, 3)
        self.assertTrue(bestaetigt.hinweis_bekannt)
        self.assertTrue(bestaetigt.runden[0].nachfrage)
        self.assertFalse(bestaetigt.runden[0].unterstuetzt)

    def test_fokusprioritaet_manuell_umfrage_profil_standard(self):
        varianten = (
            ({"einschaetzung": EINSCHAETZUNG, "fokus": "empathie", "profil_fokus": "naechster_schritt"}, "empathie", "manuell"),
            ({"einschaetzung": EINSCHAETZUNG, "profil_fokus": "naechster_schritt"}, "klaerung", "umfrage"),
            ({"einschaetzung": None, "profil_fokus": "naechster_schritt"}, "naechster_schritt", "lernprofil"),
            ({"einschaetzung": None}, None, "fallstandard"),
        )
        for eingabe, fokus, quelle in varianten:
            with self.subTest(eingabe=eingabe):
                gespraech = starte("auszahlung", **eingabe)
                self.assertEqual((gespraech.fokus, gespraech.fokus_quelle), (fokus, quelle))

    def test_manueller_fokus_benoetigt_keine_umfrage(self):
        gespraech = starte("auszahlung", fokus="empathie")
        self.assertEqual((gespraech.fokus, gespraech.fokus_quelle), ("empathie", "manuell"))

    def test_umfrage_gleichstand_verwendet_kriterienreihenfolge(self):
        gespraech = starte("auszahlung", {k: 2 for k in reversed(KRITERIEN)})
        self.assertEqual(gespraech.fokus, "empathie")

    def test_unvollstaendige_oder_ungueltige_umfrage_auch_bei_manueller_wahl(self):
        ungueltig = (
            {}, {"empathie": 3}, {**EINSCHAETZUNG, "extra": 2},
            {**EINSCHAETZUNG, "empathie": 0}, {**EINSCHAETZUNG, "empathie": 6},
            {**EINSCHAETZUNG, "empathie": True}, {**EINSCHAETZUNG, "empathie": 3.0},
            {**EINSCHAETZUNG, "empathie": "3"}, [], "keine Umfrage",
        )
        for eingabe in ungueltig:
            with self.subTest(eingabe=eingabe), self.assertRaises(ValueError):
                starte("auszahlung", eingabe, fokus="empathie")

    def test_ungueltiger_fokus_auch_wenn_andere_quelle_vorrang_hat(self):
        for argumente in (
            {"fokus": "falsch"}, {"fokus": ""},
            {"fokus": "empathie", "profil_fokus": "falsch"},
            {"profil_fokus": ""}, {"coaching": "immer"},
        ):
            with self.subTest(argumente=argumente), self.assertRaises(ValueError):
                starte("auszahlung", **argumente)
        with self.assertRaises(ValueError):
            starte("nicht_vorhanden")

    def test_zweiter_fall_hat_eigene_neutrale_nachfrage(self):
        modell = Uebungsmodell()
        petra = naechste_runde(starte("auszahlung"), "Guten Tag.", modell)
        samir = naechste_runde(starte("rueckmeldung"), "Guten Tag.", modell)
        self.assertNotEqual(petra.runden[0].nachfrage, samir.runden[0].nachfrage)
        self.assertNotIn(FAELLE["auszahlung"].hinweis, samir.runden[0].kunde)

    def test_start_laesst_fremde_umfrage_nicht_nachtraeglich_zustand_aendern(self):
        werte = EINSCHAETZUNG.copy()
        gespraech = starte("auszahlung", werte)
        werte["klaerung"] = 5
        self.assertEqual(gespraech.einschaetzung, EINSCHAETZUNG)

    def test_neuer_fall_laesst_sich_allein_durch_konfiguration_erganzen(self):
        fall = replace(
            FAELLE["rueckmeldung"], titel="Fiktive Versandfrage",
            persona="Mara wartet auf eine fiktive Sendung.", einstieg="Wo bleibt meine Sendung?",
            hinweis="Die Hausnummer fehlt im Versandauftrag.",
            standardfragen=("Was wissen Sie über meine Sendung?", "Wie klären wir die Versandfrage?"),
            interne_fakten=("Die Hausnummer fehlt.",),
            erlaubte_schritte=("Hausnummer prüfen und Zwischenstand geben.",),
            hinweis_ausloeser=("hausnummer",), schritt_woerter=("prüfe",),
            schritt_gegenstaende=("hausnummer",),
            start_aerger=3, start_vertrauen=3, rundenlimit=3,
        )
        with patch.dict(FAELLE, {"versand": fall}):
            gespraech = naechste_runde(starte("versand"), "Welche Hausnummer haben Sie angegeben?", Uebungsmodell())
            self.assertEqual(gespraech.fokus_quelle, "fallstandard")
            self.assertTrue(gespraech.hinweis_bekannt)
            self.assertIn(fall.hinweis, gespraech.runden[-1].kunde)
            self.assertIn(gespraech.runden[-1].nachfrage, fall.standardfragen)
            gespraech = naechste_runde(gespraech, "Ich prüfe die Hausnummer und melde mich morgen mit einem Zwischenstand.", Uebungsmodell())
            self.assertEqual(gespraech.status, "gelöst")


class RundenUndModellgrenzenTest(unittest.TestCase):
    def test_nachfrage_ohne_freigabe_verraet_keinen_privaten_formularhinweis(self):
        modell = NachgebildetesModell(Regie=regie_antwort(frage=1))
        gespraech = naechste_runde(starte("auszahlung"), "Guten Tag.", modell)
        self.assertFalse(gespraech.hinweis_bekannt)
        self.assertNotIn("formular", gespraech.runden[-1].kunde.casefold())

    def test_privater_hinweis_nur_an_regie_bis_er_sichtbar_geworden_ist(self):
        modell = NachgebildetesModell()
        gespraech = naechste_runde(starte("auszahlung"), "Guten Tag.", modell)
        regiedaten = next(d for rolle, _, d in modell.aufrufe if rolle == "Regie")
        kundendaten = next(d for rolle, _, d in modell.aufrufe if rolle == "Kunde")
        hinweis = FAELLE["auszahlung"].hinweis
        self.assertIn(hinweis, json.dumps(regiedaten, ensure_ascii=False))
        self.assertNotIn(hinweis, json.dumps(kundendaten, ensure_ascii=False))
        self.assertNotIn("unterschriebene Formular", json.dumps(kundendaten, ensure_ascii=False))
        self.assertFalse(gespraech.hinweis_bekannt)
        self.assertNotIn(hinweis, gespraech.runden[0].kunde)
        gespraech = naechste_runde(gespraech, DEMO_ANTWORTEN[0], modell)
        self.assertEqual(gespraech.runden[-1].kunde.count(hinweis), 1)
        gespraech = naechste_runde(gespraech, "Vielen Dank.", modell)
        letztes_kundendatum = [d for rolle, _, d in modell.aufrufe if rolle == "Kunde"][-1]
        self.assertIn(hinweis, json.dumps(letztes_kundendatum["verlauf"], ensure_ascii=False))
        self.assertNotIn(hinweis, gespraech.runden[-1].kunde)

    def test_rundenlimit_und_keine_automatische_bewertung(self):
        modell = NachgebildetesModell()
        gespraech = starte("auszahlung")
        for _ in range(6):
            gespraech = naechste_runde(gespraech, "Guten Tag.", modell)
        self.assertEqual(gespraech.status, "Rundenlimit erreicht")
        self.assertEqual(len(gespraech.runden), 6)
        self.assertTrue(feedback_moeglich(gespraech))
        self.assertNotIn("Bewertung", [rolle for rolle, _, _ in modell.aufrufe])
        self.assertNotIn("Coach", [rolle for rolle, _, _ in modell.aufrufe])
        with self.assertRaises(ValueError):
            naechste_runde(gespraech, "Noch eine Runde.", modell)

    def test_fallfremde_handlung_ist_trotz_rueckmeldezeit_keine_loesung(self):
        modell = Uebungsmodell()
        gespraech = naechste_runde(starte("auszahlung"), DEMO_ANTWORTEN[0], modell)
        self.assertTrue(gespraech.hinweis_bekannt)
        gespraech = naechste_runde(
            gespraech,
            "Ich sende Ihnen ein Werbeangebot und melde mich morgen mit einem Zwischenstand.",
            modell,
        )
        self.assertEqual(gespraech.status, "läuft")
        self.assertEqual(len(gespraech.runden), 2)

    def test_stimmungswerte_bleiben_begrenzt_und_aendern_sich_hoechstens_um_eins(self):
        modell = NachgebildetesModell(Regie=regie_antwort(aerger_delta=-1, vertrauen_delta=1))
        gespraech = starte("auszahlung")
        for _ in range(6):
            vorher = gespraech
            gespraech = naechste_runde(gespraech, "Guten Tag.", modell)
            self.assertIn(gespraech.aerger, range(1, 6))
            self.assertIn(gespraech.vertrauen, range(1, 6))
            self.assertLessEqual(abs(gespraech.aerger - vorher.aerger), 1)
            self.assertLessEqual(abs(gespraech.vertrauen - vorher.vertrauen), 1)
        self.assertEqual((gespraech.aerger, gespraech.vertrauen), (1, 5))

    def test_regieformatfehler_aendern_den_bestaetigten_zustand_nicht(self):
        ausgaben = (
            "kein JSON", "[]", "null", None,
            regie_antwort(aerger_delta=True), regie_antwort(vertrauen_delta=2),
            regie_antwort(frage=False), regie_antwort(frage=2),
            regie_antwort(hinweis_freigeben=1), regie_antwort(schritt_vereinbart="ja"),
        )
        for ausgabe in ausgaben:
            with self.subTest(ausgabe=ausgabe):
                gespraech = starte("auszahlung")
                modell = NachgebildetesModell(Regie=ausgabe)
                with self.assertRaises(Modellfehler):
                    naechste_runde(gespraech, DEMO_ANTWORTEN[0], modell)
                self.assertEqual(gespraech.runden, ())
                self.assertEqual((gespraech.aerger, gespraech.vertrauen), (4, 2))
                self.assertEqual([r for r, _, _ in modell.aufrufe], ["Regie"])

    def test_leere_zu_lange_und_nicht_textuelle_kundenantworten_sind_modellfehler(self):
        for ausgabe in ("", "   ", "x" * 451, None, {"text": "Hallo"}):
            with self.subTest(ausgabe=ausgabe):
                gespraech = starte("auszahlung")
                modell = NachgebildetesModell(Kunde=ausgabe)
                with self.assertRaises(Modellfehler):
                    naechste_runde(gespraech, DEMO_ANTWORTEN[0], modell)
                self.assertEqual(gespraech.runden, ())
                self.assertFalse(gespraech.hinweis_bekannt)

    def test_ungueltiger_servicetext_stoppt_vor_modellaufruf(self):
        for aussage in ("", "  ", "x" * 601, None, 7):
            with self.subTest(aussage=aussage):
                modell = NachgebildetesModell()
                with self.assertRaises(ValueError):
                    naechste_runde(starte("auszahlung"), aussage, modell)
                self.assertEqual(modell.aufrufe, [])


class CoachUndEntwurfTest(unittest.TestCase):
    GARANTIE = "Das Geld ist morgen garantiert da"

    def test_aus_blockiert_abruf_und_automatischen_coach(self):
        modell = NachgebildetesModell(Regie=kritische_regie(self.GARANTIE))
        gespraech = starte("auszahlung", coaching="aus")
        with self.assertRaises(ValueError):
            hinweis_anfordern(gespraech, modell)
        self.assertEqual(modell.aufrufe, [])
        gespraech = naechste_runde(gespraech, self.GARANTIE, modell)
        self.assertEqual(len(gespraech.runden), 1)
        self.assertFalse(gespraech.warte_auf_freigabe)
        self.assertIsNone(gespraech.coach_hinweis)
        self.assertNotIn("Coach", [rolle for rolle, _, _ in modell.aufrufe])

    def test_auf_abruf_reagiert_nur_auf_aktion_und_markiert_eine_runde(self):
        modell = NachgebildetesModell(Regie=kritische_regie(self.GARANTIE))
        gespraech = naechste_runde(starte("auszahlung", coaching="auf_abruf"), self.GARANTIE, modell)
        self.assertFalse(gespraech.warte_auf_freigabe)
        self.assertNotIn("Coach", [rolle for rolle, _, _ in modell.aufrufe])
        vorher = gespraech
        gespraech = hinweis_anfordern(gespraech, modell)
        self.assertEqual(gespraech.coach_hinweis["typ"], "auf_abruf")
        self.assertTrue(gespraech.coach_hinweis["text"])
        self.assertFalse(gespraech.warte_auf_freigabe)
        self.assertEqual(gespraech.runden, vorher.runden)
        self.assertEqual((gespraech.aerger, gespraech.vertrauen), (vorher.aerger, vorher.vertrauen))
        gespraech = naechste_runde(gespraech, "Vielen Dank.", modell)
        self.assertTrue(gespraech.runden[-1].unterstuetzt)
        gespraech = naechste_runde(gespraech, "Ich höre Ihnen zu.", modell)
        self.assertFalse(gespraech.runden[-1].unterstuetzt)

    def test_kritisch_stoppt_vor_kunde_und_jeder_fachlichen_aenderung(self):
        modell = NachgebildetesModell(Regie=kritische_regie(self.GARANTIE))
        vorher = starte("auszahlung", coaching="kritisch")
        entwurf = naechste_runde(vorher, self.GARANTIE, modell)
        self.assertEqual([rolle for rolle, _, _ in modell.aufrufe], ["Regie", "Coach"])
        self.assertEqual(entwurf.status, "läuft")
        self.assertTrue(entwurf.warte_auf_freigabe)
        self.assertEqual(entwurf.entwurf, self.GARANTIE)
        self.assertEqual(entwurf.coach_hinweis["typ"], "kritisch")
        self.assertEqual(entwurf.runden, vorher.runden)
        self.assertEqual((entwurf.aerger, entwurf.vertrauen), (vorher.aerger, vorher.vertrauen))
        self.assertEqual(entwurf.hinweis_bekannt, vorher.hinweis_bekannt)
        with self.assertRaises(ValueError):
            naechste_runde(entwurf, "Andere Antwort.", modell)
        self.assertEqual([rolle for rolle, _, _ in modell.aufrufe], ["Regie", "Coach"])

    def test_weiter_uebernimmt_entwurf_genau_einmal(self):
        modell = Uebungsmodell()
        entwurf = naechste_runde(starte("auszahlung", coaching="kritisch"), self.GARANTIE, modell)
        bestaetigt = weiter(entwurf, modell)
        self.assertEqual(len(bestaetigt.runden), 1)
        self.assertEqual(bestaetigt.runden[0].servicekraft, self.GARANTIE)
        self.assertTrue(bestaetigt.runden[0].unterstuetzt)
        self.assertFalse(bestaetigt.warte_auf_freigabe)
        self.assertIsNone(bestaetigt.entwurf)
        with self.assertRaises(ValueError):
            weiter(bestaetigt, modell)
        self.assertEqual(len(bestaetigt.runden), 1)

    def test_neu_formulieren_verwirft_entwurf_und_behaelt_unterstuetzung(self):
        modell = Uebungsmodell()
        entwurf = naechste_runde(starte("auszahlung", coaching="kritisch"), self.GARANTIE, modell)
        offen = neu_formulieren(entwurf)
        self.assertEqual(offen.runden, ())
        self.assertFalse(offen.warte_auf_freigabe)
        self.assertIsNone(offen.entwurf)
        with self.assertRaises(ValueError):
            neu_formulieren(offen)
        bestaetigt = naechste_runde(offen, DEMO_ANTWORTEN[0], modell)
        self.assertEqual(len(bestaetigt.runden), 1)
        self.assertEqual(bestaetigt.runden[0].servicekraft, DEMO_ANTWORTEN[0])
        self.assertTrue(bestaetigt.runden[0].unterstuetzt)
        self.assertNotIn(self.GARANTIE, json.dumps(verlauf(bestaetigt), ensure_ascii=False))

    def test_abbruch_und_beenden_raeumen_offenen_entwurf_auf(self):
        for abbrechen in (False, True):
            with self.subTest(abbrechen=abbrechen):
                entwurf = naechste_runde(starte("auszahlung", coaching="kritisch"), self.GARANTIE, Uebungsmodell())
                ende = beende(entwurf, abbrechen=abbrechen)
                self.assertFalse(ende.warte_auf_freigabe)
                self.assertIsNone(ende.entwurf)
                self.assertIsNone(ende.coach_hinweis)
                self.assertEqual(ende.runden, ())

    def test_negation_unsicherheit_und_rueckmeldezeit_loesen_nicht_aus(self):
        unkritisch = (
            "Ich melde mich morgen mit einem Zwischenstand.",
            "Das Geld ist morgen nicht garantiert da.",
            "Vielleicht ist das Geld morgen da.",
            "Ich glaube, das Geld kommt morgen.",
            "Ich vermute, das Geld kommt morgen.",
            "Ich rechne damit, dass das Geld morgen kommt.",
            "Ich melde mich morgen, die Auszahlung erfolgt nach Prüfung.",
            "Ich kann nicht garantieren, dass das Geld morgen da ist.",
            "Sie sagen: „Das Geld ist morgen garantiert da“. Das kann ich nicht zusagen.",
        )
        for aussage in unkritisch:
            with self.subTest(aussage=aussage):
                modell = NachgebildetesModell(Regie=kritische_regie(aussage))
                gespraech = naechste_runde(starte("auszahlung", coaching="kritisch"), aussage, modell)
                self.assertEqual(len(gespraech.runden), 1)
                self.assertFalse(gespraech.warte_auf_freigabe)
                self.assertNotIn("Coach", [rolle for rolle, _, _ in modell.aufrufe])

    def test_eindeutiger_auszahlungstermin_ohne_garantiewort_loest_aus(self):
        aussage = "Die Auszahlung erfolgt morgen."
        modell = NachgebildetesModell(Regie=kritische_regie(aussage))
        gespraech = naechste_runde(starte("auszahlung", coaching="kritisch"), aussage, modell)
        self.assertTrue(gespraech.warte_auf_freigabe)
        self.assertEqual(gespraech.runden, ())
        self.assertEqual(gespraech.entwurf, aussage)
        self.assertEqual(gespraech.coach_hinweis["typ"], "kritisch")
        self.assertEqual([rolle for rolle, _, _ in modell.aufrufe], ["Regie", "Coach"])

    def test_lokales_modell_markiert_angefuehrte_und_zurueckgewiesene_zitate_nicht(self):
        aussagen = (
            "Sie sagen: „Das Geld ist morgen garantiert da“. Das kann ich nicht zusagen.",
            "Der Satz „Das Geld ist morgen garantiert da“ ist eine falsche Zusage.",
        )
        for aussage in aussagen:
            with self.subTest(aussage=aussage):
                modell = Uebungsmodell()
                with patch.object(modell, "antwort", wraps=modell.antwort) as antwort:
                    gespraech = naechste_runde(starte("auszahlung", coaching="kritisch"), aussage, modell)
                self.assertEqual(len(gespraech.runden), 1)
                self.assertFalse(gespraech.warte_auf_freigabe)
                self.assertIsNone(gespraech.coach_hinweis)
                self.assertEqual([aufruf.args[0] for aufruf in antwort.call_args_list], ["Regie", "Kunde"])

    def test_regie_markierung_braucht_gueltige_regel_und_woertlichen_beleg(self):
        markierungen = (
            {"regel_id": "fremde_regel", "beleg": self.GARANTIE},
            {"regel_id": "auszahlung_termin_offen", "beleg": "Das Geld kommt ganz bestimmt."},
            {"regel_id": "auszahlung_termin_offen", "beleg": "morgen"},
            None,
        )
        for markierung in markierungen:
            with self.subTest(markierung=markierung):
                modell = NachgebildetesModell(Regie=regie_antwort(kritisch=markierung))
                gespraech = naechste_runde(starte("auszahlung", coaching="kritisch"), self.GARANTIE, modell)
                self.assertEqual(len(gespraech.runden), 1)
                self.assertFalse(gespraech.warte_auf_freigabe)
                self.assertNotIn("Coach", [rolle for rolle, _, _ in modell.aufrufe])

    def test_kritische_auszahlungsregel_gilt_nicht_fuer_anderen_fall(self):
        modell = NachgebildetesModell(Regie=kritische_regie(self.GARANTIE))
        gespraech = naechste_runde(starte("rueckmeldung", coaching="kritisch"), self.GARANTIE, modell)
        self.assertEqual(len(gespraech.runden), 1)
        self.assertFalse(gespraech.warte_auf_freigabe)

    def test_kritische_auszahlungsregel_braucht_offenen_termin_laut_fall(self):
        fall = replace(FAELLE["auszahlung"], termin_offen=False)
        modell = NachgebildetesModell(Regie=kritische_regie(self.GARANTIE))
        with patch.dict(FAELLE, {"auszahlung": fall}):
            gespraech = naechste_runde(starte("auszahlung", coaching="kritisch"), self.GARANTIE, modell)
        self.assertEqual(len(gespraech.runden), 1)
        self.assertFalse(gespraech.warte_auf_freigabe)
        self.assertNotIn("Coach", [rolle for rolle, _, _ in modell.aufrufe])

    def test_coachfehler_und_fehler_beim_weiter_lassen_bisherigen_stand_gueltig(self):
        vorher = starte("auszahlung", coaching="kritisch")
        with self.assertRaises(Modellfehler):
            naechste_runde(vorher, self.GARANTIE, NachgebildetesModell(Coach=""))
        self.assertEqual(vorher.runden, ())
        self.assertFalse(vorher.warte_auf_freigabe)
        entwurf = naechste_runde(vorher, self.GARANTIE, Uebungsmodell())
        with self.assertRaises(Modellfehler):
            weiter(entwurf, NachgebildetesModell(Kunde=""))
        self.assertTrue(entwurf.warte_auf_freigabe)
        self.assertEqual(entwurf.runden, ())
        bestaetigt = weiter(entwurf, Uebungsmodell())
        self.assertEqual(len(bestaetigt.runden), 1)


class BewertungsVertragTest(unittest.TestCase):
    def setUp(self):
        self.modell = Uebungsmodell()
        self.ende = beende(naechste_runde(starte("auszahlung"), "Guten Tag.", self.modell))

    def test_feedback_im_modus_aus_bleibt_moeglich_und_nutzt_nur_bestaetigte_texte(self):
        bericht = feedback(self.ende, self.modell)
        self.assertEqual(set(bericht["beobachtungen"]), set(KRITERIEN))
        self.assertTrue(bericht["tipp"])
        for beobachtung in bericht["beobachtungen"].values():
            self.assertFalse(beobachtung["unterstuetzt"])
            if beobachtung["stufe"] == "Keine Gelegenheit":
                self.assertIsNone(beobachtung["runde"])
                self.assertIsNone(beobachtung["zitat"])
            else:
                self.assertEqual(beobachtung["zitat"], "Guten Tag.")

    def test_unterstuetzte_belegstelle_und_verlauf_bleiben_markiert(self):
        gespraech = hinweis_anfordern(starte("auszahlung", coaching="auf_abruf"), self.modell)
        gespraech = naechste_runde(gespraech, DEMO_ANTWORTEN[0], self.modell)
        gespraech = naechste_runde(gespraech, DEMO_ANTWORTEN[1], self.modell)
        bericht = feedback(gespraech, self.modell)
        self.assertTrue(bericht["beobachtungen"]["empathie"]["unterstuetzt"])
        self.assertFalse(bericht["beobachtungen"]["naechster_schritt"]["unterstuetzt"])
        self.assertTrue(verlauf(gespraech)[0]["unterstuetzt"])
        self.assertFalse(verlauf(gespraech)[1]["unterstuetzt"])

    def test_bewertung_weist_ungueltige_belegstelle_oder_fremdes_kriterium_zurueck(self):
        basis = {k: {"stufe": "Übungsbedarf", "runde": 1} for k in KRITERIEN}
        fehler = []
        for runde in (0, 2, True, "1", None):
            ausgabe = deepcopy(basis)
            ausgabe["empathie"]["runde"] = runde
            fehler.append(ausgabe)
        fehler.extend((
            {k: v for k, v in basis.items() if k != "empathie"},
            {**basis, "fremd": {"stufe": "Gezeigt", "runde": 1}},
            {**basis, "empathie": {"stufe": "Keine Gelegenheit", "runde": 1}},
            {**basis, "empathie": {"stufe": "Sehr gut", "runde": 1}},
        ))
        for ausgabe in fehler:
            with self.subTest(ausgabe=ausgabe):
                modell = NachgebildetesModell(Bewertung=json.dumps(ausgabe, ensure_ascii=False))
                with self.assertRaises(Modellfehler):
                    feedback(self.ende, modell)
                self.assertEqual([r for r, _, _ in modell.aufrufe], ["Bewertung"])

    def test_modellzitat_wird_durch_originaltext_ersetzt(self):
        ausgabe = {k: {"stufe": "Übungsbedarf", "runde": 1, "zitat": "Erfundener Modelltext"} for k in KRITERIEN}
        modell = NachgebildetesModell(Bewertung=json.dumps(ausgabe, ensure_ascii=False))
        bericht = feedback(self.ende, modell)
        self.assertTrue(all(b["zitat"] == "Guten Tag." for b in bericht["beobachtungen"].values()))

    def test_direktstart_coacht_am_belegten_uebungsbedarf(self):
        ausgabe = {
            "empathie": {"stufe": "Gezeigt", "runde": 1},
            "klaerung": {"stufe": "Übungsbedarf", "runde": 1},
            "naechster_schritt": {"stufe": "Keine Gelegenheit", "runde": None},
        }
        modell = NachgebildetesModell(Bewertung=json.dumps(ausgabe, ensure_ascii=False))
        feedback(self.ende, modell)
        coachdaten = next(d for rolle, _, d in modell.aufrufe if rolle == "Coach")
        self.assertIn(coachdaten["fokus"], ("klaerung", KRITERIEN["klaerung"][0]))
        self.assertEqual(coachdaten["status"], "beendet")


if __name__ == "__main__":
    unittest.main()
