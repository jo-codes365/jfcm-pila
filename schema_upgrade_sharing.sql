-- Safe, repeatable public-link token upgrade for MySQL/phpMyAdmin.
-- Tokens power Copy Link and Public Files; there are no configurable permissions.
USE file_storage;

-- Add the folder link token only if it does not exist.
SET @sql = IF((SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'folders' AND column_name = 'share_token') = 0,
    'ALTER TABLE folders ADD COLUMN share_token VARCHAR(64) NULL AFTER name', 'SELECT 1');
PREPARE sharing_statement FROM @sql; EXECUTE sharing_statement; DEALLOCATE PREPARE sharing_statement;

SET @sql = IF((SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'folders' AND index_name = 'uq_folders_share_token') = 0,
    'ALTER TABLE folders ADD UNIQUE KEY uq_folders_share_token (share_token)', 'SELECT 1');
PREPARE sharing_statement FROM @sql; EXECUTE sharing_statement; DEALLOCATE PREPARE sharing_statement;

-- Existing folders need a token so Copy Link has a stable public route.
UPDATE folders SET share_token = REPLACE(UUID(), '-', '') WHERE share_token IS NULL;
