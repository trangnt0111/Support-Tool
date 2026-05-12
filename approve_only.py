import sys, json, time, websocket

GAME   = sys.argv[1] # e.g. 655
PERIOD = sys.argv[2] # e.g. 00482
DATE   = sys.argv[3] # e.g. 21042026 (DDMMYYYY) or YYYYMMDD
TXID   = sys.argv[4] # e.g. 8f60f07cc7a19

# Normalize Date to DD/MM/YYYY
if len(DATE) == 8:
    if DATE.startswith('20'): # YYYYMMDD
        UI_DATE = f"{DATE[6:8]}/{DATE[4:6]}/{DATE[:4]}"
    else: # DDMMYYYY
        UI_DATE = f"{DATE[:2]}/{DATE[2:4]}/{DATE[4:]}"
else:
    UI_DATE = DATE # Fallback

game_name_search = "6/55" if GAME == "655" else "6/45"
if GAME == "535": game_name_search = "5/35"
if GAME == "3D":  game_name_search = "Max 3D"

print(f"--- APPROVING ONLY: {GAME} | {PERIOD} | {UI_DATE} | {TXID} ---")

def run_js(ws, ex, timeout=60):
    mid = int(time.time()*1000)%1000000
    ws.send(json.dumps({'id': mid, 'method': 'Runtime.evaluate', 'params': {'expression': ex, 'returnByValue': True, 'awaitPromise': True}}))
    for _ in range(timeout):
        try:
            r = json.loads(ws.recv())
            if r.get('id') == mid:
                res = r.get('result', {}).get('result', {})
                return res.get('value') or res.get('description') or res
        except: pass
        time.sleep(0.5)
    return "TIMEOUT"

# Connect to Chrome
targets = json.loads(websocket.create_connection("ws://localhost:9222/json", timeout=5).recv() if False else '[]') # Dummy check
import requests
targets = requests.get('http://localhost:9222/json').json()
ws_url = next((p['webSocketDebuggerUrl'] for p in targets if p['type'] == 'page' and '172.16.9.29:18091/dashboard' in p.get('url', '')), None)

if not ws_url:
    print("LOI: Khong tim thay trang dashboard dang mo!"); sys.exit(1)

ws = websocket.create_connection(ws_url, suppress_origin=True, timeout=30)

master_script = f"""
(async function() {{
    const wait = (ms) => new Promise(r => setTimeout(r, ms));
    const find_btn = (txt, container=document) => Array.from(container.querySelectorAll('button, span')).find(b => b.innerText.includes(txt));

    // Tu dong Dang nhap 
    if (document.querySelector('input[formcontrolname="username"]')) {{
        document.querySelector('input[formcontrolname="username"]').value = 'ctinadmin';
        document.querySelector('input[formcontrolname="username"]').dispatchEvent(new Event('input'));
        document.querySelector('input[formcontrolname="password"]').value = 'Abc@123456';
        document.querySelector('input[formcontrolname="password"]').dispatchEvent(new Event('input'));
        await wait(500);
        let login_btn = find_btn('Đăng nhập') || document.querySelector('button[type="submit"]');
        if (login_btn) login_btn.click();
        await wait(3000);
    }}

    // Chuyển trang nếu cần (Fake click để trigger load)
    let selects = document.querySelectorAll('mat-select');
    if (selects.length > 0) {{
        selects[0].click(); await wait(500);
        let options = Array.from(document.querySelectorAll('mat-option'));
        let target = options.find(o => o.innerText.includes('{game_name_search}'));
        if (target) {{ target.click(); await wait(500); }}
    }}
    
    // Tìm kỳ quay
    let period_btn = null;
    for(let i=0; i<20; i++) {{
        let s_btn = find_btn('Tìm kiếm');
        if (s_btn) s_btn.click();
        await wait(3000);
        let rows = Array.from(document.querySelectorAll('mat-row, tr'));
        let row = rows.find(r => r.innerText.includes('{PERIOD}') && r.innerText.includes('{UI_DATE}'));
        if (row) {{
            let btns = Array.from(row.querySelectorAll('button'));
            period_btn = btns.find(b => b.innerText.trim() === 'Phê duyệt') || btns.find(b => b.innerText.trim() === 'Chi tiết');
            if (period_btn) break;
        }}
        await wait(1000);
    }}
    if (!period_btn) return 'PERIOD_NOT_FOUND';
    period_btn.click(); await wait(4000);

    // Tìm vé
    let ticket_row = null;
    for(let i=0; i<30; i++) {{
        let s_inner = find_btn('Tìm kiếm');
        if (s_inner && i%5==0) s_inner.click();
        await wait(1000);
        let rows = Array.from(document.querySelectorAll('mat-row, tr'));
        ticket_row = rows.find(r => r.innerText.includes('{TXID}'));
        if (ticket_row) break;
    }}
    if (!ticket_row) return 'TICKET_NOT_FOUND';

    // Tick chọn và Phê duyệt
    let cb = ticket_row.querySelector('mat-checkbox');
    if (cb) cb.click(); await wait(500);
    let p_btn = find_btn('Phê duyệt kết quả');
    if (!p_btn) return 'APPROVE_BTN_NOT_FOUND';
    p_btn.click(); await wait(1500);

    // Confirm modals
    let sms_btn = find_btn('Gửi SMS');
    if (sms_btn) {{
        sms_btn.click(); await wait(1500);
        let confirm_btn = find_btn('Xác nhận');
        if (confirm_btn) confirm_btn.click();
    }}
    return 'SUCCESS';
}})()
"""

res = run_js(ws, master_script)
print(f"RESULT: {res}")
ws.close()
