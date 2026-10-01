# Intent — What RepoVerse AI Is and Why It Exists

> Intent is the product north star. It defines WHY. It does not contain implementation steps.

## Problem

Developers, students, and open-source contributors struggle to understand unfamiliar
codebases. Reading files one by one is slow; generic AI chatbots hallucinate because
they have no grounding in the actual repository.

## What RepoVerse AI Is

RepoVerse AI turns a GitHub repository into an explorable, queryable AI knowledge space:

```text
Universe = All repositories
Galaxy   = Repository
Star     = Folder
Planet   = File
Moon     = Function / Class
```

The product experience:

```text
GitHub + AI Repository Assistant + VSCode-like Code Understanding + Space Exploration
```

## The User Should Be Able To

1. Connect GitHub (or upload local/ZIP repositories).
2. Select a repository.
3. See its structure visually in an interactive 3D universe.
4. Ask questions about the code.
5. Receive grounded answers with file/line citations.
6. Explore files, symbols, dependencies and repository history.
7. Run repository analysis skills (security, performance, architecture, ...).

## Principles That Must Never Be Violated

- Every AI answer is grounded in retrieved repository context — never hallucinated.
- Citations point to repository files/lines whenever they exist.
- Retrieval is preferred over generation.
- If retrieval confidence is low, the assistant says "Not Found".
- The 3D visualization must aid navigation, never hinder usability.

## In Scope

- Single-user accounts with authentication.
- GitHub repository connection and synchronization.
- Repository indexing, retrieval (hybrid RAG), and grounded chat.
- 3D visualization of repository structure.
- Repository analysis skills with exportable reports.

## Explicitly Out of Scope (for now)

- Real-time collaboration and multi-user editing.
- Autonomous code generation/PR writing.
- Mobile applications.
- On-premise / self-hosted enterprise deployment.
