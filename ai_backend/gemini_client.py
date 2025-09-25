"""Enhanced Gemini client adapter with structured prompts and conversation handling.

This module provides intelligent prompting and response parsing for natural
system administration conversations.
"""

from typing import Dict, Optional, List
import json
import re
from config import GEMINI_API_KEY, GEMINI_MODEL

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class ConversationContext:
    """Manages conversation state and context"""

    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.last_plan_id: Optional[str] = None
        self.awaiting_confirmation: bool = False
        self.last_plan_summary: Optional[str] = None

    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.history.append({"role": role, "content": content})
        # Keep only last 10 messages to avoid token limits
        if len(self.history) > 10:
            self.history = self.history[-10:]

    def set_last_plan(self, plan_id: str, summary: str):
        """Set the last created plan for reference"""
        self.last_plan_id = plan_id
        self.last_plan_summary = summary
        self.awaiting_confirmation = True

    def clear_confirmation(self):
        """Clear the awaiting confirmation state"""
        self.awaiting_confirmation = False

    def get_context_summary(self) -> str:
        """Get a summary of recent conversation for AI context"""
        if not self.history:
            return "No previous conversation."

        recent = self.history[-3:]  # Last 3 messages
        context = "Recent conversation:\n"
        for msg in recent:
            context += f"{msg['role']}: {msg['content'][:100]}...\n"

        if self.awaiting_confirmation and self.last_plan_summary:
            context += f"\nLast plan created: {self.last_plan_summary}"
            context += "\nUser may be confirming execution."

        return context


def detect_execution_intent(
    user_input: str, context: ConversationContext
) -> Dict[str, any]:
    """Detect if user wants to execute, modify, or create plans"""
    text = user_input.lower().strip()

    # Definitive execution phrases
    execute_phrases = [
        "yes",
        "y",
        "do it",
        "run it",
        "execute",
        "go ahead",
        "proceed",
        "make it happen",
        "let's go",
        "run the plan",
        "execute it",
        "go for it",
        "start",
        "begin",
        "launch",
    ]

    # Step-specific execution
    step_pattern = r"(?:run|execute|do)\s+step\s+(\d+)"
    step_match = re.search(step_pattern, text)

    # Range execution
    range_pattern = r"(?:run|execute|do)\s+steps?\s+(\d+)(?:\s*[-to]\s*(\d+))?"
    range_match = re.search(range_pattern, text)

    # Dry run detection
    dry_run_phrases = [
        "dry run",
        "test run",
        "show me first",
        "what will happen",
        "preview",
        "simulate",
        "test it",
    ]

    if (
        any(phrase in text for phrase in execute_phrases)
        and context.awaiting_confirmation
    ):
        return {"action": "execute_last_plan", "dry_run": False}

    if step_match:
        step_num = int(step_match.group(1))
        return {"action": "execute_steps", "steps": [step_num], "dry_run": False}

    if range_match:
        start_step = int(range_match.group(1))
        end_step = int(range_match.group(2)) if range_match.group(2) else start_step
        steps = list(range(start_step, end_step + 1))
        return {"action": "execute_steps", "steps": steps, "dry_run": False}

    if any(phrase in text for phrase in dry_run_phrases):
        return {"action": "execute_last_plan", "dry_run": True}

    # Check for plan modification requests
    modify_phrases = ["change", "modify", "update", "edit", "different", "instead"]
    if (
        any(phrase in text for phrase in modify_phrases)
        and context.awaiting_confirmation
    ):
        return {"action": "modify_plan", "modification": user_input}

    # Default to creating new plan
    return {"action": "create_plan", "query": user_input}


def create_system_prompt(
    user_input: str, context: ConversationContext, intent: Dict
) -> str:
    """Create a structured prompt for Gemini based on user intent and context"""

    base_instructions = """You are an expert AI system administrator assistant. Your responses must be helpful, accurate, and follow the exact format specified.

CRITICAL: You must ALWAYS return valid JSON in the exact format specified below. Never include markdown code blocks, explanations outside the JSON, or any other text.

Your role:
- Help users manage their computer systems through terminal commands and file operations
- Create clear, executable plans for system administration tasks
- Provide helpful explanations while being concise
- Always prioritize system safety and ask for confirmation on destructive operations"""

    if intent["action"] == "create_plan":
        prompt = f"""{base_instructions}

User request: "{user_input}"

Context: {context.get_context_summary()}

Create a system administration plan and return ONLY this JSON format:
{{
  "plan": "Clear descriptive name (2-5 words)",
  "steps": [
    {{"command": "terminal.run", "args": {{"command": "specific terminal command"}}}},
    {{"command": "files.list", "args": {{"path": "/path/to/check"}}}},
    {{"command": "files.read", "args": {{"path": "/path/to/file"}}}}
  ],
  "suggest_execution": true,
  "response": "I've created a plan to [describe what it does]. This will [explain impact]. Would you like me to execute it?",
  "safety_notes": ["Warning about destructive operations if any"]
}}

Available commands:
- terminal.run: Execute shell commands
- files.list: List directory contents  
- files.read: Read file contents
- files.write: Write to files

Set suggest_execution to true if the task seems ready to execute immediately.
Make the plan name descriptive but concise.
Include safety warnings for any potentially destructive operations."""

    elif intent["action"] == "modify_plan":
        prompt = f"""{base_instructions}

User wants to modify the last plan: "{user_input}"
Last plan: {context.last_plan_summary}

Context: {context.get_context_summary()}

Create a modified plan and return ONLY this JSON format:
{{
  "plan": "Modified plan name",
  "steps": [
    {{"command": "terminal.run", "args": {{"command": "modified command"}}}}
  ],
  "suggest_execution": true,
  "response": "I've updated the plan based on your request. [explain changes]. Should I execute this instead?",
  "safety_notes": ["Any safety warnings"]
}}"""

    else:  # execution intent - shouldn't reach Gemini, but handle gracefully
        prompt = f"""{base_instructions}

The user wants to execute a previously created plan. Return:
{{
  "plan": "Execution Confirmation",
  "steps": [],
  "suggest_execution": false,
  "response": "I understand you want to execute the plan. Let me proceed with that.",
  "safety_notes": []
}}"""

    return prompt


