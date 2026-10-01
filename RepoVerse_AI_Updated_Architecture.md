# RepoVerse AI — Updated Cloud Architecture & Phased Implementation Plan

> **Purpose:** This document is the implementation source of truth for moving RepoVerse AI from the current local/single-container architecture to a production-oriented AWS + Supabase + GitHub architecture.
>
> **Critical development rule:** DO NOT implement the entire architecture at once. Work **phase by phase**. Each phase must be completed, tested, and verified before the next phase begins.

---

# 1. Project Intent

## 1.1 What RepoVerse AI is

RepoVerse AI is an AI-powered GitHub repository assistant that:

- connects to GitHub repositories;
- understands repository structure, files, symbols, dependencies, and commits;
- indexes source code using AST-aware chunking and embeddings;
- answers repository questions using grounded RAG;
- uses LangGraph for complex reasoning and tool orchestration;
- visualizes the repository as an interactive 3D universe;
- provides repository analysis skills and reports;
- keeps repository knowledge synchronized as the GitHub repository changes.

The core concept remains:

```text
Universe = All repositories
Galaxy   = Repository
Star     = Folder
Planet   = File
Moon     = Function / Class
```

The product concept is:

```text
GitHub + AI Repository Assistant + VSCode-like Code Understanding + Space Exploration
```

---

# 2. Primary Architectural Goal

The current architecture is primarily designed around a persistent local machine:

```text
FastAPI
 ├── local ChromaDB
 ├── local cloned repositories
 ├── local JSON/YAML state
 ├── in-memory BM25
 └── FastAPI BackgroundTasks
```

This is suitable for development but is not the desired production architecture.

The target architecture is:

```text
React / Three.js
        |
        v
CloudFront + S3
        |
        v
AWS API / ALB
        |
        v
FastAPI API Service on ECS
        |
        +--------------------+
        |                    |
        v                    v
Supabase                 SQS
Auth + PostgreSQL          |
+ pgvector                 v
                     ECS Worker
                          |
              +-----------+-----------+
              |           |           |
              v           v           v
           GitHub      Parser     Embedding APIs
           App/API
              |
              v
             S3
```

---

# 3. Target Technology Stack

| Area | Target Technology | Purpose |
|---|---|---|
| Frontend | React + TypeScript + Three.js | 3D repository visualization and UI |
| Frontend hosting | S3 + CloudFront | Static frontend deployment |
| API | FastAPI | REST + streaming/WebSocket API |
| API hosting | AWS ECS Fargate | Stateless API containers |
| Background workers | ECS Fargate | Repository cloning, parsing, indexing |
| Queue | AWS SQS | Reliable background job processing |
| Database | Supabase PostgreSQL | Application metadata and relational data |
| Authentication | Supabase Auth | User authentication and identity |
| Vector search | Supabase pgvector | Dense semantic retrieval |
| Sparse search | BM25 | Exact/lexical code retrieval |
| Object storage | AWS S3 | Repository snapshots, reports, artifacts |
| GitHub integration | GitHub App + REST API | Repository access |
| GitHub synchronization | GitHub Webhooks | Push/PR/repository change events |
| Agent | LangGraph | Complex reasoning workflow |
| LLMs | Groq / OpenAI / Gemini / others | Generation and reasoning |
| Embeddings | BGE / Hugging Face initially | Code/document embeddings |
| Secrets | AWS Secrets Manager | API keys and GitHub App secrets |
| Logs | CloudWatch | API/worker/application logs |
| Container registry | AWS ECR | Docker image storage |
| HTTPS | ACM | TLS certificates |
| DNS | Route 53 | Domain routing |

---

# 4. Architecture Principles

These principles must be followed throughout implementation.

## Rule 1 — Phase-by-phase development

Never implement Phase 1, 2, 3, 4, and 5 simultaneously.

Correct workflow:

