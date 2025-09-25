import json
from typing import Dict, Any
from utils.validators import is_destructive
from . import gemini_client, claude_client


def normalize(raw: Dict) -> Dict:
    # Ensure the plan has 'plan' and 'steps' keys and normalize step shape
    plan = {"plan": raw.get("plan", "unnamed"), "steps": []}
    for s in raw.get("steps", []):
        cmd = s.get("command")
        args = s.get("args", {})
        plan["steps"].append({"command": cmd, "args": args})
    return plan


def get_plan(text: str, backend: str = "gemini") -> Dict:
    if backend == "claude":
        raw = claude_client.query_claude(text)
    else:
        raw = gemini_client.query_gemini(text)
    return normalize(raw)

def normalize(ai_output: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure ai_output matches expected plan schema.

    Expected:
    {"plan": str, "steps": [{"id": int, "command": str, "args": dict, "needs_confirmation": bool}]}
    """
    plan = ai_output.get("plan") or ai_output.get("description") or "unnamed plan"
    raw_steps = ai_output.get("steps") or ai_output.get("commands") or []
    steps = []
    for i, s in enumerate(raw_steps):
        # allow simple string commands
        if isinstance(s, str):
            args = {"command": s}
            needs = is_destructive(s)
            steps.append({"id": i, "command": "terminal.run", "args": args, "needs_confirmation": needs})
        elif isinstance(s, dict):
            cmd_name = s.get("command") or s.get("method") or s.get("tool")
            args = s.get("args") or s.get("params") or {}
            # mark destructive if any string in args looks destructive
            needs = any(is_destructive(v) for v in [json.dumps(args)])
            steps.append({"id": s.get("id", i), "command": cmd_name, "args": args, "needs_confirmation": needs})
        else:
            # unknown step shape, represent as a terminal echo
            steps.append({"id": i, "command": "terminal.run", "args": {"command": str(s)}, "needs_confirmation": False})

    return {"plan": plan, "steps": steps}
