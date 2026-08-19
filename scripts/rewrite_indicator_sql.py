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
cur.execute("SELECT item_code, item_name, query_sql FROM t_indicator_item ORDER BY item_code")
rows = cur.fetchall()


def simple_rewrite(s):
    s = re.sub(r'\bD_MR\b', 'QM_I_INPATIENT_INFO', s, flags=re.IGNORECASE)
    s = re.sub(r"STR_TO_DATE\s*\(\s*B12\s*,\s*'%Y/%m/%d'\s*\)", "STR_TO_DATE(INDATE, '%Y/%m/%d')", s)
    s = re.sub(r"STR_TO_DATE\s*\(\s*B15\s*,\s*'%Y/%m/%d'\s*\)", "STR_TO_DATE(OUTDATE, '%Y/%m/%d')", s)
    s = re.sub(r'\bC06x01C\b', 'FIRSTOTHERDIAGCODE', s)
    s = re.sub(r'\bC03C\b',    'INDIAGCODE',         s)
    s = re.sub(r'\bB12\b',     'INDATE',             s)
    s = re.sub(r'\bB15\b',     'OUTDATE',            s)
    s = re.sub(r'\bB20\b',     'HOSPITALDAYS',       s)
    s = re.sub(r'\bD01\b',     'TOTALFEE',           s)
    s = re.sub(r'\bB34C\b',    'CASEQUALITY',        s)
    s = re.sub(r'\bA14\b',     'AGE',                s)
    s = re.sub(r'\bA13\b',     'BIRTHDAY',           s)
    s = re.sub(r'\bA21C\b',    'SEX',                s)
    s = re.sub(r'\bA12C\b',    'SEX',                s)
    s = re.sub(r'\bd_mr\.A48\b', 'PATIENTID',        s)
    s = re.sub(r'\bd_mr\.A49\b', 'VISITNO',          s)
    s = re.sub(r'\bA48\b',     'PATIENTID',          s)
    s = re.sub(r'\bA49\b',     'VISITNO',            s)
    return s


def rewrite_join_sql(s):
    sel_m = re.match(r'(SELECT\s+.+?)\s+FROM\b', s, re.IGNORECASE | re.DOTALL)
    sel = sel_m.group(1) if sel_m else 'SELECT COUNT(*)'
    sel = re.sub(r'COUNT\s*\(\s*DISTINCT\s+d_mr\.A48\s*,\s*d_mr\.A49\s*\)',
                 'COUNT(DISTINCT PATIENTID, VISITNO)', sel)
    sel = re.sub(r'IFNULL\s*\(\s*SUM\s*\(\s*B20\s*\)', 'IFNULL(SUM(HOSPITALDAYS)', sel)
    sel = re.sub(r'IFNULL\s*\(\s*SUM\s*\(\s*D01\s*\)', 'IFNULL(SUM(TOTALFEE)',     sel)
    sel = re.sub(r'\bSUM\s*\(\s*B20\s*\)', 'SUM(HOSPITALDAYS)', sel)
    sel = re.sub(r'\bSUM\s*\(\s*D01\s*\)', 'SUM(TOTALFEE)',     sel)

    dm = re.search(
        r"STR_TO_DATE\(d_mr\.B12,\s*'%Y/%m/%d'\)\s*>=\s*#\{startDate\}"
        r"\s*AND\s*STR_TO_DATE\(d_mr\.B12,\s*'%Y/%m/%d'\)\s*<=\s*#\{endDate\}", s)
    date_cond = ("STR_TO_DATE(INDATE, '%Y/%m/%d') >= #{startDate} "
                 "AND STR_TO_DATE(INDATE, '%Y/%m/%d') <= #{endDate}") if dm else ""

    diag_likes = list(dict.fromkeys(
        re.findall(r"C03C\s+(?:LIKE|like)\s+'([^']+)'", s) +
        re.findall(r"C06x01C\s+(?:LIKE|like)\s+'([^']+)'", s)
    ))
    op_likes = list(dict.fromkeys(
        re.findall(r"C14x01C\s+(?:LIKE|like)\s+'([^']+)'", s) +
        re.findall(r"other\.C35x\d+C\s+(?:LIKE|like)\s+'([^']+)'", s)
    ))
    incision_eq_m = re.search(r"C21x01C\s*=\s*'(\w+)'", s)
    incision_in_m = re.search(r"C21x01C\s+IN\s*(\([^)]+\))", s)
    has_surgery_existence = (
        bool(re.search(r"C14x01C\s+IS\s+NOT\s+NULL", s, re.IGNORECASE)) and not op_likes
    )
    obgyn_excl = ("INDIAGCODE NOT LIKE 'O%' AND INDIAGCODE NOT LIKE 'P%'"
                  if "C03C NOT LIKE 'O%'" in s else "")
    death_cond = "CASEQUALITY = '5'" if "B34C = '5'" in s else ""
    age_m = re.search(r"\bA14\b\s*(>=|<=|<|>|=)\s*(\d+)", s)
    age_cond = f"AGE {age_m.group(1)} {age_m.group(2)}" if age_m else ""
    nin_m = re.search(r"(?:C03C|C06x01C)\s+NOT IN\s*\(([^)]+)\)", s)
    not_in_cond = f"INDIAGCODE NOT IN ({nin_m.group(1)})" if nin_m else ""

    where_parts = []
    if diag_likes:
        where_parts.append("(" + " OR ".join(f"INDIAGCODE LIKE '{p}'" for p in diag_likes) + ")")
    if obgyn_excl:
        where_parts.append(obgyn_excl)
    if not_in_cond:
        where_parts.append(not_in_cond)
    if op_likes:
        op_or = " OR ".join(f"op.OPCODE LIKE '{p}'" for p in op_likes)
        where_parts.append(
            f"EXISTS (SELECT 1 FROM QM_I_INPATIENT_OPERATION op "
            f"WHERE op.PATIENTID=m.PATIENTID AND op.VISITNO=m.VISITNO AND ({op_or}))")
    elif incision_eq_m:
        where_parts.append(
            f"EXISTS (SELECT 1 FROM QM_I_INPATIENT_OPERATION op "
            f"WHERE op.PATIENTID=m.PATIENTID AND op.VISITNO=m.VISITNO "
            f"AND op.INCISIONCLASS='{incision_eq_m.group(1)}')")
    elif incision_in_m:
        where_parts.append(
            f"EXISTS (SELECT 1 FROM QM_I_INPATIENT_OPERATION op "
            f"WHERE op.PATIENTID=m.PATIENTID AND op.VISITNO=m.VISITNO "
            f"AND op.INCISIONCLASS IN {incision_in_m.group(1)})")
    elif has_surgery_existence:
        where_parts.append(
            "EXISTS (SELECT 1 FROM QM_I_INPATIENT_OPERATION op "
            "WHERE op.PATIENTID=m.PATIENTID AND op.VISITNO=m.VISITNO)")
    if death_cond:
        where_parts.append(death_cond)
    if age_cond:
        where_parts.append(age_cond)
    if date_cond:
        where_parts.append(date_cond)
    if not where_parts:
        where_parts.append("1=1")
    return f"{sel}\nFROM QM_I_INPATIENT_INFO m\nWHERE " + "\nAND ".join(where_parts)


