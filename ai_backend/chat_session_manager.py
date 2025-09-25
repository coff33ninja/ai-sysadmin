"""Chat session management for maintaining conversation context and state."""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


class ChatSession:
    """Manages individual chat session state and context"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

        # Conversation state
        self.messages: List[Dict[str, Any]] = []
        self.last_plan_id: Optional[str] = None
        self.last_plan_summary: Optional[str] = None
        self.awaiting_confirmation = False
        self.pending_execution_intent: Optional[Dict] = None

        # Enhanced planner tracking
        self.plan_history: List[Dict] = []  # Track all plans created in session
        self.execution_history: List[Dict] = []  # Track all executions
        self.safety_warnings_acknowledged: List[str] = []  # Track acknowledged warnings

        # User preferences (could be expanded)
        self.preferred_backend = "gemini"
        self.auto_execute = False  # If true, execute plans without confirmation
        self.dry_run_first = False  # If true, always do dry runs first
        self.show_time_estimates = True  # Show execution time estimates
        self.show_prerequisites = True  # Show prerequisite checks
        self.show_safety_analysis = True  # Show safety analysis

    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to the conversation history"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,  # 'user' or 'assistant'
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.messages.append(message)
        self.last_activity = datetime.now()

        # Keep conversation manageable (last 50 messages)
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]

    def set_last_plan(
        self,
        plan_id: str,
        plan_summary: str,
        suggest_execution: bool = False,
        plan_data: Dict = None,
    ):
        """Set the last created plan for easy reference"""
        self.last_plan_id = plan_id
        self.last_plan_summary = plan_summary
        self.awaiting_confirmation = suggest_execution
        self.last_activity = datetime.now()

        # Track plan in history
        plan_record = {
            "id": plan_id,
            "summary": plan_summary,
            "created_at": datetime.now().isoformat(),
            "suggest_execution": suggest_execution,
            "data": plan_data or {},
        }
        self.plan_history.append(plan_record)

        # Keep only last 20 plans
        if len(self.plan_history) > 20:
            self.plan_history = self.plan_history[-20:]

    def set_execution_intent(self, intent: Dict):
        """Set pending execution intent from user input"""
        self.pending_execution_intent = intent
        self.last_activity = datetime.now()

    def clear_execution_state(self):
        """Clear execution state after handling"""
        self.awaiting_confirmation = False
        self.pending_execution_intent = None
        self.last_activity = datetime.now()

    def get_recent_context(self, num_messages: int = 6) -> List[Dict]:
        """Get recent conversation context for AI"""
        return self.messages[-num_messages:] if self.messages else []

    def get_context_summary(self) -> str:
        """Get a text summary of recent context"""
        if not self.messages:
            return "New conversation - no previous context."

        recent = self.get_recent_context(4)
        summary = "Recent conversation:\n"

        for msg in recent:
            role = msg["role"].title()
            content = (
                msg["content"][:100] + "..."
                if len(msg["content"]) > 100
                else msg["content"]
            )
            summary += f"{role}: {content}\n"

        if self.awaiting_confirmation and self.last_plan_summary:
            summary += f"\n🔄 Awaiting confirmation for: {self.last_plan_summary}"

        if self.pending_execution_intent:
            intent = self.pending_execution_intent
            summary += f"\n⚡ Pending execution: {intent.get('action', 'unknown')}"

        # Add plan history context
        if self.plan_history:
            recent_plans = len(
                [
                    p
                    for p in self.plan_history
                    if (
                        datetime.now() - datetime.fromisoformat(p["created_at"])
                    ).total_seconds()
                    < 3600
                ]
            )
            if recent_plans > 1:
                summary += f"\n📋 {recent_plans} plans created in the last hour"

        return summary

    def record_execution(self, plan_id: str, result: Dict):
        """Record execution result in history"""
        execution_record = {
            "plan_id": plan_id,
            "executed_at": datetime.now().isoformat(),
            "result": result,
            "success": not result.get("error", False),
        }
        self.execution_history.append(execution_record)

        # Keep only last 50 executions
        if len(self.execution_history) > 50:
            self.execution_history = self.execution_history[-50:]

    def acknowledge_safety_warning(self, warning: str):
        """Mark a safety warning as acknowledged by user"""
        if warning not in self.safety_warnings_acknowledged:
            self.safety_warnings_acknowledged.append(warning)

    def get_plan_by_id(self, plan_id: str) -> Optional[Dict]:
        """Get plan data by ID from history"""
        for plan in self.plan_history:
            if plan["id"] == plan_id:
                return plan
        return None

    def get_recent_plans(self, count: int = 5) -> List[Dict]:
        """Get recent plans from history"""
        return self.plan_history[-count:] if self.plan_history else []

    def has_recent_errors(self, hours: int = 1) -> bool:
        """Check if there have been recent execution errors"""
        cutoff = datetime.now() - datetime.timedelta(hours=hours)
        recent_executions = [
            ex
            for ex in self.execution_history
            if datetime.fromisoformat(ex["executed_at"]) > cutoff
        ]
        return any(not ex["success"] for ex in recent_executions)

    def get_user_preferences_summary(self) -> Dict:
        """Get summary of user preferences for AI context"""
        return {
            "preferred_backend": self.preferred_backend,
            "auto_execute": self.auto_execute,
            "dry_run_first": self.dry_run_first,
            "show_time_estimates": self.show_time_estimates,
            "show_prerequisites": self.show_prerequisites,
            "show_safety_analysis": self.show_safety_analysis,
            "has_recent_errors": self.has_recent_errors(),
            "total_plans_created": len(self.plan_history),
            "total_executions": len(self.execution_history),
        }

    def to_dict(self) -> Dict:
        """Serialize session to dictionary"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "messages": self.messages,
            "last_plan_id": self.last_plan_id,
            "last_plan_summary": self.last_plan_summary,
            "awaiting_confirmation": self.awaiting_confirmation,
            "pending_execution_intent": self.pending_execution_intent,
            "plan_history": self.plan_history,
            "execution_history": self.execution_history,
            "safety_warnings_acknowledged": self.safety_warnings_acknowledged,
            "preferred_backend": self.preferred_backend,
            "auto_execute": self.auto_execute,
            "dry_run_first": self.dry_run_first,
            "show_time_estimates": self.show_time_estimates,
            "show_prerequisites": self.show_prerequisites,
            "show_safety_analysis": self.show_safety_analysis,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChatSession":
        """Deserialize session from dictionary"""
        session = cls(data["session_id"])
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.messages = data.get("messages", [])
        session.last_plan_id = data.get("last_plan_id")
        session.last_plan_summary = data.get("last_plan_summary")
        session.awaiting_confirmation = data.get("awaiting_confirmation", False)
        session.pending_execution_intent = data.get("pending_execution_intent")
        session.plan_history = data.get("plan_history", [])
        session.execution_history = data.get("execution_history", [])
        session.safety_warnings_acknowledged = data.get(
            "safety_warnings_acknowledged", []
        )
        session.preferred_backend = data.get("preferred_backend", "gemini")
        session.auto_execute = data.get("auto_execute", False)
        session.dry_run_first = data.get("dry_run_first", False)
        session.show_time_estimates = data.get("show_time_estimates", True)
        session.show_prerequisites = data.get("show_prerequisites", True)
        session.show_safety_analysis = data.get("show_safety_analysis", True)
        return session


