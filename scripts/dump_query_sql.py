import pymysql

conn = pymysql.connect(
    host='127.0.0.1', port=3306,
    user='root', password='Yiguo9527_',
    db='d_hos_indicator_mtr_20260720',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()
cur.execute("SELECT item_code, item_name, query_sql FROM t_indicator_item WHERE query_sql IS NOT NULL AND query_sql != '' ORDER BY item_code")
rows = cur.fetchall()
conn.close()

print(f"Total: {len(rows)}")
for r in rows:
    print(f"\n--- {r['item_code']}  {r['item_name']}")
    print(r['query_sql'])