```text
Phase 1
  ↓
Implement
  ↓
Test
  ↓
Verify
  ↓
Freeze / checkpoint
  ↓
Phase 2
  ↓
...
```

If a phase fails, fix that phase before continuing.

---

## Rule 2 — Do not rewrite working systems unnecessarily

If an existing RepoVerse component works correctly, preserve its behavior unless the current architecture explicitly requires changing it.

Examples:

- AST-aware chunking → keep
- Hybrid retrieval → keep
- RRF → keep
- LangGraph → keep
- 3D visualization → keep
- Skills → keep

The cloud migration should improve infrastructure without destroying working product functionality.

---

## Rule 3 — No speculative infrastructure

Do not add services merely because they are common in cloud architectures.

Do NOT introduce:

```text
Kubernetes
Kafka
Redis
Elasticsearch
Neo4j
microservices everywhere
```

unless a real requirement appears.

Start with:

```text
ECS
SQS
S3
Supabase
GitHub App
```

and add infrastructure only when justified.

---

## Rule 4 — API must remain stateless

The FastAPI API container must not depend on local persistent state.

Avoid production dependencies on:

```text
active_workspace.json
mcp_settings.json
YAML runtime configuration
local ChromaDB
local cloned repository persistence
in-memory application state as the source of truth
```

Persistent state belongs in:

```text
Supabase
S3
```

Temporary processing belongs in:

```text
container ephemeral storage
```

---

## Rule 5 — Workers handle expensive operations

Do not perform long-running repository indexing inside the API request lifecycle.

API:

```text
validate
authenticate
create job
enqueue job
return job ID
```

Worker:

```text
clone/download
parse
chunk
embed
store
update status
```

---

## Rule 6 — Security before production

Never expose:

```text
GitHub private tokens
LLM API keys
AWS secrets
Supabase service-role keys
```

to the frontend.

Secrets are backend-only.

---

# 5. Target System Architecture

```text
                           INTERNET
                              |
                              v
                  +-----------------------+
                  | CloudFront            |
                  | Static Frontend       |
                  +-----------+-----------+
                              |
                              v
                    React + Three.js
                              |
                              | HTTPS
                              v
                  +-----------------------+
                  | AWS ALB / API Gateway |
                  +-----------+-----------+
                              |
                              v
                  +-----------------------+
                  | ECS Fargate API       |
                  | FastAPI               |
                  +-----------+-----------+
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
       Supabase          AWS SQS             AWS S3
       Auth + DB           Queue          Object Storage
       + pgvector             |
                              v
                    +-----------------------+
                    | ECS Fargate Worker    |
                    |                       |
                    | Clone / Parse / Chunk |
                    | Embed / Index          |
                    +-----------+-----------+
                                |
                 +--------------+--------------+
                 |              |              |
                 v              v              v
             GitHub App       Parser       Embedding API
                 |
                 v
            GitHub Webhooks
                 |
                 v
                SQS
```

---

# 6. Component Responsibilities

## 6.1 Frontend

Responsibilities:

- authentication UI;
- GitHub connection flow;
- repository selection;
- indexing status;
- 3D universe;
- repository navigation;
- file preview;
- AI chat;
- citations;
- skills;
- reports;
- settings.

The frontend must never directly access:

- GitHub private credentials;
- LLM API keys;
- AWS credentials;
- Supabase service-role credentials.

---

# 7. API Service

FastAPI becomes the central stateless application service.

Responsibilities:

```text
Authentication validation
Repository management
GitHub integration requests
Conversation management
RAG queries
Agent execution
Streaming responses
Job creation
Job status
Settings
Skills
```

Example API groups:

```text
/api/auth/*
/api/repositories/*
/api/indexing/*
/api/chat/*
/api/search/*
/api/files/*
/api/skills/*
/api/settings/*
/api/jobs/*
/api/health
```

---

# 8. Supabase Design

Supabase becomes the primary application database.

## 8.1 Core tables

Recommended initial schema:

