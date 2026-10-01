# Phase 1 Record — Supabase Foundation

> Phase records live in `docs/phases/` (architecture §29: PHASES = WHEN).

## CURRENT PHASE DECLARATION (architecture §43)

```text
CURRENT PHASE: Phase 1 COMPLETE (live-verified)
PHASE GOAL: Introduce Supabase authentication and database persistence.
ALLOWED CHANGES: backend/database/, backend/auth/, backend/api/,
                 supabase/migrations/, docs/, .env.example,
                 backend/core/config.py, backend/app.py (router registration only)
NOT IN SCOPE: AWS deployment, SQS, ECS workers, GitHub webhooks/App,
              pgvector migration, frontend auth UI
SUCCESS CRITERIA: User can sign in and repository metadata is persisted securely.
```

## What Was Implemented

| Area | Files |
|---|---|
| Database schema + RLS | `supabase/migrations/00001_init.sql` (14 tables, RLS on all, trigger-created profiles, skill catalog seed) |
| Data access layer | `backend/database/{client,models,repository}.py` |
| Auth | `backend/auth/__init__.py` — Supabase JWT validation dependency |
| REST API | `backend/api/__init__.py` — repositories, jobs, conversations, messages, citations, settings |
| Config | `backend/core/config.py` (SUPABASE_URL/ANON/SERVICE), `.env.example`, requirements (+`supabase`) |
| App wiring | `backend/app.py` includes cloud router (graceful fallback if unavailable) |
| Tests | `backend/test_phase1.py` — 7 checks |
| Docs | `docs/intent.md`, `docs/features.md` |

## Gate Status (architecture §31, §44) — ALL PASSED ✅

- [x] Migration SQL complete and structurally validated
- [x] Backend modules import cleanly; graceful degradation without Supabase
- [x] Auth dependency: 503 when unconfigured, 401 on missing/invalid token
- [x] Routes registered in the FastAPI app; Phase 0 functionality intact
- [x] Documentation updated (intent/features/phase record)
- [x] **Migration applied to live Supabase project — 14/14 tables present**
- [x] **Skill catalog seed verified (9 skills)**
- [x] **Sign-up/sign-in verified end-to-end** (admin create → profile trigger → password sign-in → JWT validated via `auth.get_user`)
- [x] **RLS verified live**: anonymous writes blocked (403), spoofed `user_id` insert blocked (403), anonymous reads return 0 rows, owner insert/read works (201/200)
- [x] Test users/repositories cleaned up (cascade delete confirmed)

## Live Verification Log

```text
apply_migration --check : 14/14 tables present
skills seed             : 9 rows
RLS anon insert         : BLOCKED
auth admin create_user  : OK (profile trigger fired, display_name derived)
auth password sign-in   : OK (JWT issued)
JWT via get_user        : OK (same path as backend/auth dependency)
owner repo insert       : HTTP 201
spoofed user_id insert  : HTTP 403 (WITH CHECK enforced)
anon repo read          : HTTP 200, 0 rows
cleanup                 : user deleted, repo cascade-removed
```

**PHASE 1 COMPLETE — checkpoint: `phase-1-complete`**

## Known Limitations

1. Indexing jobs still execute locally (BackgroundTasks reusing `index_galaxy`).
   This is intentional — Phase 3 replaces execution with SQS + ECS Worker.
2. Frontend does not yet call the new endpoints; auth UI arrives with live Supabase.
3. `chunks.embedding` column intentionally deferred to Phase 4 (pgvector).
4. Anonymous/legacy endpoints (`/api/index`, `/api/clone`, `/ws/chat`) are unchanged
   so existing functionality is not destroyed (Rule 2); they will be migrated
   per-phase later.

## Verification Log

```text
Phase 0 baseline: frontend tsc --noEmit clean; backend core imports OK
Phase 1 gate: 7 passed, 0 failed (backend/test_phase1.py)
supabase SDK: 2.31.0 installed, added to requirements
```
