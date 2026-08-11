#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymysql

conn = pymysql.connect(
    host='gz-cdb-bq7gk3k5.sql.tencentcdb.com',
    port=63606,
    user='root',
    password='Yiguo9527_',
    database='d_hos_indicator_mtr_20260720'
)

cur = conn.cursor()
cur.execute('SHOW TABLES')
tables = [t[0] for t in cur.fetchall()]

print("所有表:")
for t in tables:
    print(f"  {t}")

print("\nIndicator相关表:")
indicator_tables = [t for t in tables if 'indicator' in t.lower()]
for t in indicator_tables:
    print(f"  {t}")

cur.close()
conn.close()
