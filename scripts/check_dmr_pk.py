import sys, pymysql, random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
sys.stdout.reconfigure(encoding='utf-8')

DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=30)

conn = pymysql.connect(**DB)
cur = conn.cursor(pymysql.cursors.DictCursor)

# ─── 1. 先看 2020-01 行样本确认格式 ───────────────────────────────
cur.execute("""
    SELECT B12, B15, B33 FROM D_MR
    WHERE STR_TO_DATE(B15, '%Y/%m/%d') BETWEEN '2020-01-01' AND '2020-01-31'
    LIMIT 5
""")
print('2020-01 样本:')
for r in cur.fetchall():
    print(f"  B12={r['B12']}  B15={r['B15']}  B33={r['B33']}")

# ─── 2. 取主键列名（看是否有 auto_increment） ─────────────────────
cur2 = conn.cursor()
cur2.execute("SHOW COLUMNS FROM D_MR")
all_cols = cur2.fetchall()
pk_col = None
for c in all_cols:
    if c[3] == 'PRI':
        pk_col = c[0]
        break
print(f'\n主键列: {pk_col}')
col_names = [c[0] for c in all_cols]
non_pk_cols = [c for c in col_names if c != pk_col]
print(f'总列数: {len(col_names)}, 非主键列数: {len(non_pk_cols)}')
cur2.close()

conn.close()
print('\n准备就绪，运行主脚本...')
