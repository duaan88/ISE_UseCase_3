# Petra und Nora – Live-Vergleich der Profile 0.2

25. November 2026. Die unveränderten sechs Referenztranskripte und Sollbewertungen aus dem [ersten Vergleich](README.md) wurden mit Blablador über den produktiven Bewertungsagenten ausgewertet. Petra erhielt das Profil `auszahlung-0.2`, Nora `trauerfall-0.2`. Beide enthalten Grenzbeispiele für Empathie, Klärung und nächsten Schritt.

Das Modell sah Nachrichten-IDs von `m001` an, die Sprecher, Gesprächsbeiträge, Schwierigkeit, Abschlussgrund und Rubrik. Dateinamen, Qualitätsetiketten, Sollbewertungen und ursprüngliche IDs waren nicht im Modellkontext. Die [gespeicherten Ergebnisse](live-neutral-02/) enthalten die lokale ID-Zuordnung, den Modellalias, Validierungsfehler und die vollständigen gültigen Berichte. Für einen neuen Lauf im Projektordner mit gesetztem API-Schlüssel: `python referenzvergleich.py neuer-ergebnisordner`.

## Stufen und Begründungen

Die Zahlen geben je Kriterium an, in wie vielen der drei gültigen Berichte die Stufe der Referenz entsprach. Geprüft wurden auch die Begründungen aller 54 Kriterienbeobachtungen. Falsche Zeitangaben und unbelegte Schlussfolgerungen zählen in der Tabelle zusätzlich als qualitative Befunde, auch bei passender Stufe.

| Gespräch | Empathie | Klärung | Nächster Schritt | Abgleich der Begründungen mit dem Dialog |
|---|---:|---:|---:|---|
| Petra gut | 2/3 | 3/3 | 3/3 | Lauf 1 vergibt nur „Teilweise gezeigt“, obwohl die Servicekraft Rechnung **und** Wartezeit anspricht. Lauf 2 schreibt „dreitägige“, Lauf 3 „dreifache“ Wartezeit. Im Dialog sind es drei Wochen. Klärung und vereinbarter Zwischenstand werden nachvollziehbar beschrieben. |
| Petra gemischt | 3/3 | 3/3 | 3/3 | Die Weiterleitung ohne Ziel und Rückmeldezeit wird durchgehend als unvollständiges Angebot eingeordnet. Lauf 1 nennt die Wartezeit „dreifach“, Lauf 2 „dreitägig“. Läufe 2 und 3 schreiben der Servicekraft eine ausdrückliche Trennung offener und bestätigter Fakten zu. Belegt ist die gezielte Frage nach dem Brief. |
| Petra problematisch | 3/3 | 3/3 | 3/3 | Alle drei würdigen die Frage nach dem Brief trotz des abweisenden Tons und erkennen die unbelegte Zahlungsgarantie. Lauf 2 nennt erneut eine „dreifache“ Wartezeit. Lauf 3 beschreibt die Frage als auf das Formular gerichtet, dessen Inhalt Petra erst anschließend nennt. |
| Nora gut | 3/3 | 3/3 | 3/3 | Beileid, offene Bedarfsfrage, Angebot einer schriftlichen Übersicht und Einholen der Zustimmung sind im Dialog belegt. Keine wesentliche inhaltliche Abweichung in den Kriterienbegründungen. |
| Nora gemischt | 1/3 | 3/3 | 1/3 | Läufe 1 und 4 vergeben für Empathie „Übungsbedarf“ statt „Teilweise gezeigt“ und für den nächsten Schritt „Übungsbedarf“ statt „Keine Gelegenheit“. Beide rechnen Nora den Wunsch zu, übersehen aber, dass anschließend kein Servicebeitrag folgt. Lauf 3 ordnet die Reihenfolge richtig ein. Lauf 2 blieb ohne gültigen Bericht. |
| Nora problematisch | 3/3 | 3/3 | 3/3 | Die Begründungen identifizieren die frühe Detailfrage und die Weiterleitung ohne Zustimmung. Das lässt sich am Dialog belegen; Lauf 3 nennt auch den ignorierten Wunsch nach schriftlicher Orientierung. |

**49 von 54 Stufen** entsprechen dem Soll. In jedem gültigen Bericht wurden die Zitate aus Kriterien, Stärken und Verbesserungen über neutrale IDs auf bestätigte Servicebeiträge zurückgeführt und wortgleich geprüft. Die kritischen Befunde einschließlich Originalbeleg entsprachen in allen 18 Berichten der Referenz. Die Auszahlungsregel arbeitet deterministisch.

## Fehlversuche und Aussagegrenze

Geplant waren drei Durchgänge je Fall. Der Validator verwarf bei Nora gemischt in Durchgang 2 alle drei Antworten wegen unzulässiger Beleg-IDs. Ein separat gespeicherter vierter Durchgang lieferte den dritten gültigen Bericht. Auch Nora gemischt 1, Petra gut 1 und 3 sowie Petra problematisch 3 brauchten Wiederholungen. Damit ergaben 26 Modellaufrufe 18 gültige und acht verworfene Antworten. Die Trefferquote für die Stufen bezieht sich nur auf gültige Berichte.

Die Beispiele wurden anhand der bekannten Grenzfälle entwickelt. Die Ergebnisse beschreiben diese sechs synthetischen Verläufe; sie sind kein unabhängiger Nachweis einer allgemeinen Verbesserung. Für die nächste Iteration sind zwei klar prüfbare Punkte offen: die tatsächlich vorhandene Antwortgelegenheit beim Gesprächsende und die korrekte Wiedergabe von Fakten in Freitextbegründungen. Beides sollte zusätzlich an neuen Transkripten mit unabhängig abgestimmtem Soll geprüft werden.
