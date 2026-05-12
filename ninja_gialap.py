import oracledb, requests, time, os, sys, random, json

# Tu dong fix loi Unicode cho Windows console
if sys.platform == 'win32': sys.stdout.reconfigure(encoding='utf-8')

t0 = time.time()
DB_DSN = "10.20.30.59:1521/vietlott"
UPLOAD_API = "http://10.20.30.153:8082/mobibgt/services/uploadfile"

# ===== 1. PARSE ARGS =====
if len(sys.argv) < 6:
    print("Usage: ninja_gialap.py <GAME> <MONEY> <LEVEL> <PHONE> <TICKET_ID> [WIN_NUMS]")
    sys.exit(1)

GAME     = sys.argv[1] 
MONEY    = sys.argv[2]
LEVEL    = sys.argv[3]
MSISDN   = sys.argv[4]
TID      = int(sys.argv[5])
WIN_NUMS = sys.argv[6] if len(sys.argv) > 6 else None

G_DATA = {
    "645": {
        "csv": "LOTTO645", 
        "table": "G645_DRAW", 
        "tiers": [
            "12368271000,1,", 
            "10000000,1,", 
            "300000,0,", 
            "30000,1,"
        ],
        "default_panel": "01 02 03 04 05 44",
        "blank_lines": 1 # Winner at Line 7
    },
    "655": {
        "csv": "LOTTO655", 
        "table": "G655_DRAW", 
        "tiers": [
            "30000088200,1,",
            "0,0,",
            "40000000,2,",
            "500000,0,",
            "50000,0,"
        ],
        "default_panel": "14 16 17 19 21 22 52",
        "blank_lines": 2 # Winner at Line 9
    }
}
g = G_DATA.get(GAME)

# ===== 2. GET DB DATA =====
conn = oracledb.connect(user="vietlottsms_mobi", password="vietlottsms_mobi", dsn=DB_DSN)
cur = conn.cursor()

# 2.1 Get Ticket Info
cur.execute("SELECT TRANSACTION_ID, DRAW_ID FROM VIETLOTTSMS_MOBI.TICKET WHERE ID=:1", [TID])
res_t = cur.fetchone()
if not res_t:
    print(f"Error: Ticket ID {TID} not found.")
    sys.exit(1)
HEX_TRANS_ID, DRAW_ID = res_t

# 2.2 Get BGT_ACCOUNT_ID from CUSTOMER_ACCOUNT
cur.execute("SELECT BGT_ACCOUNT_ID FROM VIETLOTTSMS_MOBI.CUSTOMER_ACCOUNT WHERE PHONE_NUMBER=:1 AND ROWNUM=1", [MSISDN])
res_bgt = cur.fetchone()
if not res_bgt:
    print(f"Error: Không tìm thấy BGT_ACCOUNT_ID cho MSISDN {MSISDN}.")
    sys.exit(1)
BGT_ID = str(res_bgt[0])
print(f"[DB] BGT_ACCOUNT_ID = {BGT_ID}")

# 2.2 Get Draw Info
cur.execute(f"SELECT CODE, TO_CHAR(DRAW_AT, 'YYMMDD'), TO_CHAR(DRAW_AT, 'YYYYMMDD'), WINNING_PANEL FROM VIETLOTTSMS_MOBI.{g['table']} WHERE ID=:1", [DRAW_ID])
period_data = cur.fetchone()
if not period_data:
    print(f"Error: Draw ID {DRAW_ID} not found in {g['table']}.")
    sys.exit(1)
PERIOD, DATE_FILE, DATE_BODY, DB_WIN_PANEL = period_data

# ===== 3. FILENAME GEN =====
cur.execute("SELECT NVL(MAX(TO_NUMBER(SUBSTR(ORIGIN_NAME, INSTR(ORIGIN_NAME, '_', -1, 2) + 1, 3))), 0) FROM VIETLOTTSMS_MOBI.RESULT_FILE WHERE ORIGIN_NAME LIKE :1", [f"%{PERIOD}%"])
max_idx = cur.fetchone()[0]
next_num = int(max_idx) + 1
fname = f"TicketsWinning_88888888_{g['csv']}_{PERIOD}_{DATE_FILE}_{next_num:03d}_100.csv"

# ===== 4. BUILD CSV CONTENT =====
final_win_panel = (DB_WIN_PANEL.replace(",", " ") if DB_WIN_PANEL else g['default_panel'])

# Format Line 1: Header
body = f"2.0,{DATE_BODY},{PERIOD},{final_win_panel},\n"
# Lines 2-N: Tiers
for t in g['tiers']:
    body += f"{t}\n"

# Blank Lines (1 for 645, 2 for 655)
body += "\n" * g['blank_lines']

# Winner Row 
gross = int(MONEY)
# Logic thue: Neu > 10M thi thue 10% cua tong (Theo mau anh gui), neu < 10M thi de 10k test theo mau 645
tax = int(gross * 0.1) if gross >= 10000000 else 10000
net = gross - tax
winner_row = f"{BGT_ID},{HEX_TRANS_ID.lower()},{LEVEL},{gross},{tax},{net}"

csv_body_bytes = (body + winner_row).encode('utf-8')
os.makedirs("exports", exist_ok=True)
with open(f"exports/{fname}", "wb") as f: f.write(csv_body_bytes)

print(f"[{time.time()-t0:.1f}s] Filename: {fname}")
print(f"[{time.time()-t0:.1f}s] Winner Row at Line {6 + len(g['tiers']) - 5 + g['blank_lines'] + 1}: {winner_row.strip()}")

# ===== 5. UPLOAD =====
r = requests.post(UPLOAD_API, files={'file': (fname, csv_body_bytes, 'text/csv')}, timeout=15)
print(f"[{time.time()-t0:.1f}s] Upload Result: {r.text.strip()}")

time.sleep(2)
cur.execute("SELECT ID, STATUS, ERROR_REASON FROM RESULT_FILE WHERE ORIGIN_NAME=:1 ORDER BY ID DESC", [fname])
res = cur.fetchone()
conn.close()

if res:
    print(f"--- STATUS (FILE ID: {res[0]}) ---")
    print(f"STATUS: {res[1]} | ERROR: {res[2]}")
    if res[1] == 'IMPORTED':
         print(f"Target URL: http://172.16.9.29:18091/dashboard/reward-management/list-of-reward-result-approval/approval-of-reward-results/{res[0]}?isReadOnly=false")
