"""Claude client adapter with real API implementation."""

import json
import requests
from typing import Dict, Optional
from config import CLAUDE_API_KEY, CLAUDE_MODEL


def query_claude(prompt: str, context: Optional[Dict] = None, session_context=None) -> Dict:
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
    ],
    "suggest_execution": true,
    "response": "I've created a plan to [describe what it does]. Would you like me to execute it?",
    "safety_notes": ["Warning about destructive operations if any"]
}

Available commands:
- terminal.run: Execute shell commands
- files.list: List files in directory
- files.read: Read file contents
- files.write: Write to file

Set suggest_execution to true if the task seems ready to execute immediately.
Include safety warnings for any potentially destructive operations.
Only respond with valid JSON, no additional text."""

        # Add conversation context if available
        if session_context:
            recent_messages = getattr(session_context, 'messages', [])[-5:]
            if recent_messages:
                system_prompt += "\n\nRecent conversation context:\n"
                for msg in recent_messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')[:100]
                    system_prompt += f"{role}: {content}...\n"
            
            if getattr(session_context, 'awaiting_confirmation', False):
                system_prompt += f"\nLast plan: {getattr(session_context, 'last_plan_summary', 'Unknown')}"
                system_prompt += "\nUser may be confirming execution or requesting modifications."
        
        if context:
            system_prompt += "\n\nAdditional context:\n"
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