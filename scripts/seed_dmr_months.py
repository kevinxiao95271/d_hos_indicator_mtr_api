"""
seed_dmr_months.py
将 D_MR 中 2020-01 月的病历记录复制到 2020-07 ~ 2020-12，
同时平移 B12（入院日期）、B15（出院日期）、B33（手术日期）。
老数据不改动，逐月插入前先检查目标月份是否已有数据。
"""
import sys, pymysql
from dateutil.relativedelta import relativedelta
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

DB = dict(host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
          user='root', password='Yiguo9527_', database='d_hos_claude_0251230',
          charset='utf8mb4', connect_timeout=30)

# 目标月份：2020-07 ~ 2020-12（每月对应从 2020-01 平移 +6 到 +11 月）
TARGET_MONTHS = {
    '2020-07': 6,
    '2020-08': 7,
    '2020-09': 8,
    '2020-10': 9,
    '2020-11': 10,
    '2020-12': 11,
}

BATCH = 500   # 每批插入行数


def shift_date_full(s, delta_months):
    """平移 'YYYY/M/D H:MM' 格式的日期时间字符串"""
    if not s:
        return s
    s = s.strip()
    try:
        dt = datetime.strptime(s, '%Y/%m/%d %H:%M')
        dt2 = dt + relativedelta(months=delta_months)
        return dt2.strftime('%-m/%d/%Y %H:%M') if sys.platform != 'win32' \
               else dt2.strftime('%Y/%-m/%d %H:%M')
    except ValueError:
        # 兼容 Windows（strftime 不支持 %-）
        try:
            dt = datetime.strptime(s, '%Y/%m/%d %H:%M')
            dt2 = dt + relativedelta(months=delta_months)
            return f"{dt2.year}/{dt2.month}/{dt2.day} {dt2.hour:02d}:{dt2.minute:02d}"
        except Exception:
            return s


def shift_date_only(s, delta_months):
    """平移 'YYYY/M/D' 格式的日期字符串"""
    if not s:
        return s
    s = s.strip()
    try:
        dt = datetime.strptime(s, '%Y/%m/%d')
        dt2 = dt + relativedelta(months=delta_months)
        return f"{dt2.year}/{dt2.month}/{dt2.day}"
    except Exception:
        return s


def main():
    conn = pymysql.connect(**DB)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ─── 获取所有列名 ────────────────────────────────────────────
    cur2 = conn.cursor()
    cur2.execute("SHOW COLUMNS FROM D_MR")
    col_names = [c[0] for c in cur2.fetchall()]
    cur2.close()
    cols_placeholder = ', '.join(['%s'] * len(col_names))
    cols_insert = ', '.join([f'`{c}`' for c in col_names])
    sql_insert = f"INSERT INTO D_MR ({cols_insert}) VALUES ({cols_placeholder})"
    print(f'共 {len(col_names)} 列\n')

    # ─── 读取 2020-01 全部记录 ───────────────────────────────────
    cur.execute("""
        SELECT * FROM D_MR
        WHERE STR_TO_DATE(B15, '%Y/%m/%d') BETWEEN '2020-01-01' AND '2020-01-31'
    """)
    src_rows = cur.fetchall()
    print(f'2020-01 源记录数: {len(src_rows)}\n')

    for month_str, delta in TARGET_MONTHS.items():
        # 检查目标月份是否已有数据
        y, m = month_str.split('-')
        start = f"{y}/{int(m)}/1"
        # 计算月末
        end_month = int(m) + 1 if int(m) < 12 else 1
        end_year = int(y) if int(m) < 12 else int(y) + 1
        end = f"{end_year}/{end_month}/1"

        cur2 = conn.cursor()
        cur2.execute("""
            SELECT COUNT(*) FROM D_MR
            WHERE STR_TO_DATE(B15, '%%Y/%%m/%%d') >= STR_TO_DATE(%s, '%%Y/%%m/%%d')
              AND STR_TO_DATE(B15, '%%Y/%%m/%%d') <  STR_TO_DATE(%s, '%%Y/%%m/%%d')
        """, (start, end))
        existing = cur2.fetchone()[0]
        cur2.close()

        if existing > 0:
            print(f'[SKIP] {month_str} 已有 {existing} 条，跳过')
            continue

        print(f'[START] 插入 {month_str}（+{delta} 月）...')
        batch = []
        inserted = 0
        for row in src_rows:
            new_row = []
            for col in col_names:
                val = row[col]
                if col == 'B12':
                    val = shift_date_full(val, delta)
                elif col == 'B15':
                    val = shift_date_full(val, delta)
                elif col == 'B33':
                    val = shift_date_only(val, delta)
                new_row.append(val)
            batch.append(tuple(new_row))

            if len(batch) >= BATCH:
                cur2 = conn.cursor()
                cur2.executemany(sql_insert, batch)
                conn.commit()
                inserted += len(batch)
                cur2.close()
                batch = []

        if batch:
            cur2 = conn.cursor()
            cur2.executemany(sql_insert, batch)
            conn.commit()
            inserted += len(batch)
            cur2.close()

        print(f'  [OK] {month_str} 插入 {inserted} 条')

    cur.close()
    conn.close()

    # ─── 验证结果 ────────────────────────────────────────────────
    print('\n── 验证 D_MR 月份分布 ─────────────────────────────────')
    conn2 = pymysql.connect(**DB)
    c = conn2.cursor()
    c.execute("""
        SELECT DATE_FORMAT(STR_TO_DATE(B15, '%Y/%m/%d'), '%Y-%m') AS ym, COUNT(*) as cnt
        FROM D_MR
        WHERE B15 IS NOT NULL AND B15 != ''
        GROUP BY ym ORDER BY ym
    """)
    for ym, cnt in c.fetchall():
        print(f'  {ym}  {cnt} 条')
    c.close(); conn2.close()


if __name__ == '__main__':
    main()
