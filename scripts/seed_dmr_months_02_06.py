"""
seed_dmr_months_02_06.py
补全 2020-02 ~ 2020-06 月的 D_MR 记录（从 2020-01 平移）
"""
import sys, pymysql
from dateutil.relativedelta import relativedelta
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=30)

TARGET_MONTHS = {
    '2020-02': 1,
    '2020-03': 2,
    '2020-04': 3,
    '2020-05': 4,
    '2020-06': 5,
}
BATCH = 500


def shift_dt(s, delta_months):
    if not s: return s
    s = s.strip()
    try:
        dt = datetime.strptime(s, '%Y/%m/%d %H:%M')
        dt2 = dt + relativedelta(months=delta_months)
        return f"{dt2.year}/{dt2.month}/{dt2.day} {dt2.hour:02d}:{dt2.minute:02d}"
    except Exception:
        return s


def shift_d(s, delta_months):
    if not s: return s
    s = s.strip()
    try:
        dt = datetime.strptime(s, '%Y/%m/%d')
        dt2 = dt + relativedelta(months=delta_months)
        return f"{dt2.year}/{dt2.month}/{dt2.day}"
    except Exception:
        return s


def main():
    conn = pymysql.connect(**DB)

    cur_cols = conn.cursor()
    cur_cols.execute("SHOW COLUMNS FROM D_MR")
    col_names = [c[0] for c in cur_cols.fetchall()]
    cur_cols.close()

    cols_ph = ', '.join(['%s'] * len(col_names))
    cols_ins = ', '.join([f'`{c}`' for c in col_names])
    sql_insert = f"INSERT INTO D_MR ({cols_ins}) VALUES ({cols_ph})"

    cur_src = conn.cursor(pymysql.cursors.DictCursor)
    cur_src.execute("""
        SELECT * FROM D_MR
        WHERE STR_TO_DATE(B15, '%Y/%m/%d') BETWEEN '2020-01-01' AND '2020-01-31'
    """)
    src_rows = cur_src.fetchall()
    cur_src.close()
    print(f'源记录: {len(src_rows)} 条')

    for month_str, delta in TARGET_MONTHS.items():
        y, m = month_str.split('-')
        end_month = int(m) + 1 if int(m) < 12 else 1
        end_year = int(y) if int(m) < 12 else int(y) + 1

        cur_chk = conn.cursor()
        cur_chk.execute("""
            SELECT COUNT(*) FROM D_MR
            WHERE STR_TO_DATE(B15, '%%Y/%%m/%%d') >= STR_TO_DATE(%s, '%%Y/%%m/%%d')
              AND STR_TO_DATE(B15, '%%Y/%%m/%%d') <  STR_TO_DATE(%s, '%%Y/%%m/%%d')
        """, (f"{y}/{int(m)}/1", f"{end_year}/{end_month}/1"))
        existing = cur_chk.fetchone()[0]
        cur_chk.close()

        if existing > 0:
            print(f'[SKIP] {month_str} 已有 {existing} 条')
            continue

        print(f'[START] {month_str} (+{delta} 月)...', end=' ', flush=True)
        batch, inserted = [], 0
        for row in src_rows:
            new_row = []
            for col in col_names:
                v = row[col]
                if col == 'B12': v = shift_dt(v, delta)
                elif col == 'B15': v = shift_dt(v, delta)
                elif col == 'B33': v = shift_d(v, delta)
                new_row.append(v)
            batch.append(tuple(new_row))
            if len(batch) >= BATCH:
                c = conn.cursor(); c.executemany(sql_insert, batch); conn.commit(); c.close()
                inserted += len(batch); batch = []
        if batch:
            c = conn.cursor(); c.executemany(sql_insert, batch); conn.commit(); c.close()
            inserted += len(batch)
        print(f'插入 {inserted} 条')

    conn.close()

    # 验证
    conn2 = pymysql.connect(**DB)
    c = conn2.cursor()
    c.execute("""
        SELECT DATE_FORMAT(STR_TO_DATE(B15, '%Y/%m/%d'), '%Y-%m') AS ym, COUNT(*) as cnt
        FROM D_MR WHERE B15 IS NOT NULL AND B15 != ''
          AND STR_TO_DATE(B15, '%Y/%m/%d') BETWEEN '2020-01-01' AND '2020-12-31'
        GROUP BY ym ORDER BY ym
    """)
    print('\nD_MR 2020年各月:')
    for ym, cnt in c.fetchall():
        print(f'  {ym}  {cnt} 条')
    c.close(); conn2.close()


if __name__ == '__main__':
    main()
