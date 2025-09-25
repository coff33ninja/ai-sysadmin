import argparse
import threading
from core.router import Router
from commands import terminal, files


def build_router() -> Router:
    r = Router()
    r.register("terminal.run", terminal.run)
    r.register("files.list", files.list_files)
    r.register("files.read", files.read_file)
    r.register("files.write", files.write_file)

    # Plan methods
    from core.plan_store import save_plan, list_plans, load_plan
    from ai_backend.planner import get_plan

    def create_plan(text: str, backend: str = "gemini"):
        plan = get_plan(text, backend=backend)
        plan_id = save_plan(plan)
        return {"id": plan_id, "plan": plan}

    def list_all_plans():
        return list_plans()

    def get_plan_by_id(plan_id: str):
        return load_plan(plan_id)

    def execute_plan(plan_id: str, steps: list = None, confirm_steps: list = None):
        # Support on-the-fly plan generation if plan_id is an empty string and a prompt was passed
        plan = load_plan(plan_id) if plan_id else {"plan": "", "steps": []}
        if not plan.get("steps") and plan_id == "":
            # fallback: caller may have passed a prompt in confirm_steps (deprecated)
            return {"error": "no_plan_provided", "message": "Provide a plan_id or create via plan.create first."}
        if "error" in plan:
            return plan
        # safety: identify destructive steps
        from utils.validators import is_destructive

        results = []
        steps_all = list(range(len(plan.get("steps", []))))
        steps_to_run = steps if steps is not None else steps_all

        destructive_found = []
        for i in steps_to_run:
            step = plan["steps"][i]
            if step.get("command") == "terminal.run":
                if is_destructive(step.get("args", {}).get("command", "")):
                    destructive_found.append(i)

        # If destructive steps exist, require confirm_steps to include them
        if destructive_found:
            confirm_set = set(confirm_steps or [])
            missing = [i for i in destructive_found if i not in confirm_set]
            if missing:
                return {"error": "destructive_steps_found", "destructive_steps": destructive_found, "missing_confirmation": missing}

        for i in steps_to_run:
            step = plan["steps"][i]
            cmd = step["command"]
            args = step.get("args", {})
            # Only support terminal.run and files.* for now
            if cmd == "terminal.run":
                results.append(terminal.run(args.get("command", "")))
            elif cmd == "files.list":
                results.append(files.list_files(**args))
            elif cmd == "files.read":
                results.append(files.read_file(**args))
            elif cmd == "files.write":
                results.append(files.write_file(**args))
            else:
                results.append({"error": f"Unknown command {cmd}"})
        return {"plan_id": plan_id, "results": results}

    async def execute_plan_async(plan_id: str = "", prompt: str = None, backend: str = "gemini", steps: list = None, confirm_steps: list = None):
        """Async plan executor. If plan_id is empty and prompt is provided, create the plan first."""
        if not plan_id and prompt:
            from core.plan_store import save_plan
            from ai_backend.planner import get_plan
            plan = get_plan(prompt, backend=backend)
            plan_id = save_plan(plan)
        else:
            plan = load_plan(plan_id)

        if "error" in plan:
            return plan

        results = []
        steps_all = list(range(len(plan.get("steps", []))))
        steps_to_run = steps if steps is not None else steps_all

        from utils.validators import is_destructive
        destructive_found = []
        for i in steps_to_run:
            step = plan["steps"][i]
            if step.get("command") == "terminal.run":
                if is_destructive(step.get("args", {}).get("command", "")):
                    destructive_found.append(i)

        if destructive_found:
            confirm_set = set(confirm_steps or [])
            missing = [i for i in destructive_found if i not in confirm_set]
            if missing:
                return {"error": "destructive_steps_found", "destructive_steps": destructive_found, "missing_confirmation": missing}

        for i in steps_to_run:
            step = plan["steps"][i]
            cmd = step["command"]
            args = step.get("args", {})
            if cmd == "terminal.run":
                # use async runner
                res = await terminal.run_async(args.get("command", ""))
                results.append(res)
            elif cmd == "files.list":
                results.append(files.list_files(**args))
            elif cmd == "files.read":
                results.append(files.read_file(**args))
            elif cmd == "files.write":
                results.append(files.write_file(**args))
            else:
                results.append({"error": f"Unknown command {cmd}"})
        return {"plan_id": plan_id, "results": results}

    r.register("plan.create", create_plan)
    r.register("plan.list", list_all_plans)
    r.register("plan.get", get_plan_by_id)
    r.register("plan.execute", execute_plan)
    # async variant for web callers
    r.register("plan.execute_async", execute_plan_async)
    return r


def run_web(router: Router, host: str = "127.0.0.1", port: int = 8000):
    from chat import web_ui
    import uvicorn

    web_ui.router = router
    uvicorn.run(web_ui.app, host=host, port=port)


def run_tui(router: Router):
    from chat.interface_tui import ChatApp

    ChatApp(router).run()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["web", "tui", "both"], default="web")
    args = parser.parse_args()

    router = build_router()

    if args.mode == "web":
        run_web(router)
    elif args.mode == "tui":
        run_tui(router)
    else:
        # run both: web in thread, tui in main thread
        t = threading.Thread(target=run_web, args=(router,), daemon=True)
        t.start()
        run_tui(router)


if __name__ == "__main__":
    main()
