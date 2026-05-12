import oracledb, time, datetime, sys

DB_DSN = "10.20.30.59:1521/vietlott"
MSISDN = sys.argv[1] if len(sys.argv) > 1 else "0787452568"
arg2 = sys.argv[2] if len(sys.argv) > 2 else "655"
GAME_TYPE = arg2 if arg2.startswith("G") else "G" + arg2
DRAW_ID = int(sys.argv[3]) if len(sys.argv) > 3 else 1016
PERIOD = sys.argv[4] if len(sys.argv) > 4 else "00479"

def force_issue():
    conn = oracledb.connect(user="vietlottsms_mobi", password="vietlottsms_mobi", dsn=DB_DSN)
    cur = conn.cursor()

    # Get Cust ID
    cur.execute("SELECT ID FROM CUSTOMER_ACCOUNT WHERE PHONE_NUMBER = :1 AND CUSTOMER_ACCOUNT_STATUS = 'ACTIVE' FETCH FIRST 1 ROWS ONLY", [MSISDN])
    cust_id = cur.fetchone()[0]

    # 2. Create TxID
    new_txid = f"FF{int(time.time())}"
    now = datetime.datetime.now()
    draw_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 3. Insert Ticket (Using required columns from sample row)
    print(f"Force issuing ticket with TxID {new_txid} for Cust {cust_id}...")
    cur.execute("""
        INSERT INTO TICKET (
            TRANSACTION_ID, CUSTOMER_ACCOUNT_ID, DRAW_ID, DRAW_ID_BGT, GAME_TYPE, 
            AMOUNT, TICKET_COST, ISSUE_STATUS, WINNING_STATUS, 
            CREATED_AT, UPDATED_AT,
            BGT_DATE_OF_SALE, DRAW_DATE,
            NUMBER_PANEL_BUY_SUCCESS
        ) VALUES (
            :txid, :cust_id, :draw_id, :period, :game, 
            10000, 10000, 'SUCCESS', 'WAIT', 
            SYSDATE, SYSDATE,
            :d_sale, :d_draw,
            1
        )
    """, {
        'txid': new_txid, 
        'cust_id': cust_id, 
        'draw_id': DRAW_ID, 
        'period': PERIOD,
        'game': GAME_TYPE,
        'd_sale': draw_date,
        'd_draw': draw_date
    })

    # 4. Deduct Balance
    cur.execute("UPDATE HMDT SET BALANCE = BALANCE - 10000 WHERE CUSTOMER_ACCOUNT_ID = :1", [cust_id])
    
    conn.commit()
    print("Ticket issued successfully in DB!")
    conn.close()
    return new_txid

if __name__ == "__main__":
    tx = force_issue()
    print(f"NEW_TXID={tx}")