```text
users
repositories
repository_installations
repository_branches
repository_commits

files
symbols
chunks

indexing_jobs

conversations
messages
citations

skills
skill_runs

user_settings
```

---

## 8.2 Repository model

A repository should not be represented only by a local folder.

Use:

```text
Repository
    |
    +-- GitHub owner
    +-- GitHub repo
    +-- installation_id
    +-- default_branch
    +-- current_commit_sha
    +-- indexed_commit_sha
    +-- index_version
    +-- embedding_model
    +-- parser_version
```

---

# 9. Commit-Aware Indexing

RepoVerse should understand that repository contents change.

Store:

```text
repository_id
commit_sha
branch
path
file_sha
```

for indexed content.

This allows RepoVerse to know:

```text
Current GitHub commit:
ABC123

Indexed commit:
XYZ789
```

and correctly report that the repository needs re-indexing.

---

# 10. Vector Search

Replace production ChromaDB persistence with Supabase pgvector.

Target:

```text
Supabase PostgreSQL
        |
        +-- chunks.content
        +-- chunks.metadata
        +-- chunks.embedding
```

Dense retrieval:

```text
query
  |
embedding
  |
pgvector similarity
  |
top-k
```

Keep the existing BGE embedding approach initially.

Do not change embedding models and database architecture simultaneously unless required.

---

# 11. Hybrid Retrieval

The existing hybrid retrieval concept remains.

```text
                  Query
                    |
          +---------+---------+
          |                   |
          v                   v
      pgvector              BM25
      semantic             lexical
          |                   |
          +---------+---------+
                    |
                    v
                   RRF
                    |
                    v
              Ranked Context
```

RRF remains:

```text
score = 1 / (60 + rank)
```

The exact constant can remain configurable.

---

# 12. Repository Ingestion

## Old approach

```text
POST /clone
    |
FastAPI BackgroundTask
    |
git clone
    |
local filesystem
    |
ChromaDB
```

## New approach

```text
POST /repositories/{id}/index
             |
             v
        Create Job
             |
             v
            SQS
             |
             v
        ECS Worker
             |
             v
       GitHub API/App
             |
             v
       Temporary repo
             |
             v
          Parser
             |
             v
          Chunker
             |
             v
        Embeddings
             |
             v
     Supabase pgvector
             |
             v
       Update Job
```

---

# 13. Incremental Indexing

Full repository indexing should not happen after every push.

For a GitHub push:

```text
GitHub Push
    |
    v
Webhook
    |
    v
SQS
    |
    v
Worker
    |
    v
Determine changed files
    |
    +---- unchanged files ----> keep
    |
    +---- changed files -------> re-parse
    |
    +---- deleted files -------> remove chunks
    |
    v
Update embeddings
    |
    v
Update indexed commit
```

This is a major long-term optimization.

---

# 14. GitHub App Architecture

RepoVerse should use a GitHub App for production GitHub integration.

```text
User
  |
  v
Install RepoVerse GitHub App
  |
  v
Select repositories
  |
  v
RepoVerse stores installation metadata
  |
  v
Backend generates short-lived installation access token
  |
  v
GitHub REST API
```

GitHub webhooks:

```text
push
pull_request
repository
installation
installation_repositories
```

Only subscribe to events that are actually required.

---

# 15. GitHub Access Rules

Use least privilege.

Prefer read-only repository permissions where possible.

The frontend should never receive the GitHub App private key.

Backend-only:

```text
GITHUB_APP_ID
GITHUB_PRIVATE_KEY
GITHUB_WEBHOOK_SECRET
```

Store these in AWS Secrets Manager.

---

# 16. SQS Job Architecture

Suggested jobs:

```text
repository.initial_index
repository.incremental_index
repository.reindex
github.webhook
skill.execute
report.generate
```

Example:

```json
{
  "job_type": "repository.incremental_index",
  "repository_id": "...",
  "commit_sha": "...",
  "branch": "main"
}
```

Workers must be idempotent.

