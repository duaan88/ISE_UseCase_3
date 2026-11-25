# Referenzvergleich für Petra und Nora

Stand 25. November 2026, Bewertungslogik von B auf `e71ebef`. Die sechs fiktiven Transkripte enthalten stabile Nachrichten-IDs, eine vor dem Modellaufruf festgelegte Sollstufe je Kriterium, eine Begründung und den Originalbeleg. Bei „Keine Gelegenheit“ bleibt die Belegliste leer. Die Referenzen sind Arbeitsentwürfe ohne unabhängige Team- oder Allianz-Bewertung.

Jedes Transkript wurde direkt mit demselben Bewertungsagenten und Profil wie in Streamlit ausgewertet (Blablador, konfigurierter Alias im jeweiligen Live-Bericht, Schwierigkeit Mittel). Die Eingabe enthielt Dialog und Rubrik. Weder Qualitätsetikett noch Sollbewertung wurden als Bewertungsfeld übergeben. **Einschränkung:** Die Nachrichten-IDs enthalten das Qualitätsetikett und sind für das Modell sichtbar. Ein verblindeter Wiederholungslauf sollte neutrale IDs verwenden. Es wurden keine neuen Kundenantworten erzeugt. Die Dateien unter `live/` enthalten den vollständigen ersten gültigen Bericht einschließlich Stärken, Verbesserungen und Originalzitaten.

## Ergebnisse

Je Zelle steht die erwartete Stufe. Ein Pfeil kennzeichnet eine abweichende Live-Stufe. G = Gezeigt, T = Teilweise gezeigt, Ü = Übungsbedarf, K = Keine Gelegenheit.

| Referenz | Empathie | Klärung | Nächster Schritt | Kritischer Befund | Live-Bericht |
|---|---|---|---|---|---|
| [Petra gut](petra-gut.json) | G | G | G | keiner | [Bericht](live/petra-gut.json) |
| [Petra gemischt](petra-gemischt.json) | T | G → T | T → Ü | keiner | [Bericht](live/petra-gemischt.json) |
| [Petra problematisch](petra-problematisch.json) | Ü | G → T | Ü | terminierte Auszahlungszusage | [Bericht](live/petra-problematisch.json) |
| [Nora gut](nora-gut.json) | G | G | G | keine Regel hinterlegt | [Bericht](live/nora-gut.json) |
| [Nora gemischt](nora-gemischt.json) | T → Ü | G | K | keine Regel hinterlegt | [Bericht](live/nora-gemischt.json) |
| [Nora problematisch](nora-problematisch.json) | Ü | Ü | Ü | keine Regel hinterlegt | [Bericht](live/nora-problematisch.json) |

14 von 18 Kriterien stimmen in diesem Lauf in der Stufe überein. Alle Belege in den Kriterien, Stärken, Verbesserungen und kritischen Befunden wurden anhand der Nachrichten-ID wortgleich im bestätigten Servicebeitrag gefunden. Bei Nora gut und Petra problematisch wurde jeweils eine ungültige Modellbewertung verworfen und der identische Verlauf erneut bewertet. Ein gültiger Bericht pro Verlauf erlaubt keine Aussage über die Wiederholbarkeit.

## Abweichungen mit Gesprächsbezug

- **Petra gemischt.** „Was stand im letzten Brief?“ klärt den konkreten Sachverhalt. Das Modell verlangt zusätzlich die Trennung von offenen und bestätigten Informationen. „Ich leite Sie weiter.“ zählt im Soll als begonnener Handlungsvorschlag. Das Modell gibt Übungsbedarf, weil Ziel, Zuständigkeit und Rückmeldung fehlen. Petra stimmt der Weiterleitung im Gespräch nicht zu.
- **Petra problematisch.** Die Frage nach dem Brief ist trotz des abweisenden „Andere warten auch“ sachdienlich. Das Modell zieht für den Ton auch bei Klärung ab. Die Begründung nennt zudem drei **Tage** statt drei Wochen und eine Umleitung, die im Transkript nicht vorkommt. Die separate kritische Regel belegt dagegen korrekt „Das Geld ist morgen garantiert da.“ mit m004.
- **Nora gemischt.** „Was würde Ihnen jetzt helfen?“ lässt Nora Raum, ohne den Verlust ausdrücklich anzuerkennen. Die Referenz vergibt teilweise gezeigte Empathie, das Modell Übungsbedarf. Beim nächsten Schritt stimmt „Keine Gelegenheit“. Allerdings äußert Nora durchaus einen konkreten Wunsch. Entscheidend ist, dass danach kein Servicebeitrag mehr folgt.
- **Übereinstimmende Stufen sind kein vollständiger Qualitätsnachweis.** Bei Petra gut nennt der Bericht eine „Klärungsfrage zum fehlenden Formular“. Gefragt wurde allgemeiner nach dem Brief. Bei Nora gut empfiehlt er eine zusätzliche Bestätigungsmail, obwohl Nora sich nach der Übersicht selbst melden möchte. Bei Nora problematisch erkennt der Bericht den Zeitdruck und die unpassende Weiterleitung in der Bewertung der Gesprächsführung; eine separate kritische Regel für Trauerfälle ist fachlich noch offen.

## Nächste Priorität

Zuerst beide Teammitglieder die sechs Transkripte unabhängig und ohne Soll- oder Live-Berichte bewerten lassen. Daraus je Profil konkrete Beispiele für die Grenze zwischen „Teilweise gezeigt“ und „Übungsbedarf“ festlegen. Besonders relevant sind die unbeantwortete Weiterleitung, eine sachlich gute Frage mit abweisendem Ton und die letzte Offenlegung ohne weitere Antwortmöglichkeit. Im nächsten Vergleich zusätzlich prüfen, ob jede Begründung zur Chronologie und zum Inhalt des Belegs passt. Danach die überarbeitete Rubrik sowie die geplanten weiteren Kriterien mit den freigegebenen Schulungsunterlagen abgleichen. Coach, Audio und Lernhistorie können auf diesem kalibrierten Kern aufbauen.
