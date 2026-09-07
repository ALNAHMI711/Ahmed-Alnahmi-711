-- Add durable trailing state and diagnostics for conditional orders.
-- This migration is written for both PostgreSQL and SQLite compatibility.

BEGIN;

-- For SQLite, ALTER TABLE ADD COLUMN is supported but IF NOT EXISTS is not in older SQLite versions.
-- We detect by attempting to add the column and ignoring errors, but here we write migrations assuming manual application in CI.

ALTER TABLE conditional_orders ADD COLUMN trail_anchor NUMERIC(38,18);
ALTER TABLE conditional_orders ADD COLUMN trail_last_mark NUMERIC(38,18);
ALTER TABLE conditional_orders ADD COLUMN quantity_remaining NUMERIC(38,18);
ALTER TABLE conditional_orders ADD COLUMN last_error TEXT;

COMMIT;
