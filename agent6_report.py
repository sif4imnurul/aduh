import os
import re
import json
from pathlib import Path
from datetime import datetime
from dataclasses import asdict
from typing import Any
from dotenv import load_dotenv

load_dotenv()
REPORT_DIR = "./reports"

def run(output_dir: str = "./output") -> str:
    print("\n[Agent 6] 📝 Generating Final Comprehensive Report...")
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Load all data
    with open(f"{output_dir}/transactions.json") as f:
        identification = json.load(f)
    with open(f"{output_dir}/carbon_report.json") as f:
        carbon = json.load(f)
    
    # Load new agent data if exists
    refactor_data = []
    if Path(f"{output_dir}/refactor_result.json").exists():
        with open(f"{output_dir}/refactor_result.json") as f:
            refactor_data = json.load(f)
            
    validation_data = {"success": True, "details": []}
    if Path(f"{output_dir}/validation_result.json").exists():
        with open(f"{output_dir}/validation_result.json") as f:
            validation_data = json.load(f)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = [
        f"# 🤖 Multi-Agent Carbon & Refactor Report",
        f"",
        f"> Generated: `{now}`",
        f"",
        f"## 📊 Executive Summary",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Routes | `{identification.get('total_routes', 0)}` |",
        f"| Energy Consumed | `{carbon.get('total_energy_kwh', 0):.8f} kWh` |",
        f"| CO₂ Emissions | `{carbon.get('total_co2_kg', 0)*1000:.4f} g` |",
        f"| Optimization Found | `{len(refactor_data)} locations` |",
        f"| Validation Status | {'✅ Passed' if validation_data['success'] else '❌ Failed'} |",
        f"",
        f"---",
        f"",
        f"## 🛠️ Refactoring & Optimization Results",
        f""
    ]

    if refactor_data:
        for i, ref in enumerate(refactor_data, 1):
            val_status = "✅ Validated"
            for v in validation_data.get("details", []):
                if v['file'] == ref['file'] and not v['valid']:
                    val_status = f"❌ Validation Error: {v['error']}"
            
            lines.append(f"### {i}. {ref['file']} (Lines {ref['original_lines']})")
            lines.append(f"- **Status:** {val_status}")
            lines.append(f"- **Explanation:** {ref['explanation']}")
            lines.append(f"#### Proposed Code:")
            lines.append(f"```php\n{ref['refactored_code']}\n```")
            lines.append("")
    else:
        lines.append("_No refactor suggestions generated._")

    lines.append("\n---\n## 🧪 Carbon Analysis Details")
    lines.append("| Endpoint | Method | Energy (kWh) | CO₂ (g) |")
    lines.append("|----------|--------|--------------|---------|")
    for m in carbon.get("measurements", []):
        lines.append(f"| `{m['endpoint']}` | `{m['method']}` | `{m['energy_consumed_kwh']:.8f}` | `{m['co2_emissions_kg']*1000:.4f}` |")

    report_path = f"{REPORT_DIR}/final_optimization_report.md"
    with open(report_path, "w") as f:
        f.write("\n".join(lines))

    print(f"[Agent 6] ✅ Final report saved to: {report_path}")
    return report_path

if __name__ == "__main__":
    run()
