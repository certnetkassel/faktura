# Start an der Arbeit – Schritte 1 bis 3

Eigenständiges Aktionsblatt. Arbeite es von oben nach unten ab und trage die
gewonnenen Werte in die markierten Felder ein. Danach geht es mit dem
Server-Deployment weiter (`deploy/DEPLOYMENT.md`).

Voraussetzung: Du hast das Projekt an einen lokalen Pfad entpackt, z. B.:

```powershell
mkdir C:\dev\onboarding
cd C:\dev\onboarding
tar -xzf "<Pfad-zum-OneDrive>\onboarding\m365-onboarding.tar.gz"
cd .\m365-onboarding
```

---

## Schritt 1 – GitHub-Repo anlegen und pushen

Ziel: privates Repo `certnetkassel/m365-onboarding`, Code als `main` hochladen.

### Variante A: GitHub CLI (erstellt UND pusht in einem)

```powershell
cd C:\dev\onboarding\m365-onboarding
gh --version          # ist gh installiert?
gh auth status        # angemeldet? sonst: gh auth login
gh repo create certnetkassel/m365-onboarding --private --source=. --push
```

### Variante B: ohne gh (Web + Push)

1. https://github.com/organizations/certnetkassel/repositories/new
2. Name: **`m365-onboarding`**, Sichtbarkeit: **Private**,
   **nichts** ankreuzen (kein README/.gitignore/Lizenz) → „Create repository".
3. Pushen (origin ist im Projekt bereits gesetzt):
   ```powershell
   cd C:\dev\onboarding\m365-onboarding
   git push -u origin main
   ```

### Falls Git nach Anmeldung fragt
Personal Access Token (Scope „repo") als Passwort, oder vorher `gh auth login`.

### Kontrolle
```powershell
git remote -v
git log --oneline -1
```
Auf https://github.com/certnetkassel/m365-onboarding sollten ~25 Dateien
(inkl. `deploy/`, `docs/`, `package-lock.json`) liegen.

- [ ] Repo angelegt
- [ ] `git push` erfolgreich
- [ ] Dateien auf GitHub sichtbar

---

## Schritt 2 – Entra-App-Registration

Portal: https://entra.microsoft.com → **Anwendungen** → **App-Registrierungen**
→ **Neue Registrierung**.

1. **Name:** `M365-Onboarding-Tool`
2. **Kontotypen:** „Nur Konten in diesem Organisationsverzeichnis" (Single Tenant)
3. **Redirect-URI:** Plattform **Web**, vorerst die produktive URL eintragen:
   `https://onboarding.certnet.eu/auth/callback`
   (lokal zum Testen kann zusätzlich `http://localhost:3000/auth/callback` rein)
4. **Registrieren**.

### Werte notieren (von der Übersichtsseite)

```
TENANT_ID  (Verzeichnis-/Mandanten-ID): ____________________________________
CLIENT_ID  (Anwendungs-/Client-ID):     ____________________________________
```

### Client-Secret erstellen
**Zertifikate & Geheimnisse** → **Neuer geheimer Clientschlüssel** → Ablauf
wählen → **Hinzufügen** → den **Wert** (nicht die ID!) sofort kopieren:

```
CLIENT_SECRET (Wert): _______________________________________________________
```

> Der Wert wird später nicht mehr vollständig angezeigt – jetzt sichern
> (z. B. im Passwort-Manager).

### API-Berechtigungen (Microsoft Graph, delegiert)
**API-Berechtigungen** → **Berechtigung hinzufügen** → **Microsoft Graph** →
**Delegierte Berechtigungen** → folgende hinzufügen:

- [ ] `User.ReadWrite.All`
- [ ] `LicenseAssignment.ReadWrite.All`
- [ ] `Organization.Read.All`
- [ ] `User.Read`
- [ ] `openid`
- [ ] `profile`
- [ ] `offline_access`

Danach: **„Administratorzustimmung für <Tenant> erteilen"** klicken.

- [ ] Admin-Zustimmung erteilt (Status-Spalte zeigt grüne Haken)

### Rolle für das anmeldende Personal
Das Konto, das sich später im Tool anmeldet, braucht eine passende Entra-Rolle
(Entra → **Rollen und Administratoren**):

- **User Administrator** (empfohlen) — oder **Directory Writers** +
  **License Administrator**.

- [ ] Test-Konto mit ausreichender Rolle bereit

---

## Schritt 3 – DNS

Beim DNS-Anbieter der Domain `certnet.eu` einen A-Record anlegen:

```
onboarding.certnet.eu.   A   <IP_DES_CERTNET_EU_SERVERS>
```

Server-IP hier notieren: `____________________________`

Prüfen (kann etwas dauern, bis es verbreitet ist):

```powershell
nslookup onboarding.certnet.eu
```

- [ ] A-Record angelegt
- [ ] `nslookup` zeigt die richtige IP

---

## Geschafft? Dann weiter mit dem Server

Wenn 1–3 erledigt sind, geht es mit dem Deployment weiter:
**`deploy/DEPLOYMENT.md`** (Node 20, PostgreSQL, App, `.env` mit den oben
notierten Werten, systemd, nginx, Let's Encrypt). Die in Schritt 2 notierten
Werte kommen dort in die `.env` (`TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`).

> Erinnerung: Die `.env` mit den Geheimnissen wird **nie** committet.
