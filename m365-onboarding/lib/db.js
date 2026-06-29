// lib/db.js
// Stellt einen PostgreSQL-Verbindungspool bereit und bietet eine Funktion
// zum Schreiben von Audit-Einträgen.
//
// WICHTIG (Datenschutz): Die private E-Mail-Adresse des neuen Benutzers wird
// NICHT gespeichert. Im Audit-Log wird lediglich der boolesche Wert
// "mail_versendet" hinterlegt.

const { Pool } = require('pg');

// Verbindungspool aus der Umgebungsvariable DATABASE_URL aufbauen.
// Beispiel: postgres://user:pass@host:5432/datenbank
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

// Fehler aus inaktiven Pool-Clients protokollieren, damit der Prozess nicht
// unbemerkt abstürzt.
pool.on('error', (err) => {
  console.error('Unerwarteter Fehler im PostgreSQL-Pool:', err);
});

/**
 * Schreibt einen Audit-Eintrag in die Tabelle onboarding_log.
 *
 * @param {Object} eintrag
 * @param {string} eintrag.durchgefuehrtVon - UPN des eingeloggten Mitarbeiters.
 * @param {string} eintrag.neuerUpn         - UPN des neu angelegten Benutzers.
 * @param {string} eintrag.lizenzSku        - skuPartNumber/skuId der zugewiesenen Lizenz.
 * @param {boolean} eintrag.mailVersendet   - Ob die Willkommensmail versendet wurde.
 * @returns {Promise<Object>} Der eingefügte Datensatz.
 */
async function schreibeAuditEintrag({ durchgefuehrtVon, neuerUpn, lizenzSku, mailVersendet }) {
  const sql = `
    INSERT INTO onboarding_log (durchgefuehrt_von, neuer_upn, lizenz_sku, mail_versendet)
    VALUES ($1, $2, $3, $4)
    RETURNING id, erstellt_am, durchgefuehrt_von, neuer_upn, lizenz_sku, mail_versendet
  `;
  const werte = [durchgefuehrtVon, neuerUpn, lizenzSku, mailVersendet];
  const ergebnis = await pool.query(sql, werte);
  return ergebnis.rows[0];
}

module.exports = {
  pool,
  schreibeAuditEintrag,
};
