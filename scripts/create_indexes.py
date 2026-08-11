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

cursor = conn.cursor()

print("正在创建索引...")

# 索引1
try:
    cursor.execute("""
        ALTER TABLE shard_task
        ADD INDEX idx_biz_status (`biz_type`, `status`, `create_time`)
    """)
    print("✓ shard_task.idx_biz_status 创建成功")
except Exception as e:
    if "Duplicate key name" in str(e):
        print("✓ shard_task.idx_biz_status 已存在")
    else:
        print(f"✗ shard_task.idx_biz_status 失败: {e}")

# 索引2
try:
    cursor.execute("""
        ALTER TABLE shard_task_slice
        ADD INDEX idx_task_status_no (`task_id`, `status`, `slice_no`)
    """)
    print("✓ shard_task_slice.idx_task_status_no 创建成功")
except Exception as e:
    if "Duplicate key name" in str(e):
        print("✓ shard_task_slice.idx_task_status_no 已存在")
    else:
        print(f"✗ shard_task_slice.idx_task_status_no 失败: {e}")

# 索引3
try:
    cursor.execute("""
        ALTER TABLE shard_task_slice
        ADD INDEX idx_start_end_time (`start_time`, `end_time`)
    """)
    print("✓ shard_task_slice.idx_start_end_time 创建成功")
except Exception as e:
    if "Duplicate key name" in str(e):
        print("✓ shard_task_slice.idx_start_end_time 已存在")
    else:
        print(f"✗ shard_task_slice.idx_start_end_time 失败: {e}")

conn.commit()

# 验证
print("\n索引验证:")
cursor.execute("SHOW INDEX FROM shard_task WHERE Key_name = 'idx_biz_status'")
if cursor.fetchone():
    print("✓ shard_task.idx_biz_status 已生效")

cursor.execute("SHOW INDEX FROM shard_task_slice WHERE Key_name = 'idx_task_status_no'")
if cursor.fetchone():
    print("✓ shard_task_slice.idx_task_status_no 已生效")

cursor.execute("SHOW INDEX FROM shard_task_slice WHERE Key_name = 'idx_start_end_time'")
if cursor.fetchone():
    print("✓ shard_task_slice.idx_start_end_time 已生效")

cursor.close()
conn.close()

print("\n索引优化完成！")
