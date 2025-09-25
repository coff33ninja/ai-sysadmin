import zipfile
from pathlib import Path
import datetime

def zip_workspace(src_dir: str = "e:/SCRIPTS/sysmin", backup_dir: str = "storage/backups") -> str:
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"backup_{ts}.zip"
    zip_file = backup_path / zip_name
    with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in Path(src_dir).rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(src_dir))
    return str(zip_file)
