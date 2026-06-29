-- db/schema.sql
-- Datenbankschema für das M365-Onboarding-Tool.
-- Einspielen z.B. mit:  psql "$DATABASE_URL" -f db/schema.sql

-- ---------------------------------------------------------------------------
-- Audit-Log für durchgeführte Onboardings.
-- WICHTIG (Datenschutz): Die private E-Mail-Adresse wird NICHT gespeichert,
-- nur der boolesche Wert mail_versendet.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS onboarding_log (
    id                SERIAL PRIMARY KEY,
    erstellt_am       TIMESTAMPTZ NOT NULL DEFAULT now(),
    durchgefuehrt_von TEXT        NOT NULL,   -- UPN des eingeloggten Mitarbeiters
    neuer_upn         TEXT        NOT NULL,   -- UPN des neu angelegten Benutzers
    lizenz_sku        TEXT,                   -- zugewiesene SKU (skuId/Part-Number)
    mail_versendet    BOOLEAN     NOT NULL DEFAULT false
);

-- ---------------------------------------------------------------------------
-- Session-Tabelle für connect-pg-simple.
-- Struktur gemäß Vorgabe des Pakets (node_modules/connect-pg-simple/table.sql).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "session" (
    "sid"    VARCHAR      NOT NULL COLLATE "default",
    "sess"   JSON         NOT NULL,
    "expire" TIMESTAMP(6) NOT NULL
)
WITH (OIDS=FALSE);

-- Primärschlüssel nur anlegen, falls noch nicht vorhanden.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'session_pkey'
    ) THEN
        ALTER TABLE "session"
            ADD CONSTRAINT "session_pkey" PRIMARY KEY ("sid") NOT DEFERRABLE INITIALLY IMMEDIATE;
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS "IDX_session_expire" ON "session" ("expire");
