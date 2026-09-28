-- Allow usernames of any length accepted by the application (minimum 3 characters).
ALTER TABLE users MODIFY COLUMN username VARCHAR(255) NOT NULL;
ALTER TABLE audit_logs MODIFY COLUMN username VARCHAR(255) NOT NULL;
