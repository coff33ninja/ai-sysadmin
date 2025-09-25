"""Gemini client adapter.

This module exposes two helpers:
- query_gemini(prompt) -> raw backend response (dict)
- generate_plan(prompt, context) -> normalized plan dict with steps

If GEMINI_API_KEY is present in config, a real API call will be made.
"""
from typing import Dict, Optional
import json
from config import GEMINI_API_KEY, GEMINI_MODEL

try:
    import google.generativeai as genai
except ImportError:
    genai = None

def query_gemini(prompt: str, **kwargs) -> Dict:
    """Query Gemini-like backend. Currently returns a mocked response unless GEMINI_API_KEY
    is present and an implementation is provided.
    """
    if not GEMINI_API_KEY:
        return {
            "text": f"[mocked gemini response] plan for: {prompt}",
            "raw": {
                "suggested_steps": [
                    {"command": "files.list", "args": {"path": "."}},
                    {"command": "terminal.run", "args": {"command": "echo 'gemini'"}},
                ]
            },
        }

    if not genai:
        return {"text": "[gemini stub] google-genai library not found. Please install it.", "raw": {"suggested_steps": []}}

    genai.configure(api_key=GEMINI_API_KEY)

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        
        # The response might contain a JSON string with the plan.
        # It's better to parse it here.
        try:
            # It's common for the model to return a markdown code block
            text_response = response.text.replace("```json", "").replace("```", "").strip()
            plan = json.loads(text_response)
            return {
                "text": plan.get("plan", ""),
                "raw": {"suggested_steps": plan.get("steps", [])},
            }
        except (json.JSONDecodeError, AttributeError):
             # If the response is not a valid JSON, return the raw text.
            return {
                "text": response.text,
                "raw": {"suggested_steps": []},
            }

    except Exception as e:
        return {"text": f"[gemini api error] {e}", "raw": {"suggested_steps": []}}


def generate_plan(prompt: str, context: Optional[Dict] = None) -> Dict:
    """Normalize backend output into plan dict: {plan: str, steps: [{id,command,args,needs_confirmation}]}"""
    resp = query_gemini(prompt, context=context)
    raw_steps = resp.get("raw", {}).get("suggested_steps", [])
    steps = []
    for i, s in enumerate(raw_steps):
        steps.append({
            "id": i,
            "command": s.get("command"),
            "args": s.get("args", {}),
            "needs_confirmation": False,
        })
    return {"plan": resp.get("text", ""), "steps": steps}