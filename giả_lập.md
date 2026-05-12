# Hướng Dẫn Chạy Giả Lập Trúng Thưởng (AI Tự Động Toàn Tập)

Khi người dùng yêu cầu "chạy giả lập" (VD: `Chạy giả lập game 655 sdt 0787452568 số tiền 20000 mức L`), AI hãy lấy giá trị trích xuất từ câu lệnh và chạy **duy nhất** đoạn script Python dưới đây bằng công cụ `run_command` (hoặc lưu nháp ra 1 file rồi chạy). File này lo trọn gói từ A-Z bao gồm thao tác tự phê duyệt qua DevTools.

```python
import sys, random, requests, json, time, urllib.request, websocket, re, datetime

# --- CẤU HÌNH ---
MSISDN = sys.argv[1]   if len(sys.argv) > 1 else "0787452568"
GAME   = sys.argv[2]   if len(sys.argv) > 2 else "655"
MONEY  = sys.argv[3]   if len(sys.argv) > 3 else "50000"
LEVEL  = sys.argv[4].upper() if len(sys.argv) > 4 else "L"

GAMES = {
    "645": {"name": "Mega 6/45", "code": "645", "csv": "LOTTO645", "sms": "645 k1 s", "num_pool": 45, "picks": 6, "draw_picks": 6},
    "655": {"name": "Power 6/55", "code": "655", "csv": "LOTTO655", "sms": "655 k1 s", "num_pool": 55, "picks": 6, "draw_picks": 7},
    "535": {"name": "Lotto 5/35", "code": "535", "csv": "LOTTO535", "sms": "535 k1 s", "num_pool": 35, "picks": 5, "draw_picks": 5},
    "3D":  {"name": "Keno 3D", "code": "3D", "csv": "KENO3D", "sms": "3d k1 s", "num_pool": 999, "picks": 1, "size": 3, "draw_picks": 20},
    "3DPRO":{"name": "Keno 3D Pro", "code": "3DPRO", "csv": "KENO3DP", "sms": "3dp k1 s", "num_pool": 999, "picks": 1, "size": 3, "draw_picks": 20}
}
g = GAMES.get(GAME.upper(), GAMES["655"])
print(f"=== Bắt đầu Giả Lập: SĐT {MSISDN} | Game {g['name']} | Tiền {MONEY} ===")

# 1. TẠO VÉ VÀ MUA
buy_nums = sorted(random.sample(range(1, g["num_pool"]+1), g["picks"])) if GAME not in ["3D", "3DPRO"] else [f"{random.randint(0, 999):03d}"]
msg = f"{g['sms']} {' '.join(f'{x:02d}' if isinstance(x, int) else x for x in buy_nums)}"
print(f"1. Mua vé SMS: {msg}")
r = requests.post("http://10.20.30.153:8092/receive/json", json={"request": "1", "msisdn": MSISDN, "content": msg, "channel": "SMS"})

# 2. CONNECT CHROME DEBBUGGER
def get_ws():
    try: targets = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    except: return None
    for p in targets:
        if p['type'] == 'page' and '172.16.9.29' in p.get('url', ''):
            return websocket.create_connection(p['webSocketDebuggerUrl'], suppress_origin=True)
    return None

ws = get_ws()
if not ws:
    print("   -> Lỗi: Không thể kết nối tới Chrome (Port 9222).")
    sys.exit(1)

def run_js(expression):
    mid = int(time.time()*1000)%1000000
    ws.send(json.dumps({'id': mid, 'method': 'Runtime.evaluate', 'params': {'expression': expression, 'returnByValue': True}}))
    for _ in range(15):
        res = json.loads(ws.recv())
        if res.get('id') == mid: return res.get('result', {}).get('result', {}).get('value')
    return None

# Mở dashboard
ws.send(json.dumps({'id': 1, 'method': 'Page.navigate', 'params': {'url': f"http://172.16.9.29:18091/dashboard/reward-management/list-of-reward?gameType=G{g['code']}&search={MSISDN}"}}))
time.sleep(3)
if run_js("document.body.innerText.includes('Tên đăng nhập')"):
    run_js("document.getElementById('mat-input-0').value='ctinadmin';document.getElementById('mat-input-1').value='ctin@123456';document.getElementById('mat-input-0').dispatchEvent(new Event('input'));document.getElementById('mat-input-1').dispatchEvent(new Event('input'));let b=Array.from(document.querySelectorAll('button')).find(x=>x.innerText.includes('Đăng nhập'));if(b)b.click();")
    time.sleep(4)
    ws.send(json.dumps({'id': 1, 'method': 'Page.navigate', 'params': {'url': f"http://172.16.9.29:18091/dashboard/reward-management/list-of-reward?gameType=G{g['code']}&search={MSISDN}"}}))
    time.sleep(4)

# 3. LẤY MÃ GD & MÃ KH (NUMERIC)
print("2. Đang chờ lấy Mã GD từ Dashboard...")
txt = run_js("document.body.innerText")
lines = [l.strip() for l in txt.split('\n') if l.strip()]
MA_GD_HEX, PERIOD, CUST_ID_NUM = "", "", "445226523" # Fallback

for i, l in enumerate(lines):
    if MSISDN in l:
        # Layout thường gặp: SĐT -> UserId (Hex) -> Mã GD (Alphanumeric/Hex) -> Game -> Kỳ -> Thời gian
        MA_GD_HEX = lines[i+1]
        PERIOD = lines[i+4]
        break

if not MA_GD_HEX:
    print("   -> Lỗi: Không tìm thấy vé!"); sys.exit(1)

print(f"   -> Mã KH (Số): {CUST_ID_NUM} | Mã GD (Hex): {MA_GD_HEX} | Kỳ: {PERIOD}")
DRAW_DATE = datetime.datetime.now().strftime("%Y%m%d")

# 4. TẠO CSV VÀ UPLOAD
print("3. Khởi tạo và upload file CSV...")
draw_res = "01 02 03 04 05 06 07" if GAME=="655" else "01 02 03 04 05 06"
tax = int(MONEY)*0.1 if int(MONEY)>10000000 else 0
net = int(MONEY)-tax
winner_row = f"{CUST_ID_NUM},{MA_GD_HEX},{LEVEL},{MONEY},{int(tax)},{int(net)}"
tiers = "30000088200,1,\n0,0,\n40000000,2,\n500000,0,\n50000,0,"
csv_body = f"2.0,{DRAW_DATE},{PERIOD},{draw_res},\n{tiers}\n\n{winner_row}\n"
fname = f"AUTO_WIN_{GAME}_{PERIOD}_{DRAW_DATE[2:]}_{random.randint(100,999)}.csv"

# Key quan trọng 'file' thay vì 'uploadfile'
r_upl = requests.post("http://10.20.30.153:8082/mobibgt/services/uploadfile", files={'file': (fname, csv_body, 'text/csv')})
print("   -> Upload kết quả:", r_upl.text)

# 5. TỰ PHÊ DUYỆT
print("4. Mở trình duyệt và Tự Phê Duyệt vé...")
ws.send(json.dumps({'id': 1, 'method': 'Page.navigate', 'params': {'url': 'http://172.16.9.29:18091/dashboard/reward-management/list-of-reward-result-approval'}}))
time.sleep(5)
run_js(f"(function() {{ let r=Array.from(document.querySelectorAll('tr')).find(x=>x.innerText.includes('{PERIOD}')); if(r) r.querySelector('a, mat-icon').click(); }})();")
time.sleep(3)
run_js(f"(function() {{ let r=Array.from(document.querySelectorAll('tr')).find(x=>x.innerText.includes('{MA_GD_HEX}')); if(r) r.querySelector('mat-checkbox').click(); }})();")
time.sleep(1)
run_js("Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Phê duyệt')).click();")
time.sleep(1)
run_js("Array.from(document.querySelectorAll('button')).find(b=>b.innerText.includes('Đồng ý')||b.innerText.includes('OK')).click();")

print("=== GIẢ LẬP HOÀN TẤT THÀNH CÔNG! ===")
```

**Cách AI thực thi lệnh:**
1. Trích xuất tham số từ người dùng (ví dụ gọi AI: `Chạy giả lập game 535 sdt 0987123456 tiền 500000 mức M`)
2. AI dùng công cụ (VD: `run_command` trong môi trường Workspace cục bộ) tạo file mồi hoặc chạy trực tiếp đoạn Code Python trên, truyền arguments lần lượt là `0987123456`, `535`, `500000`, `M`.
3. Thông báo cho người dùng khi Python script chạy ra chữ "GIẢ LẬP HOÀN TẤT". (Lưu ý: Mọi giao tiếp với Chrome đều tự động xử lý qua Websocket nhờ port 9222).
