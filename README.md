---
title: RepoVerse AI
emoji: 🌌
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Explore any GitHub repository as a 3D galaxy universe with AI
---

# 🌌 RepoVerse AI

> Explore any GitHub repository as an interactive 3D galaxy — powered by AI.

RepoVerse AI transforms your codebase into a stunning 3D galactic universe. Navigate your repository's architecture visually, chat with an AI agent that understands your code, and run AI-powered skills to get instant insights.

## ✨ Features

- **Galactic 3D Explorer** — Repo → Galaxy, Folders → Stars, Files → Planets, Symbols → Moons
- **AI Mission Control** — Chat with an LLM agent that understands your entire codebase
- **AI Skills Engine** — Overview, Architecture, Security, Health, Dependencies, Git Timeline & more
- **GitHub Repo Cloning** — Paste any GitHub URL and explore it instantly

## 🚀 Getting Started

1. Paste a GitHub repository URL on the landing page
2. Wait for it to clone and index (30–60 seconds)
3. Explore the 3D galaxy view
4. Click the central sun to open Mission Control (AI chat)
5. Use the Skills panel for automated analysis

## ⚙️ Configuration

This Space requires API keys to be set as **Space Secrets**:

| Secret | Description |
|---|---|
| `GROQ_API_KEY` | Primary LLM (recommended) |
| `OPENROUTER_API_KEY` | Optional fallback |
| `GEMINI_API_KEY` | Optional fallback |
| `OPENAI_API_KEY` | Optional fallback |

## 🛠️ Tech Stack

- **Frontend**: React + Vite + Three.js (R3F) + Framer Motion
- **Backend**: FastAPI + LangGraph + ChromaDB
- **AI**: Groq / OpenRouter / Gemini (configurable fallback chain)
