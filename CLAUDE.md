# Faktura (Micro-Fakt 1.0)

Rechnungssystem für das Einzelunternehmen "Dirk Hildebrand - App Entwicklung" als Kleinunternehmer (§19 UStG).

## Sprache

Alle Antworten, Erklärungen, Commit-Messages und Code-Kommentare auf Deutsch. Code-Änderungen IMMER sofort committen und pushen.

## Tech-Stack

- **Backend:** Python 3 / Flask
- **Datenbank:** SQLite (`faktura.db` im Projektverzeichnis)
- **Templating:** Jinja2
- **CSS:** Eigenes CSS mit Dark/Light Theme (`static/style.css`)
- **Dokumentgenerierung:** python-docx (Word-Vorlagen mit Platzhaltern)
- **E-Mail:** Microsoft Graph (`requests`, Client-Credentials) oder SMTP (smtplib)
- **Webserver:** Gunicorn (2 Worker) hinter nginx
- **Prozessmanagement:** systemd

## Deployment

- **Server:** IONOS VPS 82.165.29.152 (Ubuntu)
- **App-Pfad:** `/opt/faktura`
- **User:** `www-data`
- **Python venv:** `/opt/faktura/venv`
- **Service:** `faktura.service` (`systemctl restart faktura`)
- **SSL:** Let's Encrypt
- **URL:** https://faktura.dirkhildebrand.de
- **Domain:** dirkhildebrand.de (alter Server, 82.165.29.152)

### SSH-Zugang

Konfiguriert in `~/.ssh/config` als Host `ionos-crm4`:

```
Host ionos-crm4
    HostName 82.165.29.152
    User root
    IdentityFile C:\Users\DirkHildebrand\.ssh\id_ed25519
```

Verbindung also einfach per `ssh ionos-crm4`.

### Deploy-Workflow

1. Lokal ändern und committen/pushen
2. Per SSH auf Server: `ssh ionos-crm4 "cd /opt/faktura && git pull"`
3. `ssh ionos-crm4 "systemctl restart faktura"`

Alternativ: Dateien per SCP hochladen:
```bash
scp <datei> ionos-crm4:/opt/faktura/<datei>
```

## GitHub

- **Repository:** https://github.com/certnetkassel/faktura (private)
- **Organisation:** certnetkassel
- **Branch:** main

## Lokaler Projektpfad

```
W:\Micro-Fakt
```

