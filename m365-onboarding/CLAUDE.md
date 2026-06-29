# M365-Onboarding-Tool

Self-Service-Werkzeug, mit dem sich Kundenpersonal mit dem eigenen
Microsoft-365-Account anmeldet (OAuth 2.0 Authorization Code Flow, delegiert)
und über ein Formular neue Benutzer im Tenant anlegt, eine Lizenz zuweist und
die Zugangsdaten an eine private E-Mail-Adresse versendet.

## Projektregeln (verbindlich)

- **Sprache:** Alle Antworten, Erklärungen, Code-Kommentare und Commit-Messages
  auf **Deutsch**.
- **Vollständige Dateien:** Immer komplette Dateien liefern, niemals nur
  Ausschnitte.
- **Sofort committen und pushen:** Änderungen direkt nach Fertigstellung ohne
  Rückfrage committen und pushen.
- **Geheimnisse nur über Umgebungsvariablen:** Keine Secrets im Code. Alle
  sensiblen Werte ausschließlich über `.env` / Umgebungsvariablen. Die echte
  `.env` wird NIEMALS committet (nur `.env.example` mit Platzhaltern).
- **Datenschutz:** Die private E-Mail-Adresse des neuen Benutzers wird NICHT
  gespeichert. Im Audit-Log steht nur das Flag `mail_versendet`.

## Tech-Stack

- Node.js / Express
- @azure/msal-node (OAuth, Authorization Code Flow, delegiert)
- express-session + connect-pg-simple (Session-Speicher in PostgreSQL)
- pg (PostgreSQL-Zugriff)
- nodemailer (Mailversand über IONOS SMTP)
- EJS (Templates)
- dotenv (Konfiguration)

## Projektstruktur

```
m365-onboarding/
├── server.js              # Express-Setup, Session, Login-Pflicht-Middleware
├── routes/
│   ├── auth.js            # Login-Start, OAuth-Callback, Logout
│   └── onboarding.js      # Formular (GET) und Benutzeranlage (POST)
├── lib/
│   ├── graph.js           # Microsoft-Graph-Helfer (Domains, SKUs, User, Lizenz)
│   ├── password.js        # Sicheres Zufallspasswort (crypto)
│   ├── mail.js            # Willkommensmail (nodemailer)
│   └── db.js              # pg-Pool + schreibeAuditEintrag
├── views/
│   ├── login.ejs          # Login-Seite
│   └── formular.ejs       # Onboarding-Formular
├── public/css/app.css     # Styling
├── db/schema.sql          # onboarding_log + session-Tabelle
├── .env.example           # Vorlage für Umgebungsvariablen
├── .gitignore
├── package.json
└── README.md
```

## Ablauf der POST-Route (/)

1. Eingaben prüfen (alle Felder vorhanden, private Mail plausibel).
2. UPN bilden: `vorname.nachname` klein, Umlaute/Sonderzeichen bereinigt, plus
   `@domain`.
3. Zufallspasswort generieren.
4. Benutzer über Graph anlegen (`createUser`).
5. Lizenz zuweisen (`assignLicense`).
6. Willkommensmail an die private Adresse senden.
7. Audit-Eintrag schreiben (ohne private Mail).
8. Erfolgs- bzw. Fehlermeldung anzeigen.
