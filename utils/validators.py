import shlex


DESTRUCTIVE_KEYWORDS = ["rm", "dd", ":(){", "shutdown", "reboot"]


def is_destructive(command: str) -> bool:
    try:
        parts = shlex.split(command)
    except Exception:
        parts = command.split()
    for p in parts:
        for k in DESTRUCTIVE_KEYWORDS:
            if p.startswith(k):
                return True
    # naive: look for patterns like rm -rf /
    if "-rf" in command and "/" in command:
        return True
    return False