W: ist per `subst` ein Alias auf den OneDrive-Ordner "01 Claude" und damit auf
allen Rechnern derselbe Pfad. Gemappt wird per Batch-Skript in `W:\`:

- Arbeits-PC: `Laufwerk-W-mappen_PC_Arbeit.bat` → `C:\Users\DirkHildebrand\OneDrive - CERTNET GmbH\01 Claude`
- Mini-PC: `Laufwerk-W-mappen_Mini_PC.bat` → `C:\Users\Dirk Mini-PC\OneDrive - CERTNET GmbH\01 Claude`

WICHTIG: Git-Repos NIEMALS auf rclone-gemounteten Laufwerken (P:\) betreiben.
W: ist davon nicht betroffen (lokaler subst-Alias, kein Netz-/rclone-Mount).

## Projektstruktur

```
/opt/faktura/
├── app.py              # Hauptanwendung (Flask-Routes, alle Endpoints)
├── config.py           # Konfiguration (SECRET_KEY, Pfade)
├── database.py         # DB-Schema und Initialisierung
├── create_templates.py # Generiert Beispiel-Vorlagen (python-docx)
├── requirements.txt    # Python-Abhängigkeiten
├── faktura.db          # SQLite-Datenbank (NICHT im Git)
├── static/
│   ├── style.css       # Komplettes CSS (Dark/Light Theme)
│   └── logos/          # Logo-Dateien (Dark + Light Variante)
├── templates/          # Jinja2-Templates
│   ├── base.html       # Layout mit Sidebar-Navigation
│   ├── login.html      # Login-Seite (Micro-Fakt 1.0 Branding)
│   ├── dashboard.html  # Dashboard mit KPIs
│   ├── customers.html  # Kundenliste
│   ├── customer_form.html
│   ├── articles.html   # Artikelliste
│   ├── article_form.html
│   ├── invoices.html   # Rechnungsliste
│   ├── invoice_form.html
│   ├── offers.html     # Angebotsliste
│   ├── offer_form.html
│   ├── credits.html    # Gutschriftenliste
│   ├── credit_form.html
│   ├── reminders.html  # Mahnungsliste
│   ├── reminder_form.html
│   ├── settings.html   # Einstellungen
│   └── vorlagen.html   # Vorlagenverwaltung
├── vorlagen/           # Word-Vorlagen mit Platzhaltern
│   ├── vorlage_rechnung.docx
│   ├── vorlage_angebot.docx
│   ├── vorlage_gutschrift.docx
│   └── vorlage_mahnung.docx
└── output/             # Generierte Dokumente (temporär)
```

## Datenbank-Schema (SQLite)

### settings (id=1, Singleton)
company_name, owner_name, street, zip, city, phone, email, tax_number, bank_name, iban, bic, smtp_host, smtp_port, smtp_user, smtp_pass, smtp_from, mail_method, graph_tenant_id, graph_client_id, graph_client_secret, graph_sender, graph_save_sent, password_hash, kleinunternehmer_text, invoice_prefix, offer_prefix, credit_prefix, next_invoice_nr, next_offer_nr, next_credit_nr, logo_dark, logo_light, logo_width_cm, logo_sidebar_px

Nachträglich ergänzte Spalten werden von `migrate_db()` in database.py per
`ALTER TABLE` nachgezogen (Liste `SETTINGS_MIGRATIONS`). Die Funktion läuft beim
Import von app.py, weil unter Gunicorn der `__main__`-Block nicht ausgeführt wird.
Neue Settings-Spalten deshalb IMMER zusätzlich dort eintragen.

### customers
id, customer_nr (Text, z.B. K-0001), company, salutation, first_name, last_name, street, zip, city, email, phone, notes

### articles
id, article_nr (Text, z.B. A-0001), name, description, unit (Stunde/Pauschale/pro Monat), price

### invoices
id, invoice_nr (Text, z.B. RE-2604001), customer_id (FK→customers), offer_id (FK→offers, optional), date, due_date, status (Entwurf/Gesendet/Bezahlt/Überfällig/Storniert), notes, total, created_at

### invoice_items
id, invoice_id (FK→invoices), position (int), description, quantity, unit, price, total

### offers
id, offer_nr (Text, z.B. AN-2604001), customer_id (FK→customers), date, valid_until, status (Entwurf/Gesendet/Angenommen/Abgelehnt), notes, total, created_at

### offer_items
id, offer_id (FK→offers), position, description, quantity, unit, price, total

### credits
id, credit_nr (Text, z.B. GU-2604001), customer_id (FK→customers), invoice_id (FK→invoices, optional), date, notes, total, created_at

### credit_items
id, credit_id (FK→credits), position, description, quantity, unit, price, total

### reminders
id, invoice_id (FK→invoices), level (int, Mahnstufe), date, due_date, fee, notes

### email_log
id, doc_type, doc_id, recipient, subject, sent_at

## Belegnummer-Format

`PREFIX-YYMM###` (z.B. RE-2604001 = Rechnung, April 2026, lfd. Nr. 1)
- Rechnung: RE-
- Angebot: AN-
- Gutschrift: GU-
- Prefixe konfigurierbar in Settings

## Dokumentgenerierung

Word-Vorlagen liegen in `/opt/faktura/vorlagen/`. Die App ersetzt Platzhalter in doppelten geschweiften Klammern per python-docx:

### Platzhalter (alle Vorlagen)
**Firma:** {{firma}}, {{inhaber}}, {{firma_strasse}}, {{firma_plz}}, {{firma_stadt}}, {{firma_telefon}}, {{firma_email}}, {{steuernummer}}, {{bank}}, {{iban}}, {{bic}}, {{kleinunternehmer}}

**Kunde:** {{kunde_firma}}, {{kunde_anrede}}, {{kunde_vorname}}, {{kunde_nachname}}, {{kunde_strasse}}, {{kunde_plz}}, {{kunde_stadt}}, {{kunde_nr}}, {{kunde_email}}, {{kunde_telefon}}

**Logo:** {{logo}} (Bild-Platzhalter, siehe unten)

### Platzhalter (dokumentspezifisch)
- **Rechnung:** {{rechnung_nr}}, {{rechnung_datum}}, {{faellig_datum}}, {{gesamtbetrag}}, {{notizen}}, {{positionen}}
- **Angebot:** {{angebot_nr}}, {{angebot_datum}}, {{gueltig_bis}}, {{gesamtbetrag}}, {{notizen}}, {{positionen}}
- **Gutschrift:** {{gutschrift_nr}}, {{gutschrift_datum}}, {{gesamtbetrag}}, {{notizen}}, {{positionen}}
- **Mahnung:** {{mahnung_stufe}}, {{mahnung_datum}}, {{mahnung_frist}}, {{mahngebuehr}}, {{rechnung_nr}}, {{rechnung_datum}}, {{rechnung_faellig_datum}}, {{rechnung_betrag}}, {{gesamtbetrag}} (= Rechnung + Mahngebühr), {{notizen}}, {{positionen}} (Positionen der gemahnten Rechnung)

### {{positionen}}-Marker
In einer Tabellenzelle platziert. Die App sucht nach diesem Marker, löscht ihn und fügt dynamisch Zeilen mit Pos/Bezeichnung/Menge/Einheit/Einzelpreis/Gesamt hinzu.

