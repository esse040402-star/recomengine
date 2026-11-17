# Supabase schema and migration workflow

## Production migration history (verified 2026-11-17)

The connected `recommengine` project has **13 applied migrations** in its production ledger. This incremental update folder contains the available production SQL files (`20261117020739` through `20261117020906`, plus the applied reconciliation `20261117050155`) and one clearly identified local bootstrap snapshot (`20261117000000_rebuild_current_public_schema.sql`). The first eight historical SQL bodies are not included in this update folder; their applied versions are verified from the live ledger, not reconstructed from missing files.

Applied production versions:

1. `20261112013753_align_survey_questions_with_updated_questionnaire`
2. `20261112023731_drop_empty_games_backup_table`
3. `20261116014601_secure_functions_and_optimize_indexes`
4. `20261116014953_claim_guest_diagnosis_sessions`
5. `20261116015851_lock_down_public_api_access`
6. `20261116015918_make_guest_session_claim_idempotent`
7. `20261116020153_secure_future_public_object_defaults`
8. `20261116020253_secure_public_sequence_access_defaults`
9. `20261117020739_seed_canonical_survey_options_and_traits`
10. `20261117020827_seed_canonical_option_trait_weights`
11. `20261117020847_seed_canonical_game_trait_tag_rules`
12. `20261117020906_revoke_public_access_and_secure_postgres_defaults`
13. `20261117050155_reconcile_current_public_schema_snapshot`

The first eight historical SQL bodies were not present in the supplied project archive and are not recreated here. Their applied status is based on the live Supabase migration ledger. Do not invent replacement SQL or treat missing historical bodies as pending migrations. The current schema snapshot remains the reproducible bootstrap for a fresh local database.

## Local-only bootstrap snapshot

`20261117000000_rebuild_current_public_schema.sql` is retained so a fresh local Supabase database can be created before the canonical seed migrations run. It is additive/idempotent: it creates missing objects, replaces the known deny-client policies and triggers, and does not drop tables or delete rows. It is intentionally not part of the connected production migration ledger because the live schema already existed before this bootstrap was introduced.

The production reconciliation migration `20261117050155_reconcile_current_public_schema_snapshot.sql` is the exact schema snapshot that was applied to the connected project and recorded in its migration ledger. It is kept as the production history record.

## Unapplied migration drafts

Four previously bundled files were not present in the production ledger. They are preserved under `supabase/archive/unapplied_migrations/` so they cannot be accidentally deployed by `supabase db push`:

- `20261117100000_backend_only_public_access.sql` — duplicates the backend-only grants/policy posture already present in production.
- `20261117100001_idempotent_guest_session_claim.sql` — duplicates the live `claim_guest_diagnosis_sessions` function.
- `20261117100002_secure_default_privileges.sql` — do **not** apply as written; it attempts to alter defaults for `supabase_admin`, which the connected SQL role is not authorized to administer.
- `20261117100003_secure_sequence_access.sql` — duplicates sequence restrictions already applied in production.

These archived files are retained for traceability, not for automatic deployment.

## Fresh local database

From the project root (requires Docker and Supabase CLI):

```powershell
supabase start
supabase db reset
```

The local-only schema snapshot runs before the canonical seed migrations. `seed.sql` can also be re-run where appropriate; it is designed for canonical seed data.

## Existing production project

The connected production project is already at the 13-version history above. Do not run `supabase db reset` against production. Before any future deployment:

```powershell
supabase login
supabase link --project-ref fppojuzgnyolrzwhisbn
supabase migration list
```

Confirm the 13 production versions are applied. The local-only bootstrap snapshot may appear as a pending local migration on a linked checkout; do not blindly run `supabase db push`. Review any pending version against the live schema and migration ledger first.

## Trait model refresh

To refresh existing game rows after changing tag rules, run:

```powershell
python -m scripts.seed_trait_model
```

This script uses the server-side `SUPABASE_SERVICE_KEY` from `.env`; never expose that key in frontend code.
