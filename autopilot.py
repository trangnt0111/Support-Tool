import oracledb, requests, time, os, sys, json, subprocess

# Tu dong fix loi Unicode cho Windows console
if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8')

DB_DSN = "10.20.30.59:1521/vietlott"
BUY_API = "http://10.20.30.153:8092/receive/json"
APPROVE_API = "http://172.16.9.29:18082/resultFile/approveResultFile"
LOGIN_API = "http://172.16.9.29:18082/auth/login"

def autopilot():
    if len(sys.argv) < 5:
        print("Usage: autopilot.py <GAME> <PERIOD> <PHONE> <MONEY> <LEVEL>")
        return

    game, period, phone, money, level = sys.argv[1:6]
    
    conn = oracledb.connect(user="vietlottsms_mobi", password="vietlottsms_mobi", dsn=DB_DSN)
    cur = conn.cursor()

    try:
        # --- BƯỚC 1: GỌI API MUA VÉ THỰC TẾ ---
        cur.execute("SELECT MAX(ID) FROM VIETLOTTSMS_MOBI.TICKET")
        last_id = cur.fetchone()[0] or 0
        
        numbers = "11 22 33 42 43 45" if game == "645" else "14 16 17 19 21 22 52"
        payload = {
            "agentcode": "MB",
            "shortCode": "9969",
            "content": f"{game} K1 S {numbers}",
            "msisdn": phone,
            "sessionId": "",
            "gw": "",
            "date": ""
        }
        
        print(f"[*] Đang gọi API mua vé cho {phone}...")
        r_buy = requests.post(BUY_API, json=payload, timeout=15)
        print(f"[OK] Mua vé: {r_buy.text.strip()}")

        # --- BƯỚC 2: ĐỢI VÉ PHÁT HÀNH ---
        print("[*] Đang đợi hệ thống phát hành...", end="", flush=True)
        new_tid, trans_id = None, None
        for _ in range(25):
            time.sleep(2)
            cur.execute("SELECT ID, TRANSACTION_ID FROM VIETLOTTSMS_MOBI.TICKET WHERE ID > :1 AND ISSUE_STATUS = 'COMPLETED' AND GAME_TYPE LIKE :2", [last_id, f"%{game}%"])
            res = cur.fetchone()
            if res:
                new_tid, trans_id = res
                break
            print(".", end="", flush=True)
        
        if not new_tid: raise Exception("\n[LỖI] Không thấy vé phát hành.")
        print(f"\n[OK] Vé mới: ID={new_tid} | TxID={trans_id}")

        # --- BƯỚC 3: NỔ GIẢI NINJA ---
        print(f"[*] Đang gọi Ninja v14 nổ giải {money}...")
        subprocess.run(["python", "ninja_gialap.py", game, money, level, phone, str(new_tid)])

        # --- BƯỚC 4: PHÊ DUYỆT TỰ ĐỘNG ---
        cur.execute("SELECT ID FROM VIETLOTTSMS_MOBI.RESULT_FILE ORDER BY ID DESC FETCH FIRST 1 ROWS ONLY")
        FID = cur.fetchone()[0]
        
        print(f"[*] Đang phê duyệt File ID {FID}...")
        sess = requests.Session()
        sess.post(LOGIN_API, json={'username':'ctinadmin','password':'ctin@123456'}, timeout=10)
        r_app = sess.post(APPROVE_API, json={'id': FID, 'listResult': [trans_id.lower()], 'status': 'APPROVED'}, timeout=10)
        
        # --- BƯỚC 5: XÁC MINH ---
        time.sleep(2)
        cur.execute("SELECT WINNING_STATUS FROM VIETLOTTSMS_MOBI.TICKET WHERE ID = :1", [new_tid])
        print(f"\n>>>> KẾT QUẢ: VÉ {new_tid} -> STATUS: {cur.fetchone()[0]} <<<<")

    except Exception as e:
        print(f"\n[LỖI] {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    autopilot()
