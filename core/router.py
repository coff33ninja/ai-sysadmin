import json
from typing import Callable, Dict, Any
import json
import threading
import asyncio

class Router:
    def __init__(self):
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self.lock = threading.Lock()

    def register(self, name: str, func: Callable[..., Any]):
        with self.lock:
            self.handlers[name] = func

    def call(self, request_json: str) -> str:
        """Synchronous JSON-RPC-like call. If the handler is a coroutine function,
        it will be executed to completion using asyncio.run()."""
        try:
            req = json.loads(request_json)
            method = req.get("method")
            params = req.get("params", {})
            if method not in self.handlers:
                return json.dumps({"error": "method_not_found"})
            handler = self.handlers[method]
            # handle coroutine handlers by running a short-lived event loop
            if asyncio.iscoroutinefunction(handler):
                if isinstance(params, dict):
                    res = asyncio.run(handler(**params))
                else:
                    res = asyncio.run(handler(*params))
            else:
                if isinstance(params, dict):
                    res = handler(**params)
                else:
                    res = handler(*params)
            return json.dumps({"result": res})
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def call_async(self, request_json: str) -> str:
        """Async-friendly caller. Runs sync handlers in a threadpool and awaits coroutines."""
        req = json.loads(request_json)
        method = req.get("method")
        params = req.get("params", {})
        if method not in self.handlers:
            return json.dumps({"error": "method_not_found"})
        handler = self.handlers[method]
        try:
            if asyncio.iscoroutinefunction(handler):
                res = await (handler(**params) if isinstance(params, dict) else handler(*params))
            else:
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(None, lambda: handler(**params) if isinstance(params, dict) else handler(*params))
            return json.dumps({"result": res})
        except Exception as e:
            return json.dumps({"error": str(e)})
