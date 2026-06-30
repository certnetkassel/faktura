# Deployment auf certnet.eu (Subdomain onboarding.certnet.eu)

Runbook zum Ausrollen des M365-Onboarding-Tools auf einem Ubuntu-Server.
Alle Befehle als `root` bzw. mit `sudo`. Subdomain hier: `onboarding.certnet.eu`
(bei abweichendem Host überall ersetzen).

Annahmen: frischer/bestehender Ubuntu-Server (22.04/24.04) mit SSH-Zugang.

Reihenfolge:

1. [DNS](#1-dns)
2. [Grundpakete: Node.js, nginx, certbot](#2-grundpakete)
3. [PostgreSQL einrichten](#3-postgresql-einrichten)
4. [App ausbringen](#4-app-ausbringen)
5. [.env konfigurieren](#5-env-konfigurieren)
6. [Schema einspielen & Preflight](#6-schema-einspielen--preflight)
7. [systemd-Service](#7-systemd-service)
8. [nginx + TLS](#8-nginx--tls)
9. [Entra-Redirect-URI nachziehen](#9-entra-redirect-uri-nachziehen)
10. [Test & Updates](#10-test--updates)

---

## 1. DNS

Beim DNS-Anbieter von `certnet.eu` einen **A-Record** anlegen:

```
onboarding.certnet.eu.   A   <IP_DES_SERVERS>
```

(Bei IPv6 zusätzlich ein AAAA-Record.) Verbreitung abwarten und prüfen:

```bash
dig +short onboarding.certnet.eu
```

---

## 2. Grundpakete

```bash
apt update
# Node.js 20 LTS aus dem NodeSource-Repo
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs nginx certbot python3-certbot-nginx git
node --version    # sollte v20.x zeigen
```

---

## 3. PostgreSQL einrichten

```bash
apt install -y postgresql
systemctl enable --now postgresql

# Datenbank und Benutzer anlegen (starkes Passwort einsetzen!)
sudo -u postgres psql <<'SQL'
CREATE USER m365 WITH PASSWORD 'BITTE_STARKES_PASSWORT';
CREATE DATABASE m365onboarding OWNER m365;
GRANT ALL PRIVILEGES ON DATABASE m365onboarding TO m365;
SQL
```

Das hier vergebene Passwort muss gleich in `DATABASE_URL` (Schritt 5) stehen.

---

## 4. App ausbringen

Systembenutzer anlegen und Code nach `/opt/m365-onboarding` bringen.

```bash
# Dedizierter, nicht-interaktiver Systembenutzer
adduser --system --group --home /opt/m365-onboarding m365

# Code holen – sobald das GitHub-Repo existiert:
git clone https://github.com/certnetkassel/m365-onboarding.git /opt/m365-onboarding
# Alternativ ohne GitHub: das entpackte Projekt per scp nach /opt/m365-onboarding kopieren.

cd /opt/m365-onboarding
# Nur Produktionsabhängigkeiten installieren
npm ci --omit=dev    # falls package-lock.json fehlt: npm install --omit=dev

# Eigentümer auf den Service-Benutzer setzen
chown -R m365:m365 /opt/m365-onboarding
```

---

## 5. .env konfigurieren

```bash
cp /opt/m365-onboarding/deploy/env.production.example /opt/m365-onboarding/.env
# SESSION_SECRET erzeugen:
openssl rand -hex 32
nano /opt/m365-onboarding/.env      # alle Werte ausfüllen (siehe unten)
chmod 600 /opt/m365-onboarding/.env
chown m365:m365 /opt/m365-onboarding/.env
```

Auszufüllen: `SESSION_SECRET`, `TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`,
`DATABASE_URL` (mit dem Passwort aus Schritt 3), `SMTP_*`, `MAIL_FROM`.
`REDIRECT_URI` ist bereits auf `https://onboarding.certnet.eu/auth/callback`
gesetzt.

---

## 6. Schema einspielen & Preflight

```bash
cd /opt/m365-onboarding
# Schema (onboarding_log + session) einspielen
sudo -u m365 psql "$(grep -E '^DATABASE_URL=' .env | cut -d= -f2-)" -f db/schema.sql

# Preflight-Check (prüft .env, DB-Verbindung, Tabellen)
sudo -u m365 --preserve-env=PATH bash -lc 'cd /opt/m365-onboarding && npm run check'
```

Erst weitermachen, wenn der Check „Alles in Ordnung“ meldet.

---

## 7. systemd-Service

```bash
cp /opt/m365-onboarding/deploy/m365-onboarding.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now m365-onboarding
systemctl status m365-onboarding --no-pager
# Logs live:
journalctl -u m365-onboarding -f
```

Die App lauscht jetzt auf `127.0.0.1:3000`.

---

## 8. nginx + TLS

```bash
cp /opt/m365-onboarding/deploy/nginx-onboarding.conf /etc/nginx/sites-available/onboarding.certnet.eu
ln -s /etc/nginx/sites-available/onboarding.certnet.eu /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Let's-Encrypt-Zertifikat holen und HTTPS einrichten
certbot --nginx -d onboarding.certnet.eu
```

certbot ergänzt den 443-Block, trägt die Zertifikatspfade ein und richtet die
HTTP→HTTPS-Weiterleitung ein. Die automatische Erneuerung läuft über den
certbot-Timer (`systemctl status certbot.timer`).

---

## 9. Entra-Redirect-URI nachziehen

In der Azure/Entra App-Registration unter **Authentifizierung** als
**Web**-Redirect-URI eintragen (zusätzlich/statt der lokalen):

```
https://onboarding.certnet.eu/auth/callback
```

Muss **exakt** mit `REDIRECT_URI` in der `.env` übereinstimmen, sonst
`AADSTS50011`.

---

## 10. Test & Updates

**Test:** `https://onboarding.certnet.eu` aufrufen → Microsoft-Login →
Testbenutzer anlegen → Willkommensmail prüfen → Audit-Eintrag prüfen:

```bash
sudo -u m365 psql "$(grep -E '^DATABASE_URL=' /opt/m365-onboarding/.env | cut -d= -f2-)" \
  -c "SELECT id, erstellt_am, durchgefuehrt_von, neuer_upn, lizenz_sku, mail_versendet FROM onboarding_log ORDER BY id DESC LIMIT 5;"
```

**Update einspielen:**

```bash
cd /opt/m365-onboarding
sudo -u m365 git pull
sudo -u m365 npm ci --omit=dev
systemctl restart m365-onboarding
```

---

### Kurz-Spickzettel

| Aufgabe            | Befehl |
|--------------------|--------|
| Status             | `systemctl status m365-onboarding` |
| Logs               | `journalctl -u m365-onboarding -f` |
| Neustart           | `systemctl restart m365-onboarding` |
| nginx neu laden    | `nginx -t && systemctl reload nginx` |
| Zertifikat-Status  | `certbot certificates` |
