import oracledb, requests, time, os, sys, json

# Tu dong fix loi Unicode cho Windows console
if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8')

DB_DSN = "10.20.30.59:1521/vietlott"
BUY_API = "http://10.20.30.51:8092/receive/json"
UPLOAD_API = "http://10.20.30.51:8082/vnptbgt/services/uploadfile"

EXPORT_DIR = "d:\\2026\\VLT Antigravity\\scripts\\giả lập trúng thưởng\\exports"

def calculate_tax(money):
    # Thue 10% cho phan vượt quá 10 trieu
    if money > 10000000:
        return int((money - 10000000) * 0.1)
    return 0

def autopilot_vina():
    if len(sys.argv) < 5:
        print("Usage: autopilot_vina.py <GAME> <PHONE> <MONEY> <LEVEL>")
        return

    # V10.0: Bo tham so PERIOD vi script se tu dong nhan dien tu ve
    game_arg, phone, money_str, level = sys.argv[1:5]
    money = int(money_str)
    
    if not os.path.exists(EXPORT_DIR): os.makedirs(EXPORT_DIR)

    conn = oracledb.connect(user="vietlott_sms", password="vietlott_sms", dsn=DB_DSN)
    cur = conn.cursor()

    try:
        # --- BƯỚC 1: LẤY ID LỚN NHẤT ĐỂ THEO DÕI VÉ MỚI ---
        cur.execute("SELECT MAX(ID) FROM VIETLOTT_SMS.TICKET")
        last_id = cur.fetchone()[0] or 0
        
        # --- BƯỚC 2: MUA VÉ (VN AGENT) ---
        payload = {
            "agentcode": "VN", "shortCode": "9969",
            "content": f"{game_arg} K1 S TC",
            "msisdn": phone, "sessionId": "", "gw": "", "date": ""
        }
        
        print(f"\n>>> SIÊU AUTOPILOT VINA v10.0 (Prize: {money:,} VNĐ) <<<")
        print(f"[*] Đang mua vé {game_arg} cho {phone}...")
        r_buy = requests.post(BUY_API, json=payload, timeout=15)
        print(f"[OK) Mua vé: {r_buy.text.strip()}")

        # --- BƯỚC 3: ĐỢI VÉ VÀ NHẬN DIỆN KỲ QUAY ---
        print("[*] Đang đợi phát hành vé...", end="", flush=True)
        new_tid, trans_id, bgt_id = None, None, None
        period, date_file, date_body = None, None, None
        
        for _ in range(30):
            time.sleep(2)
            cur.execute("""
                SELECT t.ID, t.TRANSACTION_ID, c.BGT_ACCOUNT_ID, t.DRAW_ID_BGT, 
                       TO_CHAR(t.DRAW_DATE, 'YYMMDD'), TO_CHAR(t.DRAW_DATE, 'YYYYMMDD'), t.GAME_TYPE
                FROM VIETLOTT_SMS.TICKET t 
                JOIN VIETLOTT_SMS.CUSTOMER_ACCOUNT c ON t.CUSTOMER_ACCOUNT_ID = c.ID
                WHERE t.ID > :1 AND c.PHONE_NUMBER = :2 AND t.ISSUE_STATUS = 'COMPLETED'
            """, [last_id, phone])
            res = cur.fetchone()
            if res:
                new_tid, trans_id, bgt_id, period, date_file, date_body, actual_game = res
                break
            print(".", end="", flush=True)
        
        if not new_tid: raise Exception("\n[LỖI] Không thấy vé phát hành thành công hoặc sai SĐT.")
        print(f"\n[OK] Nhận diện vé: ID={new_tid} | TxID={trans_id} | Kỳ: {period} | Ngày: {date_body}")
        
        # --- BƯỚC 4: LẤY KẾT QUẢ VÀ SEQ FILE ---
        # Tim Seq file dua tren ky vua nhan dien
        cur.execute("SELECT ORIGIN_NAME FROM VIETLOTT_SMS.RESULT_FILE WHERE ORIGIN_NAME LIKE :1 ORDER BY ID DESC FETCH FIRST 1 ROWS ONLY", [f"%{period}%"])
        res_file_latest = cur.fetchone()
        next_seq = 1
        if res_file_latest:
            try:
                last_name = res_file_latest[0]
                last_seq = int(last_name.split("_")[-2])
                next_seq = (last_seq % 100) + 1
            except: next_seq = 1

        # Tim Panel (Neu co)
        table = 'G645_DRAW' if actual_game == 'G645' else 'G655_DRAW'
        cur.execute(f"SELECT WINNING_PANEL FROM VIETLOTT_SMS.{table} WHERE CODE = :1", [period])
        row_draw = cur.fetchone()
        db_panel = row_draw[0] if row_draw else None
        
        fname = f"TicketsWinning_55555555_LOTTO{actual_game[-3:]}_{period}_{date_file}_{next_seq:03d}_100.csv"
        fpath = os.path.join(EXPORT_DIR, fname)
        
        # Cau truc CSV
        if actual_game == 'G645':
            tiers = ["12368271000,1,", "10000000,1,", "300000,0,", "30000,1,"]
            blank_lines = 1 
            panel = (db_panel.replace(",", " ") if db_panel else "01 02 03 04 05 06")
        else:
            tiers = ["30000088200,1,", "0,0,", "40000000,2,", "500000,0,", "50000,0,"]
            blank_lines = 1 
            panel = (db_panel.replace(",", " ") if db_panel else "01 02 03 04 05 06 45")
        
        tax = calculate_tax(money)
        net = money - tax
        
        csv_content = f"2.0,{date_body},{period},{panel},\n"
        for t in tiers: csv_content += f"{t}\n"
        csv_content += "\n" * blank_lines
        csv_content += f"{bgt_id},{trans_id.lower()},L,{money},{tax},{net}"
        
        with open(fpath, "w", encoding="utf-8") as f: f.write(csv_content)
        print(f"[OK] Đã lưu file trúng thưởng: {fname}")
        print("-" * 50)
        print(csv_content.strip())
        print("-" * 50)
        
        # --- BƯỚC 5: UPLOAD BÁO TRÚNG ---
        print(f"[*] Đang up file báo trúng ({money:,} VNĐ)...")
        r_up = requests.post(UPLOAD_API, files={'file': (fname, csv_content.encode('utf-8'), 'text/csv')}, timeout=15)
        print(f"[OK) Upload: {r_up.text.strip()}")
        
        # --- BƯỚC 6: XÁC MINH ---
        print("[*] Đang kiểm tra trạng thái trúng thưởng trên DS Dự Thưởng...", end="", flush=True)
        final_status = "WAIT"
        for _ in range(15):
            time.sleep(2)
            cur.execute("SELECT WINNING_STATUS FROM VIETLOTT_SMS.TICKET WHERE ID = :1", [new_tid])
            result_row = cur.fetchone()
            final_status = result_row[0] if result_row else "NOT_FOUND"
            if final_status == 'WIN':
                break
            print(".", end="", flush=True)
        
        print(f"\n[OK] KẾT QUẢ CUỐI CÙNG: Vé {trans_id} đang ở trạng thái '{final_status}'. ✨")

    except Exception as e:
        print(f"\n[LỖI] {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    autopilot_vina()

