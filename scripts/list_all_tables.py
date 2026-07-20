import sys, pymysql
sys.stdout.reconfigure(encoding='utf-8')
DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=15)
conn = pymysql.connect(**DB)
c = conn.cursor()
c.execute("SHOW TABLES")
tables = [r[0] for r in c.fetchall()]
print('数据库所有表:')
for t in tables:
    print(f'  {t}')
c.close(); conn.close()
