USE file_storage;

ALTER TABLE files ADD COLUMN share_token VARCHAR(64) NULL AFTER mime_type;
UPDATE files SET share_token = CONCAT(SHA2(CONCAT(id, UUID(), RAND()), 256)) WHERE share_token IS NULL;
ALTER TABLE files MODIFY share_token VARCHAR(64) NOT NULL;
ALTER TABLE files ADD UNIQUE KEY uq_files_share_token (share_token);
