import sqlite3
import os
from config import DATABASE


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            company_name TEXT DEFAULT '',
            owner_name TEXT DEFAULT '',
            street TEXT DEFAULT '',
            zip TEXT DEFAULT '',
            city TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            tax_number TEXT DEFAULT '',
            bank_name TEXT DEFAULT '',
            iban TEXT DEFAULT '',
            bic TEXT DEFAULT '',
            logo_dark TEXT DEFAULT '',
            logo_light TEXT DEFAULT '',
            smtp_host TEXT DEFAULT 'smtp.office365.com',
            smtp_port INTEGER DEFAULT 587,
            smtp_user TEXT DEFAULT '',
            smtp_pass TEXT DEFAULT '',
            smtp_from TEXT DEFAULT '',
            mail_method TEXT DEFAULT 'smtp',
            graph_tenant_id TEXT DEFAULT '',
            graph_client_id TEXT DEFAULT '',
            graph_client_secret TEXT DEFAULT '',
            graph_sender TEXT DEFAULT '',
            graph_save_sent INTEGER DEFAULT 1,
            kleinunternehmer_text TEXT DEFAULT 'Gemäß §19 UStG wird keine Umsatzsteuer berechnet.',
            password_hash TEXT DEFAULT '',
            invoice_prefix TEXT DEFAULT 'RE',
            offer_prefix TEXT DEFAULT 'AN',
            credit_prefix TEXT DEFAULT 'GS',
            next_invoice_nr INTEGER DEFAULT 1,
            next_offer_nr INTEGER DEFAULT 1,
            next_credit_nr INTEGER DEFAULT 1,
            logo_width_cm REAL DEFAULT 4.0,
            logo_sidebar_px INTEGER DEFAULT 200
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_nr TEXT UNIQUE NOT NULL,
            company TEXT DEFAULT '',
            salutation TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            last_name TEXT NOT NULL,
            street TEXT DEFAULT '',
            zip TEXT DEFAULT '',
            city TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_nr TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            unit TEXT DEFAULT 'Stunde',
            price REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_nr TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            valid_until TEXT,
            status TEXT DEFAULT 'Entwurf',
            notes TEXT DEFAULT '',
            total REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS offer_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            article_id INTEGER,
            position INTEGER DEFAULT 1,
            description TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            unit TEXT DEFAULT 'Stunde',
            price REAL DEFAULT 0.0,
            total REAL DEFAULT 0.0,
            FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_nr TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            offer_id INTEGER,
            date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Entwurf',
            notes TEXT DEFAULT '',
            total REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (offer_id) REFERENCES offers(id)
        );

        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            article_id INTEGER,
            position INTEGER DEFAULT 1,
            description TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            unit TEXT DEFAULT 'Stunde',
            price REAL DEFAULT 0.0,
            total REAL DEFAULT 0.0,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        );

        CREATE TABLE IF NOT EXISTS credits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_nr TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            invoice_id INTEGER,
            date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            total REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );

        CREATE TABLE IF NOT EXISTS credit_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_id INTEGER NOT NULL,
            article_id INTEGER,
            position INTEGER DEFAULT 1,
            description TEXT NOT NULL,
            quantity REAL DEFAULT 1,
            unit TEXT DEFAULT 'Stunde',
            price REAL DEFAULT 0.0,
            total REAL DEFAULT 0.0,
            FOREIGN KEY (credit_id) REFERENCES credits(id) ON DELETE CASCADE,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            level INTEGER DEFAULT 1,
            date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            fee REAL DEFAULT 0.0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );

        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL,
            doc_id INTEGER NOT NULL,
            recipient TEXT NOT NULL,
            subject TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Ensure settings row exists
    c.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")
    conn.commit()
    conn.close()

    migrate_db()


# Nachträglich ergänzte Spalten der settings-Tabelle.
# CREATE TABLE IF NOT EXISTS lässt bestehende Datenbanken unverändert,
# deshalb werden fehlende Spalten hier einzeln nachgezogen.
SETTINGS_MIGRATIONS = [
    ('logo_width_cm', 'REAL DEFAULT 4.0'),
    ('logo_sidebar_px', 'INTEGER DEFAULT 200'),
    # E-Mail-Versand über Microsoft Graph (Alternative zu SMTP)
    ('mail_method', "TEXT DEFAULT 'smtp'"),
    ('graph_tenant_id', "TEXT DEFAULT ''"),
    ('graph_client_id', "TEXT DEFAULT ''"),
    ('graph_client_secret', "TEXT DEFAULT ''"),
    ('graph_sender', "TEXT DEFAULT ''"),
    ('graph_save_sent', 'INTEGER DEFAULT 1'),
]


def migrate_db():
    """Ergänzt fehlende Spalten in bestehenden Datenbanken. Idempotent."""
    conn = get_db()
    c = conn.cursor()
    existing = {row['name'] for row in c.execute("PRAGMA table_info(settings)")}
    for column, definition in SETTINGS_MIGRATIONS:
        if column not in existing:
            c.execute(f"ALTER TABLE settings ADD COLUMN {column} {definition}")

    # Benutzerverwaltung: users-Tabelle in bestehenden Datenbanken nachziehen
    # und den Startbenutzer aus dem bisherigen Einzel-Passwort übernehmen,
    # damit die gewohnte Anmeldung (jetzt mit E-Mail) weiter funktioniert.
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        first_name TEXT DEFAULT '',
        last_name TEXT DEFAULT '',
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        row = c.execute("SELECT password_hash FROM settings WHERE id=1").fetchone()
        pw_hash = row['password_hash'] if row else ''
        if pw_hash:
            c.execute(
                "INSERT INTO users (email, password_hash, first_name, last_name, is_admin) "
                "VALUES (?, ?, ?, ?, 1)",
                ['dirk@dirkhildebrand.de', pw_hash, 'Dirk', 'Hildebrand'])

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print("Datenbank erstellt.")
