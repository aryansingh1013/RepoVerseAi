# Engineering Rules

## General

Build production-quality code.

No hardcoded values.

Every module should have a single responsibility.

---

## RAG Rules

Never answer without retrieval.

Always cite source files.

Use language-aware chunking.

Ignore binaries.

---

## LangChain

Use LangChain for:

- Document Loading
- Text Splitting
- Embeddings
- Retriever
- Prompt Templates

Avoid unnecessary chains.

---

## LangGraph

LangGraph is the application brain.

Only use nodes that solve a real problem.

Routing should decide:

- RAG
- MCP
- Python
- Browser

---

## MCP

Filesystem MCP

Read repository

Open files

List directories

GitHub MCP

Repository metadata

Commits

Branches

Pull Requests

Browser MCP

Documentation lookup

Python MCP

Static analysis

Metrics

---

## AI Responses

Never hallucinate.

Always include source citations.

Say "Not Found" if retrieval confidence is low.

---

## UI

Space theme must improve navigation.

Animations should never reduce usability.

Every interaction should be explainable.