If a job is executed twice, it should not corrupt the repository index.

---

# 17. LangGraph Architecture

Keep the existing LangGraph design, but introduce routing before the expensive graph.

```text
User Query
    |
    v
Query Classifier
    |
    +------ SIMPLE ------> Search -> Answer
    |
    +------ RAG ---------> Retrieve -> Answer -> Verify
    |
    +------ COMPLEX ------> LangGraph
```

Complex graph:

```text
intent
  |
goal analysis
  |
task decomposition
  |
planning
  |
retrieval
  |
tool execution
  |
result fusion
  |
reflection
  |
generation
  |
verification
```

Do not force every question through the complete graph.

---

# 18. MCP Architecture

MCP remains part of RepoVerse but must be treated as a controlled tool layer.

Production-safe tools:

```text
repo.search
repo.read_file
repo.symbols
repo.dependencies

github.get_repository
github.get_commit
github.get_pull_request
github.get_issue
```

Restricted tools:

```text
git.diff
git.log
```

Highly restricted:

```text
terminal.execute
arbitrary filesystem
browser automation
```

Never allow unrestricted LLM-generated shell execution in production.

---

# 19. Storage Strategy

## Supabase

Store:

```text
users
repositories
commits
branches
files
symbols
chunks
embeddings
conversations
messages
citations
jobs
settings
```

## S3

Store:

```text
repository snapshots
generated reports
large exports
temporary processing artifacts when persistence is required
```

## ECS local disk

Only temporary:

```text
/tmp/repository
/tmp/build
/tmp/index
```

Do not treat ECS local storage as permanent storage.

---

# 20. Authentication

Use Supabase Auth.

Flow:

```text
React
  |
  v
Supabase Auth
  |
  v
JWT
  |
  v
FastAPI
  |
  v
Validate JWT
  |
  v
user_id
```

Every repository, conversation, and job must be associated with an authenticated user or an explicitly defined organization/team.

---

# 21. Authorization

Authentication answers:

> Who is this user?

Authorization answers:

> Can this user access this repository?

Every sensitive API operation must verify:

```text
authenticated user
        +
repository ownership/access
        +
GitHub installation access
```

Do not trust a `repository_id` supplied by the frontend without authorization checks.

---

# 22. Secrets

Use:

```text
AWS Secrets Manager
```

for:

```text
GitHub App private key
GitHub webhook secret
OpenAI API key
Groq API key
Gemini API key
Hugging Face token
Supabase service-role key
```

Public frontend values may include only values intentionally designed to be public, such as the Supabase project URL and appropriate client-side key.

---

# 23. Observability

Every request/job should have:

```text
request_id
user_id
repository_id
commit_sha
job_id
query_id
```

Track:

```text
API latency
queue latency
indexing duration
files processed
chunks generated
embedding duration
retrieval latency
LLM latency
token usage
model
fallbacks
errors
```

Use CloudWatch for AWS logs and metrics.

---

# 24. Production Deployment

## Frontend

```text
React build
   |
   v
S3
   |
   v
CloudFront
```

## Backend

```text
Docker image
   |
   v
ECR
   |
   v
ECS Fargate
```

Run separate services:

```text
repoverse-api
repoverse-worker
```

Do not combine API and worker responsibilities in one production container.

---

# 25. Recommended Project Structure

```text
repoverse-ai/
│
├── frontend/
│
├── backend/
│   ├── api/
│   ├── auth/
│   ├── repositories/
│   ├── indexing/
│   ├── parser/
│   ├── rag/
│   ├── agent/
│   ├── llm/
│   ├── github/
│   ├── mcp/
│   ├── skills/
│   ├── workers/
│   ├── database/
│   ├── storage/
│   ├── telemetry/
│   └── core/
│
├── supabase/
│   ├── migrations/
│   ├── seed/
│   └── functions/
│
├── infrastructure/
│   ├── aws/
│   ├── ecs/
│   ├── s3/
│   ├── sqs/
│   └── secrets/
│
├── docs/
│   ├── architecture.md
│   ├── intent.md
│   ├── features.md
│   ├── rules.md
│   ├── phases/
│   └── decisions/
│
├── Dockerfile
└── README.md
```

