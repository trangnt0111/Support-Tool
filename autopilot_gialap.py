import subprocess, sys, time, oracledb, requests, json

# Integrated Autopilot v4 - Interactive Edition
# Ho tro: Nhap lieu tuong tac hoac qua tham so dong lenh

sys.stdout.reconfigure(encoding='utf-8')

DB_DSN = "10.20.30.59:1521/vietlott"
BUY_API = "http://10.20.30.153:8092/receive/json"
APPROVE_API = "http://172.16.9.29:18082/resultFile/approveResultFile"
LOGIN_API = "http://172.16.9.29:18082/auth/login"

def get_input(prompt, default):
    val = input(f"{prompt} [{default}]: ").strip()
    return val if val else default

def run_autopilot():
    # Neu khong co tham so, chuyen sang che do tuong tac
    if len(sys.argv) < 2:
        print("=== [ THIẾT LẬP GIẢ LẬP TRÚNG THƯỞNG ] ===")
        game  = get_input("1. Chọn Game (645/655)", "655")
        phone = get_input("2. Số điện thoại (MSISDN)", "0787452568")
        money = get_input("3. Số tiền trúng (Gross)", "11000000")
        level = get_input("4. Mức trúng (L/M/H)", "M")
    else:
        game  = sys.argv[1]
        money = sys.argv[2] if len(sys.argv) > 2 else "11000000"
        level = sys.argv[3] if len(sys.argv) > 3 else "M"
        phone = sys.argv[4] if len(sys.argv) > 4 else "0787452568"

    print(f"\n>>> Đang khởi tạo luồng cho {game} | SĐT: {phone} | Tiền: {money} | Mức: {level}")

    # 1. Tìm kỳ đang mở bán
    conn = oracledb.connect(user="vietlottsms_mobi", password="vietlottsms_mobi", dsn=DB_DSN)
    cur = conn.cursor()
    table = "G645_DRAW" if game == "645" else "G655_DRAW"
    
    cur.execute(f"SELECT ID, CODE FROM VIETLOTTSMS_MOBI.{table} WHERE WINNING_PANEL IS NULL ORDER BY DRAW_AT ASC FETCH FIRST 1 ROWS ONLY")
    draw_info = cur.fetchone()
    if not draw_info:
        print("Error: Không tìm thấy kỳ quay mở bán.")
        return
    DRAW_ID, DRAW_CODE = draw_info

    # 2. Mua vé
    numbers = "01 02 03 04 05 06"
    payload = {
        "agentcode": "MB", "shortCode": "9969",
        "content": f"{game} k1 s {numbers}",
        "msisdn": phone, "sessionId": "", "gw": "", "date": ""
    }
    cur.execute("SELECT MAX(ID) FROM VIETLOTTSMS_MOBI.TICKET")
    last_id = cur.fetchone()[0] or 0
    
    print(f"[*] Đang thực hiện mua vé cho {phone}...")
    requests.post(BUY_API, json=payload, timeout=10)

    new_tid = None
    trans_id = None
    for _ in range(30):
        time.sleep(2)
        cur.execute("SELECT ID, TRANSACTION_ID FROM VIETLOTTSMS_MOBI.TICKET WHERE ID > :1 AND ISSUE_STATUS = 'COMPLETED'", [last_id])
        res = cur.fetchone()
        if res:
            new_tid, trans_id = res
            break
        print(".", end="", flush=True)

    if not new_tid:
        print("\nError: Chưa thấy vé phát hành thành công.")
        return
    print(f"\n[+] Đã phát hành vé {new_tid} (TransID: {trans_id})")

    # 3. Upload File qua Ninja
    print(f"[*] Đang sinh file và upload cho kỳ {DRAW_CODE}...")
    subprocess.run(["python", "ninja_gialap.py", game, money, level, phone, str(new_tid)])
    
    time.sleep(2)
    cur.execute("SELECT ID FROM VIETLOTTSMS_MOBI.RESULT_FILE ORDER BY ID DESC FETCH FIRST 1 ROWS ONLY")
    FID = cur.fetchone()[0]
    conn.close()

    # 4. Phê duyệt tự động
    print(f"[*] Đang phê duyệt File ID {FID} trên Dashboard...")
    session = requests.Session()
    session.post(LOGIN_API, json={"username": "ctinadmin", "password": "ctin@123456"}, timeout=10)
    r_app = session.post(APPROVE_API, json={"id": FID, "listResult": [trans_id], "status": "APPROVED"}, timeout=10)
    
    print(f"\n[HOÀN THÀNH] Kết quả phê duyệt: {r_app.text}")
    print(f"Vui lòng kiểm tra tại: http://172.16.9.29:18091/dashboard/reward-management/list-of-reward?gameType=G{game}")

if __name__ == "__main__":
    run_autopilot()
