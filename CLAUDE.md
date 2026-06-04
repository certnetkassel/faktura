# CLAUDE.md – TenantPlus

## Projektbeschreibung
TenantPlus ist eine Web-App zur Verwaltung von Microsoft 365-Tenants.
Betreiber: CERTNET GmbH, Kassel (Dirk Hildebrand).
Einsatz: Intern fuer Dienstleistungen beim Kunden, spaeter als verkaufbares Produkt.

Die App kombiniert:
- Microsoft Graph API fuer Datenzugriff und Verwaltungsaktionen
- Eine PowerShell-Skript-Bibliothek: Skripte werden parametrisiert und als .ps1-Datei zum Download bereitgestellt. Ausfuehrung erfolgt lokal durch den Administrator.

---

## Tech-Stack
- **Backend:** Node.js / Express
- **Datenbank:** PostgreSQL (Datenbankname: tenantplus)
- **Frontend:** HTML / CSS / JavaScript (Vanilla) – kein Framework
- **MS 365:** Microsoft Graph API, Client Credentials Flow, pro Tenant eigene App Registration
- **PowerShell:** Skript-Vorlagen unter /scripts/, parametrisiert, Download als .ps1
- **E-Mail:** IONOS SMTP (nodemailer)
- **Deployment:** Coolify Auto-Deploy, Docker, GitHub Push zu certnetkassel/tenantplus
- **Server:** 82.165.190.147, Rocky Linux 9, tenantplus.certnet.eu
- **Lokaler Pfad:** P:\Projekte\TenantPlus

---

## Datenbankschema
```sql
-- Tenants
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    admin_email VARCHAR(255),
    admin_name VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Azure App Registrations pro Tenant
CREATE TABLE tenant_app_registrations (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    client_id VARCHAR(255),
    client_secret TEXT,
    tenant_id_azure VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Benutzer
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    display_name VARCHAR(255),
    upn VARCHAR(255),
    private_email VARCHAR(255),
    azure_object_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    delete_reminder_date TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Gruppen
CREATE TABLE groups (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    name VARCHAR(255),
    azure_object_id VARCHAR(255)
);

-- Lizenzen
CREATE TABLE licenses (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    sku_id VARCHAR(255),
    sku_part_number VARCHAR(255),
    total INTEGER,
    consumed INTEGER,
    last_synced TIMESTAMP
);

-- MS Teams
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    name VARCHAR(255),
    azure_object_id VARCHAR(255),
    template VARCHAR(255)
);

-- Kanaele
CREATE TABLE channels (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    name VARCHAR(255),
    azure_object_id VARCHAR(255)
);

-- Erinnerungen
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    reminder_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',
    extension_months INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- PowerShell-Skripte
CREATE TABLE powershell_scripts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    category VARCHAR(100),
    template TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Projektstruktur
```
/
├── src/
│   ├── routes/             # Express-Routen (eine Datei pro Modul)
│   ├── db/                 # Datenbankabfragen (eine Datei pro Modul)
│   ├── middleware/         # Auth, Session, Logging
│   └── graph/              # Graph API Hilfsfunktionen (token.js, users.js etc.)
├── public/
│   ├── css/                # Stylesheets
│   └── js/                 # Client-seitiges JavaScript
├── views/                  # HTML-Templates (EJS oder statische HTML)
├── scripts/                # PowerShell-Skript-Vorlagen (.ps1)
├── .env                    # Nicht in Git
├── .gitignore
├── package.json
├── server.js
└── README.md
```

---

## Umgebungsvariablen (.env)
```
PORT=3000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tenantplus
DB_USER=
DB_PASS=
SESSION_SECRET=
SMTP_HOST=smtp.ionos.de
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
```

---

## Graph API
- Authentifizierung: Client Credentials Flow (kein Benutzer-Login noetig)
- Token-Verwaltung: pro Tenant, gecacht bis Ablauf
- Wichtige Endpunkte:
  - GET /users – Benutzer auflisten
  - POST /users – Benutzer anlegen
  - GET /subscribedSkus – Lizenzen auslesen
  - POST /groups – Gruppe anlegen
  - POST /teams – Team anlegen
  - POST /teams/{id}/channels – Kanal anlegen
- Admin Consent: muss einmalig pro Tenant vom dortigen Admin erteilt werden

---

## PowerShell-Skripte

### Konzept
PowerShell laeuft NICHT auf dem Server (Rocky Linux 9). Die App generiert nur die Skript-Datei.
Ausfuehrung erfolgt ausschliesslich lokal auf dem Windows-PC des Administrators.

### Ablauf
1. Administrator waehlt ein Skript in der App aus
2. Gibt die benoetigten Parameter ein (z.B. Tenant, Benutzername, Lizenz)
3. App setzt Platzhalter in der Vorlage ein und stellt .ps1-Datei zum Download bereit
4. Administrator laedt die Datei herunter
5. Administrator fuehrt die Datei lokal in PowerShell aus – dort wo er Global Admin ist

### Vorteile dieses Konzepts
- Keine PowerShell-Abhaengigkeit auf dem Server
- Keine Admin-Credentials muessen auf dem Server gespeichert werden
- Administrator sieht und prueft das Skript vor der Ausfuehrung
- Funktioniert mit jedem Tenant wo der Administrator Zugang hat

### Technische Umsetzung
- Vorlagen liegen unter /scripts/ als .ps1-Dateien mit Platzhaltern (z.B. {{UPN}}, {{TENANT_DOMAIN}})
- Server-Route liest Vorlage, ersetzt Platzhalter per String-Replace, sendet Datei als Download
- Content-Type: application/octet-stream, Dateiname: [skriptname]-[datum].ps1
- Kategorien: Benutzer, Lizenzen, Teams, Bereinigung

---

## Arbeitsanweisungen fuer Claude Code

### Sprache
- Alle Antworten, Erklaerungen und Commit-Messages auf Deutsch
- Kommentare im Code auf Deutsch

### Code
- Immer vollstaendigen Code liefern – keine Snippets, keine Diff-Auszuege
- Nach jeder Aenderung sofort committen und pushen
- Commit-Messages kurz und auf Deutsch (z.B. "Tenant-CRUD hinzugefuegt")

### Stil
- Express-Routen modular (eine Datei pro Modul unter src/routes/)
- Datenbankabfragen unter src/db/ (keine SQL direkt in Routen)
- Fehlerbehandlung mit try/catch in allen async-Funktionen
- Keine node_modules in Git (.gitignore beachten)
- .env nie in Git

### Datenbank
- Kein ORM – reines SQL mit pg (node-postgres)
- Verbindung ueber .env-Variablen
- Credentials nie im Klartext im Code

### Deployment
- Coolify Auto-Deploy via GitHub Push
- Nach Push laeuft npm install automatisch im Container
- Kein manuelles Deployment noetig

---

## Offene TODOs (Entwicklungsreihenfolge)
1. Datenbankschema anlegen (Migration-Skript)
2. server.js Grundgeruest mit Session und Middleware
3. Tenant-Verwaltung (CRUD)
4. Graph API Token-Verwaltung
5. Benutzer anlegen und aus Excel importieren
6. Gruppen und Lizenzzuweisung
7. Teams und Kanaele
8. PowerShell-Skript-Download
9. E-Mail-Versand Zugangsdaten
10. Erinnerungs-Cron-Job (5 Monate)
