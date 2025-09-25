import sys
sys.path.insert(0, r'e:/SCRIPTS/sysmin/ai_sysadmin')
import asyncio
from core.plan_store import save_plan
from main import build_router


def make_echo_plan():
    # One-step plan that runs a harmless echo command (platform-appropriate)
    if sys.platform.startswith("win"):
        cmd = 'cmd /c echo hello'
    else:
        cmd = 'echo hello'
    return {
        "plan": "Echo test",
        "steps": [
            {"id": 0, "command": "terminal.run", "args": {"command": cmd}}
        ],
    }


def test_execute_plan_async_event_loop():
    router = build_router()
    # save plan and get id
    plan = make_echo_plan()
    pid = save_plan(plan)

    async def run_and_check():
        # call the registered async executor via router
        # Router.call_async expects a JSON string
        import json
        req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "plan.execute_async", "params": {"plan_id": pid}})
        resp = await router.call_async(req)
        # router.call_async returns a JSON string like {"result": {...}}
        data = json.loads(resp)
        assert "result" in data
        result = data.get("result")
        assert result.get("results") is not None
        # results is a list with one item containing 'stdout'
        results = result.get("results")
        assert len(results) == 1
        first = results[0]
        # echo on Windows appends a newline; accept presence of 'hello'
        out = first.get("stdout", "")
        assert "hello" in out.lower()

    asyncio.run(run_and_check())