### {{logo}}-Marker (Bild)
Wird durch das in den Einstellungen hinterlegte Logo als Inline-Bild ersetzt (python-docx `run.add_picture`). Verwendet wird die helle Variante (`logo_light`, für weißen Hintergrund), Fallback `logo_dark`. Die Breite stellt der Anwender in den Einstellungen per Schieberegler ein
(`settings.logo_width_cm`, 1–10 cm, Standard 4 cm = `LOGO_WIDTH_CM` in app.py als Fallback);
das Seitenverhältnis bleibt erhalten. Funktioniert in Body, Tabellen und Kopf-/Fußzeilen, auch wenn Word den Marker über mehrere Runs zerrissen hat. Ist kein Logo hinterlegt, wird der Marker-Text einfach entfernt (kein sichtbares `{{logo}}`).

## E-Mail-Versand

Zwei Verfahren, umschaltbar in den Einstellungen (`settings.mail_method`):

- **`graph` (empfohlen):** Microsoft Graph, App-Registrierung im Entra Admin Center
  mit der **Anwendungsberechtigung Mail.Send** und erteilter Administratorzustimmung.
  Token per Client-Credentials-Flow von
  `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token` (Scope
  `https://graph.microsoft.com/.default`), Versand per
  `POST https://graph.microsoft.com/v1.0/users/{postfach}/sendMail`. Anhänge werden
  inline als base64 übertragen (Limit 3 MB, `GRAPH_MAX_ATTACHMENT_BYTES`). Das Token
  wird je (Tenant, Client-ID) im Prozess zwischengespeichert (`_graph_token_cache`).
  Benötigte Einstellungen: Verzeichnis-ID, Anwendungs-ID, Client-Secret,
  Absender-Postfach (Fallback: `smtp_from`, dann `email`).
- **`smtp`:** klassisch über smtplib mit STARTTLS.

Beide laufen über `send_mail(s, empfänger, betreff, text, anhänge)` in app.py.
Die Schritt-für-Schritt-Anleitung für das Entra Admin Center steckt als (i)-Panel
in `templates/settings.html`. Testversand: `POST /settings/test-mail` (Button in den
Einstellungen, nutzt die **gespeicherten** Werte).

Hinweis: `Mail.Send` als Anwendungsberechtigung erlaubt den Versand aus allen
Postfächern des Tenants — Einschränkung per Exchange-Online
`New-ApplicationAccessPolicy` empfohlen (steht auch im (i)-Panel).

## Authentifizierung

- Einfaches Passwort-Login (kein Benutzername, Single-User)
- Passwort-Hash in settings.password_hash (werkzeug.security)
- Session via Flask-Session (Cookie-basiert)
- SECRET_KEY ist fest in config.py (NICHT os.urandom!)
- Beim ersten Start wird das Passwort gesetzt

## Navigation (Sidebar in base.html)

Dashboard → Kunden → Artikel → Angebote → Rechnungen → Gutschriften → Mahnungen → Vorlagen → Einstellungen

## Features

- Dashboard mit KPIs (Kunden, offene Rechnungen, überfällige, Monatsumsatz)
- CRUD für Kunden, Artikel, Angebote, Rechnungen, Gutschriften
- Status-Workflow: Entwurf → Gesendet → Bezahlt/Überfällig
- Automatische Überfällig-Markierung bei abgelaufenem Fälligkeitsdatum
- Angebot → Rechnung umwandeln (kopiert Positionen)
- Mahnwesen (mehrstufig, mit Mahngebühr)
- Word-Dokumentgenerierung aus Vorlagen
- E-Mail-Versand (Microsoft Graph oder SMTP, mit Dokument als Anhang) inkl. Testversand
- Vorlagenverwaltung (Upload, Download, Muster mit Beispieldaten)
- Dark/Light Theme
- Logo-Upload (Dark + Light Variante)
- Logo-Größe per Schieberegler einstellbar: beide regeln die BREITE, damit die
  Werte vergleichbar sind — Dokument (1–10 cm) und Seitenleiste (60–240 px,
  240 px = Sidebar-Breite). Beide Vorschauen sind 1:1 gezeichnet.
- Responsive (mobile Sidebar mit Toggle)

## Bekannte Hinweise

- SQLite-Datenbank (faktura.db) ist NICHT im Git (.gitignore)
- Output-Ordner (generierte Dokumente) ist NICHT im Git
- venv und __pycache__ sind NICHT im Git
- Gunicorn läuft mit 2 Workern — SECRET_KEY MUSS fest sein (nicht os.urandom)
- Bei Änderungen an app.py oder config.py immer `systemctl restart faktura`
- Bei Änderungen an Templates oder CSS reicht meist ein Browser-Refresh (Strg+Shift+R)

## Offene Punkte / Geplante Erweiterungen

- DATEV-Export
- Wiederkehrende Rechnungen
