USE file_storage;

CREATE TABLE IF NOT EXISTS events (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    name VARCHAR(255) NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR(32) NOT NULL DEFAULT 'event',
    share_token VARCHAR(64) NULL,
    is_starred BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_events_share_token (share_token),
    KEY idx_events_user (user_id, is_deleted, event_date),
    CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

ALTER TABLE events ADD COLUMN IF NOT EXISTS event_type VARCHAR(32) NOT NULL DEFAULT 'event' AFTER event_date;
ALTER TABLE events ADD COLUMN IF NOT EXISTS share_token VARCHAR(64) NULL AFTER event_type;
ALTER TABLE events ADD UNIQUE KEY uq_events_share_token (share_token);
ALTER TABLE folders ADD COLUMN IF NOT EXISTS event_id INT UNSIGNED NULL AFTER parent_id;
ALTER TABLE files ADD COLUMN IF NOT EXISTS event_id INT UNSIGNED NULL AFTER folder_id;
ALTER TABLE folders ADD KEY idx_folders_user_event (user_id, event_id, is_deleted);
ALTER TABLE files ADD KEY idx_files_user_event (user_id, event_id, is_deleted);
ALTER TABLE folders ADD CONSTRAINT fk_folders_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL;
ALTER TABLE files ADD CONSTRAINT fk_files_event FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE SET NULL;