---

# 26. What is `intent.md`?

`intent.md` defines **what RepoVerse is supposed to be and why it exists**.

It should answer:

```text
What problem are we solving?
Who is the user?
What is the product?
What is the core experience?
What principles must never be violated?
What is inside the project scope?
What is explicitly outside the scope?
```

`intent.md` should NOT contain detailed implementation steps.

Example:

```text
RepoVerse AI exists to turn a GitHub repository into an explorable,
queryable AI knowledge space.

The user should be able to:
1. Connect GitHub.
2. Select a repository.
3. See its structure visually.
4. Ask questions about the code.
5. Receive grounded answers with citations.
6. Explore files, symbols, dependencies and repository history.
7. Run repository analysis skills.
```

Intent is the product north star.

---

# 27. What is `features.md`?

`features.md` defines **what the product can do**.

It should contain feature specifications and status.

Example:

```text
## Repository Connection
Status: Phase 2

- GitHub App installation
- Repository selection
- Private repository access
- Repository metadata

## Repository Indexing
Status: Phase 3

- AST parsing
- Chunking
- Embeddings
- pgvector
- Incremental indexing

## AI Chat
Status: Phase 4

- Hybrid RAG
- Citations
- Streaming
- Query routing
- LangGraph

## Visualization
Status: Phase 5

- Galaxy
- Stars
- Planets
- Moons
- Camera navigation
```

Features should describe **capabilities**, not detailed implementation instructions.

---

# 28. What is `rules.md`?

`rules.md` defines **engineering and product constraints that every implementation must obey**.

Examples:

```text
1. Never expose secrets to frontend.
2. Never bypass repository authorization.
3. Never use local files as production source-of-truth.
4. Never execute arbitrary shell commands from untrusted LLM output.
5. Never implement future phases early.
6. Every indexing job must be idempotent.
7. Every AI answer must be grounded in repository context.
8. Citations must point to repository files/lines when available.
9. Do not destroy working functionality during migration.
10. Do not add infrastructure without a demonstrated requirement.
```

Rules are the project's guardrails.

---

# 29. Relationship Between the Documents

```text
intent.md
    |
    | Defines WHY
    v
features.md
    |
    | Defines WHAT
    v
architecture.md
    |
    | Defines HOW
    v
phases/
    |
    | Defines WHEN
    v
implementation
    |
    v
rules.md
    |
    +---- constrains everything
```

Think of them as:

```text
INTENT      = WHY
FEATURES    = WHAT
ARCHITECTURE= HOW
PHASES      = WHEN
RULES       = CONSTRAINTS
```

---

# 30. Mandatory Phase-Based Implementation

RepoVerse must be implemented in controlled phases.

## Phase 0 — Baseline and Safety

### Goal

Freeze the currently working project before architectural migration.

### Tasks

- Create migration branch.
- Run current application.
- Verify frontend.
- Verify backend.
- Verify indexing.
- Verify RAG.
- Verify chat.
- Verify visualization.
- Record known bugs.
- Record current dependency versions.

### Deliverable

```text
Known-good local baseline
```

### Gate

Do not begin Phase 1 until the existing application starts and its core functionality is documented.

---

# 31. Phase 1 — Supabase Foundation

### Goal

Introduce cloud persistence without changing the user-facing product.

### Implement

```text
Supabase project
Supabase PostgreSQL
Supabase Auth
database migrations
repository tables
user tables
conversation tables
job tables
```

### Do NOT implement yet

```text
AWS ECS
SQS
GitHub webhooks
incremental indexing
full cloud deployment
```

### Gate

Verify:

```text
user authentication works
database migrations work
repository metadata can be stored
authorization works
```

