USE file_storage;

ALTER TABLE folders ADD COLUMN IF NOT EXISTS accessed_at TIMESTAMP NULL AFTER created_at;
ALTER TABLE files ADD COLUMN IF NOT EXISTS accessed_at TIMESTAMP NULL AFTER uploaded_at;
