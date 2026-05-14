# 🤖 Multi-Agent Code Carbon System — Implementation Complete

## Files Created

| File | Description |
|------|-------------|
| [agent1_ingestion.py](file:///d:/technofest/agent1_ingestion.py) | **Agent 1** — Repository Ingestion (repomix flat bundler) |
| [agent2_gemini_identifier.py](file:///d:/technofest/agent2_gemini_identifier.py) | **Agent 2** — Gemini Transaction Identifier (route/CSRF/field detection) |
| [agent3_carbon.py](file:///d:/technofest/agent3_carbon.py) | **Agent 3** — Code Carbon Agent (live HTTP + energy measurement) |
| [agent4_report.py](file:///d:/technofest/agent4_report.py) | **Agent 4** — Refactor Report (Markdown report + unit test generator) |
| [pipeline.py](file:///d:/technofest/pipeline.py) | **Orchestrator** — Runs all 4 agents in sequence via CLI |
| [server.py](file:///d:/technofest/server.py) | **Backend Server** — Flask app serving Web UI and streaming pipeline logs |
| [web_ui/index.html](file:///d:/technofest/web_ui/index.html) | **Web Dashboard** — Interactive UI to run pipeline & test transactions |
| [.env](file:///d:/technofest/.env) | Environment configuration (API keys, URLs) |
| [requirements.txt](file:///d:/technofest/requirements.txt) | Python dependencies (Flask, Flask-CORS, CodeCarbon, etc.) |

## Directory Structure

```
d:\technofest\
├── .env                          ← Configuration
├── requirements.txt              ← Python deps (✅ installed)
├── agent1_ingestion.py           ← Agent 1: repo → flat .txt
├── agent2_gemini_identifier.py   ← Agent 2: flat .txt → transactions.json
├── agent3_carbon.py              ← Agent 3: transactions → carbon_report.json
├── agent4_report.py              ← Agent 4: all data → markdown report + tests
├── pipeline.py                   ← Full pipeline orchestrator
├── server.py                     ← Web Backend (Flask API & SSE stream)
├── web_ui/
│   └── index.html                ← Modern Web Dashboard for pipeline & testing
├── output/                       ← Agent outputs (auto-populated)
└── reports/
    └── tests/                    ← Generated unit tests
```

## Quick Start (Web Dashboard)

```bash
# 1. Set your OpenRouter API key in .env
# OPENROUTER_API_KEY=your_key_here

# 2. Start the Backend Server
python server.py

# 3. Open your browser
# Go to: http://localhost:5000
```

> **How to use the dashboard:**
> 1. Enter your **Repository Path** (e.g., `C:\xampp\htdocs\my-app`) or **Git URL**.
> 2. Enter the **Target Base URL** (e.g., `http://localhost:8000`).
> 3. Click **Run Pipeline**.
> 4. Watch the terminal logs stream in real-time.
> 5. Once finished, scroll down to interact with the detected transactions!

## Alternative: CLI Usage

```bash
# Run full pipeline via terminal
python pipeline.py --source /path/to/your/app --base-url http://localhost:8000

# Skip Agent 3
python pipeline.py --source https://github.com/user/repo --skip-carbon
```

> [!IMPORTANT]
> Before running, update `OPENROUTER_API_KEY` in `.env` with your actual OpenRouter API key.

> [!NOTE]
> All Python dependencies are already installed. `repomix` must be installed globally via `npm install -g repomix` for Agent 1 to work.

## Supported Frameworks

Laravel · Django · Express.js · Spring Boot · Rails · FastAPI · NestJS · Go (Gin/Echo) · ASP.NET Core
