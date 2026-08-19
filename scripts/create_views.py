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

cur.execute("SELECT DISTINCT del_flag FROM d_mr_other_1_20 LIMIT 5")
print("d_mr_other_1_20 del_flag:", cur.fetchall())

# 重建视图，将过滤条件改为 del_flag='N'
print("\n重建视图中...")

# QM_I_INPATIENT_INFO
cur.execute("""
CREATE OR REPLACE VIEW QM_I_INPATIENT_INFO AS
SELECT
    A48 AS PATIENTID, A49 AS VISITNO, A01 AS CASEID,
    A02 AS PATIENTNAME, A21C AS SEX, A11 AS BIRTHDAY, A13 AS AGE, A20N AS AGETYPE,
    A15C AS PAYKIND, A38C AS INWAY,
    B12 AS INDATE, B13C AS INDEPTCODE, B13C AS INDEPTNAME, B14 AS INWARDNAME,
    B15 AS OUTDATE, B16C AS OUTDEPTCODE, B16C AS OUTDEPTNAME, B16 AS OUTWARDNAME,
    B20 AS HOSPITALDAYS,
    C01C AS INDIAGCODE, C02N AS INDIAGNAME, B21C AS ADMISSIONDIAGNOSE,
    B22C AS DEPTCHIEF, B23C AS SENIORDOCT, B24C AS ATTENDINGDOCT,
    B25C AS DOCTNAME, B26C AS INDOCTNAME,
    B30C AS OUTWAY, B31 AS TRANSFERHOSPNAME, B34C AS CASEQUALITY,
    D01 AS TOTALFEE, D09 AS SELFPAYFEE, D11 AS GENERALFEE, D12 AS TREATFEE,
    D13 AS NURSEFEE, D15 AS PATHOLOGYFEE, D16 AS LABFEE, D17 AS IMAGEFEE,
    D21 AS SURGERYFEE, D22 AS ANESTHESIAFEE, D23 AS OPERATIONFEE,
    D26 AS WDRUGFEE, D27 AS ANTIBIOTICFEE, D28 AS CHINESEDRUGFEE, D30 AS BLOODFEE,
    create_time, update_time
FROM d_mr
WHERE del_flag = 'N'
""")
conn.commit()
print("✓ QM_I_INPATIENT_INFO")

# QM_I_HIS_INPATIENT_INFO
cur.execute("""
CREATE OR REPLACE VIEW QM_I_HIS_INPATIENT_INFO AS
SELECT
    A48 AS PATIENTID, A49 AS VISITNO, A02 AS PATIENTNAME,
    A21C AS SEX, A11 AS BIRTHDAY, A13 AS AGE, A20N AS AGETYPE,
    A15C AS PAYKIND, B12 AS INDATE, B13C AS INDEPTCODE, B13C AS INDEPTNAME,
    B15 AS OUTDATE, B16C AS OUTDEPTCODE, B16C AS OUTDEPTNAME,
    B20 AS HOSPITALDAYS, B30C AS OUTWAY, B25C AS DOCTCODE, B25C AS DOCTNAME,
    D01 AS TOTALFEE, A38C AS INWAYCODE, B34C AS CASEQUALITY
FROM d_mr
WHERE del_flag = 'N'
""")
conn.commit()
print("✓ QM_I_HIS_INPATIENT_INFO")

# QM_I_INPATIENT_OTHERDIAG（40组展开）
diag_parts = []
for i in range(1, 41):
    n = str(i).zfill(2)
    diag_parts.append(
        f"SELECT A48 AS PATIENTID, A49 AS VISITNO, "
        f"C06x{n}C AS P324, C07x{n}N AS P325, C08x{n}C AS P806, {i} AS SORT "
        f"FROM d_mr WHERE del_flag='N' AND C06x{n}C IS NOT NULL AND C06x{n}C != ''"
    )
