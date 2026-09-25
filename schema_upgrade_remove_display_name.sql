USE railway;

SET @drop_display_name_sql = (
  SELECT IF(
    EXISTS (
      SELECT 1 FROM information_schema.columns
      WHERE table_schema = DATABASE()
        AND table_name = 'user_preferences'
        AND column_name = 'display_name'
    ),
    'ALTER TABLE user_preferences DROP COLUMN display_name',
    'SELECT 1'
  )
);
PREPARE drop_display_name_stmt FROM @drop_display_name_sql;
EXECUTE drop_display_name_stmt;
DEALLOCATE PREPARE drop_display_name_stmt;
