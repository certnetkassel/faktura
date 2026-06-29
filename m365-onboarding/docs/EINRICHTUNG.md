# Einrichtung – Schritt für Schritt (zum Weiterarbeiten)

Diese Anleitung führt von „frisch ausgecheckt“ bis „läuft lokal und legt einen
Testbenutzer an“. Plane für die Erst-Einrichtung ca. 30–45 Minuten ein,
hauptsächlich für die Azure/Entra-App-Registration.

Checkliste-Reihenfolge:

1. [Repo & Abhängigkeiten](#1-repo--abhängigkeiten)
2. [PostgreSQL bereitstellen](#2-postgresql-bereitstellen)
3. [Azure/Entra App-Registration](#3-azureentra-app-registration)
4. [.env ausfüllen](#4-env-ausfüllen)
5. [Preflight-Check & Start](#5-preflight-check--start)
6. [Funktionstest](#6-funktionstest)
7. [Fehlerbehebung](#7-fehlerbehebung)

---

## 1. Repo & Abhängigkeiten

```bash
cd m365-onboarding
npm install
```

Node.js ≥ 18 ist erforderlich (das eingebaute `fetch` wird genutzt). Prüfen mit
`node --version`.

---

## 2. PostgreSQL bereitstellen

Du brauchst eine erreichbare PostgreSQL-Datenbank. Zwei Wege:

### Variante A: Schnell per Docker (empfohlen für lokale Entwicklung)

Im Projekt liegt ein `docker-compose.yml`, das nur eine PostgreSQL startet:

```bash
docker compose up -d db
```

Die Datenbank ist dann erreichbar unter:

```
postgres://m365:m365@localhost:5432/m365onboarding
```

### Variante B: Bestehende PostgreSQL

Lege eine leere Datenbank an und notiere die Verbindungs-URL für `DATABASE_URL`.

### Schema einspielen (beide Varianten)

```bash
psql "postgres://m365:m365@localhost:5432/m365onboarding" -f db/schema.sql
```

Das legt die Tabellen `onboarding_log` und `session` an.

---

## 3. Azure/Entra App-Registration

Im [Entra Admin Center](https://entra.microsoft.com) bzw.
[Azure Portal](https://portal.azure.com) → **App-Registrierungen** →
**Neue Registrierung**.

1. **Name:** z. B. `M365-Onboarding-Tool`.
2. **Unterstützte Kontotypen:** „Nur Konten in diesem Organisationsverzeichnis“
   (Single Tenant).
3. **Redirect-URI:** Plattform **Web** auswählen und exakt die URL eintragen,
   die später auch in `REDIRECT_URI` steht, z. B.
   - lokal: `http://localhost:3000/auth/callback`
   - produktiv: `https://onboarding.example.de/auth/callback`
4. **Registrieren** klicken.

Nach dem Anlegen notieren (Übersichtsseite):

- **Anwendungs-(Client-)ID** → `CLIENT_ID`
- **Verzeichnis-(Mandanten-)ID** → `TENANT_ID`

### Client-Secret erstellen

**Zertifikate & Geheimnisse** → **Neuer geheimer Clientschlüssel** → Ablauf
wählen → **Hinzufügen**. Den **Wert** (nicht die Secret-ID!) sofort kopieren →
`CLIENT_SECRET`. Er wird später nicht mehr vollständig angezeigt.

### API-Berechtigungen (Graph, delegiert)

**API-Berechtigungen** → **Berechtigung hinzufügen** → **Microsoft Graph** →
**Delegierte Berechtigungen**. Folgende hinzufügen:

| Scope                              | Zweck                                   |
|------------------------------------|-----------------------------------------|
| `User.ReadWrite.All`               | Benutzer anlegen                        |
| `LicenseAssignment.ReadWrite.All`  | Lizenzen zuweisen                       |
| `Organization.Read.All`            | abonnierte SKUs / Lizenzbestand lesen   |
| `User.Read`                        | Profil des angemeldeten Mitarbeiters    |
| `openid`, `profile`, `offline_access` | OpenID Connect / Token-Refresh       |

Anschließend **„Administratorzustimmung für <Tenant> erteilen“** klicken
(erforderlich für die `*.All`-Scopes).

### Rolle für das anmeldende Personal

Da der Flow **delegiert** ist, handelt das Tool im Namen der angemeldeten
Person. Diese braucht eine passende Entra-Rolle (unter **Rollen und
Administratoren**):

- **User Administrator** (empfohlen, deckt Anlegen + Lizenzieren ab)

oder kombiniert: **Directory Writers** + **License Administrator**.

> Ohne ausreichende Rolle schlägt das Anlegen mit **HTTP 403** fehl – das Tool
> zeigt dann einen entsprechenden Hinweis an.

---

## 4. .env ausfüllen

```bash
cp .env.example .env
```

Dann `.env` mit den Werten aus Schritt 2 und 3 füllen:

```
PORT=3000
SESSION_SECRET=<langer-zufallswert>           # z. B. `openssl rand -hex 32`
TENANT_ID=<Verzeichnis-(Mandanten-)ID>
CLIENT_ID=<Anwendungs-(Client-)ID>
CLIENT_SECRET=<geheimer-Clientschluessel-Wert>
REDIRECT_URI=http://localhost:3000/auth/callback
GRAPH_SCOPES=User.ReadWrite.All LicenseAssignment.ReadWrite.All Organization.Read.All User.Read openid profile offline_access
DATABASE_URL=postgres://m365:m365@localhost:5432/m365onboarding
SMTP_HOST=smtp.ionos.de
SMTP_PORT=587
SMTP_USER=<smtp-benutzer>
SMTP_PASS=<smtp-passwort>
MAIL_FROM=IT-Onboarding <onboarding@example.de>
```

Tipp für `SESSION_SECRET`: `openssl rand -hex 32`.

> Die echte `.env` wird durch `.gitignore` nie committet.

---

## 5. Preflight-Check & Start

Vor dem Start prüfen, ob alles passt (Umgebungsvariablen, DB-Verbindung,
Tabellen vorhanden):

```bash
npm run check
```

Bei „alles grün“ starten:

```bash
npm start
```

Dann im Browser `http://localhost:3000` öffnen → Weiterleitung auf den Login.

---

## 6. Funktionstest

1. Auf **„Mit Microsoft 365 anmelden“** klicken und mit einem Konto anmelden,
   das die Rolle **User Administrator** (o. ä.) hat.
2. Im Formular einen Testnamen, eine **eigene** private Mailadresse und eine
   verfügbare Lizenz wählen.
3. Absenden → es sollte der neue UPN erscheinen und die Willkommensmail bei dir
   ankommen.
4. In der DB prüfen, dass ein Audit-Eintrag **ohne** private Mailadresse steht:

   ```bash
   psql "$DATABASE_URL" -c "SELECT * FROM onboarding_log ORDER BY id DESC LIMIT 5;"
   ```

5. Den Testbenutzer im Entra-Portal wieder löschen, wenn nicht mehr gebraucht.

---

## 7. Fehlerbehebung

| Symptom                                              | Ursache / Lösung |
|------------------------------------------------------|------------------|
| Redirect-Fehler `AADSTS50011` (Reply-URL)            | `REDIRECT_URI` muss **exakt** mit der in der App-Registration hinterlegten URL übereinstimmen (inkl. http/https, Port, Pfad). |
| Anmeldung klappt, aber Anlegen schlägt mit **403** fehl | Dem angemeldeten Konto fehlt die Entra-Rolle (User Administrator) oder die Admin-Zustimmung zu den Scopes fehlt. |
| Keine Lizenzen im Dropdown                            | Es gibt keine SKUs mit freien Einheiten, oder `Organization.Read.All` fehlt/ohne Admin-Zustimmung. |
| Mail kommt nicht an                                   | SMTP-Daten prüfen; Port 587 (STARTTLS) bzw. 465 (TLS). Der Benutzer wird trotzdem angelegt – das Tool zeigt dann eine Warnung. |
| `connect-pg-simple`/Session-Fehler beim Start        | Schema nicht eingespielt? `db/schema.sql` ausführen. |
| `relation "onboarding_log" does not exist`           | Schema nicht eingespielt – siehe Schritt 2. |
