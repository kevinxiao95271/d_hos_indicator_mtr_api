import sys, pymysql
sys.stdout.reconfigure(encoding='utf-8')
DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=15)
conn = pymysql.connect(**DB)
c = conn.cursor()

# 查所有 d_mr 开头的表
c.execute("SHOW TABLES LIKE 'd_mr%'")
tables = [r[0] for r in c.fetchall()]
print('d_mr 开头的表:')
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM `{t}`")
    cnt = c.fetchone()[0]
    c.execute(f"SHOW COLUMNS FROM `{t}`")
    cols = [r[0] for r in c.fetchall()]
    has_a48 = 'A48' in cols and 'A49' in cols
    print(f'  {t:35} {cnt:6}行  {len(cols)}列  A48/A49={has_a48}')
    print(f'    前8列: {cols[:8]}')

c.close(); conn.close()
