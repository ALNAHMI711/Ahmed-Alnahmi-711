-- Durable exchange fill ledger and current position projections.
CREATE TABLE IF NOT EXISTS exchange_trades (
 id VARCHAR(36) PRIMARY KEY, account_id VARCHAR(36) NOT NULL REFERENCES api_accounts(id), market VARCHAR(32) NOT NULL, symbol VARCHAR(32) NOT NULL,
 exchange_trade_id VARCHAR(96) NOT NULL, exchange_order_id VARCHAR(96), side VARCHAR(4) NOT NULL,
 quantity NUMERIC(38,18) NOT NULL, price NUMERIC(38,18) NOT NULL, quote_quantity NUMERIC(38,18) NOT NULL,
 fee NUMERIC(38,18) NOT NULL DEFAULT 0, fee_asset VARCHAR(32), realized_pnl NUMERIC(38,18), occurred_at TIMESTAMP NOT NULL, created_at TIMESTAMP NOT NULL,
 CONSTRAINT uq_exchange_trade UNIQUE(account_id, market, exchange_trade_id));
CREATE TABLE IF NOT EXISTS exchange_positions (
 id VARCHAR(36) PRIMARY KEY, account_id VARCHAR(36) NOT NULL REFERENCES api_accounts(id), market VARCHAR(32) NOT NULL, symbol VARCHAR(32) NOT NULL,
 quantity NUMERIC(38,18) NOT NULL DEFAULT 0, average_entry_price NUMERIC(38,18), mark_price NUMERIC(38,18), realized_pnl NUMERIC(38,18) NOT NULL DEFAULT 0,
 unrealized_pnl NUMERIC(38,18), fees NUMERIC(38,18) NOT NULL DEFAULT 0, funding NUMERIC(38,18) NOT NULL DEFAULT 0, state VARCHAR(16) NOT NULL DEFAULT 'CLOSED', version INTEGER NOT NULL DEFAULT 0, updated_at TIMESTAMP NOT NULL,
 CONSTRAINT uq_exchange_position UNIQUE(account_id, market, symbol));
CREATE TABLE IF NOT EXISTS projection_events (event_key VARCHAR(255) PRIMARY KEY, account_id VARCHAR(36) NOT NULL, kind VARCHAR(32) NOT NULL, occurred_at TIMESTAMP NOT NULL, created_at TIMESTAMP NOT NULL);
CREATE TABLE IF NOT EXISTS exchange_orders (
 id VARCHAR(36) PRIMARY KEY, account_id VARCHAR(36) NOT NULL REFERENCES api_accounts(id), market VARCHAR(32) NOT NULL, symbol VARCHAR(32) NOT NULL, client_request_id VARCHAR(64) NOT NULL, exchange_order_id VARCHAR(96) UNIQUE, side VARCHAR(4) NOT NULL, order_type VARCHAR(32) NOT NULL, quantity NUMERIC(38,18) NOT NULL, status VARCHAR(24) NOT NULL DEFAULT 'NEW', created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL, CONSTRAINT uq_exchange_order_request UNIQUE(account_id, client_request_id));
CREATE TABLE IF NOT EXISTS kill_switches (id VARCHAR(32) PRIMARY KEY, enabled BOOLEAN NOT NULL DEFAULT false, updated_at TIMESTAMP NOT NULL, updated_by VARCHAR(36));
CREATE TABLE IF NOT EXISTS api_account_owners (account_id VARCHAR(36) NOT NULL REFERENCES api_accounts(id), user_id VARCHAR(36) NOT NULL REFERENCES users(id), PRIMARY KEY(account_id,user_id));
CREATE TABLE IF NOT EXISTS conditional_orders (id VARCHAR(36) PRIMARY KEY, account_id VARCHAR(36) NOT NULL REFERENCES api_accounts(id), position_id VARCHAR(36) REFERENCES exchange_positions(id), parent_order_id VARCHAR(36) REFERENCES exchange_orders(id), symbol VARCHAR(32) NOT NULL, market VARCHAR(32) NOT NULL, kind VARCHAR(16) NOT NULL, side VARCHAR(4) NOT NULL, quantity NUMERIC(38,18) NOT NULL, trigger_price NUMERIC(38,18), trail_offset NUMERIC(38,18), status VARCHAR(24) NOT NULL DEFAULT 'ACTIVE', idempotency_key VARCHAR(64) NOT NULL, exchange_order_id VARCHAR(96), created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL, CONSTRAINT uq_conditional_request UNIQUE(account_id,idempotency_key));
