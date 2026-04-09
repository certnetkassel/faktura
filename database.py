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
            kleinunternehmer_text TEXT DEFAULT 'Gemäß §19 UStG wird keine Umsatzsteuer berechnet.',
            password_hash TEXT DEFAULT '',
            invoice_prefix TEXT DEFAULT 'RE',
            offer_prefix TEXT DEFAULT 'AN',
            credit_prefix TEXT DEFAULT 'GS',
            next_invoice_nr INTEGER DEFAULT 1,
            next_offer_nr INTEGER DEFAULT 1,
            next_credit_nr INTEGER DEFAULT 1
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


if __name__ == '__main__':
    init_db()
    print("Datenbank erstellt.")
