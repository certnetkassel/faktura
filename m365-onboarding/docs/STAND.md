# Projektstand & nächste Schritte

Kurzer Übergabezettel, um an einem anderen Rechner / in einer neuen Sitzung
nahtlos weiterzumachen.

## Wo der aktuelle, maßgebliche Stand liegt

- **Dieses Verzeichnis / `.tar.gz`-Archiv** ist der vollständige Stand.
- Zusätzlich gesichert auf GitHub im Repo `certnetkassel/faktura`, Branch
  `claude/m365-onboarding-tool-vqweer`, Unterordner `m365-onboarding/`
  (dorthin wurde während der Entwicklung als Zwischenablage gepusht, weil der
  Zugang dort beschränkt war).
- Ein **eigenes** Repo `certnetkassel/m365-onboarding` ist noch **nicht**
  angelegt (siehe Schritt 1 unten).

## Was fertig ist

- Vollständige App (Node.js/Express, MSAL delegiert, Graph, nodemailer, pg).
- `package-lock.json` vorhanden, `npm audit` = 0 Schwachstellen.
- Doku: `README.md`, `docs/EINRICHTUNG.md`, `docs/GERAETEWECHSEL.md`.
- Deployment-Paket in `deploy/` (nginx, systemd, Produktions-.env, Runbook).
- Lokale Entwicklung: `docker-compose.yml` (PostgreSQL), `npm run check`.

## Eckdaten / Entscheidungen

- Ziel-Subdomain: **onboarding.certnet.eu** (neuer certnet.eu-Server).
- Datenbank: **PostgreSQL** auf dem Server.
- Node-Mindestversion: **20**.

## Nächste Schritte (Reihenfolge)

> Für Schritt 1–3 gibt es ein fertiges Abhak-Blatt mit Eintragefeldern:
> **`docs/START_AN_DER_ARBEIT.md`**. Damit anfangen.

1. **GitHub-Repo anlegen + pushen**
   - Privates Repo `certnetkassel/m365-onboarding` (leer, ohne README/.gitignore).
   - Mit GitHub CLI in einem Rutsch:
     ```
     cd <projektordner>
     gh repo create certnetkassel/m365-onboarding --private --source=. --push
     ```
   - Oder Repo im Web anlegen, dann `git push -u origin main`
     (origin ist bereits gesetzt).

2. **Entra-App-Registration** (Azure/Entra-Portal) — Details in
   `docs/EINRICHTUNG.md`, Abschnitt 3. Ergebnis: `TENANT_ID`, `CLIENT_ID`,
   `CLIENT_SECRET`, Admin-Zustimmung zu den Scopes, Test-Konto mit Rolle
   „User Administrator".

3. **DNS:** A-Record `onboarding.certnet.eu` → Server-IP.

4. **Server-Deployment** nach `deploy/DEPLOYMENT.md` (Node 20, PostgreSQL,
   App nach `/opt/m365-onboarding`, `.env`, Schema, systemd, nginx, certbot).

5. **Redirect-URI** in der Entra-App nachtragen:
   `https://onboarding.certnet.eu/auth/callback`.

6. **Funktionstest:** Testbenutzer anlegen → Willkommensmail → Audit-Eintrag
   prüfen → Testbenutzer wieder löschen.

## Optional / offen

- GitHub-Actions-CI (npm ci + node --check + npm audit) — noch nicht angelegt.
- Dockerfile für die App als Alternative zum manuellen Server-Setup — noch
  nicht angelegt.

## Wichtige Erinnerungen

- Geheimnisse nur in `.env` (lokal/Server), **nie** committen.
- Private E-Mail-Adresse des neuen Benutzers wird nicht gespeichert
  (nur Flag `mail_versendet`).
- Mehr-Geräte-Arbeit über GitHub, nicht über OneDrive-Sync
  (siehe `docs/GERAETEWECHSEL.md`).
