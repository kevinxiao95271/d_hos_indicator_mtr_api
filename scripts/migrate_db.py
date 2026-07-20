# -*- coding: utf-8 -*-
"""
数据库迁移脚本（服务端拷贝版）
两库在同一 MySQL 实例 → 全程 server-side SQL，不经过 Python 客户端传数据
依赖: pip install pymysql
"""
import sys, time
import pymysql
from pymysql.cursors import DictCursor

DB_HOST    = "gz-cdb-bq7gk3k5.sql.tencentcdb.com"
DB_PORT    = 63606
DB_USER    = "root"
DB_PASS    = "Yiguo9527_"
SRC_DB     = "d_hos_claude_0251230"
DST_DB     = "d_hos_indicator_mtr_20260720"

sys.stdout.reconfigure(encoding="utf-8")

def connect(database=None, timeout=600):
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=database, charset="utf8mb4", cursorclass=DictCursor,
        connect_timeout=30,
        read_timeout=timeout, write_timeout=timeout)

def main():
    t0 = time.time()
    print("=" * 55)
    print(f"  源库  : {SRC_DB}")
    print(f"  目标库: {DST_DB}  (server-side copy)")
    print("=" * 55)

    # ── 1. 建目标库 ──────────────────────────────────────────
    c = connect()
    with c.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DST_DB}` "
                    f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    c.commit(); c.close()
    print(f"[ OK ] 数据库 `{DST_DB}` 已就绪\n")

    # ── 2. 获取源库表列表 ─────────────────────────────────────
    src = connect(SRC_DB)
    with src.cursor() as cur:
        cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        rows = cur.fetchall()
    col = list(rows[0].keys())[0]
    tables = [r[col] for r in rows]
    print(f"[1/3] 复制表（共 {len(tables)} 张）…")

    # ── 3. 逐表：LIKE 建结构 + INSERT SELECT 拷数据 ───────────
    dst = connect(DST_DB, timeout=600)
    with dst.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        cur.execute("SET SESSION wait_timeout = 600")
        cur.execute("SET SESSION interactive_timeout = 600")

    for i, table in enumerate(tables, 1):
        print(f"  [{i:02d}/{len(tables)}] {table} ", end="", flush=True)
        ts = time.time()

        # 获取行数（快速）
        with src.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM `{SRC_DB}`.`{table}`")
            total = cur.fetchone()["n"]

        with dst.cursor() as cur:
            # 先删旧表
            cur.execute(f"DROP TABLE IF EXISTS `{table}`")
            # 用 LIKE 完整复制结构（含索引/约束）
            cur.execute(f"CREATE TABLE `{table}` LIKE `{SRC_DB}`.`{table}`")
            # 数据: 纯服务端，不经过 Python
            if total > 0:
                cur.execute(f"INSERT INTO `{table}` SELECT * FROM `{SRC_DB}`.`{table}`")
        dst.commit()
        print(f"→ {total} 行  ({time.time()-ts:.1f}s)")

    with dst.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    dst.commit()

    # ── 4. 复制存储过程 & 函数 ────────────────────────────────
    print("\n[2/3] 复制存储过程 & 函数…")
    with src.cursor() as cur:
        cur.execute("SELECT ROUTINE_TYPE, ROUTINE_NAME "
                    f"FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA='{SRC_DB}'")
        routines = cur.fetchall()

    if not routines:
        print("  (无)")
    else:
        for r in routines:
            rtype, rname = r["ROUTINE_TYPE"], r["ROUTINE_NAME"]
            try:
                with src.cursor() as cur:
                    cur.execute(f"SHOW CREATE {rtype} `{rname}`")
                    row = cur.fetchone()
                key = [k for k in row if k.lower().startswith("create")][0]
                ddl = row[key]
                if not ddl:
                    continue
                with dst.cursor() as cur:
                    cur.execute(f"DROP {rtype} IF EXISTS `{rname}`")
                    cur.execute(ddl)
                dst.commit()
                print(f"  {rtype} `{rname}` OK")
            except Exception as e:
                print(f"  {rtype} `{rname}` 跳过: {e}")

    # ── 5. 复制视图 ───────────────────────────────────────────
    print("\n[3/3] 复制视图…")
    with src.cursor() as cur:
        cur.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
        rows = cur.fetchall()
    col = list(rows[0].keys())[0] if rows else None
    views = [r[col] for r in rows] if col else []

    if not views:
        print("  (无)")
    else:
        for v in views:
            try:
                with src.cursor() as cur:
                    cur.execute(f"SHOW CREATE VIEW `{v}`")
                    ddl = cur.fetchone()["Create View"]
                with dst.cursor() as cur:
                    cur.execute(f"DROP VIEW IF EXISTS `{v}`")
                    cur.execute(ddl)
                dst.commit()
                print(f"  VIEW `{v}` OK")
            except Exception as e:
                print(f"  VIEW `{v}` 跳过: {e}")

    src.close(); dst.close()

    print(f"\n{'='*55}")
    print(f"  迁移完成！耗时 {time.time()-t0:.1f}s")
    print(f"  新库: {DST_DB}")
    print("=" * 55)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback; traceback.print_exc()
        sys.exit(1)
