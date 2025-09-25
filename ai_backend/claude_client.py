"""Claude client adapter with real API implementation."""

import json
import requests
from typing import Dict, Optional
from config import CLAUDE_API_KEY


def query_claude(prompt: str, **kwargs) -> Dict:
    """Query Claude API and return structured response."""
    if not CLAUDE_API_KEY:
        return {
            "plan": f"Mock Claude plan for: {prompt}",
            "steps": [
                {
                    "command": "terminal.run",
                    "args": {"command": "echo 'Hello from mocked Claude'"},
                }
            ],
        }

    try:
        # Use the actual Claude API
        headers = {
            "Content-Type": "application/json",
            "x-api-key": CLAUDE_API_KEY,
        }

        # Craft prompt to get structured JSON response
        system_prompt = """You are a system administrator AI. When given a task, respond with a JSON object containing:
{
    "plan": "Brief description of what you'll do",
    "steps": [
        {"command": "module.function", "args": {"param": "value"}},
        {"command": "terminal.run", "args": {"command": "shell command here"}}
    ]
}

Available commands:
- terminal.run: Execute shell commands
- files.list: List files in directory
- files.read: Read file contents  
- files.write: Write to file

Only respond with valid JSON, no additional text."""

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1000,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            content = data.get("content", [{}])[0].get("text", "")

            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Fallback: extract JSON from text if wrapped
                import re

                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return {
                        "plan": content,
                        "steps": [
                            {
                                "command": "terminal.run",
                                "args": {"command": "echo 'Manual step required'"},
                            }
                        ],
                    }
        else:
            return {"plan": f"Claude API error: {response.status_code}", "steps": []}

    except Exception as e:
        return {"plan": f"Claude API exception: {str(e)}", "steps": []}


def generate_plan(prompt: str, context: Optional[Dict] = None) -> Dict:
    """Generate a normalized plan using Claude."""
    raw_response = query_claude(prompt, context=context)

    # Normalize to expected format
    plan_text = raw_response.get("plan", prompt)
    raw_steps = raw_response.get("steps", [])

    normalized_steps = []
    for i, step in enumerate(raw_steps):
        normalized_steps.append(
            {
                "id": i,
                "command": step.get("command", "terminal.run"),
                "args": step.get("args", {}),
                "needs_confirmation": _is_destructive_step(step),
            }
        )

    return {"plan": plan_text, "steps": normalized_steps}


def _is_destructive_step(step: Dict) -> bool:
    """Check if a step contains potentially destructive operations."""
    from utils.validators import is_destructive

    if step.get("command") == "terminal.run":
        command = step.get("args", {}).get("command", "")
        return is_destructive(command)

    # Check for file operations that might be destructive
    if step.get("command") in ["files.write", "files.delete"]:
        return True

    return False
