-- RepoVerse AI — Supabase / Postgres schema (P1 + P1.5)
-- Apply in the Supabase SQL editor (or psql) for the target project.
--
-- Default embedding: Hugging Face router, BAAI/bge-small-en-v1.5 @ 384 dims.
-- If you change EMBEDDING_DIMENSIONS (see backend/rag/embeddings.py rules),
-- run the ALTER block at the bottom — the app REFUSES to mix dimensions.

create extension if not exists vector;

-- One row per indexed workspace. key = md5(root_path)[:16] (matches app hashing).
-- embed_fingerprint pins (provider:model:dimensions); a change triggers a
-- full automatic rebuild instead of silently corrupting vectors.
create table if not exists workspaces (
  key               text primary key,
  root_path         text not null,
  embed_fingerprint text,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

-- Per-file content hashes → incremental re-indexing (audit fix #5).
create table if not exists files (
  workspace_key text not null references workspaces(key) on delete cascade,
  path          text not null,
  content_hash  text not null default '',
  size_bytes    bigint,
  mtime         double precision,
  indexed_at    timestamptz not null default now(),
  primary key (workspace_key, path)
);

-- Chunks + embeddings ("planets & moons" corpus).
create table if not exists chunks (
  id              text primary key,          -- ws:path:index
  workspace_key   text not null references workspaces(key) on delete cascade,
  path            text not null,
  chunk_type      text,                       -- class | function | global_block | text_block | ...
  language        text,
  symbol_class    text,
  symbol_function text,
  start_line      integer not null default 1,
  end_line        integer not null default 0,
  content         text not null,
  extra_metadata  jsonb not null default '{}'::jsonb,  -- imports/exports/summary
  embedding       vector(384)
);

create index if not exists chunks_ws_idx     on chunks (workspace_key, path);
create index if not exists chunks_embedding_idx
  on chunks using hnsw (embedding vector_cosine_ops);

-- Hybrid retrieval: vector leg with optional path restriction (from the
-- retriever's filename resolution, audit fix #7).
create or replace function match_chunks(
  query_embedding vector(384),
  ws_key          text,
  match_count     integer default 5,
  path_list       text[]  default null
)
returns table (
  id       text,
  path     text,
  content  text,
  metadata jsonb,
  score    double precision
)
language sql stable as $$
  select
    c.id,
    c.path,
    c.content,
    jsonb_build_object(
      'path',        c.path,
      'language',    c.language,
      'class',       coalesce(c.symbol_class, ''),
      'function',    coalesce(c.symbol_function, ''),
      'chunk_type',  c.chunk_type,
      'start_line',  c.start_line,
      'end_line',    c.end_line
    ) || coalesce(c.extra_metadata, '{}'::jsonb) as metadata,
    1 - (c.embedding <=> query_embedding) as score
  from chunks c
  where c.workspace_key = ws_key
    and (path_list is null or c.path = any (path_list))
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

-- ── Analytics tables (P1 groundwork; writers wired in P2) ──────────────────

-- One row per /api/index run → index/refresh analytics.
create table if not exists index_runs (
  id            bigint generated always as identity primary key,
  workspace_key text references workspaces(key) on delete set null,
  ran_at        timestamptz not null default now(),
  files_total   integer,
  added         integer,
  updated       integer,
  removed       integer,
  chunks_total  integer,
  duration_ms   integer
);

-- ModelRouter telemetry events (was RAM-only, vanished on restart).
create table if not exists llm_telemetry (
  id          bigint generated always as identity primary key,
  ts          timestamptz not null default now(),
  provider    text,
  model       text,
  key_alias   text,
  task        text,
  ok          boolean,
  is_rate_limit boolean default false,
  latency_ms  double precision,
  tokens      integer
);

-- GitHub repo analytics snapshots (P2: cron-snapshot the 14-day traffic API
-- so users get history GitHub itself refuses to keep).
create table if not exists traffic_snapshots (
  id           bigint generated always as identity primary key,
  workspace_key text references workspaces(key) on delete set null,
  repo_full_name text,
  snapshot_at  date not null default (current_date),
  views        integer,
  uniques      integer,
  clones       integer,
  clone_uniques integer,
  referrers    jsonb,
  top_paths    jsonb,
  unique (repo_full_name, snapshot_at)
);

-- ── RLS placeholders (enable with Supabase Auth in P1 follow-up) ────────────
-- For now: service-role key access only; anon/authenticated keys get nothing.
-- alter table workspaces enable row level security;
-- alter table chunks   enable row level security;
-- (create per-user policy: auth.uid() owner mapping once users table exists)

-- ── If you changed EMBEDDING_DIMENSIONS (e.g. OpenAI text-embedding-3-small) ─
-- alter table chunks drop constraint if exists chunks_embedding_check;
-- alter table chunks alter column embedding type vector(512);
-- then re-create match_chunks with the matching vector(512) signature, and:
-- truncate chunks;  -- old vectors are incompatible by design
