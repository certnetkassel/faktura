# Faktura Power Apps – Komplette Projektdokumentation

## Projektübersicht

**App-Name:** Faktura (Mini Fakt)
**Format:** Canvas App, Tablet
**Zweck:** Rechnungs-/Belegverwaltung für Einzelunternehmen Dirk Hildebrand, IT-Dienstleistungen
**Rechtsform:** Kleinunternehmer §19 UStG (keine Umsatzsteuer)
**Plattform:** Power Apps + SharePoint (MS Lists) + Power Automate

---

## 1. Geschäftsdaten

- **Firmenname:** Dirk Hildebrand - App Entwicklung
- **Inhaber:** Dirk Hildebrand
- **Adresse:** Hirschbergstr. 4, 34123 Kassel, Deutschland
- **Mobil:** +49 1512 8225666
- **E-Mail:** dirk@dirkhildebrand.de (auch: info@dirkhildebrand.de)
- **Web:** https://dirkhildebrand.de
- **Bank:** Stadtsparkasse Grebenstein (IBAN/Steuernr. noch offen)
- **Kleinunternehmer:** Ja – „Gemäß §19 UStG wird keine Umsatzsteuer berechnet."
- **Zahlungsziel Standard:** 10 Tage
- **Währung:** EUR
- **Primärfarbe:** dunkel-orange (vom Benutzer gewählt, war ursprünglich #1F4E79)
- **Logo:** Dirk_IT.png (hochgeladen)

---

## 2. Datenstruktur – 5 SharePoint-Listen (MS Lists)

### 2.1 Kunden

| Spalte | Typ | Bemerkung |
|--------|-----|-----------|
| Titel | Text | = Firmenname |
| KundenNr | Zahl | 5-stellig, ab 10001 |
| Anrede | Auswahl | Herr/Frau/Divers/Firma |
| Vorname | Text | |
| Nachname | Text | |
| Strasse | Text | |
| PLZ | Text | Nicht Zahl! |
| Ort | Text | |
| Land | Text | |
| TelefonNr | Text | |
| MobilNr | Text | |
| EMail | Text | |
| Webseite | Text | |
| Bemerkung | Mehrzeiliger Text | |
| Aktiv | Ja/Nein | |

### 2.2 Artikel

| Spalte | Typ | Bemerkung |
|--------|-----|-----------|
| Titel | Text | Kurzname |
| ArtikelNr | Text | z.B. ART-001 |
| Artikelbezeichnung | Mehrzeiliger Text | |
| Preis | Währung | |
| Preiseinheit | Auswahl | Stunde(n)/Pauschale/pro Monat |
| Aktiv | Ja/Nein | |

### 2.3 Faktura

| Spalte | Typ | Bemerkung |
|--------|-----|-----------|
| Titel | Text | = Betreff |
| BelegTyp | Auswahl | Rechnung/Angebot/Gutschrift |
| BelegNr | Text | z.B. RE-2026-001 |
| BelegDatum | Datum | |
| KundenNr | Nachschlagen → Kunden | |
| Status | Auswahl | Entwurf/Versendet/Bezahlt/Storniert/Angenommen/Abgelehnt |
| Gesamtbetrag | Währung | |
| ZahlungszielTage | Zahl | |
| Zahlungsziel | Datum | |
| Bemerkung | Mehrzeiliger Text | |
| BezugBeleg | Text | Für Gutschriften |
| PDFLink | Text | OneDrive-Pfad |

### 2.4 FakturaPositionen

| Spalte | Typ | Bemerkung |
|--------|-----|-----------|
| Titel | Text | z.B. RE-2026-001 / Pos 1 |
| FakturaID | Nachschlagen → Faktura | |
| ArtikelID | Nachschlagen → Artikel | Optional |
| Position | Zahl | Lfd. Nr. |
| Bezeichnung | Text | |
| Beschreibung | Mehrzeiliger Text | |
| Menge | Zahl | |
| Einheit | Auswahl | Stunde(n)/Pauschale/pro Monat |
| Einzelpreis | Währung | |
| Positionspreis | Währung | |

### 2.5 Einstellungen

| Spalte | Typ | Bemerkung |
|--------|-----|-----------|
| Firmenname | Text | |
| Inhaber | Text | |
| Strasse | Text | |
| PLZ | Text | |
| Ort | Text | |
| Land | Text | |
| Telefon | Text | |
| Mobil | Text | |
| EMail | Text | |
| Webseite | Text | |
| Steuernummer | Text | |
| UStIdNr | Text | |
| Bankname | Text | |
| IBAN | Text | |
| BIC | Text | |
| Kleinunternehmer | Ja/Nein | |
| KleinunternehmerText | Mehrzeiliger Text | |
| ZahlungszielTageStd | Zahl | |
| Waehrung | Text | |
| Primaerfarbe | Text | Hex-Code |
| Logo | Bild | |

### 2.6 Nachschlagen-Konfigurationen

**KundenNr (in Faktura) → Kunden:**
- Primärspalte: KundenNr
- Zusätzlich: Titel, Vorname, Nachname, Strasse, PLZ, Ort, EMail
- OHNE: Anrede (Auswahl-Spalte, nicht als Zusatzspalte möglich)

**FakturaID (in FakturaPositionen) → Faktura:**
- Primärspalte: BelegNr
- Zusätzlich: BelegDatum, Gesamtbetrag
- OHNE: BelegTyp, Status (Auswahl-Spalten)

**ArtikelID (in FakturaPositionen) → Artikel:**
- Primärspalte: Titel
- Zusätzlich: Artikelbezeichnung, Preis
- OHNE: Preiseinheit (Auswahl-Spalte)

**Zugriff auf Nachschlagen-Zusatzspalten in Power Apps:**
```
ThisItem.'KundenNr: Nachname'.Value
ThisItem.'KundenNr: Titel'.Value
ThisItem.'FakturaID: BelegDatum'.Value
```

---

## 3. App-Architektur

### 3.1 Screens (9 Stück)

1. **ScrDashboard** – KPI-Kacheln, Quick-Actions, letzte Belege
2. **ScrBelegListe** – Alle Belege mit Filter (Typ, Status), Suche
3. **ScrBelegNeu** – Neuen Beleg erstellen mit Positionen-Popup
4. **ScrBelegDetail** – Beleg anzeigen, Positionen hinzufügen/löschen, Status-Buttons, PDF
5. **ScrKundenListe** – Kundenliste mit Suche
6. **ScrKundeDetail** – Kunde anlegen/bearbeiten
7. **ScrArtikelListe** – Artikelliste mit Suche
8. **ScrArtikelDetail** – Artikel anlegen/bearbeiten
9. **ScrEinstellungen** – Firmendaten, Farbe, Logo

### 3.2 Navigation

- Linke Seitenleiste (rectNav, Width=220, varFarben.Primaer)
- lblNavFirma zeigt varEinstellungen.Firmenname
- 5 Menüpunkte mit Emojis: 🏠 Dashboard, 📄 Belege, 👤 Kunden, 📦 Artikel, ⚙️ Einstellungen
- Navigation auf alle 9 Screens kopiert (Suffix _8 bei kopierten Screens)

### 3.3 Dynamisches Farbsystem

**App.OnStart** lädt Einstellungen und berechnet Farbpalette:

```
Set(varEinstellungen; First(Einstellungen));;

Set(varFarbHex;
    If(!IsBlank(varEinstellungen.Primaerfarbe);
        varEinstellungen.Primaerfarbe;
        "#1F4E79"
    )
);;

Set(varFarben; {
    Primaer:         ColorValue(varFarbHex);
    PrimaerDunkel:   ColorFade(ColorValue(varFarbHex); -20%);
    PrimaerHell:     ColorFade(ColorValue(varFarbHex); 70%);
    PrimaerSehrHell: ColorFade(ColorValue(varFarbHex); 85%);
    Erfolg:          ColorValue("#548235");
    Warnung:         ColorValue("#BF8F00");
    Fehler:          ColorValue("#C00000");
    Info:            ColorValue("#2E75B6");
    Grau:            ColorValue("#888888");
    DunkelGrau:      ColorValue("#444444");
    Text:            ColorValue("#333333");
    TextHell:        ColorValue("#666666");
    TextAufPrimaer:  Color.White;
    Hintergrund:     Color.White;
    HintergrundAlt:  ColorValue("#F5F5F5")
})
```

---

## 4. Wichtige Formeln & Logik

### 4.1 Deutsche Power Apps Syntax (KRITISCH!)

| Englisch | Deutsch |
|----------|---------|
| Komma `,` als Argument-Trenner | Semikolon `;` |
| Semikolon `;` als Statement-Trenner | Doppeltes Semikolon `;;` |
| `&&` für UND | `;` als weitere Filter-Bedingung oder `And()` |
| `\|\|` für ODER | `Or()` Funktion |
| Zahlenformat im Formatstring | `"#,##0.00 €"` (Punkt=Dezimal) |

### 4.2 BelegNr-Generierung (ScrBelegNeu → OnVisible)

Format: `XX-JJJJ-NNN` (z.B. RE-2026-001, AN-2026-001, GU-2026-001)

```
Set(varPraefix;
    Switch(varNeuerBelegTyp;
        "Rechnung"; "RE";
        "Angebot"; "AN";
        "Gutschrift"; "GU"
    )
);;
Set(varJahr; Text(Year(Today())));;
Set(varSuchString; varPraefix & "-" & varJahr & "-");;
Set(varLetzteBelegNr;
    First(
        Sort(
            Filter(Faktura; StartsWith(BelegNr; varSuchString));
            BelegNr;
            SortOrder.Descending
        )
    ).BelegNr
);;
Set(varNeueNummer;
    If(IsBlank(varLetzteBelegNr);
        1;
        Value(Last(Split(varLetzteBelegNr; "-")).Value) + 1
    )
);;
Set(varNeueBelegNr; varPraefix & "-" & varJahr & "-" & Text(varNeueNummer; "000"))
```

### 4.3 Positionen-Collection (ScrBelegNeu)

Schema-Initialisierung in OnVisible:
```
ClearCollect(colPositionen;
    {Position: 0; Bezeichnung: ""; Beschreibung: ""; Menge: 0; Einheit: ""; Einzelpreis: 0; Positionspreis: 0; ArtikelId: 0}
);;
Clear(colPositionen)
```

### 4.4 Beleg speichern (btnBelegSpeichern → OnSelect)

Mit Validierung, Beleg + Positionen speichern:
```
If(IsBlank(cmbNeuKunde.Selected);
    Notify("Bitte einen Kunden auswählen!"; NotificationType.Error);
    IsBlank(txtNeuBetreff.Text);
    Notify("Bitte einen Betreff eingeben!"; NotificationType.Error);
    CountRows(colPositionen) = 0;
    Notify("Bitte mindestens eine Position hinzufügen!"; NotificationType.Error);
    true;
    Set(varNeuerBeleg;
        Patch(Faktura; Defaults(Faktura); {
            Titel: txtNeuBetreff.Text;
            BelegTyp: {Value: varNeuerBelegTyp};
            BelegNr: varNeueBelegNr;
            BelegDatum: dpNeuDatum.SelectedDate;
            KundenNr: {Id: cmbNeuKunde.Selected.ID; Value: Text(cmbNeuKunde.Selected.KundenNr)};
            Status: {Value: "Entwurf"};
            Gesamtbetrag: Coalesce(Sum(colPositionen; Positionspreis); 0);
            ZahlungszielTage: Value(txtNeuZahlungszielTage.Text);
            Zahlungsziel: DateAdd(dpNeuDatum.SelectedDate; Value(txtNeuZahlungszielTage.Text); TimeUnit.Days);
            Bemerkung: txtNeuBemerkung.Text
        })
    );;
    ForAll(colPositionen As pos;
        Patch(FakturaPositionen; Defaults(FakturaPositionen); {
            Titel: varNeueBelegNr & " / Pos " & Text(pos.Position);
            FakturaID: {Id: varNeuerBeleg.ID; Value: varNeueBelegNr};
            Position: pos.Position;
            Bezeichnung: pos.Bezeichnung;
            Beschreibung: pos.Beschreibung;
            Menge: pos.Menge;
            Einheit: {Value: pos.Einheit};
            Einzelpreis: pos.Einzelpreis;
            Positionspreis: pos.Positionspreis
        })
    );;
    Notify("Beleg " & varNeueBelegNr & " gespeichert!"; NotificationType.Success);;
    Navigate(ScrBelegListe; ScreenTransition.None)
)
```

### 4.5 Status-Workflow

```
Rechnungen:   Entwurf → Versendet → Bezahlt
Angebote:     Entwurf → Versendet → Angenommen / Abgelehnt
Alle:         Entwurf/Versendet → Storniert
```

### 4.6 Gesamtbetrag-Anzeige (ScrBelegDetail)

Verwendet lokale Variable `varDetailGesamt` statt direkt aus SharePoint zu lesen (Timing-Problem):

**ScrBelegDetail → OnVisible:**
```
Set(varPopupDetailPos; false);;
Set(varDetailGesamt; Coalesce(varAktuelleFaktura.Gesamtbetrag; 0))
```

**lblDetailGesamtWert → Text:**
```
Text(Coalesce(varDetailGesamt; 0); "#,##0.00 €")
```

Position hinzufügen/löschen aktualisiert `varDetailGesamt` manuell.

### 4.7 Gutschrift-Logik (btnGutschriftErstellen)

- Erstellt neue GU-Nummer
- Kopiert alle Positionen mit **negierten Beträgen**
- Setzt Original-Rechnung auf „Storniert"
- Navigiert zur neuen Gutschrift
- Sichtbar nur bei Rechnungen mit Status Versendet/Bezahlt

### 4.8 Kundenanzeige in Belegen

Überall wird der **Firmenname** (Titel) angezeigt, nicht der Ansprechpartner:
```
ThisItem.'KundenNr: Titel'.Value
```

---

## 5. Screen-Details – Wichtige Control-Namen

### 5.1 ScrBelegNeu – Popup-Controls

Popup-Controls auf ScrBelegNeu (Original):
- rectPopupHintergrund, rectPopup
- lblPopupTitel, lblPopupArtikel, cmbPopupArtikel
- lblPopupBezeichnung, txtPopupBezeichnung
- lblPopupBeschreibung, txtPopupBeschreibung
- lblPopupMenge, txtPopupMenge
- lblPopupEinheit, drpPopupEinheit
- lblPopupEinzelpreis, txtPopupEinzelpreis
- lblPopupSumme, lblPopupSummeWert
- btnPopupSpeichern, btnPopupAbbrechen
- Visible gesteuert durch: `varPopupPosition`

### 5.2 ScrBelegDetail – Popup-Controls (kopiert)

Popup-Controls auf ScrBelegDetail (Kopie, Suffix _BD):
- Alle Popup-Controls enden auf **_BD** (z.B. txtPopupBezeichnung_BD, cmbPopupArtikel_BD, drpPopupEinheit_BD)
- Visible gesteuert durch: `varPopupDetailPos`

### 5.3 ScrBelegDetail – Status-Buttons

| Button | Sichtbar wenn |
|--------|---------------|
| btnStatusVersendet | Status = "Entwurf" |
| btnStatusBezahlt | BelegTyp = "Rechnung" AND Status = "Versendet" |
| btnStatusStorniert | Status = "Entwurf" OR "Versendet" |
| btnStatusAngenommen | BelegTyp = "Angebot" AND Status = "Versendet" |
| btnStatusAbgelehnt | BelegTyp = "Angebot" AND Status = "Versendet" |
| btnGutschriftErstellen | BelegTyp = "Rechnung" AND Status = "Versendet" OR "Bezahlt" |
| btnPDFErstellen | Status <> "Entwurf" |
| btnPDFOeffnen | PDFLink nicht leer |
| btnDetailPosHinzu | Status = "Entwurf" OR "Versendet" |

### 5.4 ScrEinstellungen – Control-Namen

Felder mit Suffix "E" (z.B. txtEFirmenname, txtEInhaber, txtEStrasse, txtEPLZ, txtEOrt, txtELand)
Kontakt: txtETelefon, txtEMobil, txtEEMail, txtEWebseite
Bank: txtESteuernr, txtEUStIdNr, txtEBankname, txtEIBAN, txtEBIC
Rechnung: tglKleinuntern, txtEKleinText, txtEZahlungsziel, txtEWaehrung
Farbe: txtEPrimaerfarbe, rectFarbVorschau1/2/3

### 5.5 ScrKundeDetail – Control-Namen

txtFeldKundenNr, drpFeldAnrede, txtFeldVorname, txtFeldNachname, txtFeldFirma
txtFeldStrasse, txtFeldPLZ, txtFeldOrt, txtFeldTelefon, txtFeldMobil
txtFeldEMail, txtFeldWeb, txtFeldBemerkung, tglKundeAktiv

### 5.6 ScrArtikelDetail – Control-Namen

txtFeldArtikelNr, txtFeldArtikelName, txtFeldArtikelBez
txtFeldArtikelPreis, drpFeldArtikelEinheit, tglArtikelAktiv

### 5.7 Dashboard – KPI-Kacheln

5 Kacheln: Offene Rechnungen, Überfällige, Bezahlt (Monat), Offene Angebote, Jahresumsatz
3 Quick-Action-Buttons: Neue Rechnung, Neues Angebot, Neue Gutschrift
Gallery galLetzteBelege mit letzten Belegen

### 5.8 Galleries – interne Spaltennamen

Bei SortByColumns muss der **interne** SharePoint-Name verwendet werden:
- Titel-Spalte: `"Title"` (nicht "Titel")
- Benutzerdefinierte Spalten: normaler Name (z.B. "Nachname", "BelegDatum")

---

## 6. Power Automate Flow: Faktura-PDF-erstellen

### 6.1 Flow-Struktur

1. **Trigger:** PowerApps (V2) – Eingabe: FakturaID (Zahl)
2. **BelegAbrufen:** SharePoint – Element abrufen (Faktura, ID = FakturaID)
3. **KundeAbrufen:** SharePoint – Element abrufen (Kunden, ID = KundenNr.Id)
4. **EinstellungenAbrufen:** SharePoint – Elemente abrufen (Einstellungen, Top=1)
5. **PositionenAbrufen:** SharePoint – Elemente abrufen (FakturaPositionen, Filter: FakturaID/Id eq [BelegID], Sort: Position asc)
6. **PositionenHTMLInit:** Variable initialisieren (varPositionenHTML, Zeichenfolge, leer)
7. **PositionenSchleife:** Auf alle anwenden (body/value von PositionenAbrufen)
   - An Zeichenfolgenvariable anfügen (varPositionenHTML, HTML-Tabellenzeile)
8. **HTMLErstellen:** Verfassen (komplette HTML-Vorlage mit POSITIONEN_PLATZHALTER ersetzt durch varPositionenHTML)
9. **HTMLSpeichern:** OneDrive – Datei erstellen (/Faktura/temp/[BelegNr].html)
10. **PDFKonvertieren:** OneDrive – Datei konvertieren (HTML → PDF)
11. **PDFSpeichern:** OneDrive – Datei erstellen (/Faktura/[Jahr]/[BelegNr].pdf)
12. **HTMLLoeschen:** OneDrive – Datei löschen (temp-HTML)
13. **PDFLinkSpeichern:** SharePoint – Element aktualisieren (PDFLink = Pfad)
14. **Antwort:** Auf PowerApp antworten (PDFLink = Pfad von PDFSpeichern)

### 6.2 Einbindung in Power Apps

**btnPDFErstellen → OnSelect:**
```
Set(varPDFResult; 'Faktura-PDF-erstellen'.Run(varAktuelleFaktura.ID));;
Set(varAktuelleFaktura; LookUp(Faktura; ID = varAktuelleFaktura.ID));;
Notify("PDF erstellt!"; NotificationType.Success)
```

**btnPDFOeffnen → OnSelect:**
```
Launch(varAktuelleFaktura.PDFLink)
```

### 6.3 Status: Noch nicht getestet!

Der Flow ist erstellt und in Power Apps verbunden, aber noch nicht getestet.

---

## 7. Bekannte Besonderheiten / Lessons Learned

1. **Deutsche Syntax:** `;` statt `,`, `;;` statt `;` – überall!
2. **Filter-Bedingungen:** Mit `;` trennen oder `Or()`/`And()` verwenden, NICHT `&&`/`||`
3. **Nachschlagen-Zusatzspalten:** `'Spalte: Feld'.Value` (mit Hochkomma)
4. **Auswahl-Spalten** können NICHT als zusätzliche Spalten in Nachschlagen verwendet werden
5. **Sum() auf leere Liste** = Blank → immer `Coalesce(Sum(...); 0)` verwenden
6. **Toggle-Werte für SharePoint:** `If(toggle.Value; true; false)` statt direkt `.Value`
7. **Toggle Default:** `IfError(...)` verwenden wenn varEinstellungen noch nicht geladen
8. **Toggle:** `HandleHoverFill` existiert nicht als Eigenschaft
9. **DisplayMode:** Muss bei Texteingaben explizit auf `DisplayMode.Edit` stehen
10. **SortByColumns:** Verwendet internen SharePoint-Spaltennamen ("Title" statt "Titel")
11. **Collection-Schema:** Muss beim ersten ClearCollect mit Dummy-Record initialisiert werden
12. **SharePoint-Timing:** Gesamtbetrag über lokale Variable `varDetailGesamt` steuern
13. **Power Apps Namen:** Global eindeutig! Kopierte Controls bekommen Suffix (_1, _BD etc.)
14. **Dropdown Default:** Record erwartet: `{Value: varPosEinheit}` statt String
15. **OnVisible + Reset():** Felder beim Screen-Betreten zurücksetzen
16. **ForAll:** `As pos` Alias verwenden statt `ThisRecord` (zuverlässiger)
17. **Power Automate verbinden:** Links im Menü unter "..." → Power Automate

---

## 8. Aktueller Stand

### ✅ Fertig
- Phase 1: Alle 5 Listen mit Daten
- Phase 2: App-Grundgerüst, Farbsystem, Navigation
- Phase 3: Kunden CRUD + Validierung + Aktiv-Toggle
- Phase 3: Artikel CRUD + Validierung
- Phase 3: Einstellungen komplett (Firmendaten, Farbe, Toggle)
- Phase 4: ScrBelegListe (Filter, Suche, Status-Farben)
- Phase 4: ScrBelegNeu (Kopf + Positionen-Popup + Validierung)
- Phase 4: ScrBelegDetail (Anzeige, Positionen hinzufügen/löschen, Status-Buttons)
- Phase 4: Gutschrift-Logik
- Phase 6: ScrDashboard (KPIs, Quick-Actions, letzte Belege)
- Phase 5: Power Automate Flow erstellt + in App verbunden

### 🔲 Noch zu testen
- PDF-Erzeugung (Flow + Button)

### 🔮 Optionale Erweiterungen
- Angebot → Rechnung umwandeln
- PDF per E-Mail versenden
- Beleg bearbeiten (Kopfdaten ändern bei Entwurf)
- Wiederkehrende Rechnungen
- Mahnwesen
- DATEV-Export

---

## 9. Vereinbarungen für die Zusammenarbeit

1. **Sprache:** Deutsch, Du-Anrede
2. **Code:** Immer deutsche Power Apps Syntax (`;` statt `,`)
3. **Code-Blöcke:** Immer den GESAMTEN Code-Block angeben, nicht nur Teile
4. **Control + Eigenschaft:** Immer angeben, z.B. `btnSpeichern → OnSelect:`
5. **Neu vs. Ändern:** Klar unterscheiden: "Erstelle Beschriftung..." vs. "Ändere lblXY → Text:"
6. **Control-Typ:** Am Präfix erkennbar: lbl=Label, txt=Texteingabe, btn=Button, drp=Dropdown, tgl=Toggle, gal=Gallery, rect=Rechteck, cmb=ComboBox, dp=DatePicker
