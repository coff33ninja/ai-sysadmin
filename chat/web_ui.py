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
    <style>
      body { font-family: system-ui, Arial, sans-serif; margin: 16px }
      #plans button { background: #f8fafc; border: 1px solid #cbd5e1; padding: 6px; margin:4px 0; width:100%; text-align:left }
      #selected { background: #0b1220; color: #e6eef6; border-radius:6px }
      #selected .step { padding:6px; border-bottom:1px solid rgba(255,255,255,0.04) }
      .destructive { background: #4c1f1f; color: #fff0f0 }
      .actions { margin-top:8px }
    </style>
    <div>
      <h3>Create Plan</h3>
      <input id="backend" type="text" value="gemini" />
      <input id="prompt" type="text" size="80" />
      <button onclick="createPlan()">Create Plan</button>
    </div>
    <div>
      <h3>Plans</h3>
      <button onclick="listPlans()">Refresh</button>
      <div id="plans" style="height:200px;overflow:auto;border:1px solid #ccc"></div>
      <h4>Selected Plan</h4>
      <div id="selected" style="height:200px;overflow:auto;border:1px solid #ccc;padding:8px"></div>
      <div id="confirm-area" style="margin-top:8px">
        <button onclick="executeAll()">Execute All</button>
        <button onclick="executeSelected()">Execute Selected Steps</button>
      </div>
    </div>
    <script>
      var ws = new WebSocket("ws://localhost:8000/ws");
      ws.onmessage = (e) => {
        try {
          const obj = JSON.parse(e.data)
          // if plan.create response includes plan, show it
          if (obj.result) {
                // plan.create returns {id, plan}
                if (obj.result.plan) {
                  setSelected(obj.result.id, obj.result.plan)
                } else if (Array.isArray(obj.result)) {
                  renderPlans(obj.result)
                } else if (obj.result.results) {
                  // execution result
                  document.getElementById('selected').textContent = JSON.stringify(obj.result, null, 2)
                }
              }
          console.log(obj)
        } catch(err) {
          console.log('non-json message', e.data)
        }
      };

      let selectedPlanId = null
      let selectedPlanObj = null

      function createPlan(){
        const backend = document.getElementById('backend').value;
        const prompt = document.getElementById('prompt').value;
        ws.send(JSON.stringify({type:'create_plan', backend: backend, prompt: prompt}));
      }

      function listPlans(){
        ws.send(JSON.stringify({type:'list_plans'}));
      }

      function renderPlans(plans){
        const el = document.getElementById('plans')
        el.innerHTML = ''
        plans.forEach(p=>{
          const btn = document.createElement('button')
          btn.textContent = `${p.id} - ${p.plan.plan || p.plan}`
          btn.style.display = 'block'
          btn.style.textAlign = 'left'
          btn.onclick = ()=> setSelected(p.id, p.plan)
          el.appendChild(btn)
        })
      }

      function setSelected(id, plan){
        selectedPlanId = id
        selectedPlanObj = plan
        renderSelectedPlan()
      }

      function renderSelectedPlan(){
        const out = document.getElementById('selected')
        out.innerHTML = ''
        if (!selectedPlanObj) {
          out.textContent = 'No plan selected'
          return
        }
        const title = document.createElement('div')
        title.textContent = selectedPlanObj.plan || 'Plan'
        out.appendChild(title)
        const list = document.createElement('div')
        selectedPlanObj.steps.forEach((s,i)=>{
          const row = document.createElement('div')
          const cb = document.createElement('input')
          cb.type = 'checkbox'
          cb.value = i
          cb.id = `step_${i}`
          const lbl = document.createElement('label')
          lbl.htmlFor = cb.id
          lbl.textContent = `${i}: ${s.command} ${JSON.stringify(s.args||{})}`
          row.appendChild(cb)
          row.appendChild(lbl)
          row.className = 'step'
          if (s.needs_confirmation) {
            row.classList.add('destructive')
            const warn = document.createElement('span')
            warn.textContent = ' ⚠ destructive'
            warn.style.marginLeft = '8px'
            lbl.appendChild(warn)
          }
          list.appendChild(row)
        })
        out.appendChild(list)
      }

      function executeAll(){
        if (!selectedPlanId) return alert('No plan selected')
        ws.send(JSON.stringify({type:'execute_plan', plan_id: selectedPlanId}))
      }

      function executeSelected(){
        if (!selectedPlanId) return alert('No plan selected')
        const checks = Array.from(document.querySelectorAll('#selected input[type=checkbox]:checked'))
        const idx = checks.map(c=>parseInt(c.value))
        // if any selected steps are destructive, prompt for confirmation
        const destructiveSelected = idx.some(i => selectedPlanObj.steps[i] && selectedPlanObj.steps[i].needs_confirmation)
        if (destructiveSelected) {
          const ok = confirm('Selected steps include destructive actions. Are you sure you want to run them?')
          if (!ok) return
        }
        ws.send(JSON.stringify({type:'execute_confirm', plan_id: selectedPlanId, confirm_steps: idx}))
      }

      // legacy: keep simple executePlan helper
      function executePlan(id){
        ws.send(JSON.stringify({type:'execute_plan', plan_id: id}));
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
