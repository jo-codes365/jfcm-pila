-- Safe, repeatable Event public-link token upgrade for MySQL/phpMyAdmin.
-- Select the file_storage database in phpMyAdmin, then paste and run this entire file.
-- No DELIMITER or stored-procedure support is required.
-- Tokens power Copy Link and Public Files; there are no configurable permissions.

USE file_storage;

-- Add the Event link token only when it is absent.
SET @sql = IF(
    (SELECT COUNT(*) FROM information_schema.columns
     WHERE table_schema = DATABASE() AND table_name = 'events' AND column_name = 'share_token') = 0,
    'ALTER TABLE events ADD COLUMN share_token VARCHAR(64) NULL',
    'SELECT 1'
);
PREPARE event_share_statement FROM @sql;
EXECUTE event_share_statement;
DEALLOCATE PREPARE event_share_statement;

-- Retain one legacy token if duplicates exist, then backfill missing tokens.
UPDATE events AS duplicate_event
JOIN events AS retained_event
    ON duplicate_event.share_token = retained_event.share_token
    AND duplicate_event.id > retained_event.id
SET duplicate_event.share_token = NULL
WHERE duplicate_event.share_token IS NOT NULL;

-- Add the unique index only when it is absent.
SET @sql = IF(
    (SELECT COUNT(*) FROM information_schema.statistics
     WHERE table_schema = DATABASE() AND table_name = 'events' AND index_name = 'uq_events_share_token') = 0,
    'ALTER TABLE events ADD UNIQUE KEY uq_events_share_token (share_token)',
    'SELECT 1'
);
PREPARE event_share_statement FROM @sql;
EXECUTE event_share_statement;
DEALLOCATE PREPARE event_share_statement;

UPDATE events SET share_token = REPLACE(UUID(), '-', '') WHERE share_token IS NULL;
