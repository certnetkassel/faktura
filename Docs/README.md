# Docs — Einordnung

Dieser Ordner enthält **historische Konzeptdokumente**, nicht die Dokumentation
der umgesetzten Anwendung. Maßgeblich für den aktuellen Stand ist `CLAUDE.md`
im Projektwurzelverzeichnis.

## Wichtiger Hinweis zur Architektur

Alle Dokumente hier beschreiben eine ursprünglich geplante **Power-Apps-Canvas-App
mit Microsoft Lists und Power Automate**. Dieser Ansatz wurde verworfen. Umgesetzt
ist stattdessen eine **Flask-Anwendung mit SQLite**, die unter
https://faktura.dirkhildebrand.de läuft.

## Inhalt

| Datei | Stand | Inhalt |
|---|---|---|
| `Faktura-App-Bauplan.docx` | 23.02.2026 | Erster Bauplan (Power Apps / MS Lists) |
| `Faktura-App-Bauplan II.docx` | 23.02.2026 | Überarbeitung, ergänzt um Anschrift, Kontaktdaten und die Festlegung "Gutschrift nur als Stornorechnung" |
| `Faktura-App-Uebergabe.md` | 27.02.2026 | Ausführliche Projektdokumentation der Power-Apps-Variante (Listen, Formeln, Flows) |
| `html-vorlage.html` | 27.02.2026 | HTML/CSS-Belegvorlage aus der Power-Automate-Zeit (PDF-Erzeugung), nicht mehr im Einsatz — die App nutzt Word-Vorlagen unter `vorlagen/` |

## Weiterhin gültige Festlegungen

Fachlich relevant geblieben und in der aktuellen App umgesetzt sind:

- Kleinunternehmerregelung §19 UStG, keine Umsatzsteuer
- Anschrift: Hirschbergstr. 4, 34123 Kassel
- Zahlungsziel: 10 Tage nach Rechnungserhalt
- Gutschrift ausschließlich als Stornorechnung zu bestehenden Rechnungen
- Preiseinheiten: Stunde(n), Pauschale, pro Monat
- Belegarten mit getrennten Nummernkreisen: RE-, AN-, GU-

Abweichend zu den alten Dokumenten gilt heute das Belegnummern-Format
`PREFIX-YYMM###` (z. B. `RE-2604001`) statt `XX-JJJJ-NNN`.

## Backups

Datenbank-Backups (`faktura-backup.tar.gz` o. ä.) liegen **außerhalb des Repos**
unter `W:\Backups\Micro-Fakt\`. Sie enthalten `faktura.db` mit echten Kunden- und
Rechnungsdaten sowie Zugangsdaten und dürfen nicht eingecheckt werden
(`*.tar.gz` und `*.zip` sind in `.gitignore`).
