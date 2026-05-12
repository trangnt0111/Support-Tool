import oracledb, sys

conn = oracledb.connect(user="vietlott_sms", password="vietlott_sms", dsn="10.20.30.59:1521/vietlott")
cur = conn.cursor()

print("--- TICKET COLS ---")
cur.execute("SELECT COLUMN_NAME FROM ALL_TAB_COLUMNS WHERE TABLE_NAME = 'TICKET'")
print([r[0] for r in cur.fetchall()])

print("\n--- SAMPLE TICKET ---")
cur.execute("SELECT * FROM VIETLOTT_SMS.TICKET ORDER BY ID DESC FETCH FIRST 1 ROWS ONLY")
r = cur.fetchone()
if r:
    colnames = [d[0] for d in cur.description]
    print(dict(zip(colnames, r)))

conn.close()
