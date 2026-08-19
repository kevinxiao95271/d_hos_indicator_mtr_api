#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymysql, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(
    host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
    user='root', password='Yiguo9527_', database='d_hos_indicator_mtr_20260720',
    charset='utf8mb4'
)
cur = conn.cursor()

cur.execute("SELECT del_flag, COUNT(*) as cnt FROM d_mr GROUP BY del_flag")
print("d_mr del_flag 值分布:")
for row in cur.fetchall():
    print(f"  del_flag='{row[0]}'  count={row[1]}")

cur.execute("SELECT COUNT(*) FROM d_mr")
print(f"\nd_mr 总记录数: {cur.fetchone()[0]}")

# 看一条记录的实际字段
cur.execute("SELECT A48, A49, A02, B12, B15, del_flag FROM d_mr LIMIT 3")
print("\nd_mr 前3条原始数据:")
for row in cur.fetchall():
    print(f"  A48={row[0]}  A49={row[1]}  A02={row[2]}  B12={row[3]}  B15={row[4]}  del_flag={repr(row[5])}")

conn.close()
