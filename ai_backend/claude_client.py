"""Claude client adapter (stubbed if no API key present)."""
from typing import Dict
from config import CLAUDE_API_KEY

def query_claude(prompt: str, **kwargs):
    if not CLAUDE_API_KEY:
        return {
            "plan": "Mock Claude plan",
            "steps": [
                {"command": "terminal.run", "args": {"command": "echo 'Hello from Claude'"}}
            ]
        }
    # TODO: implement real Claude API invocation using CLAUDE_API_KEY
    return {"plan": "Claude (stubbed, key provided but not implemented)", "steps": []}
"""Stub Claude adapter. Replace with real API calls when ready."""


def generate_plan(prompt: str, context: Dict = None) -> Dict:
    """Return a mocked plan dict. In production, call Claude API and return structured JSON."""
    return {
        "plan": f"Mock plan from Claude for: {prompt}",
        "steps": [
            {"id": 0, "command": "files.list", "args": {"path": "~/Downloads"}, "needs_confirmation": False},
            {"id": 1, "command": "terminal.run", "args": {"command": "echo 'hello from claude'"}, "needs_confirmation": False},
        ],
    }
