-- Reset users table to use local email/password authentication
-- This removes all Google OAuth fields and replaces them with email and password_hash

USE file_storage;

-- Drop the existing users table and related foreign keys
ALTER TABLE folders DROP FOREIGN KEY fk_folders_user;
ALTER TABLE files DROP FOREIGN KEY fk_files_user;

DROP TABLE IF EXISTS users;

-- Create new users table with email/password authentication
CREATE TABLE users (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(20) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    UNIQUE KEY uq_users_username (username),
    KEY idx_users_created_at (created_at)
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Restore foreign key constraints
ALTER TABLE folders
ADD CONSTRAINT fk_folders_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE files
ADD CONSTRAINT fk_files_user 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
