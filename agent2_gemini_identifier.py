#!/usr/bin/env python3
"""
Agent 2 — Gemini Transaction Identifier Agent
With streaming progress output (per-transaction display).
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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "inclusionai/ring-2.6-1t:free"

# Context window for free models on OpenRouter is often limited.
# We use 300k chars to ensure it fits within most free model limits.
MAX_CONTENT_CHARS = 300_000


@dataclass
class TransactionField:
    name: str
    type: str
    required: bool
    description: str
    validation_rules: list[str] = field(default_factory=list)


@dataclass
class Inefficiency:
    file: str
    lines: str
    reason: str
    impact: str
    suggestion: str

@dataclass
class Transaction:
    id: str
    method: str
    endpoint: str
    description: str
    requires_auth: bool
    requires_csrf: bool
    csrf_field_name: str
    fields: list[TransactionField]
    framework: str
    tags: list[str] = field(default_factory=list)


@dataclass
class IdentificationResult:
    success: bool
    framework: str
    language: str
    transactions: list[Transaction]
    inefficiencies: list[Inefficiency] = field(default_factory=list)
    total_routes: int = 0
    post_routes: int = 0
    csrf_protected_routes: int = 0
    auth_required_routes: int = 0
    error: Optional[str] = None


SYSTEM_PROMPT = """
You are an expert code analyzer. You will receive a flat bundle of a web application codebase.

Your task is to analyze EVERY SINGLE route/endpoint defined in the code. Do not skip any.
Be exhaustive. Scan all controller files and route definitions.

## What to extract per endpoint:
1. HTTP method (GET, POST, PUT, PATCH, DELETE)
2. URL path / route
3. Description of what the endpoint does
4. Whether it requires authentication (JWT, session, Bearer token, etc.)
5. Whether it requires CSRF protection — detect automatically by framework
6. The exact CSRF field name used (e.g., "_token", "csrfmiddlewaretoken")
7. ALL form fields with: name, type, required status, validation rules

## Response format — return ONLY valid JSON:

