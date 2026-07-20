import sys, pymysql
sys.stdout.reconfigure(encoding='utf-8')

DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=15)

conn = pymysql.connect(**DB)
c = conn.cursor()

# 所有 D_ 开头的表
c.execute("SHOW TABLES LIKE 'D_%'")
tables = [r[0] for r in c.fetchall()]
print('D_ 开头的表:')
for t in tables:
    c.execute(f"SELECT COUNT(*) FROM `{t}`")
    cnt = c.fetchone()[0]
    c.execute(f"SHOW COLUMNS FROM `{t}`")
    cols = c.fetchall()
    print(f'  {t:35} {cnt:6} 行  {len(cols)} 列')

# 2020-01 行数
c.execute("SELECT COUNT(*) FROM D_MR WHERE B15 LIKE '2020/1/%'")
print(f'\nD_MR 2020-01 行数: {c.fetchone()[0]}')

# 附属表是否有 A48/A49
for t in tables:
    if t == 'D_MR': continue
    c.execute(f"SHOW COLUMNS FROM `{t}`")
    col_names = [r[0] for r in c.fetchall()]
    has_key = 'A48' in col_names and 'A49' in col_names
    print(f'  {t} A48/A49: {has_key}  列: {col_names[:8]}...')

c.close(); conn.close()
