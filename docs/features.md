# Features — What RepoVerse AI Can Do

> Features define WHAT. Status reflects the current phase plan.

## Repository Connection — Status: Phase 1 (partial) / Phase 2 (GitHub App)
- [x] Local folder selection and indexing (existing)
- [x] GitHub URL cloning (existing)
- [x] Repository metadata persisted in Supabase (Phase 1)
- [ ] GitHub App installation flow (Phase 2)
- [ ] Private repository access via installation tokens (Phase 2)

## Repository Indexing — Status: Phase 1 (local) / Phase 3 (cloud workers)
- [x] AST-aware parsing and chunking (existing)
- [x] Embeddings with multi-provider fallback (existing)
- [x] Indexing job model persisted in Supabase (Phase 1)
- [ ] SQS + ECS worker execution (Phase 3)
- [ ] Idempotent job retries (Phase 3)

## AI Chat — Status: Phase 4 (RAG migration) / Phase 7 (optimization)
- [x] Hybrid retrieval: vector + BM25 + RRF (existing)
- [x] LangGraph 10-node agent with reflection/verification (existing)
- [x] Streaming reasoning steps over WebSocket (existing)
- [x] Conversation/message/citation persistence (Phase 1)
- [ ] pgvector-backed dense retrieval (Phase 4)
- [ ] Query classifier routing simple/RAG/complex paths (Phase 7)

## Visualization — Status: Phase 10 (polish; core exists today)
- [x] 3D galaxy/stars/planets/moons universe (existing)
- [x] Camera navigation and focus (existing)
- [ ] Stable API contract decoupling (Phase 10)

## Skills & Reports — Status: Phase 9
- [x] 9 analysis skills + Markdown export (existing)
- [x] Skill catalog table seeded in Supabase (Phase 1)
- [ ] Skill runs persisted per user/repository (Phase 9)
- [ ] Long-running skills on workers (Phase 9)

## Platform — Status: Phase 1 complete / Phase 5 (AWS)
- [x] Auth-ready JWT validation (Phase 1)
- [x] Row-level security on all tables (Phase 1)
- [ ] Multi-provider LLM settings persisted per user (partial — API exists)
- [ ] AWS ECS/S3/CloudFront deployment (Phase 5)
- [ ] Incremental GitHub sync via webhooks (Phase 6)
