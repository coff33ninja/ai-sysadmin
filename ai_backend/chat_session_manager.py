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
        
        # User preferences (could be expanded)
        self.preferred_backend = "gemini"
        self.auto_execute = False  # If true, execute plans without confirmation
        self.dry_run_first = False  # If true, always do dry runs first
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to the conversation history"""
        message = {
            "id": str(uuid.uuid4()),
            "role": role,  # 'user' or 'assistant' 
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.last_activity = datetime.now()
        
        # Keep conversation manageable (last 50 messages)
        if len(self.messages) > 50:
            self.messages = self.messages[-50:]
    
    def set_last_plan(self, plan_id: str, plan_summary: str, suggest_execution: bool = False):
        """Set the last created plan for easy reference"""
        self.last_plan_id = plan_id
        self.last_plan_summary = plan_summary
        self.awaiting_confirmation = suggest_execution
        self.last_activity = datetime.now()
    
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
            role = msg['role'].title()
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            summary += f"{role}: {content}\n"
        
        if self.awaiting_confirmation and self.last_plan_summary:
            summary += f"\n🔄 Awaiting confirmation for: {self.last_plan_summary}"
        
        if self.pending_execution_intent:
            intent = self.pending_execution_intent
            summary += f"\n⚡ Pending execution: {intent.get('action', 'unknown')}"
        
        return summary
    
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
            "preferred_backend": self.preferred_backend,
            "auto_execute": self.auto_execute,
            "dry_run_first": self.dry_run_first
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatSession':
        """Deserialize session from dictionary"""
        session = cls(data["session_id"])
        session.created_at = datetime.fromisoformat(data["created_at"])
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.messages = data.get("messages", [])
        session.last_plan_id = data.get("last_plan_id")
        session.last_plan_summary = data.get("last_plan_summary")
        session.awaiting_confirmation = data.get("awaiting_confirmation", False)
        session.pending_execution_intent = data.get("pending_execution_intent")
        session.preferred_backend = data.get("preferred_backend", "gemini")
        session.auto_execute = data.get("auto_execute", False)
        session.dry_run_first = data.get("dry_run_first", False)
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
            "sessions": {sid: session.to_dict() for sid, session in self.sessions.items()},
            "default_session_id": self.default_session_id
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_sessions(self, filepath: str):
        """Load sessions from file"""
        try:
            with open(filepath, 'r') as f:
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
    
    def process_user_message(self, message: str, session_id: str = None, backend: str = "gemini") -> Dict[str, Any]:
        """Process user message and return appropriate response"""
        session = self.session_manager.get_or_create_session(session_id)
        
        # Add user message to session
        session.add_message("user", message)
        
        # Import here to avoid circular imports
        from ai_backend.gemini_client import detect_execution_intent, query_gemini
        from ai_backend.planner import get_plan
        
        # Detect user intent
        intent = detect_execution_intent(message, session)
        
        response_data = {
            "session_id": session.session_id,
            "message_type": "response",
            "timestamp": datetime.now().isoformat()
        }
        
        if intent["action"] == "execute_last_plan":
            # User wants to execute the last plan
            if not session.last_plan_id:
                response = "I don't have a recent plan to execute. Could you tell me what you'd like me to do?"
                session.add_message("assistant", response)
                response_data.update({
                    "response": response,
                    "needs_plan": True
                })
            else:
                response = f"I'll execute the plan: {session.last_plan_summary}"
                session.add_message("assistant", response)
                session.set_execution_intent(intent)
                response_data.update({
                    "response": response,
                    "execute_plan": True,
                    "plan_id": session.last_plan_id,
                    "dry_run": intent.get("dry_run", False)
                })
        
        elif intent["action"] == "execute_steps":
            # User wants to execute specific steps
            if not session.last_plan_id:
                response = "I don't have a recent plan to execute steps from. Could you create a new plan first?"
                session.add_message("assistant", response)
                response_data.update({
                    "response": response,
                    "needs_plan": True
                })
            else:
                steps = intent.get("steps", [])
                response = f"I'll execute steps {steps} from the plan: {session.last_plan_summary}"
                session.add_message("assistant", response)
                session.set_execution_intent(intent)
                response_data.update({
                    "response": response,
                    "execute_plan": True,
                    "plan_id": session.last_plan_id,
                    "steps": steps,
                    "dry_run": intent.get("dry_run", False)
                })
        
        else:
            # Create or modify plan
            try:
                # Use the enhanced gemini client with session context
                from ai_backend.gemini_client import ConversationContext
                
                # Convert session to context
                context = ConversationContext()
                context.history = [{"role": msg["role"], "content": msg["content"]} 
                                 for msg in session.get_recent_context()]
                context.last_plan_id = session.last_plan_id
                context.awaiting_confirmation = session.awaiting_confirmation
                context.last_plan_summary = session.last_plan_summary
                
                # Get plan from AI
                ai_response = query_gemini(message, context)
                
                # Handle execution intent returned by AI
                if ai_response.get("_execution_intent"):
                    session.set_execution_intent(ai_response["_execution_intent"])
                    response_data["execute_plan"] = True
                    response_data["plan_id"] = session.last_plan_id
                
                # Create the plan if steps were provided
                if ai_response["steps"]:
                    # This would normally call the plan creation endpoint
                    # For now, we'll simulate it
                    plan_data = {
                        "plan": ai_response["plan"],
                        "steps": ai_response["steps"],
                        "suggest_execution": ai_response.get("suggest_execution", False),
                        "safety_notes": ai_response.get("safety_notes", [])
                    }
                    
                    # In a real implementation, save the plan and get an ID
                    plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    session.set_last_plan(plan_id, ai_response["plan"], 
                                         ai_response.get("suggest_execution", False))
                    
                    response_data.update({
                        "response": ai_response["response"],
                        "plan_created": True,
                        "plan_id": plan_id,
                        "plan_data": plan_data,
                        "suggest_execution": ai_response.get("suggest_execution", False)
                    })
                else:
                    response_data.update({
                        "response": ai_response["response"],
                        "plan_created": False
                    })
                
                # Add AI response to session
                session.add_message("assistant", ai_response["response"])
                
            except Exception as e:
                error_response = f"I encountered an error: {str(e)}. Could you try rephrasing your request?"
                session.add_message("assistant", error_response)
                response_data.update({
                    "response": error_response,
                    "error": True
                })
        
        return response_data
    
    def handle_plan_execution_result(self, session_id: str, result: Dict):
        """Handle the result of plan execution and update session"""
        session = self.session_manager.get_or_create_session(session_id)
        
        if result.get("error"):
            response = f"Execution failed: {result['error']}"
        else:
            response = "Plan executed successfully!"
            if result.get("results"):
                # Add summary of results
                success_count = sum(1 for r in result["results"] if not r.get("error"))
                total_count = len(result["results"])
                response += f" ({success_count}/{total_count} steps completed)"
        
        session.add_message("assistant", response)
        session.clear_execution_state()
        
        return {
            "session_id": session.session_id,
            "response": response,
            "execution_complete": True
        }