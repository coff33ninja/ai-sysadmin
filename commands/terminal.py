import shlex
import subprocess
from typing import Dict
import asyncio


def _run_sync(command: str) -> Dict[str, str]:
    """Synchronous execution helper."""
    if not command or not command.strip():
        return {"stdout": "", "stderr": "empty command"}
    try:
        parts = shlex.split(command, posix=(subprocess.os.name != "nt"))
        result = subprocess.run(parts, capture_output=True, text=True, check=False)
        return {"stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"stdout": "", "stderr": str(e)}


def run(command: str) -> Dict[str, str]:
    """Synchronous API kept for CLI/TUI usage."""
    return _run_sync(command)


async def run_async(command: str) -> Dict[str, str]:
    """Async wrapper that runs the command in the default threadpool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_sync, command)
