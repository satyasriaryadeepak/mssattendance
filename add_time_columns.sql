-- Migration to add missing time columns
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS morning_time TEXT;
ALTER TABLE attendance ADD COLUMN IF NOT EXISTS afternoon_time TEXT;
