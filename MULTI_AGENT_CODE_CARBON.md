# 🤖 Multi-Agent Code Carbon System
> **Universal Code Analyzer · Transaction Detector · Carbon Auditor · Refactor Reporter**

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Prerequisites](#prerequisites)
4. [Agent 1 — Repository Ingestion Agent](#agent-1--repository-ingestion-agent)
5. [Agent 2 — Gemini Transaction Identifier Agent](#agent-2--gemini-transaction-identifier-agent)
6. [Agent 3 — Code Carbon Agent (Live Runner)](#agent-3--code-carbon-agent-live-runner)
7. [Agent 4 — Refactor Report Agent](#agent-4--refactor-report-agent)
8. [Pipeline Orchestrator](#pipeline-orchestrator)
9. [Web UI — CSRF & Form Field Handler](#web-ui--csrf--form-field-handler)
10. [Unit Test Generator](#unit-test-generator)
11. [Configuration & Environment](#configuration--environment)
12. [Running the Full Pipeline](#running-the-full-pipeline)
13. [Output Examples](#output-examples)

---

## System Overview

System ini terdiri dari **4 agen yang bekerja secara pipeline** untuk menganalisis codebase dari berbagai framework/bahasa, mendeteksi transaksi, mengukur konsumsi energi (carbon), dan menghasilkan laporan refactoring.

```
┌─────────────────────────────────────────────────────────────────┐
│                     MULTI-AGENT PIPELINE                        │
│                                                                 │
│  [Repo/Local]  →  [Repomix]  →  [Gemini AI]  →  [Code Carbon] │
│      Agent 1         ↓             Agent 2         Agent 3      │
│                  flat_pack                              ↓        │
│                  .txt file      transactions        energy_data  │
│                                      ↓                  ↓       │
│                               ┌──────────────────────────┐      │
│                               │    Agent 4 — Refactor    │      │
│                               │         Report           │      │
│                               └──────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Supported Languages / Frameworks

| Framework | Language | CSRF Support | Unit Test |
|-----------|----------|--------------|-----------|
| Laravel | PHP | ✅ Auto-detect `@csrf` | PHPUnit |
| Django | Python | ✅ `{% csrf_token %}` | pytest |
| Express.js | JavaScript/TypeScript | ✅ `csurf` middleware | Jest |
| Spring Boot | Java | ✅ `CsrfToken` | JUnit |
| Rails | Ruby | ✅ `authenticity_token` | RSpec |
| FastAPI | Python | ✅ Custom CSRF | pytest |
| NestJS | TypeScript | ✅ `@nestjs/csrf` | Jest |
| Go (Gin/Echo) | Go | ✅ `gorilla/csrf` | go test |
| ASP.NET Core | C# | ✅ `[ValidateAntiForgeryToken]` | xUnit |

---

## Architecture Diagram

```
                         ╔══════════════════════╗
                         ║   AGENT 1            ║
                         ║   Repo Ingestion     ║
                         ║                      ║
                         ║  Input:              ║
                         ║  • Local filepath    ║
                         ║  • Git URL           ║
                         ║  • ZIP upload        ║
                         ║                      ║
                         ║  Process:            ║
                         ║  repomix → flat .txt ║
                         ╚══════════╦═══════════╝
                                    ║ flat_codebase.txt
                                    ▼
                         ╔══════════════════════╗
                         ║   AGENT 2            ║
                         ║   Gemini Identifier  ║
                         ║                      ║
                         ║  • Detect routes     ║
                         ║  • Detect CSRF fields║
                         ║  • Detect POST/PUT   ║
                         ║  • Form fields map   ║
                         ║  • Auth endpoints    ║
                         ╚══════════╦═══════════╝
                                    ║ transactions.json
                                    ▼
                         ╔══════════════════════╗
                         ║   AGENT 3            ║
                         ║   Code Carbon        ║
                         ║                      ║
                         ║  • Run live requests ║
                         ║  • Measure energy    ║
                         ║  • Track CO₂ per req ║
                         ║  • Perf profiling    ║
                         ╚══════════╦═══════════╝
                                    ║ carbon_report.json
                                    ▼
                         ╔══════════════════════╗
                         ║   AGENT 4            ║
                         ║   Refactor Report    ║
                         ║                      ║
                         ║  • Combine all data  ║
                         ║  • Suggest fixes     ║
                         ║  • Generate tests    ║
                         ║  • Send MD report    ║
                         ╚══════════════════════╝
```

---

## Prerequisites

### System Requirements

```bash
# Node.js >= 18
node --version

# Python >= 3.9
python3 --version

# Git
git --version

# repomix (Agent 1)
npm install -g repomix

# codecarbon (Agent 3)
pip install codecarbon requests python-dotenv

# Optional: jq (untuk parsing JSON di terminal)
# Ubuntu/Debian
sudo apt install jq
# macOS
brew install jq
```

### API Keys

```bash
# .env
GEMINI_API_KEY=your_gemini_api_key_here
TARGET_BASE_URL=http://localhost:8000   # URL app yang sedang running
REPOMIX_OUTPUT_DIR=./output
REPORT_OUTPUT_DIR=./reports
```

---

## Agent 1 — Repository Ingestion Agent

### Konsep

Agent 1 bertanggung jawab untuk **mengkonversi codebase** (baik dari path lokal maupun Git URL) menjadi satu file teks flat menggunakan **repomix**. Format flat ini kemudian dikirim ke Agent 2.

> **Kenapa repomix?** Repomix menghasilkan satu file `.txt` yang merepresentasikan seluruh struktur folder + isi file, sehingga Gemini AI dapat memahami konteks penuh codebase tanpa harus dikirim file per file.

### File: `agent1_ingestion.py`

```python
#!/usr/bin/env python3
"""
Agent 1 — Repository Ingestion Agent
Converts local path or Git URL to a flat repomix bundle.
"""

import subprocess
import os
import sys
import shutil
import tempfile
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class IngestionResult:
    success: bool
    flat_file_path: str
    source_type: str          # "local" | "git"
    source_path: str
    file_size_bytes: int
    detected_language: str
    detected_framework: str
    error: Optional[str] = None


FRAMEWORK_SIGNATURES = {
    "laravel":     ["artisan", "composer.json", "app/Http/Controllers"],
    "django":      ["manage.py", "settings.py", "wsgi.py"],
    "express":     ["package.json", "app.js", "routes/"],
    "nestjs":      ["nest-cli.json", "src/main.ts"],
    "springboot":  ["pom.xml", "src/main/java", "Application.java"],
    "rails":       ["Gemfile", "config/routes.rb", "app/controllers"],
    "fastapi":     ["main.py", "requirements.txt"],  # + fastapi in requirements
    "gin":         ["go.mod", "main.go"],
    "aspnet":      ["*.csproj", "Program.cs", "Startup.cs"],
}

LANGUAGE_MAP = {
    "laravel": "PHP",
    "django": "Python",
    "fastapi": "Python",
    "express": "JavaScript",
    "nestjs": "TypeScript",
    "springboot": "Java",
    "rails": "Ruby",
    "gin": "Go",
    "aspnet": "C#",
}


def detect_framework(path: str) -> tuple[str, str]:
    """Detect framework and language from directory structure."""
    for framework, signatures in FRAMEWORK_SIGNATURES.items():
        for sig in signatures:
            check = Path(path) / sig
            # Check direct file/dir
            if check.exists():
                return framework, LANGUAGE_MAP.get(framework, "Unknown")
            # Glob pattern
            if "*" in sig:
                matches = list(Path(path).glob(sig))
                if matches:
                    return framework, LANGUAGE_MAP.get(framework, "Unknown")
    return "unknown", "Unknown"


def clone_repo(git_url: str, target_dir: str) -> str:
    """Clone a git repository to target_dir."""
    print(f"[Agent 1] Cloning {git_url}...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", git_url, target_dir],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")
    return target_dir


def run_repomix(source_dir: str, output_path: str) -> None:
    """Run repomix to create flat bundle from source_dir."""
    print(f"[Agent 1] Running repomix on {source_dir}...")

    # repomix config — exclude common non-essential files
    repomix_config = {
        "output": {
            "filePath": output_path,
            "style": "plain",
            "removeComments": False,
            "removeEmptyLines": False,
            "showLineNumbers": True,
            "copyToClipboard": False,
        },
        "ignore": {
            "useGitignore": True,
            "useDefaultPatterns": True,
            "customPatterns": [
                "node_modules/**",
                "vendor/**",
                ".git/**",
                "*.lock",
                "*.log",
                "dist/**",
                "build/**",
                "__pycache__/**",
                "*.pyc",
                ".env",
                "storage/**",
                "public/storage/**",
            ]
        }
    }

    config_path = Path(source_dir) / ".repomix-config.json"
    with open(config_path, "w") as f:
        json.dump(repomix_config, f, indent=2)

    result = subprocess.run(
        ["repomix", "--config", str(config_path), "--output", output_path, source_dir],
        capture_output=True, text=True
    )

    # Cleanup config
    config_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"repomix failed: {result.stderr}")

    print(f"[Agent 1] ✅ repomix output: {output_path}")


def run(source: str, output_dir: str = "./output") -> IngestionResult:
    """
    Main entry point for Agent 1.
    
    Args:
        source: Local directory path OR Git URL
        output_dir: Where to save the flat bundle
    
    Returns:
        IngestionResult with flat_file_path pointing to repomix output
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = str(Path(output_dir) / "flat_codebase.txt")
    temp_dir = None

    try:
        # Determine source type
        if source.startswith("http") or source.startswith("git@"):
            source_type = "git"
            temp_dir = tempfile.mkdtemp(prefix="agent1_repo_")
            working_dir = clone_repo(source, temp_dir)
        else:
            source_type = "local"
            working_dir = os.path.abspath(source)
            if not os.path.isdir(working_dir):
                raise ValueError(f"Directory not found: {working_dir}")

        # Detect framework
        framework, language = detect_framework(working_dir)
        print(f"[Agent 1] Detected: {framework} / {language}")

        # Run repomix
        run_repomix(working_dir, output_path)

        file_size = Path(output_path).stat().st_size

        return IngestionResult(
            success=True,
            flat_file_path=output_path,
            source_type=source_type,
            source_path=source,
            file_size_bytes=file_size,
            detected_language=language,
            detected_framework=framework,
        )

    except Exception as e:
        return IngestionResult(
            success=False,
            flat_file_path="",
            source_type="unknown",
            source_path=source,
            file_size_bytes=0,
            detected_language="Unknown",
            detected_framework="unknown",
            error=str(e),
        )
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "."
    result = run(source)
    print(json.dumps(asdict(result), indent=2))
```

---

## Agent 2 — Gemini Transaction Identifier Agent

### Konsep

Agent 2 menerima file flat dari Agent 1, lalu mengirimkannya ke **Gemini AI** untuk dianalisis. Gemini akan:

- Mendeteksi semua **route/endpoint** (GET, POST, PUT, DELETE, PATCH)
- Mengidentifikasi **field yang wajib diisi** untuk setiap endpoint
- Mendeteksi kebutuhan **CSRF token** secara otomatis per framework
- Mengidentifikasi endpoint yang membutuhkan **autentikasi**
- Menghasilkan **unit test skeleton** untuk transaksi POST/PUT/DELETE

### File: `agent2_gemini_identifier.py`

```python
#!/usr/bin/env python3
"""
Agent 2 — Gemini Transaction Identifier Agent
Sends repomix bundle to Gemini AI for transaction analysis.
"""

import os
import json
import time
import requests
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"
)

# Max chars to send to Gemini (stay under token limit)
MAX_CONTENT_CHARS = 800_000


@dataclass
class TransactionField:
    name: str
    type: str            # "string" | "email" | "password" | "integer" | "boolean" | "file"
    required: bool
    description: str
    validation_rules: list[str] = field(default_factory=list)


@dataclass
class Transaction:
    id: str
    method: str          # GET | POST | PUT | PATCH | DELETE
    endpoint: str
    description: str
    requires_auth: bool
    requires_csrf: bool
    csrf_field_name: str  # e.g. "_token", "csrfmiddlewaretoken", "X-CSRF-Token"
    fields: list[TransactionField]
    framework: str
    unit_test_skeleton: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class IdentificationResult:
    success: bool
    framework: str
    language: str
    transactions: list[Transaction]
    total_routes: int
    post_routes: int
    csrf_protected_routes: int
    auth_required_routes: int
    error: Optional[str] = None


SYSTEM_PROMPT = """
You are an expert code analyzer. You will receive a flat bundle of a web application codebase.

Your task is to analyze ALL routes/endpoints and return a STRICT JSON response.

## What to extract per endpoint:
1. HTTP method (GET, POST, PUT, PATCH, DELETE)
2. URL path / route
3. Description of what the endpoint does
4. Whether it requires authentication (JWT, session, Bearer token, etc.)
5. Whether it requires CSRF protection — detect automatically by framework:
   - Laravel: look for @csrf, csrf_field(), VerifyCsrfToken middleware, X-CSRF-TOKEN header
   - Django: look for {% csrf_token %}, CsrfViewMiddleware, csrf_protect decorator
   - Express.js: look for csurf, csrf(), csrfToken()
   - Rails: look for authenticity_token, protect_from_forgery
   - Spring Boot: look for CsrfToken, .csrf(), SecurityConfig
   - FastAPI: look for custom CSRF implementations or fastapi-csrf-protect
   - NestJS: look for @nestjs/csrf, CsrfGuard
   - Go (Gin/Echo): look for gorilla/csrf, nosurf
   - ASP.NET: look for [ValidateAntiForgeryToken], AntiForgeryToken()
6. The exact CSRF field name used (e.g., "_token", "csrfmiddlewaretoken", "authenticity_token")
7. ALL form fields/request body fields with: name, type, required status, and any validation rules
8. For POST/PUT/PATCH/DELETE: generate a unit test skeleton in the framework's native test style

## Response format — return ONLY valid JSON, no markdown, no explanation:

{
  "framework": "laravel",
  "language": "PHP",
  "transactions": [
    {
      "id": "txn_001",
      "method": "POST",
      "endpoint": "/api/login",
      "description": "User authentication endpoint",
      "requires_auth": false,
      "requires_csrf": true,
      "csrf_field_name": "_token",
      "fields": [
        {
          "name": "email",
          "type": "email",
          "required": true,
          "description": "User email address",
          "validation_rules": ["required", "email", "max:255"]
        },
        {
          "name": "password",
          "type": "password",
          "required": true,
          "description": "User password",
          "validation_rules": ["required", "min:8"]
        }
      ],
      "unit_test_skeleton": "/** @test */\\npublic function test_user_can_login()\\n{\\n    $response = $this->post('/api/login', [\\n        'email' => 'test@example.com',\\n        'password' => 'password123',\\n    ]);\\n    $response->assertStatus(200);\\n}",
      "tags": ["auth", "csrf"]
    }
  ]
}
"""


def chunk_content(content: str, max_chars: int) -> str:
    """Truncate content if too large, prioritizing route/controller files."""
    if len(content) <= max_chars:
        return content

    # Try to keep the most important parts
    lines = content.split("\n")
    priority_keywords = [
        "route", "controller", "middleware", "csrf", "request",
        "form", "validate", "auth", "login", "register", "api",
        "POST", "GET", "PUT", "DELETE", "PATCH"
    ]

    priority_lines = []
    other_lines = []

    for line in lines:
        if any(kw.lower() in line.lower() for kw in priority_keywords):
            priority_lines.append(line)
        else:
            other_lines.append(line)

    result = "\n".join(priority_lines)
    if len(result) < max_chars:
        remaining = max_chars - len(result)
        result += "\n" + "\n".join(other_lines)[:remaining]

    return result[:max_chars]


def call_gemini(content: str) -> dict:
    """Call Gemini API with the codebase content."""
    print("[Agent 2] Sending codebase to Gemini AI...")

    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [{
            "parts": [{
                "text": f"Analyze this codebase and return the JSON:\n\n{content}"
            }]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json"
        }
    }

    for attempt in range(3):
        try:
            response = requests.post(
                GEMINI_ENDPOINT,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()

            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Strip possible markdown fences
            raw_text = raw_text.strip()
            if raw_text.startswith("```"):
                raw_text = "\n".join(raw_text.split("\n")[1:-1])

            return json.loads(raw_text)

        except requests.exceptions.Timeout:
            print(f"[Agent 2] Timeout on attempt {attempt + 1}, retrying...")
            time.sleep(5 * (attempt + 1))
        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}")

    raise RuntimeError("Gemini API failed after 3 attempts")


def parse_result(raw: dict, framework_hint: str = "") -> IdentificationResult:
    """Parse Gemini response into typed IdentificationResult."""
    transactions = []

    for t in raw.get("transactions", []):
        fields = [
            TransactionField(
                name=f["name"],
                type=f.get("type", "string"),
                required=f.get("required", False),
                description=f.get("description", ""),
                validation_rules=f.get("validation_rules", []),
            )
            for f in t.get("fields", [])
        ]

        transactions.append(Transaction(
            id=t.get("id", f"txn_{len(transactions):03d}"),
            method=t["method"].upper(),
            endpoint=t["endpoint"],
            description=t.get("description", ""),
            requires_auth=t.get("requires_auth", False),
            requires_csrf=t.get("requires_csrf", False),
            csrf_field_name=t.get("csrf_field_name", ""),
            fields=fields,
            framework=raw.get("framework", framework_hint),
            unit_test_skeleton=t.get("unit_test_skeleton", ""),
            tags=t.get("tags", []),
        ))

    mutating_methods = {"POST", "PUT", "PATCH", "DELETE"}
    return IdentificationResult(
        success=True,
        framework=raw.get("framework", framework_hint),
        language=raw.get("language", "Unknown"),
        transactions=transactions,
        total_routes=len(transactions),
        post_routes=sum(1 for t in transactions if t.method in mutating_methods),
        csrf_protected_routes=sum(1 for t in transactions if t.requires_csrf),
        auth_required_routes=sum(1 for t in transactions if t.requires_auth),
    )


def run(flat_file_path: str, framework_hint: str = "") -> IdentificationResult:
    """
    Main entry point for Agent 2.
    
    Args:
        flat_file_path: Path to repomix output file
        framework_hint: Optional hint from Agent 1
    
    Returns:
        IdentificationResult with all transactions
    """
    try:
        content = Path(flat_file_path).read_text(encoding="utf-8", errors="replace")
        content = chunk_content(content, MAX_CONTENT_CHARS)

        raw = call_gemini(content)
        result = parse_result(raw, framework_hint)

        print(f"[Agent 2] ✅ Found {result.total_routes} routes")
        print(f"[Agent 2]    POST/mutating: {result.post_routes}")
        print(f"[Agent 2]    CSRF protected: {result.csrf_protected_routes}")
        print(f"[Agent 2]    Auth required: {result.auth_required_routes}")

        # Save transactions to file
        output_path = Path(flat_file_path).parent / "transactions.json"
        with open(output_path, "w") as f:
            json.dump(asdict(result), f, indent=2)
        print(f"[Agent 2] Saved: {output_path}")

        return result

    except Exception as e:
        return IdentificationResult(
            success=False,
            framework=framework_hint,
            language="Unknown",
            transactions=[],
            total_routes=0,
            post_routes=0,
            csrf_protected_routes=0,
            auth_required_routes=0,
            error=str(e),
        )


if __name__ == "__main__":
    import sys
    flat_file = sys.argv[1] if len(sys.argv) > 1 else "./output/flat_codebase.txt"
    result = run(flat_file)
    print(json.dumps(asdict(result), indent=2))
```

---

## Agent 3 — Code Carbon Agent (Live Runner)

### Konsep

Agent 3 menerima `transactions.json` dari Agent 2 dan mengeksekusi **HTTP requests nyata** ke aplikasi yang sedang berjalan. Setiap request diukur menggunakan **CodeCarbon** untuk melacak konsumsi energi dan emisi CO₂.

Untuk endpoint yang membutuhkan CSRF, agent ini secara otomatis:
1. Melakukan GET request ke halaman login/form terlebih dahulu
2. Mengekstrak CSRF token dari response (cookie, header, atau HTML hidden input)
3. Menyertakan token tersebut di request POST

### File: `agent3_carbon.py`

```python
#!/usr/bin/env python3
"""
Agent 3 — Code Carbon Agent
Runs live HTTP requests to the target app and measures CO2 emissions.
"""

import os
import json
import time
import re
import requests
from bs4 import BeautifulSoup
from codecarbon import EmissionsTracker
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("TARGET_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
DELAY_BETWEEN_REQUESTS = float(os.getenv("DELAY_BETWEEN_REQUESTS", "0.5"))


@dataclass
class RequestMeasurement:
    transaction_id: str
    method: str
    endpoint: str
    full_url: str
    status_code: int
    response_time_ms: float
    energy_consumed_kwh: float
    co2_emissions_kg: float
    success: bool
    csrf_obtained: bool
    fields_sent: list[str]
    error: Optional[str] = None
    response_preview: str = ""


@dataclass
class CarbonResult:
    success: bool
    base_url: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_energy_kwh: float
    total_co2_kg: float
    avg_response_time_ms: float
    measurements: list[RequestMeasurement]
    error: Optional[str] = None


# ─── CSRF Token Extractors ───────────────────────────────────────────────────

def extract_csrf_from_html(html: str, field_name: str) -> Optional[str]:
    """Extract CSRF token from HTML hidden input."""
    soup = BeautifulSoup(html, "html.parser")

    # Try direct name match
    token_input = soup.find("input", {"name": field_name})
    if token_input:
        return token_input.get("value")

    # Try meta tag (common in SPAs)
    meta = soup.find("meta", {"name": field_name})
    if meta:
        return meta.get("content")

    # Generic CSRF patterns
    for pattern in ["csrf", "token", "_token", "xsrf"]:
        token_input = soup.find("input", {"name": re.compile(pattern, re.I)})
        if token_input:
            return token_input.get("value")

    return None


def get_csrf_token(
    session: requests.Session,
    transaction_endpoint: str,
    csrf_field_name: str,
    framework: str
) -> tuple[Optional[str], bool]:
    """
    Attempt to retrieve CSRF token before a mutating request.
    Returns (token_value, success).
    """
    # Guess the form/GET page that provides the CSRF token
    # Strip /api/ prefix for web form pages
    form_endpoint = transaction_endpoint.replace("/api/", "/")
    candidates = [
        f"{BASE_URL}{form_endpoint}",
        f"{BASE_URL}/",
        f"{BASE_URL}/login",
        f"{BASE_URL}/home",
    ]

    for url in candidates:
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                # 1. Check HTML for hidden input
                token = extract_csrf_from_html(r.text, csrf_field_name)
                if token:
                    return token, True

                # 2. Check cookies (XSRF-TOKEN style, e.g., Laravel Sanctum)
                for cookie_name in ["XSRF-TOKEN", "csrftoken", "csrf_token"]:
                    if cookie_name in session.cookies:
                        import urllib.parse
                        return urllib.parse.unquote(session.cookies[cookie_name]), True

                # 3. Check response headers
                for header_name in ["X-CSRF-Token", "X-XSRF-Token", "CSRF-Token"]:
                    if header_name in r.headers:
                        return r.headers[header_name], True

        except Exception:
            continue

    return None, False


# ─── Dummy Data Generator ────────────────────────────────────────────────────

DUMMY_VALUES: dict[str, Any] = {
    "email":    "test@example.com",
    "password": "TestPassword123!",
    "name":     "Test User",
    "username": "testuser",
    "phone":    "+1234567890",
    "address":  "123 Test Street",
    "title":    "Test Title",
    "body":     "Test body content for automated testing",
    "content":  "Test content",
    "message":  "Test message",
    "amount":   "100.00",
    "price":    "99.99",
    "quantity": "1",
    "date":     "2024-01-01",
    "token":    "dummy_token_for_testing",
    "code":     "TEST123",
    "url":      "https://example.com",
    "file":     None,  # Skip file uploads
}

TYPE_DEFAULTS: dict[str, Any] = {
    "email":    "test@example.com",
    "password": "TestPassword123!",
    "string":   "test_value",
    "integer":  "1",
    "number":   "1",
    "boolean":  "true",
    "text":     "Test text content",
    "file":     None,
}


def generate_dummy_payload(fields: list[dict]) -> dict:
    """Generate dummy payload from field definitions."""
    payload = {}
    for f in fields:
        name = f["name"].lower()
        ftype = f.get("type", "string").lower()

        if ftype == "file":
            continue  # Skip file fields in automated testing

        # Try name match first
        value = DUMMY_VALUES.get(name)
        if value is None:
            # Try partial match
            for key, val in DUMMY_VALUES.items():
                if key in name:
                    value = val
                    break

        # Fallback to type default
        if value is None:
            value = TYPE_DEFAULTS.get(ftype, "test_value")

        if value is not None:
            payload[f["name"]] = value

    return payload


# ─── Main Runner ─────────────────────────────────────────────────────────────

def run_transaction(
    session: requests.Session,
    transaction: dict,
    framework: str,
    tracker: EmissionsTracker
) -> RequestMeasurement:
    """Execute a single transaction with carbon tracking."""
    method = transaction["method"].upper()
    endpoint = transaction["endpoint"]
    full_url = f"{BASE_URL}{endpoint}"

    csrf_obtained = False
    csrf_token = None

    # Get CSRF token if required
    if transaction.get("requires_csrf") and method in ["POST", "PUT", "PATCH", "DELETE"]:
        csrf_field = transaction.get("csrf_field_name", "_token")
        csrf_token, csrf_obtained = get_csrf_token(session, endpoint, csrf_field, framework)

        if csrf_token:
            # Set in headers too (SPA pattern)
            session.headers.update({
                "X-CSRF-Token": csrf_token,
                "X-XSRF-Token": csrf_token,
            })

    # Build payload
    payload = generate_dummy_payload(transaction.get("fields", []))

    # Add CSRF to payload if token found
    if csrf_token and transaction.get("csrf_field_name"):
        payload[transaction["csrf_field_name"]] = csrf_token

    # Track energy for this request
    tracker.start_task(transaction["id"])
    start_time = time.time()

    try:
        if method == "GET":
            response = session.get(full_url, timeout=REQUEST_TIMEOUT)
        elif method == "POST":
            response = session.post(full_url, data=payload, timeout=REQUEST_TIMEOUT)
        elif method == "PUT":
            response = session.put(full_url, data=payload, timeout=REQUEST_TIMEOUT)
        elif method == "PATCH":
            response = session.patch(full_url, data=payload, timeout=REQUEST_TIMEOUT)
        elif method == "DELETE":
            response = session.delete(full_url, timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError(f"Unsupported method: {method}")

        elapsed_ms = (time.time() - start_time) * 1000
        emissions_data = tracker.stop_task(transaction["id"])

        return RequestMeasurement(
            transaction_id=transaction["id"],
            method=method,
            endpoint=endpoint,
            full_url=full_url,
            status_code=response.status_code,
            response_time_ms=round(elapsed_ms, 2),
            energy_consumed_kwh=emissions_data.energy_consumed if emissions_data else 0.0,
            co2_emissions_kg=emissions_data.emissions if emissions_data else 0.0,
            success=200 <= response.status_code < 400,
            csrf_obtained=csrf_obtained,
            fields_sent=list(payload.keys()),
            response_preview=response.text[:200],
        )

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        try:
            tracker.stop_task(transaction["id"])
        except Exception:
            pass

        return RequestMeasurement(
            transaction_id=transaction["id"],
            method=method,
            endpoint=endpoint,
            full_url=full_url,
            status_code=0,
            response_time_ms=round(elapsed_ms, 2),
            energy_consumed_kwh=0.0,
            co2_emissions_kg=0.0,
            success=False,
            csrf_obtained=csrf_obtained,
            fields_sent=list(payload.keys()),
            error=str(e),
        )


def run(transactions_path: str) -> CarbonResult:
    """
    Main entry point for Agent 3.
    
    Args:
        transactions_path: Path to transactions.json from Agent 2
    
    Returns:
        CarbonResult with per-request energy measurements
    """
    try:
        with open(transactions_path) as f:
            data = json.load(f)

        transactions = data.get("transactions", [])
        framework = data.get("framework", "unknown")

        print(f"[Agent 3] Running {len(transactions)} transactions against {BASE_URL}")

        session = requests.Session()
        session.headers.update({
            "Accept": "application/json, text/html",
            "User-Agent": "CodeCarbonAgent/1.0",
        })

        # Initialize CodeCarbon tracker
        tracker = EmissionsTracker(
            project_name="code_carbon_agent",
            output_dir=str(Path(transactions_path).parent),
            log_level="warning",
            save_to_file=False,
            tracking_mode="process",
        )
        tracker.start()

        measurements = []

        for txn in transactions:
            print(f"[Agent 3]   {txn['method']} {txn['endpoint']}")
            measurement = run_transaction(session, txn, framework, tracker)
            measurements.append(measurement)

            status_icon = "✅" if measurement.success else "❌"
            print(f"[Agent 3]   {status_icon} {measurement.status_code} "
                  f"({measurement.response_time_ms:.0f}ms, "
                  f"{measurement.co2_emissions_kg*1000:.4f}g CO₂)")

            time.sleep(DELAY_BETWEEN_REQUESTS)

        tracker.stop()

        successful = sum(1 for m in measurements if m.success)
        total_energy = sum(m.energy_consumed_kwh for m in measurements)
        total_co2 = sum(m.co2_emissions_kg for m in measurements)
        avg_time = (sum(m.response_time_ms for m in measurements) / len(measurements)
                    if measurements else 0)

        result = CarbonResult(
            success=True,
            base_url=BASE_URL,
            total_requests=len(measurements),
            successful_requests=successful,
            failed_requests=len(measurements) - successful,
            total_energy_kwh=round(total_energy, 8),
            total_co2_kg=round(total_co2, 8),
            avg_response_time_ms=round(avg_time, 2),
            measurements=measurements,
        )

        # Save carbon report
        output_path = Path(transactions_path).parent / "carbon_report.json"
        with open(output_path, "w") as f:
            json.dump(asdict(result), f, indent=2)
        print(f"[Agent 3] ✅ Saved: {output_path}")

        return result

    except Exception as e:
        return CarbonResult(
            success=False,
            base_url=BASE_URL,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            total_energy_kwh=0.0,
            total_co2_kg=0.0,
            avg_response_time_ms=0.0,
            measurements=[],
            error=str(e),
        )


if __name__ == "__main__":
    import sys
    txn_path = sys.argv[1] if len(sys.argv) > 1 else "./output/transactions.json"
    result = run(txn_path)
    print(json.dumps(asdict(result), indent=2))
```

---

## Agent 4 — Refactor Report Agent

### Konsep

Agent 4 mengambil semua hasil dari Agent 1–3 dan menghasilkan:

- **Laporan refactoring lengkap** dalam format Markdown
- **Unit test files** untuk setiap transaksi POST/mutating
- **Ringkasan carbon footprint** dengan rekomendasi optimasi

### File: `agent4_report.py`

```python
#!/usr/bin/env python3
"""
Agent 4 — Refactor Report Agent
Combines all data and generates comprehensive Markdown report + unit tests.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from typing import Any
from dotenv import load_dotenv

load_dotenv()

REPORT_DIR = os.getenv("REPORT_OUTPUT_DIR", "./reports")


# ─── Unit Test Generators ─────────────────────────────────────────────────────

UNIT_TEST_TEMPLATES = {
    "laravel": {
        "ext": "php",
        "header": """<?php

namespace Tests\\Feature;

use Illuminate\\Foundation\\Testing\\RefreshDatabase;
use Illuminate\\Foundation\\Testing\\WithFaker;
use Tests\\TestCase;

class GeneratedTransactionTest extends TestCase
{{
    use RefreshDatabase, WithFaker;
""",
        "footer": "}\n",
        "test_case": """
    /** @test */
    public function test_{method_lower}_{endpoint_slug}()
    {{
        // Transaction: {description}
        {auth_setup}
        $response = $this->{method_lower}('{endpoint}', [
{fields}
        {csrf_field}]);

        $response->assertStatus({expected_status});
    }}
""",
    },
    "django": {
        "ext": "py",
        "header": """import pytest
from django.test import TestCase, Client
from django.urls import reverse


class GeneratedTransactionTests(TestCase):
    def setUp(self):
        self.client = Client()
""",
        "footer": "\n",
        "test_case": """
    def test_{method_lower}_{endpoint_slug}(self):
        \"\"\"Transaction: {description}\"\"\"
        {auth_setup}
        data = {{
{fields}
        }}
        url = '{endpoint}'
        response = self.client.{method_lower}(url, data{csrf_kwarg})
        self.assertIn(response.status_code, [{expected_status}])
""",
    },
    "express": {
        "ext": "test.js",
        "header": """const request = require('supertest');
const app = require('../app');

describe('Generated Transaction Tests', () => {
""",
        "footer": "});\n",
        "test_case": """
  it('{method} {endpoint} - {description}', async () => {{
    {auth_setup}
    const response = await request(app)
      .{method_lower}('{endpoint}')
      .set('Content-Type', 'application/json')
      {csrf_header}
      .send({{
{fields}
      }});

    expect(response.statusCode).toBe({expected_status});
  }});
""",
    },
    "springboot": {
        "ext": "java",
        "header": """package com.example.tests;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
public class GeneratedTransactionTest {{

    @Autowired
    private MockMvc mockMvc;
""",
        "footer": "}\n",
        "test_case": """
    @Test
    public void test{method}{EndpointCamel}() throws Exception {{
        // {description}
        {auth_setup}
        mockMvc.perform({method_lower}("{endpoint}")
            .contentType(MediaType.APPLICATION_JSON)
            {csrf_header}
            .content("{{\\"test\\": \\"value\\"}}"))
            .andExpect(status().is{expected_status_name}());
    }}
""",
    },
}


def slugify(text: str) -> str:
    """Convert endpoint path to test function name."""
    return re.sub(r"[^a-z0-9]", "_", text.lower()).strip("_")


def generate_unit_tests(transactions: list[dict], framework: str) -> str:
    """Generate unit test file content for the given framework."""
    import re

    template = UNIT_TEST_TEMPLATES.get(framework, UNIT_TEST_TEMPLATES["express"])
    lines = [template["header"]]

    mutating = ["POST", "PUT", "PATCH", "DELETE"]
    test_transactions = [t for t in transactions if t["method"] in mutating]

    if not test_transactions:
        test_transactions = transactions  # Include all if no mutating found

    for txn in test_transactions:
        method = txn["method"].upper()
        endpoint = txn["endpoint"]
        slug = slugify(endpoint)
        fields = txn.get("fields", [])
        requires_csrf = txn.get("requires_csrf", False)
        requires_auth = txn.get("requires_auth", False)
        description = txn.get("description", "Auto-generated test")

        # Format fields
        field_lines = []
        for f in fields[:10]:  # Max 10 fields
            name = f["name"]
            ftype = f.get("type", "string")
            if framework in ("laravel", "django"):
                if ftype == "email":
                    field_lines.append(f"            '{name}' => 'test@example.com',")
                elif ftype == "password":
                    field_lines.append(f"            '{name}' => 'TestPassword123!',")
                else:
                    field_lines.append(f"            '{name}' => 'test_value',")
            elif framework in ("express", "nestjs"):
                if ftype == "email":
                    field_lines.append(f'        "{name}": "test@example.com",')
                elif ftype == "password":
                    field_lines.append(f'        "{name}": "TestPassword123!",')
                else:
                    field_lines.append(f'        "{name}": "test_value",')

        fields_str = "\n".join(field_lines)

        # Auth setup
        if requires_auth:
            if framework == "laravel":
                auth_setup = "$this->actingAs(User::factory()->create());"
            elif framework == "django":
                auth_setup = "self.client.force_login(User.objects.create_user('testuser', 'test@test.com', 'pass'))"
            elif framework in ("express", "nestjs"):
                auth_setup = "// TODO: Set Authorization header with valid JWT token"
            else:
                auth_setup = "// TODO: Setup authentication"
        else:
            auth_setup = ""

        # CSRF setup
        if requires_csrf:
            csrf_field_name = txn.get("csrf_field_name", "_token")
            if framework == "laravel":
                csrf_field = f"'{csrf_field_name}' => csrf_token(),"
                csrf_kwarg = ""
                csrf_header = ""
            elif framework == "django":
                csrf_field = ""
                csrf_kwarg = ", enforce_csrf_checks=False"
                csrf_header = ""
            elif framework in ("express", "nestjs"):
                csrf_field = ""
                csrf_kwarg = ""
                csrf_header = f'.set("X-CSRF-Token", "test-csrf-token")'
            else:
                csrf_field = ""
                csrf_kwarg = ""
                csrf_header = ""
        else:
            csrf_field = ""
            csrf_kwarg = ""
            csrf_header = ""

        expected_status = 201 if method == "POST" else 200

        test_case = template["test_case"].format(
            method=method,
            method_lower=method.lower(),
            endpoint=endpoint,
            endpoint_slug=slug,
            EndpointCamel="".join(w.capitalize() for w in slug.split("_")),
            description=description,
            auth_setup=auth_setup,
            fields=fields_str,
            csrf_field=csrf_field,
            csrf_kwarg=csrf_kwarg,
            csrf_header=csrf_header,
            expected_status=expected_status,
            expected_status_name="Ok" if expected_status == 200 else "Created",
        )

        lines.append(test_case)

    lines.append(template["footer"])
    return "".join(lines)


# ─── Markdown Report Builder ─────────────────────────────────────────────────

def build_report(
    ingestion: dict,
    identification: dict,
    carbon: dict,
    output_dir: str,
) -> str:
    """Build full Markdown report."""

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    framework = identification.get("framework", "unknown")
    language = identification.get("language", "Unknown")
    transactions = identification.get("transactions", [])
    measurements = {m["transaction_id"]: m for m in carbon.get("measurements", [])}

    lines = [
        f"# 🤖 Code Carbon Report",
        f"",
        f"> Generated: `{now}`",
        f"> Source: `{ingestion.get('source_path', 'N/A')}`",
        f"> Framework: `{framework}` · Language: `{language}`",
        f"",
        f"---",
        f"",
        f"## 📊 Executive Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Routes | `{identification.get('total_routes', 0)}` |",
        f"| POST/Mutating | `{identification.get('post_routes', 0)}` |",
        f"| CSRF Protected | `{identification.get('csrf_protected_routes', 0)}` |",
        f"| Auth Required | `{identification.get('auth_required_routes', 0)}` |",
        f"| Successful Requests | `{carbon.get('successful_requests', 0)}/{carbon.get('total_requests', 0)}` |",
        f"| Total Energy | `{carbon.get('total_energy_kwh', 0):.8f} kWh` |",
        f"| Total CO₂ | `{carbon.get('total_co2_kg', 0)*1000:.4f} g` |",
        f"| Avg Response Time | `{carbon.get('avg_response_time_ms', 0):.1f} ms` |",
        f"",
        f"---",
        f"",
        f"## 🔍 Transaction Analysis",
        f"",
    ]

    # Group by method
    for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
        method_txns = [t for t in transactions if t["method"] == method]
        if not method_txns:
            continue

        icon = {"GET": "🔵", "POST": "🟢", "PUT": "🟡", "PATCH": "🟠", "DELETE": "🔴"}.get(method, "⚪")
        lines.append(f"### {icon} {method} Endpoints ({len(method_txns)})")
        lines.append("")

        for txn in method_txns:
            m = measurements.get(txn["id"], {})
            status = m.get("status_code", "—")
            rtime = m.get("response_time_ms", 0)
            co2 = m.get("co2_emissions_kg", 0) * 1000
            success = "✅" if m.get("success") else "❌"

            lines.append(f"#### `{txn['endpoint']}`")
            lines.append(f"")
            lines.append(f"- **Description:** {txn.get('description', 'N/A')}")
            lines.append(f"- **Auth Required:** {'✅ Yes' if txn.get('requires_auth') else '❌ No'}")
            lines.append(f"- **CSRF Protected:** {'✅ Yes' if txn.get('requires_csrf') else '❌ No'}")
            if txn.get("csrf_field_name"):
                lines.append(f"- **CSRF Field:** `{txn['csrf_field_name']}`")
            lines.append(f"- **Live Result:** {success} `HTTP {status}` · `{rtime:.0f}ms` · `{co2:.4f}g CO₂`")

            if txn.get("fields"):
                lines.append(f"")
                lines.append(f"**Required Fields:**")
                lines.append(f"")
                lines.append(f"| Field | Type | Required | Validation |")
                lines.append(f"|-------|------|----------|------------|")
                for f in txn["fields"]:
                    req = "✅" if f.get("required") else "⬜"
                    rules = ", ".join(f.get("validation_rules", [])) or "—"
                    lines.append(f"| `{f['name']}` | `{f['type']}` | {req} | `{rules}` |")

            lines.append(f"")

    # CSRF Summary
    lines += [
        f"---",
        f"",
        f"## 🔐 CSRF Analysis",
        f"",
        f"Framework `{framework}` uses the following CSRF pattern:",
        f"",
    ]

    csrf_txns = [t for t in transactions if t.get("requires_csrf")]
    if csrf_txns:
        csrf_fields = list(set(t.get("csrf_field_name", "") for t in csrf_txns if t.get("csrf_field_name")))
        for cf in csrf_fields:
            lines.append(f"- CSRF field name: **`{cf}`**")
        lines.append("")
        lines.append("Endpoints with CSRF protection:")
        for t in csrf_txns:
            lines.append(f"- `{t['method']} {t['endpoint']}`")
    else:
        lines.append("_No CSRF-protected endpoints detected._")

    lines += [
        f"",
        f"---",
        f"",
        f"## 🌱 Carbon Footprint Analysis",
        f"",
        f"| Endpoint | Method | Status | Energy (kWh) | CO₂ (g) | Time (ms) |",
        f"|----------|--------|--------|-------------|---------|-----------|",
    ]

    for m in carbon.get("measurements", []):
        co2_g = m["co2_emissions_kg"] * 1000
        icon = "✅" if m["success"] else "❌"
        lines.append(
            f"| `{m['endpoint']}` | `{m['method']}` | {icon} `{m['status_code']}` "
            f"| `{m['energy_consumed_kwh']:.8f}` | `{co2_g:.4f}` | `{m['response_time_ms']:.0f}` |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## 🔧 Refactoring Recommendations",
        f"",
    ]

    # Auto recommendations
    recs = []

    slow_txns = [m for m in carbon.get("measurements", []) if m["response_time_ms"] > 1000]
    if slow_txns:
        recs.append(f"**⚠️ Slow endpoints detected** ({len(slow_txns)} endpoint > 1000ms):")
        for m in slow_txns:
            recs.append(f"  - `{m['method']} {m['endpoint']}` ({m['response_time_ms']:.0f}ms) — consider caching or query optimization")

    failed_txns = [m for m in carbon.get("measurements", []) if not m["success"]]
    if failed_txns:
        recs.append(f"**❌ Failed requests** ({len(failed_txns)} endpoints returned error):")
        for m in failed_txns:
            recs.append(f"  - `{m['method']} {m['endpoint']}` → HTTP {m['status_code']}")

    unprotected_mutating = [
        t for t in transactions
        if t["method"] in ["POST", "PUT", "PATCH", "DELETE"]
        and not t.get("requires_csrf")
        and not t.get("requires_auth")
    ]
    if unprotected_mutating:
        recs.append(f"**🔓 Unprotected mutating endpoints** — no CSRF or auth:")
        for t in unprotected_mutating:
            recs.append(f"  - `{t['method']} {t['endpoint']}`")

    if not recs:
        recs.append("✅ No critical issues detected. Code looks clean!")

    for rec in recs:
        lines.append(rec)
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## 🧪 Generated Unit Tests",
        f"",
        f"Unit test files have been saved to `{output_dir}/tests/`",
        f"",
        f"| File | Framework | Test Count |",
        f"|------|-----------|------------|",
        f"| `GeneratedTransactionTest.{UNIT_TEST_TEMPLATES.get(framework, UNIT_TEST_TEMPLATES['express'])['ext']}` | `{framework}` | `{identification.get('post_routes', 0)}` |",
        f"",
        f"---",
        f"",
        f"_Report generated by Multi-Agent Code Carbon System_",
    ]

    return "\n".join(lines)


def run(output_dir: str = "./output") -> str:
    """
    Main entry point for Agent 4.
    
    Args:
        output_dir: Directory containing all agent outputs
    
    Returns:
        Path to the generated report
    """
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(f"{REPORT_DIR}/tests", exist_ok=True)

    # Load all agent outputs
    with open(f"{output_dir}/transactions.json") as f:
        identification = json.load(f)

    with open(f"{output_dir}/carbon_report.json") as f:
        carbon = json.load(f)

    # Agent 1 result may or may not exist
    ingestion_path = Path(output_dir) / "ingestion_result.json"
    if ingestion_path.exists():
        with open(ingestion_path) as f:
            ingestion = json.load(f)
    else:
        ingestion = {"source_path": output_dir}

    framework = identification.get("framework", "express")

    # Generate unit tests
    print("[Agent 4] Generating unit tests...")
    test_content = generate_unit_tests(identification.get("transactions", []), framework)
    test_ext = UNIT_TEST_TEMPLATES.get(framework, UNIT_TEST_TEMPLATES["express"])["ext"]
    test_path = f"{REPORT_DIR}/tests/GeneratedTransactionTest.{test_ext}"
    with open(test_path, "w") as f:
        f.write(test_content)
    print(f"[Agent 4] Unit tests saved: {test_path}")

    # Generate markdown report
    print("[Agent 4] Building report...")
    report_md = build_report(ingestion, identification, carbon, REPORT_DIR)
    report_path = f"{REPORT_DIR}/code_carbon_report.md"
    with open(report_path, "w") as f:
        f.write(report_md)

    print(f"[Agent 4] ✅ Report saved: {report_path}")
    return report_path


if __name__ == "__main__":
    import sys
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "./output"
    run(out_dir)
```

---

## Pipeline Orchestrator

### File: `pipeline.py`

```python
#!/usr/bin/env python3
"""
Pipeline Orchestrator
Runs all 4 agents in sequence.
"""

import sys
import json
import argparse
from dataclasses import asdict
from pathlib import Path

import agent1_ingestion
import agent2_gemini_identifier
import agent3_carbon
import agent4_report


def main():
    parser = argparse.ArgumentParser(
        description="Multi-Agent Code Carbon Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local directory
  python pipeline.py --source ./my-laravel-app

  # Git repository
  python pipeline.py --source https://github.com/user/repo

  # Skip carbon testing (no live app running)
  python pipeline.py --source ./my-app --skip-carbon

  # Specify output directory
  python pipeline.py --source ./my-app --output ./my-analysis
        """
    )
    parser.add_argument("--source", required=True, help="Local path or Git URL")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--skip-carbon", action="store_true",
                        help="Skip Agent 3 (no live app required)")
    parser.add_argument("--base-url", default=None,
                        help="Override TARGET_BASE_URL for Agent 3")

    args = parser.parse_args()

    if args.base_url:
        import os
        os.environ["TARGET_BASE_URL"] = args.base_url

    print("=" * 60)
    print("🤖 MULTI-AGENT CODE CARBON PIPELINE")
    print("=" * 60)

    # ── Agent 1 ───────────────────────────────────────────────
    print("\n[PIPELINE] ▶ Agent 1 — Repository Ingestion")
    ingestion = agent1_ingestion.run(args.source, args.output)
    if not ingestion.success:
        print(f"[PIPELINE] ❌ Agent 1 failed: {ingestion.error}")
        sys.exit(1)

    # Save ingestion result
    with open(f"{args.output}/ingestion_result.json", "w") as f:
        json.dump(asdict(ingestion), f, indent=2)

    # ── Agent 2 ───────────────────────────────────────────────
    print("\n[PIPELINE] ▶ Agent 2 — Gemini Transaction Identifier")
    identification = agent2_gemini_identifier.run(
        ingestion.flat_file_path,
        ingestion.detected_framework
    )
    if not identification.success:
        print(f"[PIPELINE] ❌ Agent 2 failed: {identification.error}")
        sys.exit(1)

    # ── Agent 3 ───────────────────────────────────────────────
    if args.skip_carbon:
        print("\n[PIPELINE] ⏭  Agent 3 — Skipped (--skip-carbon)")
        # Create empty carbon result
        empty_carbon = {
            "success": True, "base_url": "", "total_requests": 0,
            "successful_requests": 0, "failed_requests": 0,
            "total_energy_kwh": 0.0, "total_co2_kg": 0.0,
            "avg_response_time_ms": 0.0, "measurements": []
        }
        with open(f"{args.output}/carbon_report.json", "w") as f:
            json.dump(empty_carbon, f, indent=2)
    else:
        print("\n[PIPELINE] ▶ Agent 3 — Code Carbon")
        carbon = agent3_carbon.run(f"{args.output}/transactions.json")
        if not carbon.success:
            print(f"[PIPELINE] ⚠️  Agent 3 warning: {carbon.error}")

    # ── Agent 4 ───────────────────────────────────────────────
    print("\n[PIPELINE] ▶ Agent 4 — Refactor Report")
    report_path = agent4_report.run(args.output)

    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE")
    print(f"📄 Report: {report_path}")
    print(f"🧪 Tests:  ./reports/tests/")
    print("=" * 60)


if __name__ == "__main__":
    main()
```

---

## Web UI — CSRF & Form Field Handler

File ini adalah **web interface** yang menampilkan form dari hasil Gemini, lengkap dengan field yang harus diisi, label, dan CSRF token secara otomatis.

### File: `web_ui/index.html`

```html
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>Code Carbon — Transaction Tester</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }
    .method-badge { display: inline-block; padding: 2px 10px; border-radius: 4px;
                    font-weight: bold; font-size: 0.8rem; color: white; }
    .POST   { background: #2ecc71; }
    .GET    { background: #3498db; }
    .PUT    { background: #f39c12; }
    .PATCH  { background: #e67e22; }
    .DELETE { background: #e74c3c; }
    .form-group { margin: 0.75rem 0; }
    label { display: block; font-weight: 500; margin-bottom: 4px; }
    input, select { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px;
                    box-sizing: border-box; }
    input[type=password] { font-family: monospace; }
    .csrf-badge { font-size: 0.75rem; background: #fff3cd; padding: 2px 6px;
                  border-radius: 3px; border: 1px solid #ffc107; }
    .auth-badge { font-size: 0.75rem; background: #cce5ff; padding: 2px 6px;
                  border-radius: 3px; border: 1px solid #004085; }
    button[type=submit] { background: #2c3e50; color: white; border: none;
                          padding: 10px 20px; border-radius: 4px; cursor: pointer; }
    .response-box { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;
                    padding: 1rem; margin-top: 1rem; font-family: monospace;
                    white-space: pre-wrap; max-height: 300px; overflow-y: auto; }
    .required-mark { color: #e74c3c; }
  </style>
</head>
<body>
  <h1>🤖 Code Carbon — Transaction Tester</h1>
  <p>Load <code>transactions.json</code> to auto-generate forms for each endpoint.</p>

  <input type="file" id="txnFile" accept=".json">
  <div id="app"></div>

  <script>
    const BASE_URL = 'http://localhost:8000';  // Change this!

    document.getElementById('txnFile').addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const data = JSON.parse(await file.text());
      renderTransactions(data.transactions || [], data.framework || 'unknown');
    });

    function renderTransactions(transactions, framework) {
      const app = document.getElementById('app');
      app.innerHTML = '';

      transactions.forEach((txn, i) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.id = `txn-${txn.id}`;

        const badges = [
          `<span class="method-badge ${txn.method}">${txn.method}</span>`,
          txn.requires_csrf ? '<span class="csrf-badge">🔐 CSRF</span>' : '',
          txn.requires_auth ? '<span class="auth-badge">🔑 Auth</span>' : '',
        ].filter(Boolean).join(' ');

        let fieldsHtml = '';
        (txn.fields || []).forEach(f => {
          const inputType = {
            'email': 'email', 'password': 'password',
            'integer': 'number', 'number': 'number', 'file': 'file',
          }[f.type] || 'text';

          const req = f.required ? '<span class="required-mark">*</span>' : '';
          const rules = (f.validation_rules || []).join(', ');
          const placeholder = f.description || f.name;

          fieldsHtml += `
            <div class="form-group">
              <label for="${txn.id}_${f.name}">${f.name} ${req}
                <small style="color:#888;">(${f.type}${rules ? ' · ' + rules : ''})</small>
              </label>
              <input type="${inputType}"
                     id="${txn.id}_${f.name}"
                     name="${f.name}"
                     placeholder="${placeholder}"
                     ${f.required ? 'required' : ''}>
            </div>`;
        });

        // CSRF hidden field
        if (txn.requires_csrf && txn.csrf_field_name) {
          fieldsHtml += `
            <div class="form-group" style="opacity:0.5">
              <label>CSRF Token (auto-fetched: <code>${txn.csrf_field_name}</code>)</label>
              <input type="text" id="${txn.id}_csrf" name="${txn.csrf_field_name}"
                     placeholder="Will be fetched automatically" readonly>
            </div>`;
        }

        card.innerHTML = `
          <h3>${badges} <code>${txn.endpoint}</code></h3>
          <p style="color:#666;">${txn.description || ''}</p>
          <form id="form-${txn.id}">
            ${fieldsHtml}
            <button type="submit">Send ${txn.method} Request</button>
          </form>
          <div id="response-${txn.id}" class="response-box" style="display:none;"></div>
        `;

        app.appendChild(card);

        // Auto-fetch CSRF if needed
        if (txn.requires_csrf && txn.csrf_field_name) {
          fetchCsrfToken(txn, framework);
        }

        // Form submit
        document.getElementById(`form-${txn.id}`).addEventListener('submit', async (e) => {
          e.preventDefault();
          await submitTransaction(txn);
        });
      });
    }

    async function fetchCsrfToken(txn, framework) {
      try {
        // Try to get CSRF from the same page
        const endpoints = [txn.endpoint.replace('/api/', '/'), '/', '/login'];
        for (const ep of endpoints) {
          const r = await fetch(`${BASE_URL}${ep}`, { credentials: 'include' });
          if (r.ok) {
            const html = await r.text();
            const match = html.match(
              new RegExp(`name=["']${txn.csrf_field_name}["']\\s+value=["']([^"']+)["']`)
            ) || html.match(
              new RegExp(`value=["']([^"']+)["']\\s+name=["']${txn.csrf_field_name}["']`)
            );
            if (match) {
              const csrfInput = document.getElementById(`${txn.id}_csrf`);
              if (csrfInput) csrfInput.value = match[1];
              return;
            }
          }
        }
      } catch (e) {
        console.warn('Could not auto-fetch CSRF:', e.message);
      }
    }

    async function submitTransaction(txn) {
      const form = document.getElementById(`form-${txn.id}`);
      const responseBox = document.getElementById(`response-${txn.id}`);
      const formData = new FormData(form);
      const payload = Object.fromEntries(formData);

      responseBox.style.display = 'block';
      responseBox.textContent = '⏳ Sending...';

      try {
        const options = {
          method: txn.method,
          credentials: 'include',
          headers: {},
        };

        if (txn.method !== 'GET') {
          options.headers['Content-Type'] = 'application/json';
          options.body = JSON.stringify(payload);

          if (txn.requires_csrf && txn.csrf_field_name) {
            options.headers['X-CSRF-Token'] = payload[txn.csrf_field_name] || '';
          }
        }

        const start = performance.now();
        const r = await fetch(`${BASE_URL}${txn.endpoint}`, options);
        const elapsed = (performance.now() - start).toFixed(0);
        const text = await r.text();

        let display;
        try {
          display = JSON.stringify(JSON.parse(text), null, 2);
        } catch {
          display = text.substring(0, 1000);
        }

        responseBox.textContent =
          `HTTP ${r.status} (${elapsed}ms)\n\n${display}`;

      } catch (err) {
        responseBox.textContent = `❌ Error: ${err.message}`;
      }
    }
  </script>
</body>
</html>
```

---

## Unit Test Generator

Contoh output unit test untuk **Laravel** dari Agent 4:

```php
<?php
// reports/tests/GeneratedTransactionTest.php

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;
use App\Models\User;

class GeneratedTransactionTest extends TestCase
{
    use RefreshDatabase;

    /** @test */
    public function test_post_api_login()
    {
        $response = $this->post('/api/login', [
            'email'    => 'test@example.com',
            'password' => 'TestPassword123!',
            '_token'   => csrf_token(),
        ]);
        $response->assertStatus(200);
        $response->assertJsonStructure(['token']);
    }

    /** @test */
    public function test_post_api_register()
    {
        $response = $this->post('/api/register', [
            'name'                  => 'Test User',
            'email'                 => 'newuser@example.com',
            'password'              => 'TestPassword123!',
            'password_confirmation' => 'TestPassword123!',
            '_token'                => csrf_token(),
        ]);
        $response->assertStatus(201);
    }

    /** @test */
    public function test_post_api_transactions_requires_auth()
    {
        $response = $this->post('/api/transactions', [
            'amount'      => '100.00',
            'description' => 'Test transaction',
            '_token'      => csrf_token(),
        ]);
        // Should redirect to login or return 401
        $response->assertStatus(401);
    }

    /** @test */
    public function test_post_api_transactions_authenticated()
    {
        $user = User::factory()->create();
        $this->actingAs($user);

        $response = $this->post('/api/transactions', [
            'amount'      => '100.00',
            'description' => 'Test transaction',
            '_token'      => csrf_token(),
        ]);
        $response->assertStatus(201);
    }
}
```

---

## Configuration & Environment

### File: `.env`

```dotenv
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Agent 3 — Target app URL (must be running)
TARGET_BASE_URL=http://localhost:8000

# Optional tuning
REQUEST_TIMEOUT=30
DELAY_BETWEEN_REQUESTS=0.5

# Output paths
REPOMIX_OUTPUT_DIR=./output
REPORT_OUTPUT_DIR=./reports
```

### File: `requirements.txt`

```
codecarbon>=2.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0
python-dotenv>=1.0.0
lxml>=4.9.0
```

### Installation

```bash
# Install Python deps
pip install -r requirements.txt

# Install repomix (Node.js required)
npm install -g repomix

# Verify
repomix --version
python -c "import codecarbon; print('CodeCarbon OK')"
```

---

## Running the Full Pipeline

```bash
# 1. Analyze local Laravel project (app must be running)
python pipeline.py \
  --source /path/to/my-laravel-app \
  --base-url http://localhost:8000

# 2. Analyze from Git URL, skip live testing
python pipeline.py \
  --source https://github.com/user/my-express-api \
  --skip-carbon

# 3. Analyze Django app
python pipeline.py \
  --source /path/to/my-django-app \
  --base-url http://127.0.0.1:8000

# 4. Run only Agent 2 (already have repomix output)
python agent2_gemini_identifier.py ./output/flat_codebase.txt

# 5. Open Web UI
# Open web_ui/index.html in browser
# Load transactions.json
# Fill required fields → Send request
```

---

## Output Examples

### Directory Structure After Run

```
output/
├── flat_codebase.txt          ← Agent 1: repomix bundle
├── ingestion_result.json      ← Agent 1: metadata
├── transactions.json          ← Agent 2: all transactions + fields
└── carbon_report.json         ← Agent 3: per-request energy data

reports/
├── code_carbon_report.md      ← Agent 4: full report
└── tests/
    └── GeneratedTransactionTest.php  ← Agent 4: unit tests
```

### `transactions.json` Sample

```json
{
  "framework": "laravel",
  "language": "PHP",
  "total_routes": 12,
  "post_routes": 5,
  "csrf_protected_routes": 5,
  "auth_required_routes": 8,
  "transactions": [
    {
      "id": "txn_001",
      "method": "POST",
      "endpoint": "/api/login",
      "description": "Authenticate user and return token",
      "requires_auth": false,
      "requires_csrf": true,
      "csrf_field_name": "_token",
      "fields": [
        {
          "name": "email",
          "type": "email",
          "required": true,
          "description": "User email",
          "validation_rules": ["required", "email"]
        },
        {
          "name": "password",
          "type": "password",
          "required": true,
          "description": "User password",
          "validation_rules": ["required", "min:8"]
        }
      ],
      "tags": ["auth"]
    }
  ]
}
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `repomix: command not found` | Not installed | `npm install -g repomix` |
| `Gemini API 429 Too Many Requests` | Rate limit hit | Add `GEMINI_DELAY=10` to .env |
| `Connection refused` in Agent 3 | App not running | Start app or use `--skip-carbon` |
| `CSRF token mismatch` in Agent 3 | Wrong field name | Gemini will detect correct name; check `transactions.json` |
| `CodeCarbon ImportError` | Not installed | `pip install codecarbon` |
| `repomix output too large` | Big codebase | Add exclusions in `FRAMEWORK_SIGNATURES` |

---

_Dibuat dengan ❤️ untuk semua framework — Laravel, Django, Express, Spring, Rails, FastAPI, NestJS, Go, ASP.NET_
