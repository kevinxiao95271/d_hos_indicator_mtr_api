import sys
import pymysql
sys.stdout.reconfigure(encoding='utf-8')

conn = pymysql.connect(
    host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
    user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
    charset='utf8mb4', connect_timeout=15
)
cur = conn.cursor()

# D_MR 行数和B15分布
cur.execute("SELECT COUNT(*) FROM D_MR")
total = cur.fetchone()[0]
print(f'D_MR 总行数: {total}')

cur.execute("""
    SELECT DATE_FORMAT(STR_TO_DATE(B15, '%Y/%m/%d'), '%Y-%m') AS ym, COUNT(*) as cnt
    FROM D_MR
    WHERE B15 IS NOT NULL AND B15 != ''
    GROUP BY ym
    ORDER BY ym
""")
rows = cur.fetchall()
print('\nB15（出院日期）月份分布:')
for ym, cnt in rows:
    print(f'  {ym}  {cnt} 条')

# 看看 B12 的格式
cur.execute("SELECT B12, B15 FROM D_MR LIMIT 3")
print('\nB12/B15 样例:')
for row in cur.fetchall():
    print(f'  B12={row[0]}  B15={row[1]}')

cur.close(); conn.close()
