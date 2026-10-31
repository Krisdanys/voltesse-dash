-- Additive migration. Apply after the existing db/schema.sql. No driver tables changed.
CREATE TABLE IF NOT EXISTS web_auth_session (
    token_hash TEXT PRIMARY KEY,
    technician_id INT NOT NULL REFERENCES technician_user(technician_id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS web_auth_session_expiry ON web_auth_session(expires_at);
CREATE TABLE IF NOT EXISTS web_login_throttle (
    bucket TEXT PRIMARY KEY,
    attempts INT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS technician_preferences (
    technician_id INT PRIMARY KEY REFERENCES technician_user(technician_id) ON DELETE CASCADE,
    warning_temp INT NOT NULL DEFAULT 60 CHECK (warning_temp BETWEEN 40 AND 110),
    warning_battery INT NOT NULL DEFAULT 20 CHECK (warning_battery BETWEEN 5 AND 40)
);
