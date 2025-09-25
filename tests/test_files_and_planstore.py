import sys
from pathlib import Path
sys.path.insert(0, r'e:/SCRIPTS/sysmin/ai_sysadmin')

from commands.files import list_files, read_file, write_file
from core.plan_store import save_plan, load_plan, list_plans


def test_files_write_and_read(tmp_path):
    p = tmp_path / "demo.txt"
    res = write_file(str(p), "hello")
    assert res.get('written') == 5
    r = read_file(str(p))
    assert r.get('content') == 'hello'


def test_list_files(tmp_path):
    d = tmp_path / "sub"
    d.mkdir()
    (d / "a.txt").write_text("x")
    res = list_files(str(d))
    assert res.get('items')


def test_planstore(tmp_path):
    plan = {"plan": "demo", "steps": [{"command": "files.list", "args": {"path": "."}}]}
    pid = save_plan(plan)
    loaded = load_plan(pid)
    assert loaded.get('plan') == 'demo'
    allp = list_plans()
    assert any(p.get('id') == pid for p in allp)
