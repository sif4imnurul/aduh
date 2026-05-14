import json
import time
from pathlib import Path

def run(output_dir: str = "./output") -> dict:
    print("\n[Agent 5] 🧪 Starting Validation Agent...")
    
    # Load refactor results
    refactor_path = Path(output_dir) / "refactor_result.json"
    if not refactor_path.exists():
        print("[Agent 5] ⏭️ No refactoring to validate.")
        return {"success": True, "validated_items": 0}

    with open(refactor_path) as f:
        suggestions = json.load(f)

    results = []
    print(f"[Agent 5] Validating {len(suggestions)} refactor suggestions...")

    for item in suggestions:
        print(f"[Agent 5] [VALIDATE-START] Checking {item['file']}...")
        
        # Simulated Validation Logic
        # In a real scenario, this could run 'php artisan test' or a linter
        time.sleep(1)
        
        is_valid = True
        error_msg = ""
        
        # Simple heuristic check: does refactored code contain '??' or empty?
        if not item['refactored_code'] or "error" in item['refactored_code'].lower():
            is_valid = False
            error_msg = "Syntax error or empty refactor suggested"

        status = "Passed" if is_valid else "Failed"
        print(f"[AGENT5-VALIDATE] {item['file']} | result:{status}")
        
        results.append({
            "file": item['file'],
            "valid": is_valid,
            "error": error_msg,
            "timestamp": time.time()
        })

    validation_result = {
        "success": all(r['valid'] for r in results),
        "total_validated": len(results),
        "details": results
    }

    with open(f"{output_dir}/validation_result.json", "w") as f:
        json.dump(validation_result, f, indent=2)

    print(f"[Agent 5] ✅ Validation Complete. Success: {validation_result['success']}")
    return validation_result

if __name__ == "__main__":
    run()
