#!/usr/bin/env python3
"""
Agent 4 — Refactor Report Agent
Combines all data and generates comprehensive Markdown report + unit tests.
"""

import os
import re
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
        f"|----------|--------|--------|-------------|---------|-----------| ",
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
