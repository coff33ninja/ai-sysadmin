"""Enhanced planner with conversation context and intelligent plan management."""

import json
from typing import Dict, Any, Optional, List
from utils.validators import is_destructive
from . import gemini_client, claude_client


def get_plan(text: str, backend: str = "gemini", context: Dict = None, session_context=None) -> Dict:
    """Get a plan from AI backend with full conversation context"""
    
    if backend == "claude":
        raw = claude_client.query_claude(text, context=context, session_context=session_context)
    else:
        # Use the enhanced Gemini client with conversation context
        if hasattr(gemini_client, 'ConversationContext') and session_context:
            # Convert session context to ConversationContext
            conv_context = gemini_client.ConversationContext()
            conv_context.history = getattr(session_context, 'messages', [])
            conv_context.last_plan_id = getattr(session_context, 'last_plan_id', None)
            conv_context.awaiting_confirmation = getattr(session_context, 'awaiting_confirmation', False)
            conv_context.last_plan_summary = getattr(session_context, 'last_plan_summary', None)
            
            raw = gemini_client.query_gemini(text, context=conv_context)
        else:
            raw = gemini_client.query_gemini(text, context=context)
    
    return normalize_with_context(raw, text, session_context)


def normalize_with_context(ai_output: Dict[str, Any], original_request: str, session_context=None) -> Dict[str, Any]:
    """Enhanced normalization with conversation context and intelligent defaults"""
    
    # Handle execution intents that don't need normalization
    if ai_output.get("_execution_intent"):
        return {
            "plan": ai_output.get("plan", "Execute Plan"),
            "steps": [],
            "execution_intent": ai_output["_execution_intent"],
            "response": ai_output.get("response", "Ready to execute."),
            "suggest_execution": False,
            "safety_notes": ai_output.get("safety_notes", [])
        }
    
    # Extract plan information with context-aware defaults
    plan_name = (
        ai_output.get("plan") or 
        ai_output.get("description") or 
        _generate_plan_name(original_request, session_context)
    )
    
    # Get steps and normalize them
    raw_steps = ai_output.get("steps") or ai_output.get("commands") or []
    normalized_steps = _normalize_steps(raw_steps)
    
    # Determine if execution should be suggested
    suggest_execution = ai_output.get("suggest_execution", _should_suggest_execution(normalized_steps, session_context))
    
    # Extract safety information
    safety_notes = ai_output.get("safety_notes", [])
    if not safety_notes:
        safety_notes = _analyze_safety_concerns(normalized_steps)
    
    # Build the normalized response
    result = {
        "plan": plan_name,
        "steps": normalized_steps,
        "suggest_execution": suggest_execution,
        "response": ai_output.get("response", f"I've created a plan to {plan_name.lower()}. Would you like me to execute it?"),
        "safety_notes": safety_notes
    }
    
    # Add context-specific metadata
    if session_context:
        result["context_metadata"] = {
            "has_previous_plan": bool(getattr(session_context, 'last_plan_id', None)),
            "awaiting_confirmation": getattr(session_context, 'awaiting_confirmation', False),
            "conversation_length": len(getattr(session_context, 'messages', []))
        }
    
    return result


def _generate_plan_name(request: str, session_context=None) -> str:
    """Generate an intelligent plan name based on request and context"""
    # Extract key action words
    action_words = {
        'install': 'Install Package',
        'update': 'Update System', 
        'upgrade': 'Upgrade Package',
        'remove': 'Remove Package',
        'delete': 'Delete Files',
        'create': 'Create Files',
        'backup': 'Backup Data',
        'restore': 'Restore Data',
        'configure': 'Configure System',
        'setup': 'Setup Service',
        'start': 'Start Service',
        'stop': 'Stop Service',
        'restart': 'Restart Service',
        'check': 'System Check',
        'monitor': 'Monitor System',
        'fix': 'Fix Issue',
        'troubleshoot': 'Troubleshoot Problem'
    }
    
    request_lower = request.lower()
    for keyword, plan_name in action_words.items():
        if keyword in request_lower:
            return plan_name
    
    # If no specific action found, create generic name
    words = request.split()[:3]  # First 3 words
    return f"Execute: {' '.join(words).title()}"


