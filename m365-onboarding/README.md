# M365-Onboarding-Tool

Ein webbasiertes Self-Service-Werkzeug, mit dem sich Kundenpersonal mit dem
eigenen Microsoft-365-Account anmeldet (OAuth 2.0 Authorization Code Flow,
**delegiert**) und über ein einfaches Formular neue Benutzer im
Microsoft-365-Tenant anlegt:

- Eingabe von Vorname, Nachname und privater E-Mail-Adresse
- automatische Bildung des Anmeldenamens als `vorname.nachname@domain`
- Zuweisung einer ausgewählten Lizenz (nur SKUs mit freien Einheiten)
- Versand der Zugangsdaten samt Initial-Passwort an die private Adresse
- Audit-Log in PostgreSQL (**ohne** Speicherung der privaten E-Mail-Adresse)

## Voraussetzungen

- Node.js ≥ 20 (von `@azure/msal-node` v5 vorausgesetzt; nutzt das eingebaute `fetch`)
- PostgreSQL-Datenbank
- SMTP-Zugang (z. B. IONOS) für den Mailversand
- Eine Azure/Entra App-Registration (siehe unten)

## Setup

> Ausführliche Schritt-für-Schritt-Anleitung (inkl. Azure/Entra-App-Registration
> und Fehlerbehebung): siehe [`docs/EINRICHTUNG.md`](./docs/EINRICHTUNG.md).
>
> An mehreren Rechnern arbeiten (Notebook ↔ Mini-PC ↔ Office) ohne
> OneDrive-Sync des Codes: siehe [`docs/GERAETEWECHSEL.md`](./docs/GERAETEWECHSEL.md).
>
> Schnellstart für die ersten drei Schritte (GitHub-Repo, Entra-App, DNS)
> mit Abhak-Liste: siehe [`docs/START_AN_DER_ARBEIT.md`](./docs/START_AN_DER_ARBEIT.md).

1. **Abhängigkeiten installieren**

   ```bash
   npm install
   ```

2. **Konfiguration anlegen** – `.env` aus der Vorlage erstellen und ausfüllen:

   ```bash
   cp .env.example .env
   # anschließend .env mit echten Werten befüllen
   ```

3. **Datenbankschema einspielen** (Audit-Log + Session-Tabelle):

   ```bash
   psql "$DATABASE_URL" -f db/schema.sql
   ```

4. **Preflight-Check** (prüft Umgebungsvariablen, DB-Verbindung und Tabellen):

   ```bash
   npm run check
   ```

5. **Starten**

   ```bash
   npm start
   ```

   Standardmäßig läuft die Anwendung auf dem in `PORT` konfigurierten Port
   (Vorgabe: 3000).

### Lokale PostgreSQL per Docker (optional)

Für die lokale Entwicklung liegt ein `docker-compose.yml` bei, das eine
PostgreSQL startet und das Schema automatisch einspielt:

```bash
docker compose up -d db
```

Verbindungs-URL: `postgres://m365:m365@localhost:5432/m365onboarding`

## Umgebungsvariablen

Alle Geheimnisse werden ausschließlich über Umgebungsvariablen gesetzt. Siehe
[`.env.example`](./.env.example):

| Variable        | Bedeutung                                                        |
|-----------------|------------------------------------------------------------------|
| `PORT`          | Port des Express-Servers                                         |
| `SESSION_SECRET`| Geheimnis zur Signierung der Session-Cookies                    |
| `TENANT_ID`     | Verzeichnis-(Mandanten-)ID des Tenants                          |
| `CLIENT_ID`     | Anwendungs-(Client-)ID der App-Registration                    |
| `CLIENT_SECRET` | Client-Secret der App-Registration                              |
| `REDIRECT_URI`  | Redirect-URI (exakt wie in der App-Registration hinterlegt)    |
| `GRAPH_SCOPES`  | angeforderte Graph-Scopes (durch Leerzeichen getrennt)         |
| `DATABASE_URL`  | PostgreSQL-Verbindungs-URL                                       |
| `SMTP_HOST`     | SMTP-Server (z. B. `smtp.ionos.de`)                            |
| `SMTP_PORT`     | SMTP-Port (587 für STARTTLS, 465 für implizites TLS)           |
| `SMTP_USER`     | SMTP-Benutzer                                                    |
| `SMTP_PASS`     | SMTP-Passwort                                                    |
| `MAIL_FROM`     | Absenderadresse der Willkommensmails                            |

## Deployment auf dem Server

Für das Ausrollen auf einem Ubuntu-Server (Subdomain `onboarding.certnet.eu`,
nginx + systemd + PostgreSQL + Let's Encrypt) gibt es ein vollständiges
Runbook samt Konfigurationsvorlagen im Verzeichnis [`deploy/`](./deploy):

- [`deploy/DEPLOYMENT.md`](./deploy/DEPLOYMENT.md) – Schritt-für-Schritt-Anleitung
- [`deploy/nginx-onboarding.conf`](./deploy/nginx-onboarding.conf) – nginx-Reverse-Proxy
- [`deploy/m365-onboarding.service`](./deploy/m365-onboarding.service) – systemd-Unit
- [`deploy/env.production.example`](./deploy/env.production.example) – Produktions-`.env`-Vorlage

## Azure / Entra App-Registration

Die App muss als **Web**-Anwendung registriert sein, mit der oben gesetzten
`REDIRECT_URI` (z. B. `https://onboarding.example.de/auth/callback`) und einem
Client-Secret.

### Benötigte Microsoft-Graph-Scopes (delegiert)

Folgende **delegierten** Berechtigungen sind erforderlich (mit
Administrator-Zustimmung, wo nötig):

- `User.ReadWrite.All` – Benutzer anlegen
- `LicenseAssignment.ReadWrite.All` – Lizenzen zuweisen
- `Organization.Read.All` – abonnierte SKUs / Lizenzbestände lesen
- `User.Read` – Profil des angemeldeten Mitarbeiters
- `openid`, `profile`, `offline_access` – OpenID Connect / Token-Refresh

### Erforderliche Entra-Rolle des anmeldenden Personals

Da der Flow **delegiert** arbeitet, handelt das Tool im Namen der angemeldeten
Person. Diese benötigt im Tenant eine passende Entra-Rolle, damit das Anlegen
von Benutzern und das Zuweisen von Lizenzen erlaubt ist:

- **User Administrator** (empfohlen, deckt beides ab)

oder alternativ kombiniert:

- **Directory Writers** (Benutzer anlegen) **und**
- **License Administrator** (Lizenzen zuweisen)

Ohne ausreichende Rolle schlägt das Anlegen mit einem Berechtigungsfehler
(HTTP 403) fehl.

## Sicherheit & Datenschutz

- Geheimnisse stehen ausschließlich in der `.env` (nicht im Git).
- Das Initial-Passwort wird zufällig erzeugt (mind. 16 Zeichen, alle
  Komplexitätskategorien) und muss bei der ersten Anmeldung geändert werden
  (`forceChangePasswordNextSignIn`).
- Die private E-Mail-Adresse wird **nicht** gespeichert; im Audit-Log steht nur
  das Flag `mail_versendet`.

## Lizenzhinweis

Internes Werkzeug – ohne gesonderte Lizenzangabe.
