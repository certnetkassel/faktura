// lib/password.js
// Erzeugt ein sicheres Zufallspasswort mit dem Node-Modul "crypto".
//
// Anforderungen:
// - mindestens 16 Zeichen
// - enthält Groß- und Kleinbuchstaben, Ziffern und Sonderzeichen
// - erfüllt die Microsoft-365-Komplexitätsregeln
//   (mindestens drei von vier Zeichenkategorien)

const crypto = require('crypto');

// Zeichensätze. Mehrdeutige Zeichen (O/0, l/1/I) werden bewusst vermieden,
// damit das Initial-Passwort gut ablesbar bleibt.
const GROSS = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
const KLEIN = 'abcdefghijkmnpqrstuvwxyz';
const ZIFFERN = '23456789';
// Sonderzeichen, die von Microsoft akzeptiert werden.
const SONDER = '!@#$%^&*()-_=+[]{}?';

const ALLE = GROSS + KLEIN + ZIFFERN + SONDER;

/**
 * Wählt mit kryptografisch sicherem Zufall ein Zeichen aus einer Zeichenkette.
 * Es wird Rejection-Sampling verwendet, um eine gleichverteilte Auswahl ohne
 * Modulo-Bias zu garantieren.
 *
 * @param {string} zeichen - Pool, aus dem gewählt wird.
 * @returns {string} ein einzelnes Zeichen.
 */
function zufallsZeichen(zeichen) {
  const grenze = Math.floor(256 / zeichen.length) * zeichen.length;
  let wert;
  do {
    wert = crypto.randomBytes(1)[0];
  } while (wert >= grenze);
  return zeichen[wert % zeichen.length];
}

/**
 * Mischt ein Array kryptografisch sicher (Fisher-Yates mit crypto-Zufall).
 *
 * @param {Array} feld
 * @returns {Array} dasselbe, nun gemischte Array.
 */
function mischen(feld) {
  for (let i = feld.length - 1; i > 0; i--) {
    const grenze = Math.floor(256 / (i + 1)) * (i + 1);
    let wert;
    do {
      wert = crypto.randomBytes(1)[0];
    } while (wert >= grenze);
    const j = wert % (i + 1);
    [feld[i], feld[j]] = [feld[j], feld[i]];
  }
  return feld;
}

/**
 * Generiert ein sicheres Zufallspasswort.
 *
 * @param {number} [laenge=20] - gewünschte Länge (mindestens 16).
 * @returns {string} das generierte Passwort.
 */
function generierePasswort(laenge = 20) {
  const echteLaenge = Math.max(16, laenge);

  // Mindestens je ein Zeichen aus jeder Kategorie garantieren.
  const zeichen = [
    zufallsZeichen(GROSS),
    zufallsZeichen(KLEIN),
    zufallsZeichen(ZIFFERN),
    zufallsZeichen(SONDER),
  ];

  // Restliche Stellen mit beliebigen Zeichen aus dem Gesamtpool auffüllen.
  while (zeichen.length < echteLaenge) {
    zeichen.push(zufallsZeichen(ALLE));
  }

  // Reihenfolge mischen, damit die garantierten Zeichen nicht immer vorne stehen.
  return mischen(zeichen).join('');
}

module.exports = {
  generierePasswort,
};
