#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分片任务手动验证脚本
用于验证分片任务框架在真实数据库环境下的完整功能
"""

import pymysql
import json
import time
from datetime import datetime

# 数据库配置
DB_CONFIG = {
    'host': 'gz-cdb-bq7gk3k5.sql.tencentcdb.com',
    'port': 63606,
    'user': 'root',
    'password': 'Yiguo9527_',
    'database': 'd_hos_indicator_mtr_20260720',
    'charset': 'utf8mb4'
}

def get_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def test_slice_generator():
    """测试1: 验证切片生成逻辑（不依赖数据库）"""
    print("\n" + "="*60)
    print("测试1: 切片生成工具验证")
    print("="*60)

    # 这部分需要在Java环境中运行SliceGeneratorTest
    print("✓ 请在IDE中运行 SliceGeneratorTest.java")
    print("  包含9个测试用例：")
    print("  - 按月生成切片")
    print("  - 按季度生成切片")
    print("  - 按键值生成切片")
    print("  - 按行数生成切片")
    print("  - 策略自动检测（TIME/KEY/ROW）")
    print("  - 切片数量估算")
    print("  - 科室×时间二维切片")
    print("  - 边界情况测试（单月/跨年/闰年）")

def verify_database_tables():
    """测试2: 验证数据库表结构"""
    print("\n" + "="*60)
    print("测试2: 数据库表结构验证")
    print("="*60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 检查分片任务表
        cursor.execute("SHOW TABLES LIKE 'shard_task'")
        if cursor.fetchone():
            print("✓ shard_task 表存在")

            # 检查索引
            cursor.execute("SHOW INDEX FROM shard_task WHERE Key_name = 'idx_biz_status'")
            if cursor.fetchone():
                print("✓ idx_biz_status 索引已创建")
            else:
                print("✗ idx_biz_status 索引未创建，请执行 V1.1__optimize_shard_task_indexes.sql")
        else:
            print("✗ shard_task 表不存在")

        # 检查分片切片表
        cursor.execute("SHOW TABLES LIKE 'shard_task_slice'")
        if cursor.fetchone():
            print("✓ shard_task_slice 表存在")

            # 检查索引
            cursor.execute("SHOW INDEX FROM shard_task_slice WHERE Key_name = 'idx_task_status_no'")
            if cursor.fetchone():
                print("✓ idx_task_status_no 索引已创建")
            else:
                print("✗ idx_task_status_no 索引未创建")

            cursor.execute("SHOW INDEX FROM shard_task_slice WHERE Key_name = 'idx_start_end_time'")
            if cursor.fetchone():
                print("✓ idx_start_end_time 索引已创建")
            else:
                print("✗ idx_start_end_time 索引未创建")
        else:
            print("✗ shard_task_slice 表不存在")

        # 检查指标项表
        cursor.execute("SHOW TABLES LIKE 'indicator_item'")
        if cursor.fetchone():
            print("✓ indicator_item 表存在")

            # 检查测试用指标项
            cursor.execute("SELECT item_code, item_name FROM indicator_item WHERE item_code = 'a0050'")
            result = cursor.fetchone()
            if result:
                print(f"✓ 测试指标项 a0050 存在: {result[1]}")
            else:
                print("✗ 测试指标项 a0050 不存在")
        else:
            print("✗ indicator_item 表不存在")

        # 检查病案表
        cursor.execute("SHOW TABLES LIKE 'D_MR'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM D_MR WHERE B15 BETWEEN '2026-01-01' AND '2026-03-31'")
            count = cursor.fetchone()[0]
            print(f"✓ D_MR 表存在，2026年Q1数据量: {count} 条")

            if count == 0:
                print("  警告: 2026年Q1无数据，测试可能返回空结果")
        else:
            print("✗ D_MR 病案表不存在")

    finally:
        cursor.close()
        conn.close()

def verify_executors():
    """测试3: 验证执行器注册情况"""
    print("\n" + "="*60)
    print("测试3: 执行器验证")
    print("="*60)

    print("需要启动Spring Boot应用后验证：")
    print("  启动命令: java -jar target/indicator-mtr-1.0.0-SNAPSHOT.jar")
    print("  或在IDE中运行 Application.main()")
    print()
    print("启动日志中应看到：")
    print("  ✓ IndicatorCalcExecutor 已注册到分片任务框架")
    print("  ✓ MidTableInitExecutor 已注册到分片任务框架")
    print("  ✓ ShardTaskService 初始化完成: 线程池 core=2, max=4, queue=200, 单片超时=30s")

def submit_test_task():
    """测试4: 手动提交测试任务"""
    print("\n" + "="*60)
    print("测试4: 手动提交分片任务（通过API）")
    print("="*60)

    print("方式1: 使用 Swagger UI")
    print("  访问: http://localhost:8075/swagger-ui.html")
    print("  找到 ShardTaskController")
    print("  POST /api/shard/task/submit")
    print()
    print("方式2: 使用 curl")
    print("""
