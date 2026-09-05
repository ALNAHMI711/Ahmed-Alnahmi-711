***
Template PR body for frontend features: ApiAccounts & Strategy Manager
***

PHASE4: Add ApiAccounts page and Strategy Manager UI (upload + list) with React Query integration.

Features:
- ApiAccounts: list, create modal, test action
- Strategy Manager: upload form and strategies list
- Services: apiAccounts and strategies service modules

Notes:
- Endpoints used: /v1/api-accounts/, /v1/strategies/ (backend endpoints expected to exist)
- UI uses HttpOnly session cookie for auth (withCredentials enabled)