def parse_gemini_response(raw_response: str) -> Dict:
    """Parse Gemini's response and ensure it matches expected format"""
    try:
        # Clean up the response - remove markdown code blocks if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Parse JSON
        parsed = json.loads(cleaned)

        # Validate required fields and set defaults
        result = {
            "plan": parsed.get("plan", "Unnamed Plan"),
            "steps": parsed.get("steps", []),
            "suggest_execution": parsed.get("suggest_execution", False),
            "response": parsed.get("response", "Plan created successfully."),
            "safety_notes": parsed.get("safety_notes", []),
        }

        # Validate steps format
        validated_steps = []
        for i, step in enumerate(result["steps"]):
            if isinstance(step, dict) and "command" in step:
                validated_steps.append(
                    {
                        "command": step["command"],
                        "args": step.get("args", {}),
                        "id": step.get("id", i),
                    }
                )
            elif isinstance(step, str):
                # Handle simple string commands
                validated_steps.append(
                    {"command": "terminal.run", "args": {"command": step}, "id": i}
                )

        result["steps"] = validated_steps
        return result

    except json.JSONDecodeError as e:
        print(f"JSON decoding failed: {e}")
        # If JSON parsing fails, try to extract plan info from natural language
        return {
            "plan": "Parse Error Recovery",
            "steps": [],
            "suggest_execution": False,
            "response": f"I had trouble formatting my response properly. Here's what I understood: {raw_response[:200]}...",
            "safety_notes": [
                "Response parsing failed - please try rephrasing your request"
            ],
        }
    except Exception as e:
        return {
            "plan": "Error",
            "steps": [],
            "suggest_execution": False,
            "response": f"An error occurred while processing the request: {str(e)}",
            "safety_notes": ["System error occurred"],
        }


def query_gemini(
    prompt: str, context: Optional[ConversationContext] = None, **kwargs
) -> Dict:
    """Enhanced Gemini query with conversation context and structured prompting"""

    if not context:
        context = ConversationContext()

    # Detect user intent
    intent = detect_execution_intent(prompt, context)

    # Handle execution intents without calling Gemini
    if intent["action"] in ["execute_last_plan", "execute_steps"]:
        return {
            "plan": "Execute Plan",
            "steps": [],
            "suggest_execution": False,
            "response": "Ready to execute the plan.",
            "safety_notes": [],
            "_execution_intent": intent,  # Pass intent to caller
        }

    # For plan creation/modification, use Gemini
    if not GEMINI_API_KEY:
        # Enhanced mock response for testing
        mock_steps = []
        if "install" in prompt.lower():
            mock_steps = [
                {"command": "terminal.run", "args": {"command": "sudo apt update"}},
                {
                    "command": "terminal.run",
                    "args": {
                        "command": f"sudo apt install -y {prompt.split()[-1] if prompt.split() else 'package'}"
                    },
                },
            ]
        elif "list" in prompt.lower() or "find" in prompt.lower():
            mock_steps = [
                {"command": "files.list", "args": {"path": ".", "recursive": True}}
            ]
        else:
            mock_steps = [
                {
                    "command": "terminal.run",
                    "args": {"command": f"echo 'Executing: {prompt}'"},
                }
            ]

        return {
            "plan": f"Mock Plan for: {prompt[:20]}...",
            "steps": mock_steps,
            "suggest_execution": True,
            "response": f"I've created a mock plan for '{prompt}'. This is a test response since no API key is configured. Would you like me to execute it?",
            "safety_notes": ["This is a mock response for testing"],
        }

    if not genai:
        return {
            "plan": "Library Missing",
            "steps": [],
            "suggest_execution": False,
            "response": "Google GenerativeAI library not found. Please install it with: pip install google-generativeai",
            "safety_notes": ["Missing dependencies"],
        }

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        # Create structured prompt
        structured_prompt = create_system_prompt(prompt, context, intent)

        # Add conversation context if available
        if context.history:
            structured_prompt += (
                f"\n\nRecent conversation context:\n{context.get_context_summary()}"
            )

        response = model.generate_content(structured_prompt)

        # Parse and validate the response
        parsed_response = parse_gemini_response(response.text)

        # Add user message to context (only if context is ConversationContext)
        if hasattr(context, 'add_message'):
            context.add_message("user", prompt)
            context.add_message("assistant", parsed_response["response"])

        return parsed_response

    except Exception as e:
        # Add error message to context (only if context is ConversationContext)
        if hasattr(context, 'add_message'):
            context.add_message("user", prompt)
            context.add_message("assistant", f"Error: {str(e)}")

        return {
            "plan": "API Error",
            "steps": [],
            "suggest_execution": False,
            "response": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            "safety_notes": ["API call failed"],
        }


def generate_plan(prompt: str, context: Optional[ConversationContext] = None) -> Dict:
    """Generate a normalized plan from user input with conversation context"""
    result = query_gemini(prompt, context)

    # Ensure the result has the expected structure for the rest of the system
    return {
        "plan": result["plan"],
        "steps": result["steps"],
        "suggest_execution": result.get("suggest_execution", False),
        "response": result.get("response", ""),
        "safety_notes": result.get("safety_notes", []),
        "_execution_intent": result.get("_execution_intent"),
    }
