 AI Sysadmin — modular AI-driven system operator
 
 Overview
 
 This project is a modular AI-driven sysadmin skeleton that lets an LLM plan and execute tasks on a host machine. It provides:
 
 - A JSON-RPC-like router to register and call tool methods.
 - Dual frontends: a Textual TUI and a FastAPI Web UI (WebSocket + REST).
 - Pluggable AI backends (Gemini/Google GenAI via `genai`, Claude adapter stubbed).
 - Plan generation and normalization into a simple plan schema.
 - Plan persistence (storage/plans) and backup-before-execute support.
 - Safety gates: destructive-step detection and explicit confirmation.
 
 Quick setup
 
 1. Create and activate a virtualenv (recommended):
 
 ```powershell
 python -m venv .venv
 & .\.venv\Scripts\Activate.ps1
 pip install -r requirements.txt
 ```
 
 2. Create a `.env` in the project root (see `config.py`) and add provider keys as needed:
 
 ```
 GEMINI_API_KEY=your_api_key_here
 GEMINI_API_URL=     # optional custom endpoint
 GEMINI_MODEL=models/text-bison-001  # default used for Google GenAI REST fallback
 CLAUDE_API_KEY=     # optional
 ```
 
 Running
 
 - Web UI (FastAPI + Uvicorn):
 
 ```powershell
 python main.py --mode web
 ```
 
 - TUI (Textual):
 
 ```powershell
 python main.py --mode tui
 ```
 
 - Both (web in background + tui in foreground):
 
 ```powershell
 python main.py --mode both
 ```
 
 Testing
 
 Run the unit tests with pytest:
 
 ```powershell
 python -m pytest -q
 ```
 
 Notes on API backends
 
 - The Gemini adapter (`ai_backend/gemini_client.py`) prefers the official `genai` client (`google-genai` / `genai`) if it's installed and configured. If `genai` is unavailable it will attempt a custom `GEMINI_API_URL` HTTP POST (if configured) or the Google Generative REST endpoint as a fallback. When no key is present, the adapter returns a mocked plan (safe for dev/test).
 
 Safety and backups
 
 - Plans are stored under `storage/plans` and backups are written to `storage/backups` before execution.
 - Steps detected as destructive must be explicitly confirmed via the `confirm_steps` input to `plan.execute`/`plan.execute_async`.
 
 Developer TODOs
 
 See `TODO.md` for an actionable list of next tasks, priorities, and notes for contributors.
 
 Contributing
 
 - Please open issues or PRs for improvements. Be mindful of secrets — never commit `.env` or API keys.
 
 License
 
 - This repository is provided as-is for experimentation.
