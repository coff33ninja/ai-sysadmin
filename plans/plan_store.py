import json
from pathlib import Path
from typing import Dict, Any, List
import datetime
import zipfile

STORE_DIR = Path("storage/plans")
BACKUP_DIR = Path("storage/backups")
STORE_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _plan_path(plan_id: int) -> Path:
    return STORE_DIR / f"plan_{plan_id}.json"


def save_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    # assign an id
    plan_id = int(datetime.datetime.utcnow().timestamp())
    path = _plan_path(plan_id)
    with path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    return {"id": plan_id, "path": str(path)}


def list_plans() -> List[Dict[str, Any]]:
    plans = []
    for p in sorted(STORE_DIR.glob("plan_*.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            plans.append({"id": int(p.stem.split("_")[1]), "path": str(p), "plan": data})
        except Exception:
            continue
    return plans


def get_plan(plan_id: int) -> Dict[str, Any]:
    p = _plan_path(plan_id)
    if not p.exists():
        return {"error": "not found", "id": plan_id}
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def backup_workspace(target_paths: list = None) -> Dict[str, Any]:
    """Create a zip backup of given paths (or whole project) and return its path."""
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    zip_name = BACKUP_DIR / f"backup_{ts}.zip"
    if not target_paths:
        # default: backup the current working directory
        target_paths = ["."]
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for tp in target_paths:
            p = Path(tp).expanduser()
            if p.is_file():
                zf.write(p, arcname=p.name)
            elif p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        try:
                            zf.write(f, arcname=str(f.relative_to(Path.cwd())))
                        except Exception:
                            # skip unreadable files
                            continue
    return {"backup": str(zip_name)}


def delete_plan(plan_id: int) -> Dict[str, Any]:
    p = _plan_path(plan_id)
    if p.exists():
        p.unlink()
        return {"deleted": plan_id}
    return {"error": "not found", "id": plan_id}
