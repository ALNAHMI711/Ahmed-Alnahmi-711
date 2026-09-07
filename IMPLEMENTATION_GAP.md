# Implementation and operational gaps

This repository is **not LIVE-ready**. The durable fill/position projection and authenticated WebSocket hub are implemented, but the following are deliberately blocked rather than simulated: real order placement and TP/SL management; owned account authorization; 2FA/device trust; Telegram provider ingestion; durable distributed workers/Redis fan-out; historical market-data ingestion/backtest persistence and reporting; backup/restore operations; and operational Binance credential verification/rotation. No UI endpoint may invent balances, PnL, fills, or status.

LIVE operation requires a reviewed PostgreSQL migration runner, encrypted secrets in an external secret manager, account ownership/RBAC, testnet verification, explicit human approval, static egress IP allow-list, and observability/incident procedures.
