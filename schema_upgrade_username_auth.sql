-- Add optional usernames to existing local-auth accounts.
-- Existing users can continue signing in with their email until a username is assigned.

USE file_storage;

ALTER TABLE users
ADD COLUMN username VARCHAR(20) NULL AFTER email,
ADD UNIQUE KEY uq_users_username (username);