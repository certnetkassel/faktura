// server.js
// Express-Grundgerüst für das M365-Onboarding-Tool.
// Hier werden Sessions (in PostgreSQL via connect-pg-simple), die View-Engine,
// die Routen sowie die Login-Pflicht-Middleware konfiguriert.

require('dotenv').config();

const path = require('path');
const express = require('express');
const session = require('express-session');
const PgSession = require('connect-pg-simple')(session);

const { pool } = require('./lib/db');
const authRoutes = require('./routes/auth');
const onboardingRoutes = require('./routes/onboarding');

const app = express();
const PORT = process.env.PORT || 3000;

// Hinter einem Reverse-Proxy (nginx) laufen wir mit "trust proxy",
// damit Secure-Cookies und die korrekte Client-IP funktionieren.
app.set('trust proxy', 1);

// EJS als Template-Engine, Views liegen im Verzeichnis "views".
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Statische Dateien (CSS) ausliefern.
app.use(express.static(path.join(__dirname, 'public')));

// Formulardaten (application/x-www-form-urlencoded) einlesen.
app.use(express.urlencoded({ extended: false }));

// Session-Konfiguration: Speicherung in PostgreSQL.
// Die benötigte Tabelle "session" wird über db/schema.sql angelegt.
app.use(
  session({
    store: new PgSession({
      pool: pool,
      tableName: 'session',
      // Tabelle nicht automatisch erzeugen – wir verwalten das Schema selbst.
      createTableIfMissing: false,
    }),
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      // Im Produktivbetrieb (HTTPS) sollte das Cookie nur über sichere
      // Verbindungen übertragen werden.
      secure: process.env.NODE_ENV === 'production',
      maxAge: 1000 * 60 * 60 * 8, // 8 Stunden
      sameSite: 'lax',
    },
  })
);

// Login-Pflicht-Middleware:
// Nicht eingeloggte Nutzer werden auf den Login umgeleitet.
// Ausgenommen sind die Auth-Routen selbst und statische Dateien.
function loginErforderlich(req, res, next) {
  const oeffentlichePfade = ['/auth/login', '/auth/callback', '/auth/logout'];
  if (oeffentlichePfade.includes(req.path)) {
    return next();
  }
  if (req.session && req.session.accessToken && req.session.upn) {
    return next();
  }
  return res.redirect('/auth/login');
}

app.use(loginErforderlich);

// Routen einbinden.
app.use('/auth', authRoutes);
app.use('/', onboardingRoutes);

// Einfacher Health-Check (nicht login-pflichtig wäre er praktischer, aber
// für den internen Gebrauch reicht dies; er liegt hinter der Login-Pflicht).
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Zentrale Fehlerbehandlung: unerwartete Fehler protokollieren und eine
// verständliche Meldung anzeigen.
app.use((err, req, res, next) => {
  console.error('Unerwarteter Fehler:', err);
  res.status(500).render('formular', {
    upn: (req.session && req.session.upn) || 'Unbekannt',
    domains: [],
    skus: [],
    erfolg: null,
    fehler:
      'Es ist ein unerwarteter interner Fehler aufgetreten. Bitte versuchen Sie es erneut oder wenden Sie sich an die IT.',
    eingaben: {},
  });
});

app.listen(PORT, () => {
  console.log(`M365-Onboarding-Tool läuft auf Port ${PORT}`);
});