def _normalize_steps(raw_steps: List) -> List[Dict]:
    """Normalize steps to consistent format with enhanced validation"""
    normalized = []
    
    for i, step in enumerate(raw_steps):
        if isinstance(step, str):
            # Simple string command
            normalized_step = {
                "id": i,
                "command": "terminal.run",
                "args": {"command": step},
                "needs_confirmation": is_destructive(step),
                "description": f"Run: {step[:50]}..." if len(step) > 50 else f"Run: {step}"
            }
        elif isinstance(step, dict):
            # Dictionary step - normalize fields
            cmd_name = step.get("command") or step.get("method") or step.get("tool") or "terminal.run"
            args = step.get("args") or step.get("params") or {}
            
            # Enhanced destructive detection
            needs_confirmation = step.get("needs_confirmation")
            if needs_confirmation is None:
                needs_confirmation = _is_step_destructive(cmd_name, args)
            
            normalized_step = {
                "id": step.get("id", i),
                "command": cmd_name,
                "args": args,
                "needs_confirmation": needs_confirmation,
                "description": step.get("description") or _generate_step_description(cmd_name, args)
            }
        else:
            # Unknown format - convert to safe echo
            normalized_step = {
                "id": i,
                "command": "terminal.run",
                "args": {"command": f"echo 'Unknown step: {str(step)}'"},
                "needs_confirmation": False,
                "description": f"Echo unknown step: {str(step)[:30]}..."
            }
        
        normalized.append(normalized_step)
    
    return normalized


def _is_step_destructive(command: str, args: Dict) -> bool:
    """Enhanced destructive operation detection"""
    # Check command type
    destructive_commands = {
        "terminal.run": lambda a: is_destructive(a.get("command", "")),
        "files.delete": lambda a: True,
        "files.write": lambda a: True,  # Writing files can be destructive
        "system.shutdown": lambda a: True,
        "system.reboot": lambda a: True,
        "service.stop": lambda a: True,
        "package.remove": lambda a: True
    }
    
    if command in destructive_commands:
        return destructive_commands[command](args)
    
    # Check for destructive patterns in args
    args_str = json.dumps(args).lower()
    destructive_patterns = ['rm ', 'delete', 'remove', 'drop', 'truncate', 'format', 'wipe']
    return any(pattern in args_str for pattern in destructive_patterns)


def _generate_step_description(command: str, args: Dict) -> str:
    """Generate human-readable step descriptions"""
    descriptions = {
        "terminal.run": lambda a: f"Execute: {a.get('command', 'unknown command')}",
        "files.read": lambda a: f"Read file: {a.get('path', 'unknown path')}",
        "files.write": lambda a: f"Write to: {a.get('path', 'unknown path')}",
        "files.list": lambda a: f"List directory: {a.get('path', 'current directory')}",
        "files.delete": lambda a: f"Delete: {a.get('path', 'unknown path')}",
        "service.start": lambda a: f"Start service: {a.get('name', 'unknown service')}",
        "service.stop": lambda a: f"Stop service: {a.get('name', 'unknown service')}",
        "package.install": lambda a: f"Install package: {a.get('name', 'unknown package')}"
    }
    
    if command in descriptions:
        return descriptions[command](args)
    
    return f"Execute {command} with {len(args)} parameters"


def _should_suggest_execution(steps: List[Dict], session_context=None) -> bool:
    """Determine if execution should be suggested based on steps and context"""
    if not steps:
        return False
    
    # Don't suggest if there are destructive operations without confirmation
    destructive_count = sum(1 for step in steps if step.get("needs_confirmation", False))
    if destructive_count > 0:
        return False
    
    # Don't suggest if user is already awaiting confirmation
    if session_context and getattr(session_context, 'awaiting_confirmation', False):
        return False
    
    # Suggest for simple, safe operations
    safe_commands = {"files.list", "files.read", "system.info", "service.status"}
    all_safe = all(step.get("command") in safe_commands for step in steps)
    
    return all_safe and len(steps) <= 3