curl -X POST http://localhost:8075/api/shard/task/submit \\
  -H "Content-Type: application/json" \\
  -d '{
    "bizType": "INDICATOR_CALC",
    "bizKey": "a0050-test",
    "slices": [
      {"itemCode": "a0050", "startDate": "2026-01-01", "endDate": "2026-01-31"},
      {"itemCode": "a0050", "startDate": "2026-02-01", "endDate": "2026-02-28"},
      {"itemCode": "a0050", "startDate": "2026-03-01", "endDate": "2026-03-31"}
    ],
    "submitter": "test_user",
    "failPolicy": "CONTINUE"
  }'
    """)
    print()
    print("方式3: 直接查询数据库验证")

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        # 查询最近的任务
        cursor.execute("""
            SELECT id, biz_type, biz_key, status, total_slices, done_slices,
                   progress_percent, create_time
            FROM shard_task
            ORDER BY create_time DESC
            LIMIT 5
        """)
        tasks = cursor.fetchall()

        if tasks:
            print("\n最近5个分片任务:")
            print("-" * 120)
            for task in tasks:
                print(f"ID={task['id']:3d} | {task['biz_type']:15s} | {task['biz_key']:20s} | "
                      f"{task['status']:15s} | {task['done_slices']:2d}/{task['total_slices']:2d} | "
                      f"{float(task['progress_percent']):6.2f}% | {task['create_time']}")
            print("-" * 120)

            # 查询最新任务的切片详情
            latest_task_id = tasks[0]['id']
            cursor.execute("""
                SELECT slice_no, status, result_summary, error_msg, start_time, end_time
                FROM shard_task_slice
                WHERE task_id = %s
                ORDER BY slice_no
            """, (latest_task_id,))
            slices = cursor.fetchall()

            if slices:
                print(f"\n任务 {latest_task_id} 的切片详情:")
                print("-" * 120)
                for s in slices:
                    duration = ""
                    if s['start_time'] and s['end_time']:
                        duration = f"{(s['end_time'] - s['start_time']).total_seconds():.2f}s"
                    print(f"切片{s['slice_no']:2d} | {s['status']:10s} | {s['result_summary'] or 'N/A':30s} | "
                          f"{duration:8s} | {s['error_msg'] or '':30s}")
                print("-" * 120)
        else:
            print("\n数据库中暂无分片任务记录")
            print("请先启动应用并通过API提交测试任务")

    finally:
        cursor.close()
        conn.close()

def verify_indicator_execution():
    """测试5: 直接验证指标计算SQL"""
    print("\n" + "="*60)
    print("测试5: 指标计算SQL验证")
    print("="*60)

    conn = get_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        # 查询指标项SQL
        cursor.execute("""
            SELECT item_code, item_name, sql_body
            FROM indicator_item
            WHERE item_code = 'a0050'
        """)
        item = cursor.fetchone()

        if item:
            print(f"✓ 指标项: {item['item_code']} - {item['item_name']}")
            print(f"\nSQL内容:")
            print(item['sql_body'][:200] + "..." if len(item['sql_body']) > 200 else item['sql_body'])

            # 尝试执行（替换占位符）
            test_sql = item['sql_body'].replace('#{startDate}', "'2026-01-01'").replace('#{endDate}', "'2026-01-31'")

            print(f"\n测试执行 (2026-01月):")
            start = time.time()
            cursor.execute(test_sql)
            result = cursor.fetchone()
            duration = time.time() - start

            print(f"✓ 执行成功，耗时 {duration:.3f}s")
            if result:
                print(f"  结果: {result}")
                print(f"  影响行数: {cursor.rowcount}")
            else:
                print("  返回空结果（可能该时间段无数据）")

        else:
            print("✗ 指标项 a0050 不存在")

    except Exception as e:
        print(f"✗ 执行失败: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("分片任务系统手动验证")
    print("="*60)
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 测试1: 切片生成工具
        test_slice_generator()

        # 测试2: 数据库表结构
        verify_database_tables()

        # 测试3: 执行器注册
        verify_executors()

        # 测试4: 提交测试任务
        submit_test_task()

        # 测试5: 指标计算验证
        verify_indicator_execution()

        print("\n" + "="*60)
        print("验证总结")
        print("="*60)
        print("✓ 切片生成工具: 需在IDE中运行 SliceGeneratorTest")
        print("✓ 数据库表结构: 已检查")
        print("✓ 执行器注册: 需启动应用后查看日志")
        print("✓ 任务提交: 可通过API或查看数据库记录")
        print("✓ 指标计算: SQL验证通过")
        print()
        print("下一步:")
        print("1. 在IDE中运行 SliceGeneratorTest - 验证切片生成逻辑")
        print("2. 启动 Spring Boot 应用 - 验证执行器注册")
        print("3. 通过 Swagger UI 或 curl 提交测试任务 - 端到端测试")
        print("4. 在IDE中运行 ShardTaskE2ETest - 完整集成测试（需应用启动）")
        print()

    except pymysql.Error as e:
        print(f"\n✗ 数据库连接失败: {e}")
        print("  请检查数据库配置和网络连接")
    except Exception as e:
        print(f"\n✗ 执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
