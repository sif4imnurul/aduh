import os
import json
import time
import requests
from pathlib import Path
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = "inclusionai/ring-2.6-1t:free"

@dataclass
class RefactorSuggestion:
    file: str
    original_lines: str
    original_code: str
    refactored_code: str
    explanation: str

def run(output_dir: str = "./output") -> list[dict]:
    print("\n[Agent 4] 🛠️ Starting Code Refactoring Agent...")
    
    # Load inefficiencies from Agent 2
    with open(f"{output_dir}/transactions.json") as f:
        data = json.load(f)
    
    inefficiencies = data.get("inefficiencies", [])
    if not inefficiencies:
        print("[Agent 4] ✅ No inefficiencies found to refactor.")
        return []

    suggestions = []
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://carbon-dashboard.enterprise",
        "X-Title": "Enterprise Carbon Dashboard"
    }

    for item in inefficiencies:
        print(f"[Agent 4] [REFACTOR-START] Analyzing {item['file']} (Lines {item['lines']})")
        
        prompt = f"""
        Refactor the following code to improve energy efficiency and performance.
        Reason for refactor: {item['reason']}
        Impact: {item['impact']}
        Suggestion: {item['suggestion']}

        File: {item['file']}
        Lines: {item['lines']}
        
        Return ONLY a JSON object with:
        {{
          "refactored_code": "...",
          "explanation": "..."
        }}
        """

        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }

        try:
            # Simulated API call for speed in demo, or real call
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            result = response.json()
            ai_content = result["choices"][0]["message"]["content"]
            
            # Clean JSON
            if "```json" in ai_content:
                ai_content = ai_content.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_content:
                ai_content = ai_content.split("```")[1].split("```")[0].strip()
                
            parsed = json.loads(ai_content)
            
            suggestion = RefactorSuggestion(
                file=item['file'],
                original_lines=item['lines'],
                original_code="[Original Code Snippet]", # Ideally read from flat_codebase
                refactored_code=parsed['refactored_code'],
                explanation=parsed['explanation']
            )
            
            suggestions.append(asdict(suggestion))
            print(f"[AGENT4-REFACTOR] {item['file']} | {item['lines']} | status:Success")
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[Agent 4] Error refactoring {item['file']}: {str(e)}")

    # Save refactor result
    with open(f"{output_dir}/refactor_result.json", "w") as f:
        json.dump(suggestions, f, indent=2)
    
    return suggestions

if __name__ == "__main__":
    run()