Only then proceed.

---

# 32. Phase 2 — GitHub App

### Goal

Replace manually supplied GitHub credentials/clone assumptions with proper GitHub integration.

### Implement

```text
GitHub App
installation flow
repository listing
repository metadata
access validation
webhook endpoint
```

### Do NOT implement yet

```text
full incremental indexing
production workers
advanced MCP GitHub tools
```

### Gate

Verify:

```text
User
 → GitHub
 → Install App
 → Select repo
 → Backend can access repo
```

---

# 33. Phase 3 — Cloud Indexing Worker

### Goal

Move expensive repository processing out of FastAPI.

### Implement

```text
SQS
ECS Worker
job model
job status
idempotency
temporary repository storage
parser pipeline
chunking
embedding
```

### Replace

```text
FastAPI BackgroundTasks
```

with:

```text
FastAPI → SQS → ECS Worker
```

### Gate

Test:

```text
small repo
medium repo
failed job
duplicate job
worker restart
```

---

# 34. Phase 4 — pgvector + Hybrid RAG

### Goal

Move vector persistence from local ChromaDB to Supabase pgvector.

### Implement

```text
chunks table
embedding column
vector index
metadata filters
dense retrieval
BM25
RRF
citation metadata
```

### Gate

Compare:

```text
old Chroma retrieval
vs
new pgvector retrieval
```

before removing ChromaDB.

The migration is successful only if retrieval quality is acceptable and citations remain correct.

---

# 35. Phase 5 — AWS Deployment

### Goal

Deploy the application.

### Implement

```text
Docker
ECR
ECS API
ECS Worker
SQS
S3
ALB
CloudWatch
Secrets Manager
CloudFront
S3 frontend
```

### Gate

Verify:

```text
frontend loads
authentication works
API works
GitHub integration works
indexing works
chat works
worker failures recover
secrets are not exposed
```

---

# 36. Phase 6 — Incremental GitHub Synchronization

### Goal

Stop rebuilding the complete repository index for every change.

### Implement

```text
GitHub webhook
      ↓
SQS
      ↓
changed files
      ↓
incremental parser
      ↓
delete/update chunks
      ↓
new embeddings
      ↓
new commit state
```

### Gate

Test:

```text
new file
modified file
deleted file
renamed file
multiple changed files
branch change
rapid consecutive pushes
```

---

# 37. Phase 7 — Production Agent Optimization

### Goal

Optimize the existing LangGraph system.

### Implement

```text
query classifier
simple path
RAG path
complex agent path
tool permission system
cost controls
timeouts
retry policies
context limits
```

### Goal

Do not run the complete agent graph when a simple retrieval answer is enough.

---

# 38. Phase 8 — MCP Production Layer

### Goal

Make MCP useful and safe in the cloud environment.

### Implement

```text
MCP registry
tool permissions
GitHub tools
repository tools
safe execution
timeouts
audit logging
```

Terminal/browser capabilities should remain restricted unless there is a clear production requirement.

---

# 39. Phase 9 — Skills and Reports

### Goal

Move existing skills into the cloud architecture.

Skills:

```text
repository_overview
architecture_analyzer
dependency_explorer
security_review
performance_review
health_analyzer
readme_generator
git_timeline
learning_mode
```

Each skill should have:

```text
skill_id
repository_id
user_id
job_id
status
result
created_at
```

Long-running skills should use SQS workers.

---

# 40. Phase 10 — 3D Experience and Product Polish

Only after backend stability:

```text
Galaxy
Stars
Planets
Moons
Camera navigation
File previews
AI Orb
HUD
animations
loading states
error states
```

The 3D layer should consume stable API contracts instead of depending on backend implementation details.

---

# 41. Phase Completion Protocol

At the end of every phase:

```text
1. Run tests.
2. Run the application.
3. Test the affected user flow.
4. Review logs.
5. Review security implications.
6. Update documentation.
7. Commit changes.
8. Tag/checkpoint the phase.
9. Record known limitations.
10. Only then begin the next phase.
```