{
  "framework": "laravel",
  "language": "PHP",
  "transactions": [
    {
      "id": "txn_001",
      "method": "POST",
      "endpoint": "/api/login",
      "description": "User authentication",
      "requires_auth": false,
      "requires_csrf": true,
      "csrf_field_name": "_token",
      "fields": [
        {"name": "email", "type": "email", "required": true, "validation_rules": ["required", "email"]}
      ]
    }
  ],
  "inefficiencies": [
    {
      "file": "app/Http/Controllers/UserController.php",
      "lines": "45-60",
      "reason": "N+1 Query in user list",
      "impact": "High Database Load / Energy Waste",
      "suggestion": "Use Eager Loading with User::with('profile')->get()"
    }
  ]
}
"""


def chunk_content(content: str, max_chars: int) -> str:
    total_lines = content.count("\n")
    print(f"[Agent 2] [DEBUG] Original codebase size: {len(content)} chars, {total_lines} lines", flush=True)
    
    if len(content) <= max_chars:
        print(f"[Agent 2] [DEBUG] Content within limit, no chunking needed.", flush=True)
        return content
    
    lines = content.split("\n")
    priority_keywords = ["route", "controller", "middleware", "csrf", "request",
                        "form", "validate", "auth", "login", "register", "api",
                        "POST", "GET", "PUT", "DELETE", "PATCH"]
    
    priority_lines = []
    other_lines = []
    
    for line in lines:
        if any(kw.lower() in line.lower() for kw in priority_keywords):
            priority_lines.append(line)
        else:
            other_lines.append(line)
    
    print(f"[Agent 2] [DEBUG] Keywords found in {len(priority_lines)} lines. Non-priority lines: {len(other_lines)}", flush=True)
    
    result = "\n".join(priority_lines)
    if len(result) < max_chars:
        remaining = max_chars - len(result)
        print(f"[Agent 2] [DEBUG] Adding {remaining} chars from non-priority lines...", flush=True)
        result += "\n" + "\n".join(other_lines)[:remaining]
    
    final_chars = len(result)
    print(f"[Agent 2] [DEBUG] Final context size: {final_chars} chars", flush=True)
    return result[:max_chars]


def call_openrouter(content: str) -> dict:
    key_preview = f"{OPENROUTER_API_KEY[:6]}..." if OPENROUTER_API_KEY else "None"
    print(f"[Agent 2] [DEBUG] API Key configured: {key_preview}", flush=True)
    print(f"[Agent 2] [DEBUG] Initializing OpenRouter (Model: {MODEL_NAME})", flush=True)
    print(f"[Agent 2] Sending {len(content)} chars to OpenRouter...", flush=True)
    start_time = time.time()
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://carbon-dashboard.enterprise", # Required for OpenRouter
        "X-Title": "Enterprise Carbon Dashboard"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": f"{SYSTEM_PROMPT}\n\nAnalyze this codebase:\n\n{content}"}
        ],
        "temperature": 0.1,
    }
    
    for attempt in range(5):
        try:
            print(f"[Agent 2] [DEBUG] Generation attempt {attempt + 1}/5...", flush=True)
            
            response = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=180
            )
            
            if response.status_code != 200:
                print(f"[Agent 2] [DEBUG] Error {response.status_code}: {response.text}", flush=True)
                response.raise_for_status()
            
            try:
                data = response.json()
            except Exception as json_err:
                print(f"[Agent 2] [ERROR] Gagal memproses JSON dari OpenRouter: {str(json_err)}", flush=True)
                print(f"[Agent 2] [DEBUG] Raw Response: {response.text[:500]}...", flush=True)
                raise json_err
                
            raw_text = data["choices"][0]["message"]["content"].strip()
            
            # Remove markdown if present
            if raw_text.startswith("```"):
                lines = raw_text.split("\n")
                if lines[0].startswith("```json"):
                    raw_text = "\n".join(lines[1:-1])
                else:
                    raw_text = "\n".join(lines[1:-1])

            print(f"[Agent 2] [DEBUG] Raw AI response length: {len(raw_text)} chars", flush=True)
            
            elapsed = time.time() - start_time
            print(f"[Agent 2] OpenRouter responded in {elapsed:.1f}s", flush=True)
            
            try:
                parsed_json = json.loads(raw_text)
                print(f"[Agent 2] [DEBUG] JSON validation successful.", flush=True)
                return parsed_json
            except json.JSONDecodeError as je:
                print(f"[Agent 2] [ERROR] AI output is not valid JSON. Content snippet: {raw_text[:200]}...", flush=True)
                raise je
        
        except requests.exceptions.Timeout:
            print(f"[Agent 2] [ERROR] Request TIMEOUT! OpenRouter took too long (>180s).", flush=True)
            if attempt == 4: raise
            time.sleep(10)
        except Exception as e:
            print(f"[Agent 2] [ERROR] Gagal memanggil OpenRouter: {str(e)}", flush=True)
            if "429" in str(e):
                wait_time = 30 * (attempt + 1)
                print(f"[Agent 2] [DEBUG] Rate limit hit. Waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
            elif attempt == 4:
                raise e
            else:
                time.sleep(5)
    
    raise RuntimeError("OpenRouter failed after 5 attempts")


def parse_result(raw: dict, framework_hint: str = "") -> IdentificationResult:
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
            tags=t.get("tags", []),
        ))
    
    inefficiencies = [
        Inefficiency(**i) for i in raw.get("inefficiencies", [])
    ]
    
    mutating = {"POST", "PUT", "PATCH", "DELETE"}
    return IdentificationResult(
        success=True,
        framework=raw.get("framework", framework_hint),
        language=raw.get("language", "Unknown"),
        transactions=transactions,
        inefficiencies=inefficiencies,
        total_routes=len(transactions),
        post_routes=sum(1 for t in transactions if t.method in mutating),
        csrf_protected_routes=sum(1 for t in transactions if t.requires_csrf),
        auth_required_routes=sum(1 for t in transactions if t.requires_auth),
    )


def stream_transactions_output(result: IdentificationResult):
    """
    Stream tiap transaksi ke stdout dengan format yang bisa di-parse frontend.
    Format: [AGENT2-TX] method | endpoint | csrf:yes/no | auth:yes/no | fields:N
    """
    print(f"[Agent 2] Found {result.total_routes} routes — streaming details:", flush=True)
    
    for i, tx in enumerate(result.transactions, 1):
        csrf = "yes" if tx.requires_csrf else "no"
        auth = "yes" if tx.requires_auth else "no"
        field_count = len(tx.fields)
        
        # Format khusus untuk parsing di frontend
        print(
            f"[AGENT2-TX] {tx.method} | {tx.endpoint} | "
            f"csrf:{csrf} | auth:{auth} | fields:{field_count} | "
            f"id:{tx.id} | desc:{tx.description[:60]}",
            flush=True
        )
        
        # Delay kecil supaya visual streaming effect
        time.sleep(0.15)
    
    print(f"[Agent 2]    POST/mutating: {result.post_routes}", flush=True)
    print(f"[Agent 2]    CSRF protected: {result.csrf_protected_routes}", flush=True)
    print(f"[Agent 2]    Auth required: {result.auth_required_routes}", flush=True)


def run(flat_file_path: str, framework_hint: str = "") -> IdentificationResult:
    try:
        print(f"[Agent 2] Reading: {flat_file_path}", flush=True)
        content = Path(flat_file_path).read_text(encoding="utf-8", errors="replace")
        
        print(f"[Agent 2] Preparing context (limit: {MAX_CONTENT_CHARS} chars)...", flush=True)
        content = chunk_content(content, MAX_CONTENT_CHARS)
        
        raw = call_openrouter(content)
        print("[Agent 2] Parsing results...", flush=True)
        result = parse_result(raw, framework_hint)
        
        # STREAMING OUTPUT — yang baru ditambahkan
        stream_transactions_output(result)
        
        # Save transactions
        output_path = Path(flat_file_path).parent / "transactions.json"
        with open(output_path, "w") as f:
            json.dump(asdict(result), f, indent=2)
        print(f"[Agent 2] Saved: {output_path}", flush=True)
        
        return result
    
    except Exception as e:
        print(f"[Agent 2] Error: {str(e)}", flush=True)
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