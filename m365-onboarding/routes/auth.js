// routes/auth.js
// OAuth-2.0-Authorization-Code-Flow (delegiert) mit @azure/msal-node.
//
// Routen:
//   GET /auth/login    -> Weiterleitung zur Microsoft-Anmeldung.
//   GET /auth/callback -> Token per acquireTokenByCode holen, in Session ablegen.
//   GET /auth/logout   -> Session beenden.

const express = require('express');
const crypto = require('crypto');
const { ConfidentialClientApplication } = require('@azure/msal-node');

const router = express.Router();

// Die angeforderten Scopes aus der Umgebung (durch Leerzeichen getrennt).
// Beispiel: "User.ReadWrite.All LicenseAssignment.ReadWrite.All Organization.Read.All User.Read"
const SCOPES = (process.env.GRAPH_SCOPES || '')
  .split(/\s+/)
  .map((s) => s.trim())
  .filter(Boolean);

// MSAL-Konfiguration für die vertrauliche Client-Anwendung.
const msalConfig = {
  auth: {
    clientId: process.env.CLIENT_ID,
    authority: `https://login.microsoftonline.com/${process.env.TENANT_ID}`,
    clientSecret: process.env.CLIENT_SECRET,
  },
};

const msalClient = new ConfidentialClientApplication(msalConfig);

/**
 * GET /auth/login
 * Erzeugt die Microsoft-Anmelde-URL und leitet den Browser dorthin weiter.
 * Ein zufälliger "state" wird zur CSRF-Absicherung in der Session abgelegt.
 */
router.get('/login', async (req, res, next) => {
  try {
    // Zufälligen State erzeugen und in der Session merken.
    const state = crypto.randomBytes(16).toString('hex');
    req.session.authState = state;

    const authUrl = await msalClient.getAuthCodeUrl({
      scopes: SCOPES,
      redirectUri: process.env.REDIRECT_URI,
      state,
      // "select_account" zeigt die Kontoauswahl, damit der Mitarbeiter
      // bewusst sein eigenes Konto wählt.
      prompt: 'select_account',
    });

    res.redirect(authUrl);
  } catch (err) {
    next(err);
  }
});

/**
 * GET /auth/callback
 * Empfängt den Authorization Code, tauscht ihn gegen Tokens und legt
 * Access-Token sowie UPN in der Session ab.
 */
router.get('/callback', async (req, res) => {
  try {
    // Fehler vom Identity Provider abfangen (z.B. abgebrochene Anmeldung).
    if (req.query.error) {
      console.error('Fehler bei der Microsoft-Anmeldung:', req.query.error, req.query.error_description);
      return res
        .status(400)
        .render('login', { fehler: 'Die Anmeldung wurde abgebrochen oder ist fehlgeschlagen.' });
    }

    // State prüfen (CSRF-Schutz).
    if (!req.query.state || req.query.state !== req.session.authState) {
      console.error('Ungültiger State im OAuth-Callback.');
      return res
        .status(400)
        .render('login', { fehler: 'Sicherheitsprüfung fehlgeschlagen (ungültiger State). Bitte erneut anmelden.' });
    }

    const tokenAntwort = await msalClient.acquireTokenByCode({
      code: req.query.code,
      scopes: SCOPES,
      redirectUri: process.env.REDIRECT_URI,
    });

    // Access-Token und UPN in der Session speichern.
    req.session.accessToken = tokenAntwort.accessToken;
    req.session.upn =
      (tokenAntwort.account && tokenAntwort.account.username) ||
      (tokenAntwort.idTokenClaims && tokenAntwort.idTokenClaims.preferred_username) ||
      'unbekannt';

    // State wird nicht mehr benötigt.
    delete req.session.authState;

    res.redirect('/');
  } catch (err) {
    console.error('Fehler beim Token-Tausch:', err);
    res
      .status(500)
      .render('login', { fehler: 'Beim Abschluss der Anmeldung ist ein Fehler aufgetreten. Bitte erneut versuchen.' });
  }
});

/**
 * GET /auth/logout
 * Beendet die lokale Session und zeigt wieder die Login-Seite.
 */
router.get('/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) {
      console.error('Fehler beim Beenden der Session:', err);
    }
    res.clearCookie('connect.sid');
    res.redirect('/auth/login');
  });
});

module.exports = router;
