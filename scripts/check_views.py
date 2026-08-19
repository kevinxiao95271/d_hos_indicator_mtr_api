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

# 查所有视图
print("=== 数据库中的视图 ===")
cur.execute("""SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
               WHERE TABLE_SCHEMA='d_hos_indicator_mtr_20260720' AND TABLE_TYPE='VIEW'
               ORDER BY TABLE_NAME""")
views = cur.fetchall()
if views:
    for v in views:
        print(v[0])
else:
    print("(无视图)")

# 查所有表
print("\n=== 数据库中的表 ===")
cur.execute("""SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
               WHERE TABLE_SCHEMA='d_hos_indicator_mtr_20260720' AND TABLE_TYPE='BASE TABLE'
               ORDER BY TABLE_NAME""")
for row in cur.fetchall():
    print(row[0])

# 查 t_indicator_item 的列名
print("\n=== t_indicator_item 列名 ===")
cur.execute("DESCRIBE t_indicator_item")
for row in cur.fetchall():
    print(f"  {row[0]}  {row[1]}")

# 查前5条指标数据
print("\n=== 指标项示例（前5条）===")
cur.execute("SELECT id, item_code, item_name, data_source, query_sql FROM t_indicator_item LIMIT 5")
cols = [c[0] for c in cur.description]
print(" | ".join(cols))
for row in cur.fetchall():
    print(" | ".join(str(x)[:60] if x is not None else "NULL" for x in row))

# 查 d_mr 表结构
print("\n=== d_mr 表列名 ===")
cur.execute("DESCRIBE d_mr")
for row in cur.fetchall():
    print(f"  {row[0]}  {row[1]}")

conn.close()
