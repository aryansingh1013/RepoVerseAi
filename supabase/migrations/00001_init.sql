-- ============================================================
-- RepoVerse AI — Phase 1: Supabase Foundation
-- 00001_init.sql — Extensions, core tables, RLS policies
-- ============================================================
-- AUTH NOTE: Supabase Auth owns auth.users. We keep our own
-- public.profiles table for app-specific user metadata, keyed
-- to auth.users.id. RLS below restricts every table to rows
-- owned by the authenticated user unless stated otherwise.
-- ============================================================

-- ---------- Extensions ----------
create extension if not exists "uuid-ossp";
-- pgvector is intentionally NOT enabled here (Phase 4 scope).
-- enable it then: create extension if not exists vector;

-- ---------- Enums ----------
create type indexing_job_status as enum ('pending', 'running', 'succeeded', 'failed', 'cancelled');
create type indexing_job_type as enum ('initial_index', 'incremental_index', 'reindex');
create type message_role as enum ('user', 'assistant', 'system');

-- ---------- users / profiles ----------
-- Mirrors auth.users; id matches the Supabase Auth user id.
create table public.profiles (
    id uuid primary key references auth.users (id) on delete cascade,
    email text,
    display_name text,
    avatar_url text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

comment on table public.profiles is 'App-specific user metadata; 1:1 with auth.users';

-- Auto-create a profile whenever a user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
    insert into public.profiles (id, email, display_name, avatar_url)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data ->> 'name', split_part(new.email, '@', 1)),
        new.raw_user_meta_data ->> 'avatar_url'
    )
    on conflict (id) do nothing;
    return new;
end;
$$;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ---------- repositories ----------
create table public.repositories (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references public.profiles (id) on delete cascade,
    github_owner text,
    github_repo text,
    -- local/zip ingested repos have no GitHub identity
    name text not null,
    url text,
    branch text default 'main',
    default_branch text default 'main',
    installation_id bigint,          -- populated in Phase 2 (GitHub App)
    current_commit_sha text,         -- latest known commit on GitHub
    indexed_commit_sha text,         -- commit the index reflects
    index_version integer not null default 1,
    embedding_model text not null default 'BAAI/bge-small-en-v1.5',
    parser_version integer not null default 1,
    language text,
    status text not null default 'pending', -- pending | indexing | ready | error
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (user_id, github_owner, github_repo)
);

create index idx_repositories_user on public.repositories (user_id);
create index idx_repositories_installation on public.repositories (installation_id);

-- ---------- repository_branches ----------
create table public.repository_branches (
    id uuid primary key default uuid_generate_v4(),
    repository_id uuid not null references public.repositories (id) on delete cascade,
    name text not null,
    commit_sha text,
    is_default boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (repository_id, name)
);

-- ---------- repository_commits ----------
create table public.repository_commits (
    id uuid primary key default uuid_generate_v4(),
    repository_id uuid not null references public.repositories (id) on delete cascade,
    sha text not null,
    message text,
    author_name text,
    committed_at timestamptz,
    created_at timestamptz not null default now(),
    unique (repository_id, sha)
);

create index idx_commits_repo on public.repository_commits (repository_id);

-- ---------- files ----------
create table public.files (
    id uuid primary key default uuid_generate_v4(),
    repository_id uuid not null references public.repositories (id) on delete cascade,
    commit_sha text,                 -- commit this file state belongs to (Phase 6 incremental)
    path text not null,
    name text not null,
    extension text,
    language text,
    chunk_count integer not null default 0,
    summary text,
    content_sha text,                -- git blob sha / content hash for change detection
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (repository_id, path)
);

create index idx_files_repo on public.files (repository_id);
create index idx_files_repo_sha on public.files (repository_id, content_sha);

-- ---------- symbols ----------
create table public.symbols (
    id uuid primary key default uuid_generate_v4(),
    file_id uuid not null references public.files (id) on delete cascade,
    name text not null,
    symbol_type text not null,       -- function | class | global_block | file_summary
    start_line integer,
    end_line integer,
    signature text,
    summary text,
    created_at timestamptz not null default now()
);

