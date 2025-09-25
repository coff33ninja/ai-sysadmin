import sys
sys.path.insert(0, r'e:/SCRIPTS/sysmin/ai_sysadmin')
from core.router import Router


def test_register_and_call():
    r = Router()

    def add(a: int, b: int) -> int:
        return a + b

    r.register('math.add', add)
    req = '{"jsonrpc": "2.0", "id": 1, "method": "math.add", "params": {"a": 2, "b": 3}}'
    res = r.call(req)
    assert 'result' in res
