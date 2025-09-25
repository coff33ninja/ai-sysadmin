import json
from pathlib import Path
from typing import Dict, Any, List

PLAN_DIR = Path("storage/plans")
PLAN_DIR.mkdir(parents=True, exist_ok=True)

def _plan_path(plan_id: str) -> Path:
    return PLAN_DIR / f"{plan_id}.json"

def save_plan(plan: Dict[str, Any]) -> str:
    plan_id = plan.get("id") or str(hash(json.dumps(plan)))
    plan["id"] = plan_id
    path = _plan_path(plan_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    return plan_id

def load_plan(plan_id: str) -> Dict[str, Any]:
    path = _plan_path(plan_id)
    if not path.exists():
        return {"error": "plan not found", "id": plan_id}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_plans() -> List[Dict[str, Any]]:
    plans = []
    for p in PLAN_DIR.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                plans.append(json.load(f))
        except Exception:
            continue
    return plans
