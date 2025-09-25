from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import json

app = FastAPI()
router = None  # injected by main

html = """
<!DOCTYPE html>
<html>
  <body>
    <h1>🤖 AI Sysadmin Web Chat</h1>
    <div>
      <h3>Create Plan</h3>
      <input id="backend" type="text" value="gemini" />
      <input id="prompt" type="text" size="80" />
      <button onclick="createPlan()">Create Plan</button>
    </div>
    <div>
      <h3>Plans</h3>
      <button onclick="listPlans()">Refresh</button>
      <pre id="plans" style="height:200px;overflow:auto;border:1px solid #ccc"></pre>
      <h4>Selected Plan</h4>
      <pre id="selected" style="height:200px;overflow:auto;border:1px solid #ccc"></pre>
      <label>Confirm indices (comma sep): <input id="confirm_idx" type="text" /></label>
      <button onclick="executeConfirm()">Execute with confirmation</button>
    </div>
    <script>
      var ws = new WebSocket("ws://localhost:8000/ws");
      ws.onmessage = (e) => {
        try {
          const obj = JSON.parse(e.data)
          // if plan.create response includes plan, show it
          if (obj.result && obj.result.plan) {
            document.getElementById('selected').textContent = JSON.stringify(obj.result.plan, null, 2)
          }
          // if plan.list response, render
          if (obj.result && Array.isArray(obj.result)) {
            document.getElementById('plans').textContent = JSON.stringify(obj.result, null, 2)
          }
          console.log(obj)
        } catch(err) {
          console.log('non-json message', e.data)
        }
      };

      function createPlan(){
        const backend = document.getElementById('backend').value;
        const prompt = document.getElementById('prompt').value;
        ws.send(JSON.stringify({type:'create_plan', backend: backend, prompt: prompt}));
      }

      function listPlans(){
        ws.send(JSON.stringify({type:'list_plans'}));
      }

      function executePlan(id){
        ws.send(JSON.stringify({type:'execute_plan', plan_id: id}));
      }
      function executeConfirm(){
        const pid = document.getElementById('selected').textContent ? JSON.parse(document.getElementById('selected').textContent).id : null
        const idx = document.getElementById('confirm_idx').value
        const arr = idx.split(',').map(s=>parseInt(s.trim())).filter(n=>!isNaN(n))
        ws.send(JSON.stringify({type:'execute_confirm', plan_id: pid, confirm_steps: arr}))
      }
    </script>
  </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    while True:
        msg = await ws.receive_text()
        try:
            data = json.loads(msg)
        except Exception:
            # treat as plain terminal command
            req = {"jsonrpc": "2.0", "id": 1, "method": "terminal.run", "params": {"command": msg}}
            response = router.call(json.dumps(req))
            await ws.send_text(response)
            continue

        t = data.get('type')
        if t == 'create_plan':
            backend = data.get('backend', 'gemini')
            prompt = data.get('prompt', '')
            req = {"jsonrpc": "2.0", "id": 1, "method": "plan.create", "params": {"text": prompt, "backend": backend}}
            # Prefer async router call when available to avoid blocking
            if hasattr(router, 'call_async'):
                res = await router.call_async(json.dumps(req))
            else:
                res = router.call(json.dumps(req))
            await ws.send_text(res)
        elif t == 'list_plans':
            req = {"jsonrpc": "2.0", "id": 1, "method": "plan.list", "params": {}}
            if hasattr(router, 'call_async'):
                res = await router.call_async(json.dumps(req))
            else:
                res = router.call(json.dumps(req))
            await ws.send_text(res)
        elif t == 'execute_plan':
            pid = data.get('plan_id')
            # prefer async executor
            req = {"jsonrpc": "2.0", "id": 1, "method": "plan.execute_async", "params": {"plan_id": pid}}
            if hasattr(router, 'call_async'):
                res = await router.call_async(json.dumps(req))
            else:
                # fallback to sync plan.execute
                req_sync = {"jsonrpc": "2.0", "id": 1, "method": "plan.execute", "params": {"plan_id": pid}}
                res = router.call(json.dumps(req_sync))
            await ws.send_text(res)
        elif t == 'execute_confirm':
            pid = data.get('plan_id')
            confirm = data.get('confirm_steps', [])
            # prefer async executor
            req = {"jsonrpc": "2.0", "id": 1, "method": "plan.execute_async", "params": {"plan_id": pid, "confirm_steps": confirm}}
            if hasattr(router, 'call_async'):
                res = await router.call_async(json.dumps(req))
            else:
                req_sync = {"jsonrpc": "2.0", "id": 1, "method": "plan.execute", "params": {"plan_id": pid, "confirm_steps": confirm}}
                res = router.call(json.dumps(req_sync))
            await ws.send_text(res)
        else:
            await ws.send_text(json.dumps({"error": "unknown message type"}))
