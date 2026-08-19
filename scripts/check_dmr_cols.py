#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymysql, sys, io, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = pymysql.connect(
    host='gz-cdb-bq7gk3k5.sql.tencentcdb.com', port=63606,
    user='root', password='Yiguo9527_', database='d_hos_indicator_mtr_20260720',
    charset='utf8mb4'
)
cur = conn.cursor()

# 查 d_mr 所有列名，找手术相关列
cur.execute("DESCRIBE d_mr")
cols = [row[0] for row in cur.fetchall()]

print("=== d_mr 手术相关列（C14/C15/C16/C17/C18/C19/C20/C21/C22/C23）===")
op_cols = [c for c in cols if re.match(r'C1[4-9]x\d+|C2[0-3]x\d+', c, re.I)]
for c in sorted(op_cols):
    print(f"  {c}")

print("\n=== d_mr 诊断相关列（C06/C07/C08）===")
diag_cols = [c for c in cols if re.match(r'C0[678]x\d+', c, re.I)]
print(f"  共 {len(diag_cols)} 列")
for c in sorted(diag_cols)[:10]:
    print(f"  {c}")

print("\n=== d_mr_other_1_20 表结构 ===")
try:
    cur.execute("DESCRIBE d_mr_other_1_20")
    for row in cur.fetchall():
        print(f"  {row[0]}  {row[1]}")
except Exception as e:
    print(f"  查询失败: {e}")

conn.close()
