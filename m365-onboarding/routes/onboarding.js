// routes/onboarding.js
// Stellt das Onboarding-Formular bereit und verarbeitet das Anlegen neuer
// Microsoft-365-Benutzer.
//
//   GET  /  -> Formular rendern (Domains und Lizenzen aus Graph laden).
//   POST /  -> Benutzer anlegen, Lizenz zuweisen, Mail senden, Audit schreiben.

const express = require('express');

const graph = require('../lib/graph');
const { generierePasswort } = require('../lib/password');
const { sendeWillkommensmail } = require('../lib/mail');
const { schreibeAuditEintrag } = require('../lib/db');

const router = express.Router();

// Login-Anzeige (GET /auth/login) wird in routes/auth.js NICHT gerendert,
// sondern leitet direkt weiter. Die Login-SEITE selbst zeigen wir hier nicht;
// sie wird bei Bedarf aus auth.js (Fehlerfall) gerendert.

/**
 * Bereinigt einen Namensteil für die Verwendung im UPN/Mail-Alias.
 * Deutsche Umlaute werden ausgeschrieben, übrige Sonderzeichen entfernt.
 *
 * @param {string} wert
 * @returns {string} bereinigter, kleingeschriebener String (nur a-z, 0-9, .-_).
 */
function bereinigeNamensteil(wert) {
  return String(wert)
    .toLowerCase()
    .trim()
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue')
    .replace(/ß/g, 'ss')
    // Akzente abtrennen (z.B. é -> e) über Unicode-Normalisierung.
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    // Alles, was kein Kleinbuchstabe oder Ziffer ist, entfernen.
    .replace(/[^a-z0-9]/g, '');
}

/**
 * Einfache Plausibilitätsprüfung einer E-Mail-Adresse.
 *
 * @param {string} mail
 * @returns {boolean}
 */
function istPlausibleMail(mail) {
  return typeof mail === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(mail.trim());
}

/**
 * Lädt Domains und Lizenzen aus Graph für die Formularanzeige.
 *
 * @param {string} token
 * @returns {Promise<{domains: Array, skus: Array}>}
 */
async function ladeFormulardaten(token) {
  const [domains, skus] = await Promise.all([
    graph.getVerifiedDomains(token),
    graph.getAvailableSkus(token),
  ]);
  return { domains, skus };
}

/**
 * GET /
 * Rendert das Onboarding-Formular mit Domains und Lizenzen.
 */
router.get('/', async (req, res, next) => {
  try {
    const { domains, skus } = await ladeFormulardaten(req.session.accessToken);
    res.render('formular', {
      upn: req.session.upn,
      domains,
      skus,
      erfolg: null,
      fehler: null,
      eingaben: {},
    });
  } catch (err) {
    console.error('Fehler beim Laden der Formulardaten:', err);
    // Formular trotzdem anzeigen, aber mit Fehlerhinweis und leeren Listen.
    res.render('formular', {
      upn: req.session.upn,
      domains: [],
      skus: [],
      erfolg: null,
      fehler:
        'Domains und Lizenzen konnten nicht aus Microsoft Graph geladen werden. ' +
        'Bitte prüfen Sie Ihre Berechtigungen und versuchen Sie es erneut.',
      eingaben: {},
    });
  }
});

/**
 * POST /
 * Verarbeitet die Formulareingaben und legt den neuen Benutzer an.
 */