create index idx_symbols_file on public.symbols (file_id);

-- ---------- chunks ----------
-- embedding column is added in Phase 4 (pgvector). Phase 1 stores
-- chunk text + metadata only, so the relational model is complete.
create table public.chunks (
    id uuid primary key default uuid_generate_v4(),
    repository_id uuid not null references public.repositories (id) on delete cascade,
    file_id uuid not null references public.files (id) on delete cascade,
    chunk_type text not null,        -- function | class | global_block | text_block | file_summary
    content text not null,
    start_line integer,
    end_line integer,
    imports jsonb not null default '[]'::jsonb,
    exports jsonb not null default '[]'::jsonb,
    metadata jsonb not null default '{}'::jsonb,
    embedding_model text not null default 'BAAI/bge-small-en-v1.5',
    created_at timestamptz not null default now()
);

create index idx_chunks_repo on public.chunks (repository_id);
create index idx_chunks_file on public.chunks (file_id);
create index idx_chunks_metadata on public.chunks using gin (metadata);

-- ---------- indexing_jobs ----------
create table public.indexing_jobs (
    id uuid primary key default uuid_generate_v4(),
    repository_id uuid not null references public.repositories (id) on delete cascade,
    user_id uuid not null references public.profiles (id) on delete cascade,
    job_type indexing_job_type not null default 'initial_index',
    status indexing_job_status not null default 'pending',
    commit_sha text,
    branch text,
    error_message text,
    files_processed integer not null default 0,
    chunks_generated integer not null default 0,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_jobs_repo on public.indexing_jobs (repository_id);
create index idx_jobs_status on public.indexing_jobs (status);

-- ---------- conversations / messages / citations ----------
create table public.conversations (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references public.profiles (id) on delete cascade,
    repository_id uuid not null references public.repositories (id) on delete cascade,
    title text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_conversations_user on public.conversations (user_id);
create index idx_conversations_repo on public.conversations (repository_id);

create table public.messages (
    id uuid primary key default uuid_generate_v4(),
    conversation_id uuid not null references public.conversations (id) on delete cascade,
    role message_role not null,
    content text not null,
    confidence_score numeric,
    reasoning_trace jsonb,
    created_at timestamptz not null default now()
);

create index idx_messages_conversation on public.messages (conversation_id);

create table public.citations (
    id uuid primary key default uuid_generate_v4(),
    message_id uuid not null references public.messages (id) on delete cascade,
    file_path text not null,
    line_start integer,
    line_end integer,
    score numeric,
    chunk_id uuid references public.chunks (id) on delete set null,
    created_at timestamptz not null default now()
);

create index idx_citations_message on public.citations (message_id);

-- ---------- skills / skill_runs ----------
create table public.skills (
    slug text primary key,
    name text not null,
    description text,
    created_at timestamptz not null default now()
);

create table public.skill_runs (
    id uuid primary key default uuid_generate_v4(),
    skill_slug text not null references public.skills (slug),
    repository_id uuid not null references public.repositories (id) on delete cascade,
    user_id uuid not null references public.profiles (id) on delete cascade,
    job_id uuid references public.indexing_jobs (id) on delete set null,
    status indexing_job_status not null default 'pending',
    result jsonb,
    error_message text,
    created_at timestamptz not null default now(),
    finished_at timestamptz
);

create index idx_skill_runs_repo on public.skill_runs (repository_id);

-- ---------- user_settings ----------
create table public.user_settings (
    user_id uuid primary key references public.profiles (id) on delete cascade,
    preferred_provider text,         -- groq | openai | gemini | openrouter | ollama
    preferred_model text,
    fallback_order jsonb,
    embedding_model text,
    settings jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

-- ============================================================
-- updated_at trigger
-- ============================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

do $$
declare t text;
begin
    foreach t in array array[
        'profiles', 'repositories', 'repository_branches', 'files',
        'indexing_jobs', 'conversations', 'user_settings'
    ]
    loop
        execute format(
            'create trigger set_updated_at_%s before update on public.%I
             for each row execute function public.set_updated_at();', t, t
        );
    end loop;
end $$;

-- ============================================================
-- ROW LEVEL SECURITY
-- Rule: a user may only touch rows whose user_id chain points
-- to themselves. Skills table is public read-only catalog data.
-- ============================================================
alter table public.profiles            enable row level security;
alter table public.repositories        enable row level security;
alter table public.repository_branches enable row level security;
alter table public.repository_commits  enable row level security;
alter table public.files               enable row level security;
alter table public.symbols             enable row level security;
alter table public.chunks              enable row level security;
alter table public.indexing_jobs       enable row level security;
alter table public.conversations       enable row level security;
alter table public.messages            enable row level security;
alter table public.citations           enable row level security;
alter table public.skills              enable row level security;
alter table public.skill_runs          enable row level security;
alter table public.user_settings       enable row level security;

-- profiles: users see and edit only their own
create policy "profiles_select_own"  on public.profiles for select using (auth.uid() = id);
create policy "profiles_update_own"  on public.profiles for update using (auth.uid() = id);

-- repositories
create policy "repos_all_own" on public.repositories for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- helper predicate for child tables joined to repositories
create policy "branches_all_own" on public.repository_branches for all
    using (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()))
    with check (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()));

create policy "commits_all_own" on public.repository_commits for all
    using (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()))
    with check (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()));

