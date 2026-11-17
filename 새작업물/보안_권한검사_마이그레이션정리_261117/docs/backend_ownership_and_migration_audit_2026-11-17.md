# Backend ownership and migration reconciliation audit — 2026-11-17

## 1. Backend user ownership

### Result

The current FastAPI code already checks ownership before using the service-role Supabase client for session-scoped data. `app/routers/sessions.py::load_session()` loads the session by ID and returns HTTP 403 when `diagnosis_sessions.user_id` is set to a different user than the verified request identity. The guard is used by:

- `PUT /api/sessions/{session_id}/answers`
- `POST /api/sessions/{session_id}/complete`
- `GET /api/sessions/{session_id}/result`
- `POST /api/ai/explain`
- `GET /api/ai/deals`

`optional_user_id()` validates bearer tokens through Supabase Auth or reads the signed server session cookie. It does not trust a caller-supplied user ID in the request body. Account state reads/writes are scoped to the UID from the signed session cookie.

Guest sessions (`diagnosis_sessions.user_id IS NULL`) remain accessible by their unguessable session UUID until claimed. Once claimed, the same owner check applies. This is the existing guest-flow behavior, not cross-account access to another registered user's session.

`claim_guest_diagnosis_sessions` is executable only by `service_role`; it only claims completed sessions whose owner is NULL or already equals the authenticated account ID. The API supplies that account ID from the successful signup/login result.

### Regression coverage added

`tests/test_api_mock.py::test_session_ownership` now checks that Bob receives 403 when trying to read Alice's result, save answers, complete Alice's session, explain a recommendation, or load deals. Alice remains able to read her own result; invalid bearer tokens still receive 401.

## 2. Production migration reconciliation

The connected project migration ledger was verified to contain 13 applied versions, ending in `20261117050155_reconcile_current_public_schema_snapshot`.

The reconciliation snapshot is additive/idempotent and was applied through the Supabase migration mechanism. Post-apply verification:

- public base tables: 19
- tables with RLS enabled: 19
- direct table grants to `anon` / `authenticated`: 0
- `service_role` table grants: 133
- diagnosis sessions: 5
- diagnosis answers: 28
- analysis reports: 4
- analysis scores: 4

The four extra `20261117100000`–`20261117100003` drafts were not in the production ledger. They have been moved out of the active migrations directory and preserved under `supabase/archive/unapplied_migrations/`. In particular, `20261117100002_secure_default_privileges.sql` must not be deployed as written because it tries to alter defaults for `supabase_admin`, which the connected SQL role cannot administer.

The earlier `20261117000000_rebuild_current_public_schema.sql` remains as the local bootstrap migration so fresh local resets can create the schema before seed migrations. The applied production reconciliation file records the exact snapshot under its actual production version. The README now distinguishes this local-only bootstrap from the production migration ledger and warns against blindly pushing pending local migrations.

## 3. Remaining security advisory

Supabase Security Advisor still reports `Leaked Password Protection Disabled`. This is an Auth dashboard setting, not a migration mismatch, and was not changed in this pass.

## Scope excluded by request

Game data ingestion / per-game trait score generation and the real signup → survey → analysis → game recommendation → persistence end-to-end test are intentionally deferred.
