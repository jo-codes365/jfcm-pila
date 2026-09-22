USE file_storage;

CREATE TABLE IF NOT EXISTS folders (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT UNSIGNED NOT NULL,
    parent_id INT UNSIGNED NULL,
    original_parent_id INT UNSIGNED NULL,
    name VARCHAR(255) NOT NULL,
    is_starred BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_folders_user_parent (user_id, parent_id, is_deleted),
    CONSTRAINT fk_folders_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_folders_parent FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE SET NULL
) ENGINE=InnoDB;

ALTER TABLE files ADD COLUMN IF NOT EXISTS folder_id INT UNSIGNED NULL AFTER share_token;
ALTER TABLE files ADD COLUMN IF NOT EXISTS original_folder_id INT UNSIGNED NULL AFTER folder_id;
ALTER TABLE files ADD COLUMN IF NOT EXISTS is_starred BOOLEAN NOT NULL DEFAULT FALSE AFTER original_folder_id;
ALTER TABLE files ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE AFTER is_starred;
ALTER TABLE files ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL AFTER is_deleted;
ALTER TABLE files ADD KEY idx_files_user_folder (user_id, folder_id, is_deleted);
ALTER TABLE files ADD CONSTRAINT fk_files_folder FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL;
