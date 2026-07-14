# 🚀 RepoVerse AI - User Guide

Welcome to **RepoVerse AI**, an immersive, space-themed repository visualization and agentic RAG chat assistant. RepoVerse maps codebase components to a celestial taxonomy:
*   **🌌 Universe**: All codebase spaces.
*   **🌀 Galaxy**: The active Git repository (e.g., `SUMMERTRAININGPROJECT`).
*   **✨ Constellation**: Feature groups (e.g., Database, Core, API, RAG).
*   **⭐ Star**: Sub-directories.
*   **🪐 Planet**: Source files.
*   **🌙 Moon**: Functions or classes within files.

---

## ⚡ Quick Start & Launch

Both the frontend and backend servers are running in your active terminals:
*   **FastAPI Backend Server**: Running on `http://127.0.0.1:8000`
*   **React Frontend (Vite)**: Running on `http://localhost:5173`

To open the app, simply navigate to **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## 🧭 Interface Walkthrough

RepoVerse AI features an IDE-style 3-column dashboard:

```
┌────────────────────────────────────────────────────────────────────────┐
│                               TOP NAVBAR                               │
├────────────────────┬──────────────────────────────────┬────────────────┤
│                    │                                  │                │
│  GALAXY EXPLORER   │        AI COMM-LINK CHAT         │ SOURCE PREVIEW │
│  (Left Column)     │        (Middle Column)           │ (Right Column) │
│                    │                                  │                │
│  Navigate Stars,   │  * Stream real-time answers.     │  * Read code   │
│  Planets (files),  │  * View live LangGraph steps.    │    with line   │
│  and Moons         │  * Click citations to locate.    │    highlights. │
│  (symbols).        │                                  │  * View Repo   │
│                    │                                  │    Summary.    │
└────────────────────┴──────────────────────────────────┴────────────────┘
```

### 1. Left Panel: Galaxy Explorer
*   This panel shows all files grouped into **Constellations** (high-level feature clusters) and **Stars** (folders).
*   **Planet Symbols**: Click any file to load it into the **Source Preview** panel.
*   **Moons (Classes/Functions)**: Expand a file row to see its functions and classes. Click a Moon to load the file and instantly jump to that symbol's starting line!

### 2. Center Panel: Space Station AI Comm-Link
*   Use the chat box at the bottom to type natural language questions about your repository (e.g., *"How does the retriever merge BM25 and Vector search?"* or *"List all functions in parser/code_analyzer.py"*).
*   **Live LangGraph Nodes**: When you send a query, a dashboard shows the active agent nodes (Classifier, Retriever, MCP Tool executor, Fact Checker, Generator) executing in real-time.
*   **Grounded Citations**: The AI grounds every response in the codebase. Click the generated file pills (e.g. `Planet: backend/rag/retriever.py:10-25`) to automatically open that file and highlight the line range.
*   **Fact-Checking Score**: Below each response, the system displays a confidence score showing how strictly grounded the answer was in the retrieved text.

### 3. Right Panel: Source Preview & Galaxy Profile
*   **Source Preview (Top)**: Reads the active file with syntax font and custom line-highlight overlays.
*   **Galaxy Profile (Bottom)**: Automatically profiles the repository upon indexing. It displays:
    *   **Tech Stack**: Detected languages and framework packages.
    *   **Entry Points**: Target executable files.
    *   **Total Indexed Planets**: Number of analyzed files.
    *   **Dependencies**: Imported third-party libraries.

---

## 🛠️ Indexing Your Codebase

When loading the app for the first time, you must index the files to populate the search index:
1.  Click the **Settings Gear** in the top-right corner.
2.  Input your **Groq API Key** (starts with `gsk_`) or **OpenAI API Key** (starts with `sk-`).
    *   *Note: If no keys are provided, the system will use local fallbacks and Ollama if running.*
3.  Click **Reinitialize Engine** to save settings.
4.  Click the **Index Galaxy** button in the top navbar.
    *   This clears the database, parses AST details, creates metadata chunks, fits the BM25 lexical engine, and generates the repository summary.
    *   The Galaxy Explorer tree and Galaxy Profile dashboard will refresh automatically when finished.

---

## 💬 Codebase Chat Commands (MCP Server Tools)

The agent connects to external tools (using the Model Context Protocol concept). You can request specific actions directly in the chat:
*   **Git History**: Ask *"What were the last 5 git commits?"* (Executes `git log`).
*   **File Changes**: Ask *"What changes are currently uncommitted?"* (Executes `git diff`).
*   **Execution Sandbox**: Ask *"Calculate the fibonacci of 10 in Python"* (Runs the code in a sandbox and returns the stdout).
*   **Web Documentation**: Ask *"Search online for the latest LangGraph state graph API documentation"* (Performs web queries to retrieve docs).
*   **Run Test Suite**: Ask *"Run pytest in the workspace"* (Triggers local test runners).
