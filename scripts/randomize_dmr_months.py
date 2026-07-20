"""
randomize_dmr_months.py
对 2020-02 ~ 2020-12 每月随机删除 20%~70% 的 D_MR 记录，
使各月数据量不同，重算后指标值自然出现波动。
2020-01（原始数据）不动。
"""
import sys, pymysql, random
sys.stdout.reconfigure(encoding='utf-8')

DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=30)

random.seed(42)

DELETE_RATIOS = {
    '2020-02': random.uniform(0.20, 0.70),
    '2020-03': random.uniform(0.20, 0.70),
    '2020-04': random.uniform(0.20, 0.70),
    '2020-05': random.uniform(0.20, 0.70),
    '2020-06': random.uniform(0.20, 0.70),
    '2020-07': random.uniform(0.20, 0.70),
    '2020-08': random.uniform(0.20, 0.70),
    '2020-09': random.uniform(0.20, 0.70),
    '2020-10': random.uniform(0.20, 0.70),
    '2020-11': random.uniform(0.20, 0.70),
    '2020-12': random.uniform(0.20, 0.70),
}

print('各月计划删除比例:')
for m, r in DELETE_RATIOS.items():
    print(f'  {m}  {r*100:.1f}%')
print()

conn = pymysql.connect(**DB)

for month_str, ratio in DELETE_RATIOS.items():
    y, m = month_str.split('-')
    like_prefix = f"{int(y)}/{int(m)}/%"   # e.g. "2020/2/%" or "2020/10/%"

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM D_MR WHERE B15 LIKE %s", (like_prefix,))
    total = cur.fetchone()[0]
    to_delete = int(total * ratio)

    cur.execute("DELETE FROM D_MR WHERE B15 LIKE %s LIMIT %s", (like_prefix, to_delete))
    conn.commit()
    cur.close()

    cur2 = conn.cursor()
    cur2.execute("SELECT COUNT(*) FROM D_MR WHERE B15 LIKE %s", (like_prefix,))
    remaining = cur2.fetchone()[0]
    cur2.close()
    print(f'  {month_str}: 原 {total} 条 → 删 {to_delete} → 剩 {remaining} 条  ({ratio*100:.1f}%)')

conn.close()

# 验证分布
print('\n── 最终 D_MR 2020 年各月数量 ──────────────────────')
conn2 = pymysql.connect(**DB)
c = conn2.cursor()
c.execute("""
    SELECT DATE_FORMAT(STR_TO_DATE(SUBSTRING_INDEX(B15,' ',1), '%Y/%m/%d'), '%Y-%m') AS ym, COUNT(*) as cnt
    FROM D_MR
    WHERE B15 LIKE '2020/%'
    GROUP BY ym ORDER BY ym
""")
for ym, cnt in c.fetchall():
    bar = '█' * (cnt // 100)
    print(f'  {ym}  {cnt:5} 条  {bar}')
c.close(); conn2.close()
