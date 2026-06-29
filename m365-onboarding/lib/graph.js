// lib/graph.js
// Helfer-Funktionen für den Zugriff auf die Microsoft Graph API mit dem
// delegierten Access-Token aus der Session.
//
// Alle Funktionen erwarten als ersten Parameter das Access-Token (String),
// das in der Session unter req.session.accessToken liegt.

const GRAPH_BASIS = 'https://graph.microsoft.com/v1.0';

/**
 * Führt einen Graph-Aufruf aus und liefert die JSON-Antwort.
 * Bei HTTP-Fehlern wird eine aussagekräftige Exception geworfen, die – falls
 * vorhanden – die Graph-Fehlermeldung enthält.
 *
 * @param {string} token  - delegiertes Access-Token.
 * @param {string} pfad   - Pfad relativ zur Graph-Basis (z.B. "/domains").
 * @param {Object} [optionen] - fetch-Optionen (method, body, ...).
 * @returns {Promise<Object|null>} geparste JSON-Antwort oder null bei 204.
 */
async function graphAnfrage(token, pfad, optionen = {}) {
  const url = pfad.startsWith('http') ? pfad : `${GRAPH_BASIS}${pfad}`;

  const kopf = {
    Authorization: `Bearer ${token}`,
    Accept: 'application/json',
    ...(optionen.headers || {}),
  };

  // Bei Schreibanfragen mit Body den Content-Type setzen.
  if (optionen.body && !kopf['Content-Type']) {
    kopf['Content-Type'] = 'application/json';
  }

  const antwort = await fetch(url, { ...optionen, headers: kopf });

  // 204 No Content (z.B. erfolgreiche Lizenzzuweisung gibt teils 200 mit Body,
  // andere Aktionen 204) – dann gibt es nichts zu parsen.
  if (antwort.status === 204) {
    return null;
  }

  const text = await antwort.text();
  let daten = null;
  if (text) {
    try {
      daten = JSON.parse(text);
    } catch (e) {
      daten = { rohtext: text };
    }
  }

  if (!antwort.ok) {
    const meldung =
      (daten && daten.error && daten.error.message) ||
      `Graph-Anfrage fehlgeschlagen (HTTP ${antwort.status})`;
    const fehler = new Error(meldung);
    fehler.status = antwort.status;
    fehler.graphFehler = daten && daten.error ? daten.error : daten;
    throw fehler;
  }

  return daten;
}

/**
 * Liefert alle im Tenant verifizierten Domains.
 * GET /domains – es werden nur Domains mit isVerified === true zurückgegeben.
 *
 * @param {string} token - delegiertes Access-Token.
 * @returns {Promise<Array<{id: string, isDefault: boolean}>>}
 */
async function getVerifiedDomains(token) {
  const daten = await graphAnfrage(token, '/domains');
  const domains = (daten && daten.value) || [];
  return domains
    .filter((d) => d.isVerified === true)
    .map((d) => ({
      id: d.id,
      isDefault: d.isDefault === true,
    }));
}

/**
 * Liefert die abonnierten SKUs (Lizenzpläne) mit noch freien Einheiten.
 * GET /subscribedSkus
 *
 * Freie Einheiten = prepaidUnits.enabled - consumedUnits.
 * Es werden nur SKUs mit mindestens einer freien Einheit angeboten.
 *
 * @param {string} token - delegiertes Access-Token.
 * @returns {Promise<Array<{skuId: string, skuPartNumber: string, freieEinheiten: number}>>}
 */
async function getAvailableSkus(token) {
  const daten = await graphAnfrage(token, '/subscribedSkus');
  const skus = (daten && daten.value) || [];
  return skus
    .map((s) => {
      const aktiviert = (s.prepaidUnits && s.prepaidUnits.enabled) || 0;
      const verbraucht = s.consumedUnits || 0;
      return {
        skuId: s.skuId,
        skuPartNumber: s.skuPartNumber,
        freieEinheiten: aktiviert - verbraucht,
      };
    })
    .filter((s) => s.freieEinheiten > 0);
}

/**
 * Legt einen neuen Benutzer im Tenant an.
 * POST /users
 *
 * @param {string} token - delegiertes Access-Token.
 * @param {Object} benutzer
 * @param {string} benutzer.displayName        - Anzeigename (z.B. "Max Mustermann").
 * @param {string} benutzer.mailNickname        - Mail-Alias (z.B. "max.mustermann").
 * @param {string} benutzer.userPrincipalName   - vollständiger UPN inkl. Domain.
 * @param {string} benutzer.passwort            - generiertes Initial-Passwort.
 * @returns {Promise<Object>} der angelegte Benutzer (inkl. id und userPrincipalName).
 */
async function createUser(token, { displayName, mailNickname, userPrincipalName, passwort }) {
  const koerper = {
    accountEnabled: true,
    displayName,
    mailNickname,
    userPrincipalName,
    // Nutzungsstandort ist für die Lizenzzuweisung zwingend erforderlich.
    usageLocation: 'DE',
    passwordProfile: {
      password: passwort,
      forceChangePasswordNextSignIn: true,
    },
  };

  return graphAnfrage(token, '/users', {
    method: 'POST',
    body: JSON.stringify(koerper),
  });
}

/**
 * Weist einem Benutzer eine Lizenz (SKU) zu.
 * POST /users/{id}/assignLicense
 *
 * @param {string} token        - delegiertes Access-Token.
 * @param {string} benutzerId   - id oder UPN des Benutzers.
 * @param {string} skuId        - die zuzuweisende skuId.
 * @returns {Promise<Object|null>} die Graph-Antwort.
 */
async function assignLicense(token, benutzerId, skuId) {
  const koerper = {
    addLicenses: [
      {
        skuId,
        // Keine Pläne deaktivieren – die komplette Lizenz wird zugewiesen.
        disabledPlans: [],
      },
    ],
    removeLicenses: [],
  };

  return graphAnfrage(token, `/users/${encodeURIComponent(benutzerId)}/assignLicense`, {
    method: 'POST',
    body: JSON.stringify(koerper),
  });
}

module.exports = {
  graphAnfrage,
  getVerifiedDomains,
  getAvailableSkus,
  createUser,
  assignLicense,
};
