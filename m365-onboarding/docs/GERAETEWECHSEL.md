# Geräte-Wechsel-Merkkarte (Notebook ↔ Mini-PC ↔ Office)

Kurzreferenz, um an mehreren Rechnern am selben Projekt zu arbeiten – **ohne**
OneDrive-Sync des Codes. Das Synchronisieren übernimmt **GitHub** (inhaltliches
Mergen statt Datei-Kopien).

Goldene Regel: **Code lebt auf GitHub und lokal unter `C:\dev\...`.**
OneDrive höchstens für das `.tar.gz`-Backup oder Notizen – **nie** das aktive
`.git` oder `node_modules`.

---

## Einmalig pro Gerät: einrichten

```powershell
# 1. In den lokalen Entwicklungsordner (kein OneDrive!)
mkdir C:\dev\onboarding
cd C:\dev\onboarding

# 2. Repo klonen
git clone https://github.com/certnetkassel/m365-onboarding.git
cd .\m365-onboarding

# 3. Abhängigkeiten installieren (aus dem Lockfile, reproduzierbar)
npm ci

# 4. .env anlegen und mit den Werten füllen (liegt NICHT im Git)
copy .env.example .env
notepad .env
```

> Die `.env` wird bewusst nicht synchronisiert. Trage sie auf jedem Gerät
> einmal ein (oder bewahre die Werte in einem Passwort-Manager auf).

---

## Bei jedem Arbeitsbeginn: holen

```powershell
cd C:\dev\onboarding\m365-onboarding
git pull
# Falls sich package.json/Lockfile geändert haben:
npm ci
```

## Bei jedem Arbeitsende (vor Gerätewechsel): sichern

```powershell
git add -A
git commit -m "kurze Beschreibung der Änderung"
git push
```

> **Wichtig:** Erst `push`, dann am anderen Gerät `pull`. So vermeidest du
> Divergenzen.

---

## Der typische Tag im Schnelldurchlauf

| Wo               | Befehl                                  |
|------------------|-----------------------------------------|
| Mini-PC, Start   | `git pull`                              |
| Mini-PC, Ende    | `git add -A && git commit -m "…" && git push` |
| Notebook, Start  | `git pull`                              |
| Notebook, Ende   | `git add -A && git commit -m "…" && git push` |
| Office, Start    | `git pull`                              |
| Office, Ende     | `git add -A && git commit -m "…" && git push` |

Immer dasselbe Muster: **Start = pull, Ende = commit + push.**

---

## Wenn doch mal etwas hakt

**„Your branch is behind / Updates were rejected" beim Push**
Am anderen Gerät wurde schon gepusht. Erst holen, dann erneut pushen:

```powershell
git pull --rebase
git push
```

**„You have unsaved changes" beim `git pull`**
Erst committen (oder kurz beiseitelegen), dann ziehen:

```powershell
git stash          # Änderungen zwischenlagern
git pull --rebase
git stash pop      # Änderungen zurückholen
```

**Merge-Konflikt nach `pull`**
Git markiert die betroffenen Dateien (`<<<<<<<` / `=======` / `>>>>>>>`).
Stelle von Hand her, was bleiben soll, dann:

```powershell
git add <datei>
git rebase --continue   # bei pull --rebase
# bzw. git commit         # bei normalem Merge
```

**„node_modules" macht Ärger / nach Branch-Wechsel komisch**
Einfach neu aufbauen – ist aus dem Lockfile schnell wiederhergestellt:

```powershell
rmdir /s /q node_modules
npm ci
```

---

## Was wohin gehört (Kurzfassung)

| Inhalt                     | Ort                          | Im Git? |
|----------------------------|------------------------------|---------|
| Quellcode, Doku, deploy/   | GitHub + `C:\dev\...`        | ja      |
| `package-lock.json`        | GitHub                       | ja      |
| `node_modules/`            | nur lokal (`npm ci`)         | nein    |
| `.env` (Geheimnisse)       | nur lokal / Passwort-Manager | nein    |
| `.tar.gz`-Backup, Notizen  | OneDrive (optional)          | –       |

Merksatz: **GitHub ist der Sync, OneDrive nur das Backup.**
