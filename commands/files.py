from pathlib import Path
from typing import Dict, Any


def list_files(path: str = ".", limit: int = 100) -> Dict[str, Any]:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": "path not found", "path": str(p)}
    if not p.is_dir():
        return {"error": "path is not a directory", "path": str(p)}
    items = []
    for i, child in enumerate(sorted(p.iterdir(), key=lambda x: x.name)[:limit]):
        items.append({"name": child.name, "is_dir": child.is_dir()})
    return {"path": str(p), "items": items}


def read_file(path: str) -> Dict[str, Any]:
    p = Path(path).expanduser()
    if not p.exists():
        return {"error": "not found", "path": str(p)}
    try:
        text = p.read_text(encoding="utf-8")
        return {"path": str(p), "content": text}
    except Exception as e:
        return {"error": str(e), "path": str(p)}


def write_file(path: str, content: str) -> Dict[str, Any]:
    p = Path(path).expanduser()
    try:
        p.write_text(content, encoding="utf-8")
        return {"path": str(p), "written": len(content)}
    except Exception as e:
        return {"error": str(e), "path": str(p)}