class SessionManager:
    """Manages multiple chat sessions"""

    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.default_session_id: Optional[str] = None

    def get_or_create_session(self, session_id: str = None) -> ChatSession:
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        # Create new session
        new_session = ChatSession(session_id)
        self.sessions[new_session.session_id] = new_session

        # Set as default if it's the first session
        if not self.default_session_id:
            self.default_session_id = new_session.session_id

        return new_session

    def get_default_session(self) -> ChatSession:
        """Get the default session"""
        if self.default_session_id and self.default_session_id in self.sessions:
            return self.sessions[self.default_session_id]
        return self.get_or_create_session()

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Remove sessions older than max_age_hours"""
        now = datetime.now()
        to_remove = []

        for session_id, session in self.sessions.items():
            age_hours = (now - session.last_activity).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_remove.append(session_id)

        for session_id in to_remove:
            del self.sessions[session_id]
            if self.default_session_id == session_id:
                self.default_session_id = None

    def save_sessions(self, filepath: str):
        """Save all sessions to file"""
        data = {
            "sessions": {
                sid: session.to_dict() for sid, session in self.sessions.items()
            },
            "default_session_id": self.default_session_id,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_sessions(self, filepath: str):
        """Load sessions from file"""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            self.sessions = {}
            for sid, session_data in data.get("sessions", {}).items():
                self.sessions[sid] = ChatSession.from_dict(session_data)

            self.default_session_id = data.get("default_session_id")
        except (FileNotFoundError, json.JSONDecodeError):
            # File doesn't exist or is corrupted, start fresh
            self.sessions = {}
            self.default_session_id = None


class ConversationHandler:
    """Handles conversation flow and integrates with AI backends"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    def process_user_message(
        self, message: str, session_id: str = None, backend: str = "gemini"
    ) -> Dict[str, Any]:
        """Process user message and return appropriate response with enhanced planner integration"""
        session = self.session_manager.get_or_create_session(session_id)

        # Add user message to session
        session.add_message("user", message)

        # Import here to avoid circular imports
        from ai_backend.gemini_client import detect_execution_intent
        from ai_backend.planner import create_plan_with_context, get_plan_summary

        # Detect user intent
        intent = detect_execution_intent(message, session)

        response_data = {
            "session_id": session.session_id,
            "message_type": "response",
            "timestamp": datetime.now().isoformat(),
        }

        if intent["action"] == "execute_last_plan":
            # User wants to execute the last plan
            if not session.last_plan_id:
                response = "I don't have a recent plan to execute. Could you tell me what you'd like me to do?"
                session.add_message("assistant", response)
                response_data.update({"response": response, "needs_plan": True})
            else:
                response = f"I'll execute the plan: {session.last_plan_summary}"
                session.add_message("assistant", response)
                session.set_execution_intent(intent)
                response_data.update(
                    {
                        "response": response,
                        "execute_plan": True,
                        "plan_id": session.last_plan_id,
                        "dry_run": intent.get("dry_run", False),
                    }
                )

        elif intent["action"] == "execute_steps":
            # User wants to execute specific steps
            if not session.last_plan_id:
                response = "I don't have a recent plan to execute steps from. Could you create a new plan first?"
                session.add_message("assistant", response)
                response_data.update({"response": response, "needs_plan": True})
            else:
                steps = intent.get("steps", [])
                response = f"I'll execute steps {steps} from the plan: {session.last_plan_summary}"
                session.add_message("assistant", response)
                session.set_execution_intent(intent)
                response_data.update(
                    {
                        "response": response,
                        "execute_plan": True,
                        "plan_id": session.last_plan_id,
                        "steps": steps,
                        "dry_run": intent.get("dry_run", False),
                    }
                )

        else:
            # Create or modify plan using enhanced planner
            try:
                # Use the enhanced planner with full session context
                enhanced_plan = create_plan_with_context(
                    message, session_context=session, backend=backend
                )

                # Handle execution intent returned by planner
                if enhanced_plan.get("execution_intent"):
                    session.set_execution_intent(enhanced_plan["execution_intent"])
                    response_data["execute_plan"] = True
                    response_data["plan_id"] = session.last_plan_id

                # Create the plan if steps were provided
                if enhanced_plan["steps"]:
                    # Generate plan ID and summary
                    plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    plan_summary = get_plan_summary(enhanced_plan)

                    # Set plan in session with full data
                    session.set_last_plan(
                        plan_id,
                        plan_summary,
                        enhanced_plan.get("suggest_execution", False),
                        enhanced_plan,
                    )

                    # Prepare enhanced response data
                    response_data.update(
                        {
                            "response": enhanced_plan["response"],
                            "plan_created": True,
                            "plan_id": plan_id,
                            "plan_data": {
                                "plan": enhanced_plan["plan"],
                                "steps": enhanced_plan["steps"],
                                "suggest_execution": enhanced_plan.get(
                                    "suggest_execution", False
                                ),
                                "safety_notes": enhanced_plan.get("safety_notes", []),
                                "estimated_duration": enhanced_plan.get(
                                    "estimated_duration"
                                ),
                                "prerequisites": enhanced_plan.get("prerequisites", []),
                                "contextual_suggestions": enhanced_plan.get(
                                    "contextual_suggestions", []
                                ),
                                "rollback_suggestions": enhanced_plan.get(
                                    "rollback_suggestions", []
                                ),
                            },
                            "suggest_execution": enhanced_plan.get(
                                "suggest_execution", False
                            ),
                            "enhanced_features": {
                                "has_safety_analysis": bool(
                                    enhanced_plan.get("safety_notes")
                                ),
                                "has_time_estimate": bool(
                                    enhanced_plan.get("estimated_duration")
                                ),
                                "has_prerequisites": bool(
                                    enhanced_plan.get("prerequisites")
                                ),
                                "has_contextual_suggestions": bool(
                                    enhanced_plan.get("contextual_suggestions")
                                ),
                                "has_rollback_plan": bool(
                                    enhanced_plan.get("rollback_suggestions")
                                ),
                            },
                        }
                    )
                else:
                    response_data.update(
                        {"response": enhanced_plan["response"], "plan_created": False}
                    )

                # Add AI response to session with metadata
                session.add_message(
                    "assistant",
                    enhanced_plan["response"],
                    {
                        "plan_created": bool(enhanced_plan["steps"]),
                        "plan_id": plan_id if enhanced_plan["steps"] else None,
                        "safety_concerns": len(enhanced_plan.get("safety_notes", [])),
                        "step_count": len(enhanced_plan["steps"]),
                    },
                )

            except Exception as e:
                error_response = f"I encountered an error: {str(e)}. Could you try rephrasing your request?"
                session.add_message("assistant", error_response, {"error": True})
                response_data.update({"response": error_response, "error": True})

        return response_data

    def handle_plan_execution_result(self, session_id: str, result: Dict):
        """Handle the result of plan execution and update session with enhanced tracking"""
        session = self.session_manager.get_or_create_session(session_id)

        # Record execution in history
        if session.last_plan_id:
            session.record_execution(session.last_plan_id, result)

        if result.get("error"):
            response = f"Execution failed: {result['error']}"
            # Add contextual help for common errors
            if "permission denied" in result["error"].lower():
                response += "\n💡 Tip: You might need to run with sudo or check file permissions."
            elif "command not found" in result["error"].lower():
                response += (
                    "\n💡 Tip: The command might not be installed or not in your PATH."
                )
        else:
            response = "Plan executed successfully!"
            if result.get("results"):
                # Add detailed summary of results
                success_count = sum(1 for r in result["results"] if not r.get("error"))
                total_count = len(result["results"])
                response += f" ({success_count}/{total_count} steps completed)"

                # Add execution time if available
                if result.get("execution_time"):
                    response += f" in {result['execution_time']}"

        session.add_message(
            "assistant",
            response,
            {
                "execution_result": True,
                "success": not result.get("error", False),
                "plan_id": session.last_plan_id,
            },
        )
        session.clear_execution_state()

        return {
            "session_id": session.session_id,
            "response": response,
            "execution_complete": True,
            "success": not result.get("error", False),
            "execution_summary": {
                "total_steps": len(result.get("results", [])),
                "successful_steps": sum(
                    1 for r in result.get("results", []) if not r.get("error")
                ),
                "execution_time": result.get("execution_time"),
                "plan_id": session.last_plan_id,
            },
        }