Recommended tags:

```text
phase-0-complete
phase-1-complete
phase-2-complete
...
```

---

# 42. AI Coding Agent Rules

If RepoVerse is being developed with an AI coding agent, the agent MUST follow this workflow:

```text
READ
  ↓
intent.md
  ↓
features.md
  ↓
rules.md
  ↓
architecture.md
  ↓
CURRENT PHASE
  ↓
IMPLEMENT ONLY CURRENT PHASE
  ↓
TEST
  ↓
REPORT
```

The agent must NOT:

```text
implement all phases;
rewrite unrelated modules;
introduce future infrastructure;
change APIs without documenting it;
delete working functionality without justification;
skip tests;
store secrets in source code;
assume production persistence is local;
```

---

# 43. Current Phase Declaration

At the top of the development session, explicitly declare:

```text
CURRENT PHASE: Phase X
PHASE GOAL: <one sentence>
ALLOWED CHANGES: <modules/services allowed>
NOT IN SCOPE: <future work>
SUCCESS CRITERIA: <testable conditions>
```

Example:

```text
CURRENT PHASE: Phase 1

PHASE GOAL:
Introduce Supabase authentication and database persistence.

ALLOWED CHANGES:
backend/auth/
backend/database/
supabase/migrations/
frontend/auth/

NOT IN SCOPE:
AWS deployment
SQS
GitHub webhooks
pgvector migration

SUCCESS CRITERIA:
User can sign in and repository metadata is persisted securely.
```

---

# 44. Definition of Done

A phase is NOT complete because code was written.

A phase is complete only when:

```text
[ ] Implementation complete
[ ] Tests pass
[ ] Manual flow verified
[ ] Error cases tested
[ ] Security checked
[ ] Documentation updated
[ ] No unrelated changes
[ ] Git checkpoint created
[ ] Known limitations recorded
```

---

# 45. Final Target State

The final RepoVerse architecture should provide:

```text
                  RepoVerse AI
                       |
       +---------------+---------------+
       |               |               |
       v               v               v
   GitHub         AI/RAG          Visualization
       |               |               |
       v               v               v
 GitHub App      LangGraph       Three.js
 Webhooks        Hybrid RAG      Universe
       |               |
       v               v
      SQS         pgvector
       |               |
       v               v
 ECS Workers       Supabase
       |               |
       +-------+-------+
               |
               v
              S3
               |
               v
             AWS
```

The system should be:

- cloud deployable;
- stateless at the API layer;
- asynchronous for expensive work;
- commit-aware;
- incrementally indexable;
- secure;
- observable;
- cost-conscious;
- grounded in repository data;
- capable of scaling workers independently from API instances.

---

# 46. Non-Goals for the First Production Version

Do not attempt to build all of these immediately:

```text
Kubernetes
multi-region deployment
complex microservice mesh
real-time collaborative editing
full autonomous coding agent
unrestricted terminal execution
unrestricted browser automation
large-scale distributed vector infrastructure
custom LLM hosting
```

These can be evaluated later based on actual usage.

---

# 47. Implementation Order Summary

```text
PHASE 0
Baseline
   ↓
PHASE 1
Supabase + Auth
   ↓
PHASE 2
GitHub App
   ↓
PHASE 3
SQS + ECS Worker
   ↓
PHASE 4
pgvector + Hybrid RAG
   ↓
PHASE 5
AWS Deployment
   ↓
PHASE 6
Incremental GitHub Sync
   ↓
PHASE 7
Agent Optimization
   ↓
PHASE 8
Production MCP
   ↓
PHASE 9
Skills + Reports
   ↓
PHASE 10
3D/Product Polish
```

**Do not skip directly to Phase 10.**

The recommended order intentionally stabilizes data, authentication, repository access, indexing, retrieval, and infrastructure before adding higher-level AI and UI complexity.
