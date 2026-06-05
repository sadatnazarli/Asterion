-- Asterion 0010 - portfolio partial data

ALTER TABLE portfolio_positions ALTER COLUMN quantity DROP NOT NULL;
ALTER TABLE portfolio_positions ALTER COLUMN average_cost DROP NOT NULL;
ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS current_value NUMERIC;
