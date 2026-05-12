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
