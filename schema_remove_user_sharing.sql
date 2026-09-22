-- Remove retired sharing data and controls from an existing database.
-- Public tokens are preserved because they power Copy Link and Public Files.
USE file_storage;

DROP TABLE IF EXISTS event_user_shares;
DROP TABLE IF EXISTS file_user_shares;
DROP TABLE IF EXISTS folder_user_shares;

UPDATE files
SET share_token = REPLACE(UUID(), '-', '')
WHERE share_token IS NULL;

UPDATE folders
SET share_token = REPLACE(UUID(), '-', '')
WHERE share_token IS NULL;

UPDATE events
SET share_token = REPLACE(UUID(), '-', '')
WHERE share_token IS NULL;


ALTER TABLE files
DROP COLUMN share_permission,
DROP COLUMN is_share_link_enabled;

ALTER TABLE folders
DROP COLUMN share_permission,
DROP COLUMN is_share_link_enabled;

ALTER TABLE events
DROP COLUMN share_permission,
DROP COLUMN is_share_link_enabled;