sql = "CREATE OR REPLACE VIEW QM_I_INPATIENT_OTHERDIAG AS\n" + "\nUNION ALL\n".join(diag_parts)
cur.execute(sql)
conn.commit()
print("✓ QM_I_INPATIENT_OTHERDIAG")

# QM_I_INPATIENT_OPERATION（主手术 + d_mr_other_1_20 扩展手术）
op_parts = ["""SELECT m.A48 AS PATIENTID, m.A49 AS VISITNO,
    m.C14x01C AS OPCODE, m.C15x01N AS OPNAME, m.C16x01 AS OPDATE,
    m.C17x01 AS ANATYPE, m.C18x01 AS SURGEONDOCT, m.C19x01 AS SURGEONHELPER1,
    m.C20x01 AS SURGEONHELPER2, m.C21x01C AS INCISIONCLASS,
    m.C22x01C AS HEALCLASS, m.C23x01 AS ANAESTNAME, 1 AS SORT
FROM d_mr m
WHERE m.del_flag='N' AND m.C14x01C IS NOT NULL AND m.C14x01C != ''"""]

for i in range(1, 21):
    n = str(i).zfill(2)
    op_parts.append(
        f"SELECT o.A48 AS PATIENTID, o.A49 AS VISITNO, "
        f"o.C35x{n}C AS OPCODE, o.C36x{n}N AS OPNAME, o.C37x{n} AS OPDATE, "
        f"o.C38x{n} AS ANATYPE, o.C39x{n} AS SURGEONDOCT, o.C40x{n} AS SURGEONHELPER1, "
        f"o.C41x{n} AS SURGEONHELPER2, o.C42x{n}C AS INCISIONCLASS, "
        f"o.C43x{n}C AS HEALCLASS, o.C44x{n} AS ANAESTNAME, {i+1} AS SORT "
        f"FROM d_mr_other_1_20 o "
        f"WHERE o.del_flag='N' AND o.C35x{n}C IS NOT NULL AND o.C35x{n}C != ''"
    )
sql = "CREATE OR REPLACE VIEW QM_I_INPATIENT_OPERATION AS\n" + "\nUNION ALL\n".join(op_parts)
cur.execute(sql)
conn.commit()
print("✓ QM_I_INPATIENT_OPERATION")

# 验证数据
print("\n=== 各视图记录数 ===")
for v in ['QM_I_INPATIENT_INFO', 'QM_I_INPATIENT_OTHERDIAG', 'QM_I_INPATIENT_OPERATION', 'QM_I_HIS_INPATIENT_INFO']:
    cur.execute(f"SELECT COUNT(*) FROM {v}")
    print(f"  {v}: {cur.fetchone()[0]:,} 条")

print("\n=== QM_I_INPATIENT_INFO 前3条 ===")
cur.execute("SELECT PATIENTID, VISITNO, PATIENTNAME, INDATE, OUTDATE, HOSPITALDAYS FROM QM_I_INPATIENT_INFO LIMIT 3")
for row in cur.fetchall():
    print(f"  住院号:{row[0]}  次:{row[1]}  姓名:{row[2]}  入院:{row[3]}  出院:{row[4]}  天数:{row[5]}")

print("\n=== QM_I_INPATIENT_OTHERDIAG 前5条 ===")
cur.execute("SELECT PATIENTID, SORT, P324, P325 FROM QM_I_INPATIENT_OTHERDIAG ORDER BY PATIENTID, SORT LIMIT 5")
for row in cur.fetchall():
    print(f"  住院号:{row[0]}  诊断{row[1]}: {row[2]} {row[3]}")

print("\n=== QM_I_INPATIENT_OPERATION 前5条 ===")
cur.execute("SELECT PATIENTID, SORT, OPCODE, OPNAME, OPDATE FROM QM_I_INPATIENT_OPERATION LIMIT 5")
for row in cur.fetchall():
    print(f"  住院号:{row[0]}  手术{row[1]}: {row[2]} {row[3]} {row[4]}")

conn.close()
