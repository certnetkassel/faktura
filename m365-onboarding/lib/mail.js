// lib/mail.js
// Versendet die Willkommensmail über nodemailer an die private Adresse des
// neuen Benutzers. Die SMTP-Parameter stammen ausschließlich aus
// Umgebungsvariablen (IONOS SMTP).

const nodemailer = require('nodemailer');

// Anmelde-Portal von Microsoft 365.
const PORTAL_LINK = 'https://portal.office.com';

/**
 * Erstellt den nodemailer-Transport aus den Umgebungsvariablen.
 *
 * @returns {import('nodemailer').Transporter}
 */
function erstelleTransport() {
  const port = parseInt(process.env.SMTP_PORT, 10) || 587;
  return nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port,
    // Port 465 nutzt implizites TLS (secure=true), 587 nutzt STARTTLS.
    secure: port === 465,
    auth: {
      user: process.env.SMTP_USER,
      pass: process.env.SMTP_PASS,
    },
  });
}

/**
 * Sendet die Willkommensmail mit Zugangsdaten an die private Adresse.
 *
 * @param {Object} optionen
 * @param {string} optionen.empfaenger - private E-Mail-Adresse.
 * @param {string} optionen.vorname    - Vorname für die persönliche Anrede.
 * @param {string} optionen.upn        - neuer User Principal Name (Anmeldename).
 * @param {string} optionen.passwort   - generiertes Initial-Passwort.
 * @returns {Promise<Object>} Ergebnis des Sendevorgangs (nodemailer-Info).
 */
async function sendeWillkommensmail({ empfaenger, vorname, upn, passwort }) {
  const transport = erstelleTransport();

  const betreff = 'Ihr neues Microsoft-365-Konto – Zugangsdaten';

  const text = [
    `Hallo ${vorname},`,
    '',
    'für Sie wurde ein neues Microsoft-365-Konto eingerichtet.',
    '',
    'Ihre Zugangsdaten:',
    `  Anmeldename (UPN): ${upn}`,
    `  Initial-Passwort:  ${passwort}`,
    '',
    'WICHTIG: Aus Sicherheitsgründen müssen Sie das Passwort bei der ersten',
    'Anmeldung ändern.',
    '',
    `Anmeldung über: ${PORTAL_LINK}`,
    '',
    'Bei Fragen wenden Sie sich bitte an Ihre IT-Abteilung.',
    '',
    'Mit freundlichen Grüßen',
    'Ihr IT-Team',
  ].join('\n');

  const html = `
    <div style="font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #1f2937; line-height: 1.6;">
      <p>Hallo ${escapeHtml(vorname)},</p>
      <p>für Sie wurde ein neues Microsoft-365-Konto eingerichtet.</p>
      <p><strong>Ihre Zugangsdaten:</strong></p>
      <table style="border-collapse: collapse;">
        <tr>
          <td style="padding: 4px 12px 4px 0;"><strong>Anmeldename (UPN):</strong></td>
          <td style="padding: 4px 0;"><code>${escapeHtml(upn)}</code></td>
        </tr>
        <tr>
          <td style="padding: 4px 12px 4px 0;"><strong>Initial-Passwort:</strong></td>
          <td style="padding: 4px 0;"><code>${escapeHtml(passwort)}</code></td>
        </tr>
      </table>
      <p style="color: #b91c1c;"><strong>Wichtig:</strong> Aus Sicherheitsgründen müssen Sie das
        Passwort bei der ersten Anmeldung ändern.</p>
      <p>Anmeldung über:
        <a href="${PORTAL_LINK}">${PORTAL_LINK}</a>
      </p>
      <p>Bei Fragen wenden Sie sich bitte an Ihre IT-Abteilung.</p>
      <p>Mit freundlichen Grüßen<br>Ihr IT-Team</p>
    </div>
  `;

  return transport.sendMail({
    from: process.env.MAIL_FROM,
    to: empfaenger,
    subject: betreff,
    text,
    html,
  });
}

/**
 * Einfaches HTML-Escaping, um Sonderzeichen in der HTML-Mail abzusichern.
 *
 * @param {string} wert
 * @returns {string}
 */
function escapeHtml(wert) {
  return String(wert)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

module.exports = {
  sendeWillkommensmail,
};