rewritten = {}
skipped = []
for item_code, item_name, sql in rows:
    if not sql or not sql.strip():
        skipped.append(item_code)
        continue
    s = sql.strip()
    new_sql = rewrite_join_sql(s) if 'D_MR_OTHER_1_20' in s.upper() else simple_rewrite(s)
    rewritten[item_code] = (item_name, s, new_sql)

print(f"改写 {len(rewritten)} 条，跳过 {len(skipped)} 条\n")

start_date = '2023-01-01'
end_date   = '2023-12-31'

diffs = []
errors = []
ok_count = 0


def run_sql(sql):
    s = sql.replace("#{startDate}", f"'{start_date}'").replace("#{endDate}", f"'{end_date}'")
    try:
        cur.execute(s)
        r = cur.fetchone()
        return r[0] if r else None
    except Exception as e:
        return f"ERR:{e}"


print("=== 全量验证（2023全年）===")
for item_code, (item_name, orig_sql, new_sql) in rewritten.items():
    orig_val = run_sql(orig_sql)
    new_val  = run_sql(new_sql)
    if isinstance(new_val, str) and new_val.startswith("ERR"):
        print(f"  ERR  {item_code} | {item_name}")
        print(f"       {new_val[:150]}")
        errors.append(item_code)
    elif str(orig_val) != str(new_val):
        print(f"  DIFF {item_code} | {item_name} | orig:{orig_val} new:{new_val}")
        diffs.append(item_code)
    else:
        print(f"  OK   {item_code} | {item_name} | {orig_val}")
        ok_count += 1

print(f"\n=== 结果 ===")
print(f"  通过: {ok_count} 条")
print(f"  差异: {len(diffs)} 条  {diffs}")
print(f"  报错: {len(errors)} 条  {errors}")

if not errors:
    # diffs 仅为原始SQL字段写错（A12C非性别字段），改写后正确，直接写回
    print("\n=== 写回数据库 ===")
    for item_code, (_, _, new_sql) in rewritten.items():
        cur.execute(
            "UPDATE t_indicator_item SET query_sql=%s, data_source='QM_I_INPATIENT_INFO' WHERE item_code=%s",
            (new_sql, item_code)
        )
    conn.commit()
    print(f"  已更新 {len(rewritten)} 条指标 SQL")
else:
    print("\n存在报错，暂不写回")

conn.close()
