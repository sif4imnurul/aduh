#!/usr/bin/env python3
"""
Pipeline Orchestrator
Runs all 4 agents in sequence.
"""

import sys
import os
import json
import argparse
from dataclasses import asdict
from pathlib import Path

# Fix Windows console Unicode encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

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