create policy "files_all_own" on public.files for all
    using (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()))
    with check (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()));

create policy "symbols_all_own" on public.symbols for all
    using (exists (
        select 1 from public.files f
        join public.repositories r on r.id = f.repository_id
        where f.id = file_id and r.user_id = auth.uid()
    ))
    with check (exists (
        select 1 from public.files f
        join public.repositories r on r.id = f.repository_id
        where f.id = file_id and r.user_id = auth.uid()
    ));

create policy "chunks_all_own" on public.chunks for all
    using (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()))
    with check (exists (select 1 from public.repositories r where r.id = repository_id and r.user_id = auth.uid()));

create policy "jobs_all_own" on public.indexing_jobs for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- conversations
create policy "conversations_all_own" on public.conversations for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "messages_all_own" on public.messages for all
    using (exists (select 1 from public.conversations c where c.id = conversation_id and c.user_id = auth.uid()))
    with check (exists (select 1 from public.conversations c where c.id = conversation_id and c.user_id = auth.uid()));

create policy "citations_all_own" on public.citations for all
    using (exists (
        select 1 from public.messages m
        join public.conversations c on c.id = m.conversation_id
        where m.id = message_id and c.user_id = auth.uid()
    ))
    with check (exists (
        select 1 from public.messages m
        join public.conversations c on c.id = m.conversation_id
        where m.id = message_id and c.user_id = auth.uid()
    ));

-- skills: catalog readable by any authenticated user; writes are service-role only
create policy "skills_select_auth" on public.skills for select to authenticated using (true);

create policy "skill_runs_all_own" on public.skill_runs for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- user_settings
create policy "settings_all_own" on public.user_settings for all
    using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ============================================================
-- Seed: skill catalog (mirrors backend/skills registry)
-- ============================================================
insert into public.skills (slug, name, description) values
    ('repository_overview',   'Repository Overview',   'High-level summary of the repository structure and purpose'),
    ('architecture_analyzer', 'Architecture Analyzer', 'Analyzes the architectural layers and patterns of the codebase'),
    ('dependency_explorer',   'Dependency Explorer',   'Maps internal and external dependencies of the repository'),
    ('security_review',       'Security Review',       'Scans for common security issues and unsafe patterns'),
    ('performance_review',    'Performance Review',    'Identifies likely performance bottlenecks and hot paths'),
    ('health_analyzer',       'Health Analyzer',       'Assesses repository health: dead code, TODOs, complexity'),
    ('readme_generator',      'README Generator',      'Generates a README draft from repository analysis'),
    ('git_timeline',          'Git Timeline',          'Summarizes recent commit history and activity'),
    ('learning_mode',         'Learning Mode',         'Guided onboarding tour of the codebase for new contributors')
on conflict (slug) do nothing;
