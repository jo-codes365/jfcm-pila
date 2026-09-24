USE railway;

-- Existing accounts retain their current authenticated workspace access.
ALTER TABLE users
  MODIFY COLUMN email VARCHAR(255) NULL,
  ADD COLUMN role VARCHAR(20) NULL DEFAULT 'admin' AFTER password_hash;

ALTER TABLE users
  ADD CONSTRAINT chk_users_role CHECK (role IS NULL OR role IN ('admin', 'super-admin'));

-- This is a Werkzeug scrypt password hash for the requested initial account.
-- The plaintext password is never stored in the database.
INSERT INTO users (email, username, password_hash, role)
VALUES (NULL, 'Harrycillian', 'scrypt:32768:8:1$JVs64xFakb0Zq0zZ$2297500b0c5e7f78f93461618d6a9dd9a6244b06dbc094338ef6da132abef19e851fcd98f4b3c0ad65af2d33376f862c62e9c824ced76954a4e0a500759c5864', 'super-admin')
ON DUPLICATE KEY UPDATE role = 'super-admin';
