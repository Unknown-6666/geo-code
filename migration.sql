ALTER TABLE user_economy ADD COLUMN username VARCHAR(100);
ALTER TABLE user_economy ADD COLUMN display_name VARCHAR(100);
ALTER TABLE inventory ADD COLUMN username VARCHAR(100);
ALTER TABLE inventory ADD COLUMN display_name VARCHAR(100);
ALTER TABLE transaction ADD COLUMN username VARCHAR(100);
ALTER TABLE transaction ADD COLUMN display_name VARCHAR(100);