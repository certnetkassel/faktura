// scripts/check.js
// Preflight-Prüfung vor dem Start: Sind alle Umgebungsvariablen gesetzt,
// ist die Datenbank erreichbar und sind die benötigten Tabellen vorhanden?
//
// Aufruf:  npm run check
//
// Beendet mit Exit-Code 0 (alles in Ordnung) oder 1 (Probleme gefunden).

require('dotenv').config();

const { Pool } = require('pg');

// Erwartete Umgebungsvariablen.
const PFLICHT_VARIABLEN = [
  'SESSION_SECRET',
  'TENANT_ID',
  'CLIENT_ID',
  'CLIENT_SECRET',
  'REDIRECT_URI',
  'GRAPH_SCOPES',
  'DATABASE_URL',
  'SMTP_HOST',
  'SMTP_PORT',
  'SMTP_USER',
  'SMTP_PASS',
  'MAIL_FROM',
];

// Empfohlene Graph-Scopes (nur als Hinweis geprüft).
const EMPFOHLENE_SCOPES = [
  'User.ReadWrite.All',
  'LicenseAssignment.ReadWrite.All',
  'Organization.Read.All',
  'User.Read',
  'openid',
  'profile',
  'offline_access',
];

// Erwartete Tabellen.
const TABELLEN = ['onboarding_log', 'session'];

const grad = { ok: '✓', warn: '!', fehler: '✗' };
let hatFehler = false;

function zeile(symbol, text) {
  console.log(`  ${symbol}  ${text}`);
}

async function main() {
  console.log('\nPreflight-Check für das M365-Onboarding-Tool\n');

  // 1. Umgebungsvariablen.
  console.log('Umgebungsvariablen:');
  for (const name of PFLICHT_VARIABLEN) {
    const wert = process.env[name];
    if (!wert || wert.trim() === '') {
      zeile(grad.fehler, `${name} fehlt`);
      hatFehler = true;
    } else {
      // Geheimnisse nicht im Klartext ausgeben.
      const istGeheim = /SECRET|PASS/i.test(name);
      const anzeige = istGeheim ? '(gesetzt)' : wert;
      zeile(grad.ok, `${name} = ${anzeige}`);
    }
  }

  // 2. Graph-Scopes prüfen (nur Warnung bei fehlenden Empfehlungen).
  console.log('\nGraph-Scopes:');
  const gesetzteScopes = (process.env.GRAPH_SCOPES || '')
    .split(/\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  for (const scope of EMPFOHLENE_SCOPES) {
    if (gesetzteScopes.includes(scope)) {
      zeile(grad.ok, scope);
    } else {
      zeile(grad.warn, `${scope} fehlt (empfohlen)`);
    }
  }

  // 3. REDIRECT_URI grob plausibilisieren.
  console.log('\nRedirect-URI:');
  const redirect = process.env.REDIRECT_URI || '';
  if (/^https?:\/\/.+\/auth\/callback$/.test(redirect)) {
    zeile(grad.ok, redirect);
  } else if (redirect) {
    zeile(grad.warn, `${redirect} – sollte auf /auth/callback enden`);
  }

  // 4. Datenbank.
  console.log('\nDatenbank:');
  if (!process.env.DATABASE_URL) {
    zeile(grad.fehler, 'DATABASE_URL nicht gesetzt – Prüfung übersprungen');
    hatFehler = true;
  } else {
    const pool = new Pool({ connectionString: process.env.DATABASE_URL });
    try {
      await pool.query('SELECT 1');
      zeile(grad.ok, 'Verbindung erfolgreich');

      for (const tabelle of TABELLEN) {
        const res = await pool.query('SELECT to_regclass($1) AS vorhanden', [tabelle]);
        if (res.rows[0].vorhanden) {
          zeile(grad.ok, `Tabelle "${tabelle}" vorhanden`);
        } else {
          zeile(grad.fehler, `Tabelle "${tabelle}" fehlt – db/schema.sql einspielen`);
          hatFehler = true;
        }
      }
    } catch (err) {
      zeile(grad.fehler, `Verbindung fehlgeschlagen: ${err.message}`);
      hatFehler = true;
    } finally {
      await pool.end();
    }
  }

  console.log('');
  if (hatFehler) {
    console.log('Ergebnis: Es wurden Probleme gefunden. Bitte oben markierte Punkte (✗) beheben.\n');
    process.exit(1);
  } else {
    console.log('Ergebnis: Alles in Ordnung. Du kannst "npm start" ausführen.\n');
    process.exit(0);
  }
}

main().catch((err) => {
  console.error('Unerwarteter Fehler im Preflight-Check:', err);
  process.exit(1);
});
