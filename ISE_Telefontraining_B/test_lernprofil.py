"""Persistenztests ohne Netz, echte Personen oder Datenbankreste im Projekt."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from lernprofil import fortschritt_speichern, profil_vorschlag
from training import KRITERIEN, starte


def vorbereitete_uebung(stufen=None, *, unterstuetzt=False, status="beendet"):
    """Gleichwertige Beispieldaten: bestätigte Runde und zugehöriger Bericht."""
    text = "Ich verstehe Ihren Ärger. Ich prüfe den Vorgang und melde mich morgen mit einem Zwischenstand."
    gespraech = SimpleNamespace(
        status=status,
        runden=(SimpleNamespace(servicekraft=text, unterstuetzt=unterstuetzt),),
    )
    stufen = stufen or {k: "Gezeigt" for k in KRITERIEN}
    bericht = {"tipp": "Frage genauer nach. Beispiel: „Welche Nachricht liegt Ihnen vor?“", "beobachtungen": {}}
    for kriterium in KRITERIEN:
        stufe = stufen.get(kriterium, "Gezeigt")
        vorhanden = stufe != "Keine Gelegenheit"
        bericht["beobachtungen"][kriterium] = {
            "stufe": stufe, "runde": 1 if vorhanden else None,
            "zitat": text if vorhanden else None,
            "unterstuetzt": unterstuetzt if vorhanden else False,
        }
    return gespraech, bericht


class LernprofilTest(unittest.TestCase):
    def setUp(self):
        self.verzeichnis = TemporaryDirectory()
        self.addCleanup(self.verzeichnis.cleanup)
        self.db = Path(self.verzeichnis.name) / "test.sqlite3"

    def speichern(self, uebung, stufen=None, *, profil="fiktiv-a", unterstuetzt=False):
        gespraech, bericht = vorbereitete_uebung(stufen, unterstuetzt=unterstuetzt)
        return fortschritt_speichern(profil, uebung, gespraech, bericht, db_pfad=self.db)

    def vorschlag(self, profil="fiktiv-a"):
        return profil_vorschlag(profil, db_pfad=self.db)

    def test_leeres_profil_erlaubt_fallstandard_ohne_datei(self):
        self.assertIsNone(self.vorschlag()["fokus"])
        self.assertFalse(self.db.exists())

    def test_start_liest_und_speichert_kein_profil(self):
        with patch("lernprofil.sqlite3.connect") as zugriff:
            gespraech = starte("auszahlung")
        zugriff.assert_not_called()
        self.assertIsNone(gespraech.fokus)

    def test_expliziter_abruf_kann_nach_freigabe_an_start_uebergeben_werden(self):
        self.speichern("uebung-1", {"klaerung": "Übungsbedarf"})
        vorschlag = self.vorschlag()
        gespraech = starte("auszahlung", profil_fokus=vorschlag["fokus"])
        self.assertEqual(gespraech.fokus, "klaerung")
        self.assertEqual(gespraech.fokus_quelle, "lernprofil")

    def test_speichern_ist_idempotent_und_ueberschreibt_nichts(self):
        erstes = self.speichern("uebung-1", {"klaerung": "Übungsbedarf"})
        zweites = self.speichern("uebung-1", {"empathie": "Übungsbedarf"})
        self.assertTrue(erstes["gespeichert"])
        self.assertFalse(erstes["bereits_vorhanden"])
        self.assertTrue(zweites["gespeichert"])
        self.assertTrue(zweites["bereits_vorhanden"])
        self.assertEqual(self.vorschlag()["fokus"], "klaerung")
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT count(*) FROM uebungen").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM beobachtungen").fetchone()[0], 3)

    def test_parallele_wiederholung_speichert_hoechstens_einmal(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            bestaetigungen = list(pool.map(lambda _: self.speichern("parallel"), range(4)))
        self.assertEqual(sum(not b["bereits_vorhanden"] for b in bestaetigungen), 1)
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT count(*) FROM beobachtungen").fetchone()[0], 3)

    def test_profile_bleiben_getrennt_auch_bei_gleicher_uebungs_id(self):
        self.speichern("uebung-1", {"empathie": "Übungsbedarf"})
        self.speichern("uebung-1", {"klaerung": "Übungsbedarf"}, profil="fiktiv-b")
        self.assertEqual(self.vorschlag()["fokus"], "empathie")
        self.assertEqual(self.vorschlag("fiktiv-b")["fokus"], "klaerung")
        self.assertIsNone(self.vorschlag("fiktiv-neu")["fokus"])

    def test_wiederkehrender_bedarf_vor_einmaligem_bedarf_und_teilweise(self):
        self.speichern("eins", {"empathie": "Übungsbedarf", "klaerung": "Übungsbedarf", "naechster_schritt": "Teilweise gezeigt"})
        self.speichern("zwei", {"klaerung": "Übungsbedarf", "naechster_schritt": "Teilweise gezeigt"})
        vorschlag = self.vorschlag()
        self.assertEqual(vorschlag["fokus"], "klaerung")
        self.assertIn("2× Übungsbedarf", vorschlag["begruendung"])

    def test_gleichstand_nutzt_kriterienreihenfolge(self):
        self.speichern("eins", {"empathie": "Übungsbedarf", "klaerung": "Übungsbedarf"})
        self.assertEqual(self.vorschlag()["fokus"], "empathie")

    def test_teilweise_ist_vorschlag_wenn_kein_uebungsbedarf(self):
        self.speichern("eins", {"klaerung": "Teilweise gezeigt"})
        self.assertEqual(self.vorschlag()["fokus"], "klaerung")

    def test_keine_gelegenheit_ist_fehlende_beobachtung(self):
        self.speichern("ohne-gelegenheit", {k: "Keine Gelegenheit" for k in KRITERIEN})
        self.assertIsNone(self.vorschlag()["fokus"])
        self.speichern("beobachtet", {"klaerung": "Übungsbedarf"})
        for nummer in range(6):
            self.speichern(str(nummer), {k: "Keine Gelegenheit" for k in KRITERIEN})
        self.assertEqual(self.vorschlag()["fokus"], "klaerung")

    def test_letzte_fuenf_beobachtungen_erlauben_neuen_lernstand(self):
        self.speichern("alter-bedarf", {"empathie": "Übungsbedarf"})
        for nummer in range(5):
            self.speichern("gezeigt-" + str(nummer))
        self.assertIsNone(self.vorschlag()["fokus"])

    def test_nur_gezeigt_laesst_fokus_offen(self):
        self.speichern("gezeigt")
        self.assertIsNone(self.vorschlag()["fokus"])

    def test_kompakte_daten_enthalten_zeit_und_hilfe_aber_keine_gespraechstexte(self):
        self.speichern("mit-hilfe", unterstuetzt=True)
        with closing(sqlite3.connect(self.db)) as db, db:
            spalten = {r[1] for r in db.execute("PRAGMA table_info(beobachtungen)")}
            self.assertEqual(spalten, {"profil_id", "uebung_id", "kriterium", "stufe", "unterstuetzt"})
            self.assertEqual(db.execute("SELECT SUM(unterstuetzt) FROM beobachtungen").fetchone()[0], 3)
            self.assertEqual(db.execute("SELECT unterstuetzt FROM uebungen").fetchone()[0], 1)
            zeitpunkt = db.execute("SELECT zeitpunkt FROM uebungen").fetchone()[0]
            self.assertTrue(zeitpunkt.endswith("+00:00"))
            self.assertNotIn("Zwischenstand", " ".join(db.iterdump()))

    def test_hilfe_in_nicht_zitiertem_beitrag_bleibt_pro_uebung_markiert(self):
        gespraech, bericht = vorbereitete_uebung()
        gespraech.runden = (
            SimpleNamespace(servicekraft="Mit Hilfe formulierte frühere Antwort.", unterstuetzt=True),
            *gespraech.runden,
        )
        for beobachtung in bericht["beobachtungen"].values():
            beobachtung["runde"] = 2
        fortschritt_speichern("fiktiv-a", "nicht-zitierte-hilfe", gespraech, bericht, db_pfad=self.db)
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT SUM(unterstuetzt) FROM beobachtungen").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT unterstuetzt FROM uebungen").fetchone()[0], 1)

    def test_aeltere_datenbank_wird_ohne_datenverlust_erweitert(self):
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("CREATE TABLE uebungen (profil_id TEXT, uebung_id TEXT, zeitpunkt TEXT, PRIMARY KEY (profil_id, uebung_id))")
            db.execute("CREATE TABLE beobachtungen (profil_id TEXT, uebung_id TEXT, kriterium TEXT, stufe TEXT, unterstuetzt INTEGER, PRIMARY KEY (profil_id, uebung_id, kriterium))")
            db.execute("INSERT INTO uebungen VALUES ('fiktiv-a', 'alt', '2026-01-01T00:00:00+00:00')")
            db.execute("INSERT INTO beobachtungen VALUES ('fiktiv-a', 'alt', 'klaerung', 'Übungsbedarf', 1)")
        self.speichern("neu")
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT unterstuetzt FROM uebungen WHERE uebung_id = 'alt'").fetchone()[0], 1)
        self.assertEqual(self.vorschlag()["fokus"], "klaerung")

    def test_ohne_bericht_waehrend_gespraech_oder_nach_abbruch_nicht_speichern(self):
        for status, bericht_fehlt in (("beendet", True), ("läuft", False), ("abgebrochen", False)):
            with self.subTest(status=status):
                gespraech, bericht = vorbereitete_uebung(status=status)
                with self.assertRaises(ValueError):
                    fortschritt_speichern("fiktiv-a", status, gespraech, None if bericht_fehlt else bericht, db_pfad=self.db)
        self.assertFalse(self.db.exists())

    def test_unpassende_berichtdaten_werden_vor_schreiben_abgewiesen(self):
        gespraech, original = vorbereitete_uebung()
        varianten = []
        for schluessel, wert in (("stufe", "Gut"), ("runde", True), ("runde", 2), ("zitat", "Erfunden"), ("unterstuetzt", True)):
            bericht = deepcopy(original)
            bericht["beobachtungen"]["empathie"][schluessel] = wert
            varianten.append(bericht)
        bericht = deepcopy(original)
        del bericht["beobachtungen"]["klaerung"]
        varianten.append(bericht)
        bericht = deepcopy(original)
        bericht["beobachtungen"]["empathie"]["stufe"] = "Keine Gelegenheit"
        varianten.append(bericht)
        for bericht in varianten:
            with self.subTest(bericht=bericht):
                with self.assertRaises(ValueError):
                    fortschritt_speichern("fiktiv-a", "ungültig", gespraech, bericht, db_pfad=self.db)
        self.assertFalse(self.db.exists())

    def test_konfigurierte_datei_und_lesbarkeit_in_neuem_prozess(self):
        with patch.dict(os.environ, {"ISE_LERNPROFIL_DB": str(self.db)}):
            gespraech, bericht = vorbereitete_uebung({"klaerung": "Übungsbedarf"})
            fortschritt_speichern("fiktiv-a", "persistiert", gespraech, bericht)
            resultat = subprocess.run(
                [sys.executable, "-c", "import json; from lernprofil import profil_vorschlag; print(json.dumps(profil_vorschlag('fiktiv-a')))"],
                cwd=Path(__file__).parent, env=os.environ.copy(), text=True, capture_output=True, check=True,
            )
        self.assertEqual(json.loads(resultat.stdout)["fokus"], "klaerung")

    def test_ids_mit_leerem_oder_falschem_wert_werden_abgewiesen(self):
        for kennung in ("", " ", " fiktiv", None, 42, "a" * 129):
            with self.subTest(kennung=kennung):
                with self.assertRaises(ValueError):
                    self.vorschlag(kennung)


if __name__ == "__main__":
    unittest.main()
