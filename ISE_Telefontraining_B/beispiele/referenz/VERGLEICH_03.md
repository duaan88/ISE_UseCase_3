# Nachtest vom 25. November 2026

Dieselben sechs Transkripte, unveränderte Sollstufen und Profile 0.2 wie im [vorigen Lauf](VERGLEICH_02.md). Der produktive Bewertungsagent erhielt neutrale IDs ab m001. Die Sollbewertung war nur dem Vergleichsskript bekannt. Modellalias: alias-fast. [Berichte und Fehlversuche](live-neutral-03/)

| Gespräch | Richtige Stufen (drei Berichte mit je drei Kriterien) | Beobachtung |
|---|---:|---|
| Petra gut | 9/9 | Finanzielle Belastung und Wartezeit anerkannt. Eine Begründung nennt korrekt drei Wochen. |
| Petra gemischt | 9/9 | Alle drei Berichte erkennen die unvollständige Weiterleitung. Eine Begründung nennt korrekt drei Wochen. Lauf 4 schreibt der Servicekraft bei der Klärung eine Trennung offener und bestätigter Informationen zu; belegt ist die Frage nach dem Brief. |
| Petra problematisch | 9/9 | Die Begründungen beschreiben die relativierte Belastung und die unbelegte Zahlungsgarantie. |
| Nora gut | 9/9 | Auf den Wunsch folgte ein Serviceangebot. Der nächste Schritt war bewertbar. |
| Nora gemischt | 7/9 | Alle drei Berichte weisen für den nächsten Schritt „Keine Gelegenheit“ ohne Servicebeleg aus. Bei Empathie vergeben Lauf 2 und 3 weiterhin „Übungsbedarf“ statt „Teilweise gezeigt“. |
| Nora problematisch | 9/9 | Die Servicekraft konnte auf den Wunsch reagieren und ging darüber hinweg. Die drei Berichte weisen für den nächsten Schritt Übungsbedarf aus. |

**Prüfung:** 52/54 Stufen entsprechen der Referenz. In den 27 akzeptierten Petra-Kriterienbegründungen fand sich keine falsche Zeitangabe. Alle Belegzitate stimmten mit den über die IDs referenzierten Servicebeiträgen überein; die kritischen Befunde entsprachen dem Soll. Bei Nora bindet die Anwendung die Sonderregel an die erste bestätigte Offenlegung des Fallhinweises und das Fehlen eines späteren Servicebeitrags. Bei Petra weist der Validator erkannte, im Dialog nicht wörtlich belegte Zeitspannen zurück. Die Prüfung ist konservativ: Auch sinngemäß korrekte Umformulierungen können einen erneuten Abruf erfordern.

**Aufwand:** 30 Modellaufrufe für 18 gültige Berichte. Acht Ausgaben wurden wegen unbelegter Zeitspannen, vier wegen ungültiger Beleg-IDs verworfen. Bei Petra gemischt lieferten Durchgang 1 und 2 auch nach Wiederholung keinen gültigen Bericht. Die zusätzlich dokumentierten Durchgänge 4 und 5 ergänzen Durchgang 3. Die Stufenzahlen beziehen sich auf gültige Berichte; sie messen nicht die Erfolgsquote beim ersten Abruf.
