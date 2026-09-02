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
3. `ssh ionos-crm4 "chown -R www-data:www-data /opt/faktura"`
4. `ssh ionos-crm4 "systemctl restart faktura"`

WICHTIG zu Schritt 3: `git pull` läuft als root, alle dabei geänderten Dateien
gehören danach root. Der Dienst läuft aber als `www-data` und kann sie dann nicht
mehr überschreiben — z.B. schlägt der Vorlagen-Upload mit `PermissionError` fehl,
sobald `git pull` eine Datei in `vorlagen/` angefasst hat. Deshalb nach jedem Pull
den chown ausführen.

Das Repo auf dem Server zieht per **SSH** (Deploy-Key), nicht per HTTPS —
sonst fragt `git pull` nach GitHub-Benutzername und bricht ab:

```
origin              git@github.com:certnetkassel/faktura.git
core.sshCommand     ssh -i ~/.ssh/github_brr_ts -o IdentitiesOnly=yes
```

Der Schlüssel `~/.ssh/github_brr_ts` liegt auf dem Server und hat Zugriff auf
das Repo. Bei einer Neuaufsetzung beides mit einrichten.

WICHTIG: Vorlagen und Logos, die der Anwender über die Weboberfläche hochlädt,
überschreiben die Dateien in `vorlagen/` bzw. `static/logos/` direkt auf dem
Server. Sie sind dann dort geändert bzw. neu, aber nicht im Git — der nächste
`git pull` bricht deshalb ab („would be overwritten"). Solche Uploads deshalb
per SCP zurückholen und einchecken (vor dem Aufräumen auf dem Server mit
`git hash-object` gegen die Repo-Version prüfen, damit nichts verloren geht).

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

### users
id, email (UNIQUE), password_hash, first_name, last_name, is_admin (0/1), created_at

Benutzerverwaltung (Mehrbenutzer). Angelegt in database.py (init_db + migrate_db).
`migrate_db()` zieht die Tabelle in bestehenden Datenbanken nach und legt beim
ersten Lauf den Startbenutzer `dirk@dirkhildebrand.de` (Admin) aus dem bisherigen
`settings.password_hash` an — das gewohnte Passwort bleibt also gültig, nur die
Anmeldung erfolgt jetzt mit E-Mail + Passwort. `settings.password_hash` wird vom
Login nicht mehr verwendet (Altlast, bleibt für die einmalige Migration stehen).

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

### email_templates
doc_type (PK: invoice/offer/credit/reminder), subject, body

Anpassbare E-Mail-Anschreiben je Belegart (Betreff + Text mit Platzhaltern).
Standardtexte in `database.py` (`EMAIL_TEMPLATE_DEFAULTS`), von `seed_email_templates()`
per `INSERT OR IGNORE` angelegt (in init_db + migrate_db, idempotent). `send_email`
lädt die Vorlage (`get_email_template`, Fallback auf die Defaults) und ersetzt die
Platzhalter (`apply_placeholders`). Verfügbare Platzhalter: `{{anrede}}`, `{{signatur}}`,
`{{betrag}}`, belegspezifisch `{{rechnung_nr}}`/`{{rechnung_datum}}`/`{{faellig_datum}}`,
`{{angebot_nr}}`/`{{angebot_datum}}`/`{{gueltig_bis}}`, `{{gutschrift_nr}}`/`{{gutschrift_datum}}`,
`{{mahnung_stufe}}`/`{{mahnung_frist}}`/`{{mahngebuehr}}`/`{{rechnung_faellig_datum}}`,
sowie **alle Einzelfelder zu Kunde und Absender** — dieselben Namen wie in den
Word-Vorlagen (`{{kunde_anrede}}`, `{{kunde_nachname}}`, `{{kunde_firma}}`,
`{{kunde_nr}}`, `{{kunde_strasse}}`, `{{kunde_plz}}`, `{{kunde_stadt}}`,
`{{kunde_email}}`, `{{kunde_telefon}}`, `{{inhaber}}`, `{{firma}}`,
`{{firma_strasse}}`, `{{firma_plz}}`, `{{firma_stadt}}`, `{{firma_telefon}}`,
`{{firma_email}}`, `{{steuernummer}}`, `{{bank}}`, `{{iban}}`, `{{bic}}`,
`{{kleinunternehmer}}`). Anrede und Grußformel lassen sich damit im Vorlagentext
selbst zusammenstellen, statt `{{anrede}}`/`{{signatur}}` zu verwenden.

Die Werte liefern `company_placeholders(s)` und `customer_placeholders(cust)` —
**eine Quelle für Word- und E-Mail-Vorlagen**, damit die Namen nicht wieder
auseinanderlaufen. Neue Felder deshalb dort ergänzen, nicht an zwei Stellen.
`{{anrede}}` (mail_anrede) und `{{signatur}}` (mail_signatur) bleiben als
zusammengesetzte Bausteine bestehen; die Grußformel "Mit freundlichen Grüßen"
steckt fest in `mail_signatur()`.
Bearbeiten unter `/email-vorlagen` (Speichern: `/email-vorlagen/save/<doc_type>`,
Zurücksetzen: `/email-vorlagen/reset/<doc_type>`). Nicht verwechseln mit den
**Word-Dokumentvorlagen** (`vorlagen/*.docx`, Menü „Dokumentvorlagen").

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
In einer Tabellenzelle platziert. `fill_positions()` sucht die Zeile mit dem Marker,
legt für jede Position eine **Kopie dieser Markerzeile** an (Pos/Bezeichnung/Menge/
Einheit/Einzelpreis/Gesamt) und entfernt die Markerzeile danach.

Wichtig für Änderungen an dieser Stelle:

- **Nicht `table.add_row()` und nicht `cell.text = ...` verwenden.** Beides
  verwirft die Formatierung der Vorlage — die Beträge wurden dadurch
  linksbündig. Text deshalb über `set_cell_text()` setzen: es schreibt in den
  vorhandenen Run und erhält Ausrichtung, Schrift und Rahmen.
- **`freeze_table_layout()` nagelt die Spaltenbreiten fest** (`tblLayout=fixed`,
  `tblGrid` aus den Breiten der Kopfzeile). Ohne das verteilt Word/LibreOffice
  die Spalten nach Inhalt neu (Autofit): die Pos.-Spalte wurde breit, die
  Zahlenspalten gequetscht. In den Vorlagen wich das `tblGrid` zusätzlich von
  den Zellbreiten ab (Spalte 1: 1219 statt 817 Twips).
- Spaltenbreiten der Vorlagen (Twips, Summe 9905 = 17,5 cm): Pos. 700,
  Beschreibung 4400, Menge 950, Einheit 1150, Einzelpreis 1450, Gesamt 1255.
  Enger sollten die vier rechten Spalten nicht werden, sonst brechen
  Überschriften und Beträge um.
- Die **Mahnungsvorlage hat keine Positionstabelle** (verweist auf die
  Rechnung) — dort passiert nichts, das ist kein Fehler.

Layoutänderungen immer am gerenderten PDF prüfen, nicht nur an der .docx:
`pdftoppm -png -r 110 output/<beleg>.pdf /tmp/x` auf dem Server und das Bild
ansehen — LibreOffice legt die Tabelle anders aus als python-docx vermuten lässt.

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

**WICHTIG – die App versendet Belege NICHT selbst.** Der Knopf ✉ an Rechnung,
Angebot, Gutschrift und Mahnung (`POST /draft-email/<doc_type>/<id>`, Funktion
`draft_email`) bereitet die E-Mail nur vor: Empfänger aus den Kundendaten,
Betreff und Anschreiben aus der E-Mail-Vorlage, Beleg als PDF im Anhang. Gesendet
wird **von Hand** nach Prüfung durch den Anwender. Das ist ausdrücklich so
gewünscht — nicht auf Direktversand zurückbauen. Zwei Wege, automatisch gewählt:

- **Entwurf im Postfach** (bevorzugt, nur bei `mail_method='graph'`):
  `create_graph_draft()` legt die Mail per `POST /users/{sender}/messages` im
  Ordner „Entwürfe" ab; die Belegliste zeigt danach nur die Meldung
  „E-Mail im Outlook-Ordner "Entwürfe" erstellt.". Bearbeitet wird der Entwurf
  im **Desktop-Outlook**. Bewusst wird NICHT auf Outlook im Web verlinkt oder
  weitergeleitet: dort ist womöglich ein anderes Konto angemeldet, der Anwender
  landete im falschen Postfach. Der `webLink` der Nachricht taugt ohnehin nicht
  zum Öffnen eines Entwurfs — im Lesemodus meldet Outlook „verschoben oder
  gelöscht", mit `viewmodel=ComposeMessageItem` „Diese Seite funktioniert im
  Moment nicht" (beides ausprobiert). Das braucht
  die Anwendungsberechtigung **Mail.ReadWrite** — `Mail.Send` allein genügt
  NICHT. Beide sind im Tenant erteilt (Stand 02.09.2026, mit Administrator-
  zustimmung); `graph_can_draft()` prüft das vorab am `roles`-Claim des
  Access-Tokens. Nach einer Berechtigungsänderung `systemctl restart faktura` —
  `_graph_token_cache` hält das alte Token sonst bis zu einer Stunde und die
  neue Rolle wirkt scheinbar nicht.
- **`.eml`-Datei zum Download** (Fallback und SMTP-Weg): `build_eml()` baut die
  Mail als MIME-Nachricht mit dem Header **`X-Unsent: 1`** — nur damit öffnet
  Outlook sie als noch nicht gesendeten Entwurf **mit Senden-Knopf** statt als
  empfangene Nachricht. Beim Download wird bewusst kein Flash gesetzt (er
  erschiene erst auf der nächsten Seite).

Weil noch nichts versendet ist, setzt `draft_email` den Belegstatus **nicht**
mehr automatisch auf „Gesendet" und schreibt **keinen** `email_log`-Eintrag; der
Status wird nach dem Senden per Dropdown in der Liste gesetzt. Echten Versand
macht nur noch der Testversand in den Einstellungen (`send_mail()` →
`send_mail_graph`/`send_mail_smtp`, bleibt bestehen).

**Anhang immer als PDF:** `build_pdf()` erzeugt das Dokument per
`build_document()` (→ .docx) und wandelt es mit `convert_to_pdf()` in ein **PDF**
um; angehängt wird ausschließlich das PDF, nie die .docx. Die Umwandlung nutzt
**LibreOffice headless** (`soffice --headless --convert-to pdf`, System­paket
`libreoffice`, auf dem Server unter `/usr/bin/soffice`). Gesucht wird die Binary
mit `find_soffice()`: `shutil.which()` allein reicht NICHT, weil die
systemd-Unit `PATH=/opt/faktura/venv/bin` setzt — im Dienst schlug die
Umwandlung deshalb mit „nicht gefunden" fehl, während sie auf der SSH-Shell mit
vollem PATH lief. Zusätzlich bekommt der soffice-Unterprozess per
`soffice_env()` einen um die Systempfade ergänzten PATH: `/usr/bin/soffice` ist
ein Shell-Skript und ruft `dirname`, `basename`, `ls` und `sed` auf, die es im
venv-PATH sonst nicht findet („dirname: not found").

Wer PDF-Funktionen testet, muss das im Dienst-Kontext tun, z.B.
`sudo -u www-data env -i PATH=/opt/faktura/venv/bin venv/bin/python ...`, **und
vorher `output/` leeren**: `convert_to_pdf()` löscht eine vorhandene PDF
gleichen Namens zwar inzwischen vor der Umwandlung (sonst gälte eine veraltete
Datei als Ergebnis und ein alter Beleg würde angehängt) — eine Datei aus einem
früheren Lauf hat einen Test aber schon einmal fälschlich grün aussehen lassen.
Die Umwandlung läuft mit einem eigenen
`UserInstallation`-Profil je Aufruf (www-data hat kein nutzbares HOME; vermeidet
auch das Single-Instance-Lock). Schlägt die Umwandlung fehl, entsteht keine Mail
(Flash-Fehler statt docx-Fallback).

Dieselbe Umwandlung nutzt der Knopf **„PDF generieren"** (`/generate-pdf/...`,
Funktion `generate_pdf`) neben **„Word generieren"** (`/generate/...`) — letzterer
liefert weiterhin bewusst die **.docx** zum Bearbeiten.

Hinweis: `Mail.Send` als Anwendungsberechtigung erlaubt den Versand aus allen
Postfächern des Tenants — Einschränkung per Exchange-Online
`New-ApplicationAccessPolicy` empfohlen (steht auch im (i)-Panel).

## Authentifizierung

- Mehrbenutzer-Login mit **E-Mail + Passwort** (Tabelle `users`)
- Passwort-Hash je Benutzer in `users.password_hash` (werkzeug.security)
- Session via Flask-Session (Cookie-basiert), speichert `session['user_id']`
- `login_required` prüft `session['user_id']`; `admin_required` zusätzlich
  `users.is_admin` (Nicht-Admins werden mit Flash aufs Dashboard geleitet)
- `current_user()` liefert die Row des angemeldeten Benutzers; per
  `context_processor` als `current_user` in allen Templates verfügbar
- SECRET_KEY ist fest in config.py (NICHT os.urandom!)
- Erststart (frische DB ohne Benutzer): der Login legt `dirk@dirkhildebrand.de`
  als ersten Admin mit dem eingegebenen Passwort an
- Benutzerverwaltung (nur Admins): `/users`, `/users/new`, `/users/<id>/edit`,
  `/users/<id>/delete`. Geschützt: letzter Admin kann weder gelöscht noch
  degradiert werden; Selbstlöschung verhindert. Gemeinsame Speicherlogik:
  `_save_user()` in app.py.
- „Mein Passwort ändern" in den Einstellungen ändert `users.password_hash` des
  angemeldeten Benutzers (nicht mehr `settings.password_hash`)

## Navigation (Sidebar in base.html)

Dashboard → Kunden → Artikel → Angebote → Rechnungen → Gutschriften → Mahnungen → Dokumentvorlagen → E-Mail-Vorlagen → Einstellungen → Benutzer (nur Admins)

## Features

- Dashboard mit KPIs (Kunden, offene Rechnungen, überfällige, Monatsumsatz)
- CRUD für Kunden, Artikel, Angebote, Rechnungen, Gutschriften
- Status-Workflow: Entwurf → Gesendet → Bezahlt/Überfällig
- Automatische Überfällig-Markierung bei abgelaufenem Fälligkeitsdatum
- Angebot → Rechnung umwandeln (kopiert Positionen)
- Mahnwesen (mehrstufig, mit Mahngebühr)
- Word-Dokumentgenerierung aus Vorlagen, wahlweise Download als .docx oder PDF
- E-Mail-Vorbereitung mit PDF-Anhang (Entwurf im Postfach oder .eml-Datei) —
  gesendet wird von Hand; echter Versand nur beim Testversand
- Dokumentvorlagen-Verwaltung (Word: Upload, Download, Muster mit Beispieldaten)
- E-Mail-Vorlagen je Belegart mit Platzhaltern anpassbar (Betreff + Text)
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
- Bei Änderungen an Templates (Jinja2/HTML) ebenfalls `systemctl restart faktura`:
  Gunicorn läuft ohne Debug, Jinja2 cacht die kompilierten Templates im
  Worker-Speicher und prüft die Datei nicht bei jedem Request. Ohne Neustart
  liefern die Worker weiter die ALTE Vorlage, obwohl die Datei auf der Platte neu ist.
- Bei reinen CSS-Änderungen reicht ein Hard-Refresh im Browser (Strg+Shift+R);
  die Datei wird als statisches File direkt ausgeliefert (kein Template-Cache).

## Offene Punkte / Geplante Erweiterungen

- DATEV-Export
- Wiederkehrende Rechnungen