def _analyze_safety_concerns(steps: List[Dict]) -> List[str]:
    """Analyze steps for safety concerns and generate warnings"""
    concerns = []
    
    destructive_steps = [step for step in steps if step.get("needs_confirmation", False)]
    if destructive_steps:
        concerns.append(f"This plan contains {len(destructive_steps)} potentially destructive operations that require confirmation.")
    
    # Check for system-level operations
    system_commands = [step for step in steps if step.get("command") == "terminal.run" 
                      and any(keyword in step.get("args", {}).get("command", "").lower() 
                             for keyword in ["sudo", "rm -rf", "format", "fdisk"])]
    if system_commands:
        concerns.append("This plan includes system-level operations that could affect system stability.")
    
    # Check for network operations
    network_commands = [step for step in steps if step.get("command") == "terminal.run"
                       and any(keyword in step.get("args", {}).get("command", "").lower()
                              for keyword in ["wget", "curl", "ssh", "scp", "rsync"])]
    if network_commands:
        concerns.append("This plan includes network operations that may transfer data.")
    
    return concerns


# Legacy function for backward compatibility
def normalize(ai_output: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy normalize function - redirects to enhanced version"""
    return normalize_with_context(ai_output, "legacy request")


def create_plan_with_context(text: str, session_context=None, backend: str = "gemini") -> Dict:
    """Create a plan with full conversation context and intelligent enhancements"""
    
    # Get the raw plan from AI
    raw_plan = get_plan(text, backend=backend, session_context=session_context)
    
    # Apply context-aware enhancements
    enhanced_plan = _enhance_plan_with_context(raw_plan, text, session_context)
    
    return enhanced_plan


def _enhance_plan_with_context(plan: Dict, original_request: str, session_context=None) -> Dict:
    """Apply context-aware enhancements to the plan"""
    
    # Add conversation-aware suggestions
    if session_context:
        plan = _add_contextual_suggestions(plan, session_context)
    
    # Add intelligent step ordering
    plan["steps"] = _optimize_step_order(plan["steps"])
    
    # Add estimated execution time
    plan["estimated_duration"] = _estimate_execution_time(plan["steps"])
    
    # Add prerequisite checks
    plan["prerequisites"] = _identify_prerequisites(plan["steps"])
    
    # Add rollback suggestions for destructive operations
    if any(step.get("needs_confirmation") for step in plan["steps"]):
        plan["rollback_suggestions"] = _generate_rollback_suggestions(plan["steps"])
    
    return plan


def _add_contextual_suggestions(plan: Dict, session_context) -> Dict:
    """Add suggestions based on conversation context"""
    suggestions = []
    
    # Check if user has been having issues
    recent_messages = getattr(session_context, 'messages', [])[-5:]
    error_keywords = ['error', 'failed', 'problem', 'issue', 'broken', 'not working']
    
    has_recent_errors = any(
        any(keyword in msg.get('content', '').lower() for keyword in error_keywords)
        for msg in recent_messages if msg.get('role') == 'user'
    )
    
    if has_recent_errors:
        suggestions.append("Consider running diagnostic commands first to identify the root cause.")
        # Add diagnostic step at the beginning
        diagnostic_step = {
            "id": -1,
            "command": "terminal.run",
            "args": {"command": "echo 'Running diagnostics...' && systemctl status || service --status-all | head -10"},
            "needs_confirmation": False,
            "description": "Run system diagnostics"
        }
        plan["steps"].insert(0, diagnostic_step)
    
    # Check if user is repeating similar requests
    if len(recent_messages) >= 4:
        recent_requests = [msg.get('content', '') for msg in recent_messages[-4:] if msg.get('role') == 'user']
        if len(set(recent_requests)) < len(recent_requests) / 2:  # Many similar requests
            suggestions.append("You seem to be working on a recurring task. Consider creating a script to automate this.")
    
    if suggestions:
        plan["contextual_suggestions"] = suggestions
    
    return plan


def _optimize_step_order(steps: List[Dict]) -> List[Dict]:
    """Optimize the order of steps for better execution flow"""
    if not steps:
        return steps
    
    # Separate steps by type
    read_steps = []
    write_steps = []
    service_steps = []
    other_steps = []
    
    for step in steps:
        command = step.get("command", "")
        if "read" in command or "list" in command or "status" in command:
            read_steps.append(step)
        elif "write" in command or "create" in command or "install" in command:
            write_steps.append(step)
        elif "service" in command or "systemctl" in command:
            service_steps.append(step)
        else:
            other_steps.append(step)
    
    # Optimal order: read first, then write, then services, then others
    optimized = read_steps + write_steps + service_steps + other_steps
    
    # Reassign IDs
    for i, step in enumerate(optimized):
        step["id"] = i
    
    return optimized


def _estimate_execution_time(steps: List[Dict]) -> str:
    """Estimate how long the plan will take to execute"""
    if not steps:
        return "< 1 minute"
    
    total_seconds = 0
    
    for step in steps:
        command = step.get("command", "")
        args = step.get("args", {})
        
        # Estimate based on command type
        if command == "terminal.run":
            cmd = args.get("command", "").lower()
            if any(keyword in cmd for keyword in ["install", "update", "upgrade"]):
                total_seconds += 60  # Package operations take time
            elif any(keyword in cmd for keyword in ["download", "wget", "curl"]):
                total_seconds += 30  # Network operations
            elif any(keyword in cmd for keyword in ["compile", "build", "make"]):
                total_seconds += 120  # Build operations
            else:
                total_seconds += 5  # Basic commands
        elif "service" in command:
            total_seconds += 10  # Service operations
        else:
            total_seconds += 3  # File operations
    
    if total_seconds < 60:
        return f"~{total_seconds} seconds"
    elif total_seconds < 300:
        return f"~{total_seconds // 60} minutes"
    else:
        return f"~{total_seconds // 60} minutes (long-running)"


def _identify_prerequisites(steps: List[Dict]) -> List[str]:
    """Identify prerequisites needed before executing the plan"""
    prerequisites = []
    
    for step in steps:
        command = step.get("command", "")
        args = step.get("args", {})
        
        if command == "terminal.run":
            cmd = args.get("command", "").lower()
            
            # Check for common prerequisites
            if "sudo" in cmd and "sudo access" not in prerequisites:
                prerequisites.append("sudo access")
            
            if any(pkg in cmd for pkg in ["apt", "yum", "dnf", "pacman"]) and "package manager" not in prerequisites:
                prerequisites.append("package manager access")
            
            if any(net in cmd for net in ["wget", "curl", "git clone"]) and "internet connection" not in prerequisites:
                prerequisites.append("internet connection")
            
            if "systemctl" in cmd and "systemd" not in prerequisites:
                prerequisites.append("systemd")
    
    return prerequisites


def _generate_rollback_suggestions(steps: List[Dict]) -> List[str]:
    """Generate rollback suggestions for destructive operations"""
    rollback_suggestions = []
    
    for step in steps:
        if not step.get("needs_confirmation"):
            continue
            
        command = step.get("command", "")
        args = step.get("args", {})
        
        if command == "terminal.run":
            cmd = args.get("command", "").lower()
            
            if "rm " in cmd:
                rollback_suggestions.append("Create backups before deleting files")
            elif "install" in cmd:
                rollback_suggestions.append("Note installed packages for potential removal")
            elif any(svc in cmd for svc in ["stop", "disable"]):
                rollback_suggestions.append("Remember current service states for restoration")
            elif "modify" in cmd or "edit" in cmd:
                rollback_suggestions.append("Backup configuration files before modification")
    
    return rollback_suggestions


def get_plan_summary(plan: Dict) -> str:
    """Generate a concise summary of the plan for conversation context"""
    plan_name = plan.get("plan", "Unknown Plan")
    step_count = len(plan.get("steps", []))
    destructive_count = sum(1 for step in plan.get("steps", []) if step.get("needs_confirmation", False))
    
    summary = f"{plan_name} ({step_count} steps"
    if destructive_count > 0:
        summary += f", {destructive_count} need confirmation"
    summary += ")"
    
    return summary