router.post('/', async (req, res) => {
  const token = req.session.accessToken;
  const durchgefuehrtVon = req.session.upn;

  // Rohwerte aus dem Formular.
  const vorname = (req.body.vorname || '').trim();
  const nachname = (req.body.nachname || '').trim();
  const privateMail = (req.body.private_mail || '').trim();
  const domain = (req.body.domain || '').trim();
  const skuId = (req.body.sku_id || '').trim();

  // Eingaben für eine erneute Anzeige im Fehlerfall (ohne private Mail nicht
  // nötig zu verbergen – sie wird nur angezeigt, nicht gespeichert).
  const eingaben = { vorname, nachname, privateMail, domain, skuId };

  /**
   * Hilfsfunktion: Formular mit aktueller Meldung erneut rendern.
   */
  async function zeigeFormular(erfolg, fehler) {
    let domains = [];
    let skus = [];
    try {
      const daten = await ladeFormulardaten(token);
      domains = daten.domains;
      skus = daten.skus;
    } catch (e) {
      console.error('Fehler beim Nachladen der Formulardaten:', e);
    }
    res.render('formular', {
      upn: durchgefuehrtVon,
      domains,
      skus,
      erfolg,
      fehler,
      // Bei Erfolg keine alten Eingaben mehr vorbelegen.
      eingaben: erfolg ? {} : eingaben,
    });
  }

  // 1. Eingaben prüfen.
  if (!vorname || !nachname || !privateMail || !domain || !skuId) {
    return zeigeFormular(null, 'Bitte füllen Sie alle Felder aus.');
  }
  if (!istPlausibleMail(privateMail)) {
    return zeigeFormular(null, 'Die private E-Mail-Adresse ist nicht gültig.');
  }

  // 2. UPN und Alias bilden.
  const vornameRein = bereinigeNamensteil(vorname);
  const nachnameRein = bereinigeNamensteil(nachname);
  if (!vornameRein || !nachnameRein) {
    return zeigeFormular(
      null,
      'Vor- und Nachname müssen mindestens einen verwertbaren Buchstaben enthalten.'
    );
  }
  const mailNickname = `${vornameRein}.${nachnameRein}`;
  const userPrincipalName = `${mailNickname}@${domain}`;
  const displayName = `${vorname} ${nachname}`;

  // 3. Zufallspasswort generieren.
  const passwort = generierePasswort(20);

  let neuerBenutzer = null;
  let mailVersendet = false;

  try {
    // 4. Benutzer anlegen.
    neuerBenutzer = await graph.createUser(token, {
      displayName,
      mailNickname,
      userPrincipalName,
      passwort,
    });

    // 5. Lizenz zuweisen.
    await graph.assignLicense(token, neuerBenutzer.id, skuId);
  } catch (err) {
    console.error('Fehler beim Anlegen des Benutzers oder der Lizenzzuweisung:', err);
    let meldung = 'Der Benutzer konnte nicht angelegt werden.';
    if (err.status === 403) {
      meldung =
        'Fehlende Berechtigung: Ihr Konto darf keine Benutzer anlegen oder Lizenzen zuweisen. ' +
        'Erforderlich ist die Entra-Rolle "User Administrator" (oder vergleichbar).';
    } else if (err.message) {
      meldung = `Der Benutzer konnte nicht angelegt werden: ${err.message}`;
    }
    return zeigeFormular(null, meldung);
  }

  // 6. Willkommensmail senden.
  try {
    await sendeWillkommensmail({
      empfaenger: privateMail,
      vorname,
      upn: userPrincipalName,
      passwort,
    });
    mailVersendet = true;
  } catch (err) {
    console.error('Fehler beim Versand der Willkommensmail:', err);
    mailVersendet = false;
  }

  // 7. Audit-Eintrag schreiben (OHNE private Mail – nur Flag mail_versendet).
  try {
    await schreibeAuditEintrag({
      durchgefuehrtVon,
      neuerUpn: userPrincipalName,
      lizenzSku: skuId,
      mailVersendet,
    });
  } catch (err) {
    console.error('Fehler beim Schreiben des Audit-Eintrags:', err);
    // Der Benutzer wurde bereits angelegt – wir scheitern hier nicht hart.
  }

  // 8. Erfolgsseite anzeigen.
  if (mailVersendet) {
    return zeigeFormular(
      `Der Benutzer "${userPrincipalName}" wurde erfolgreich angelegt und die Zugangsdaten ` +
        'wurden an die private E-Mail-Adresse versendet.',
      null
    );
  }
  // Benutzer angelegt, aber Mailversand fehlgeschlagen -> als Warnung anzeigen.
  return zeigeFormular(
    null,
    `Der Benutzer "${userPrincipalName}" wurde angelegt, aber die Willkommensmail konnte NICHT ` +
      'versendet werden. Bitte teilen Sie die Zugangsdaten manuell und sicher mit.'
  );
});

module.exports = router;
