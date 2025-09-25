"""Gemini client adapter (mocked implementation).

This module exposes two helpers:
- query_gemini(prompt) -> raw backend response (dict)
- generate_plan(prompt, context) -> normalized plan dict with steps

If GEMINI_API_KEY is present in config, a real API call could be implemented here.
"""
from typing import Dict, Optional
from config import GEMINI_API_KEY
from config import GEMINI_API_URL
from config import GEMINI_MODEL

try:
    import requests
except Exception:
    requests = None
try:
    import genai
except Exception:
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

    # Prefer the official genai client if available (googleapis/python-genai)
    if genai:
        try:
            # genai usage: genai.configure(api_key=GEMINI_API_KEY) and then genai.Client().generate_text
            try:
                genai.configure(api_key=GEMINI_API_KEY)
            except Exception:
                # Some versions configure differently or may have been preconfigured
                pass
            client = getattr(genai, "Client", None)
            if client:
                c = client()
                # simple generate call; adapt different SDK shapes gracefully
                if hasattr(c, "generate"):
                    out = c.generate(prompt=prompt)
                    text = getattr(out, "text", None) or str(out)
                elif hasattr(c, "generate_text"):
                    out = c.generate_text(prompt=prompt)
                    text = getattr(out, "text", None) or str(out)
                else:
                    out = c
                    text = str(out)
                # Attempt to extract suggested steps if present in the response
                raw = getattr(out, "raw", None) or (out if isinstance(out, dict) else {})
                suggested = raw.get("suggested_steps") if isinstance(raw, dict) else None
                return {"text": text, "raw": {"suggested_steps": suggested or []}}
        except Exception:
            # fallthrough to HTTP approach on error
            pass

    # If a URL is provided and requests is available, attempt a simple POST call.
    if GEMINI_API_URL and requests:
        try:
            headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
            payload = {"prompt": prompt, **(kwargs or {})}
            resp = requests.post(GEMINI_API_URL, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Expecting a simple structure; fall back to text/raw fields if present.
                return {
                    "text": data.get("text") or data.get("message") or str(data),
                    "raw": data.get("raw", {"suggested_steps": data.get("suggested_steps", [])}),
                }
            else:
                return {"text": f"[gemini http error {resp.status_code}]", "raw": {"suggested_steps": []}}
        except Exception as e:
            return {"text": f"[gemini http exception] {e}", "raw": {"suggested_steps": []}}

    # If no custom URL provided but a GEMINI_API_KEY exists, attempt Google Generative API format
    if GEMINI_API_KEY and requests and not GEMINI_API_URL:
        try:
            # Google GenAI REST endpoint
            url = f"https://generativelanguage.googleapis.com/v1/{GEMINI_MODEL}:generateText"
            headers = {"Authorization": f"Bearer {GEMINI_API_KEY}", "Content-Type": "application/json"}
            body = {"prompt": {"text": prompt}, "temperature": 0.2}
            resp = requests.post(url, json=body, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # Google response may have 'candidates' with 'content'
                text = ""
                if isinstance(data, dict):
                    candidates = data.get("candidates") or []
                    if candidates:
                        text = "\n".join(c.get("content", "") for c in candidates)
                    else:
                        text = data.get("output") or str(data)
                return {"text": text, "raw": {"suggested_steps": []}}
            else:
                return {"text": f"[gemini google http error {resp.status_code}]", "raw": {"suggested_steps": []}}
        except Exception as e:
            return {"text": f"[gemini google exception] {e}", "raw": {"suggested_steps": []}}

    return {"text": "[gemini stub] key provided but network call not implemented", "raw": {"suggested_steps": []}}


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

