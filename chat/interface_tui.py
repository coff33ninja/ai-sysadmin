from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Static
import json


class ChatApp(App):
    CSS_PATH = "chat.css"

    def __init__(self, router):
        super().__init__()
        self.router = router

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("🤖 AI Sysadmin Chat (TUI)", id="log")
        yield Input(placeholder="Type command or natural text...", id="input")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value
        log_widget = self.query_one("#log", Static)
        # basic plan commands: /plan create|list|get|exec ...
        if text.startswith("/plan "):
            parts = text.split(maxsplit=2)
            cmd = parts[1] if len(parts) > 1 else ""
            if cmd == "create":
                prompt = parts[2] if len(parts) > 2 else ""
                req = {"jsonrpc": "2.0", "id": 1, "method": "plan.create", "params": {"text": prompt, "backend": "gemini"}}
                response = self.router.call(json.dumps(req))
                log_widget.update(log_widget.renderable + f"\nYou: {text}\n{response}")
            elif cmd == "list":
                req = {"jsonrpc": "2.0", "id": 1, "method": "plan.list", "params": {}}
                response = self.router.call(json.dumps(req))
                log_widget.update(log_widget.renderable + f"\nYou: {text}\n{response}")
            elif cmd == "get":
                pid = parts[2] if len(parts) > 2 else ""
                req = {"jsonrpc": "2.0", "id": 1, "method": "plan.get", "params": {"plan_id": pid}}
                response = self.router.call(json.dumps(req))
                log_widget.update(log_widget.renderable + f"\nYou: {text}\n{response}")
            elif cmd in ("exec", "execute"):
                pid = parts[2] if len(parts) > 2 else ""
                req = {"jsonrpc": "2.0", "id": 1, "method": "plan.execute", "params": {"plan_id": pid}}
                response = self.router.call(json.dumps(req))
                log_widget.update(log_widget.renderable + f"\nYou: {text}\n{response}")
            elif cmd == "confirm":
                # /plan confirm <id> <i,j,k>
                if len(parts) < 3:
                    log_widget.update(log_widget.renderable + "\nUsage: /plan confirm <id> <i,j>")
                else:
                    sub = parts[2].split(maxsplit=1)
                    pid = sub[0]
                    idxs = []
                    if len(sub) > 1:
                        idxs = [int(x) for x in sub[1].split(",") if x.strip().isdigit()]
                    req = {"jsonrpc": "2.0", "id": 1, "method": "plan.execute", "params": {"plan_id": pid, "confirm_steps": idxs}}
                    response = self.router.call(json.dumps(req))
                    log_widget.update(log_widget.renderable + f"\nYou: {text}\n{response}")
            else:
                log_widget.update(log_widget.renderable + f"\nUnknown plan subcommand: {cmd}")
            event.input.value = ""
            return

        req = {"jsonrpc": "2.0", "id": 1, "method": "terminal.run", "params": {"command": text}}
        response = self.router.call(json.dumps(req))
        # append to log
        log_widget.update(log_widget.renderable + f"\nYou: {text}\nResult: {response}")
        event.input.value = ""
