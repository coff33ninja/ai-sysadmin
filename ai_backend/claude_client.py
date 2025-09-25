"""Claude client adapter with real API implementation."""

import json
import requests
from typing import Dict, Optional
from config import CLAUDE_API_KEY, CLAUDE_MODEL


def query_claude(prompt: str, context: Optional[Dict] = None) -> Dict:
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
        headers = {
            "Content-Type": "application/json",
            "x-api-key": CLAUDE_API_KEY,
            "anthropic-version": "2023-06-01"
        }

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

        if context:
            system_prompt += "\n\nHere is some relevant context from previous conversations:\n"
            system_prompt += json.dumps(context)


        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 1000,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "system": system_prompt
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

            try:
                return json.loads(content)
            except json.JSONDecodeError:
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