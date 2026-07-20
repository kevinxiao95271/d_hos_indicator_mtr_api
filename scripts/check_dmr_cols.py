import sys
import pymysql
sys.stdout.reconfigure(encoding='utf-8')

conn = pymysql.connect(
    host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
    user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
    charset='utf8mb4', connect_timeout=15
)
cur = conn.cursor()

# 获取 D_MR 所有列名
cur.execute("SHOW COLUMNS FROM D_MR")
cols = cur.fetchall()
print(f'D_MR 共 {len(cols)} 列\n')

# 找日期类字段（含日期格式样值）
cur.execute("SELECT * FROM D_MR LIMIT 1")
row = cur.fetchone()
col_names = [c[0] for c in cols]
print('疑似日期字段（值含 / 或 -）:')
for i, v in enumerate(row):
    if v and isinstance(v, str) and ('/' in str(v) or '-' in str(v)) and len(str(v)) >= 8:
        print(f'  {col_names[i]:8} = {v}')

cur.close(); conn.close()
