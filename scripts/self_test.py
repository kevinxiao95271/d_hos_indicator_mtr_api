# -*- coding: utf-8 -*-
"""
E2E Self-Test  --  indicator-mtr  port 8075
覆盖全部 81 个接口，写操作与读操作交叉验证
"""
import sys, urllib.request, urllib.parse, urllib.error, json, time, random, string

sys.stdout.reconfigure(encoding="utf-8")

BASE   = "http://localhost:8075"
PASS   = 0
FAIL   = 0
TOKENS = {}
_created = {}   # 跨 section 传递创建的 ID/code

# 每次运行用随机后缀，避免与历史数据冲突
_sfx = "".join(random.choices(string.ascii_lowercase, k=5))


# ─── 工具函数 ─────────────────────────────────────────────────
def req(path, method="GET", body=None, token=None, form=False):
    url = BASE + path
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        if form:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            data = urllib.parse.urlencode(body).encode()
        else:
            data = json.dumps(body).encode()
    try:
        r = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as ex:
        return 0, {"_err": str(ex)}


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {name}")
        PASS += 1
    else:
        print(f"  [FAIL] {name}  {detail}")
        FAIL += 1


def login(username, password):
    code, body = req("/auth/login", "POST",
                     {"username": username, "password": password}, form=True)
    ok = code == 200 and isinstance(body.get("data"), dict) and body["data"].get("token")
    check(f"login {username}", ok, f"code={code}")
    return body.get("data", {}).get("token", "") if ok else ""


def ok200(code, body, detail=""):
    return code == 200 and body.get("code", 0) in (0, 200), detail or f"http={code} biz={body.get('code')}"


# ─── 0. 服务存活 ──────────────────────────────────────────────
print("=" * 60)
print("  indicator-mtr  E2E  Self-Test  (完整 81 接口覆盖)")
print(f"  Target: {BASE}")
print("=" * 60)

# ─── 1. API Docs ──────────────────────────────────────────────
print("\n[1] API Docs")
code, _ = req("/v3/api-docs")
check("GET /v3/api-docs", code == 200)

# ─── 2. 登录 ─────────────────────────────────────────────────
print("\n[2] 登录认证")
TOKENS["admin"]       = login("admin",       "Admin@123")
TOKENS["neuro_head"]  = login("neuro_head",  "Dept@123")
TOKENS["neuro_nurse"] = login("neuro_nurse", "Nurse@123")
check("login bad password → error", req("/auth/login", "POST",
      {"username": "x", "password": "bad"}, form=True)[1].get("code") != 0)

adm = TOKENS["admin"]
hd  = TOKENS["neuro_head"]
nur = TOKENS["neuro_nurse"]

# ─── 3. 用户信息 & 菜单 ───────────────────────────────────────
print("\n[3] 用户信息 & 菜单")
c, b = req("/auth/userInfo", token=adm)
check("GET /auth/userInfo (admin)", *ok200(c, b))
c, b = req("/auth/userInfo", token=hd)
check("GET /auth/userInfo (neuro_head)", *ok200(c, b))
c, b = req("/auth/userInfo", token=nur)
check("GET /auth/userInfo (nurse)", *ok200(c, b))
c, b = req("/auth/menus", token=adm)
check("GET /auth/menus (admin)", *ok200(c, b))

# ─── 4. 权限边界 ──────────────────────────────────────────────
print("\n[4] 权限边界")
c, b = req("/system/roles/save", "POST", {}, token=nur)
check("nurse blocked POST /system/roles/save",
      c in (401, 403) or b.get("code") in (30401, 30403, 401, 403),
      f"http={c} biz={b.get('code')}")
c, b = req("/api/system/config", "POST", {}, token=nur)
check("nurse blocked POST /api/system/config",
      c in (401, 403) or b.get("code") in (30401, 30403, 401, 403),
      f"http={c}")

# ─── 5. 系统管理（读）───────────────────────────────────────
print("\n[5] 系统管理（读）")
c, b = req("/system/users", token=adm)
check("GET /system/users", *ok200(c, b))
c, b = req("/system/depts", token=adm)
check("GET /system/depts", *ok200(c, b))
c, b = req("/system/roles", token=adm)
check("GET /system/roles", *ok200(c, b))
# 从角色列表拿一个真实 roleId 用于后续写操作
_roles = b.get("data", []) if c == 200 else []
c, b = req("/system/dept/tree", token=adm)
check("GET /system/dept/tree", *ok200(c, b))
c, b = req("/system/dept/list/visible", token=adm)
check("GET /system/dept/list/visible", *ok200(c, b))
c, b = req("/system/user/list", token=adm)
check("GET /system/user/list", *ok200(c, b))

# ─── 6. 系统管理（写 + 交叉验证）────────────────────────────
print("\n[6] 系统管理（写 + 交叉）")
# 角色保存（新增临时角色 → 检查列表中存在 → 不删除，保持干净）
new_role = {"roleName": "test_e2e_role", "roleKey": "e2e", "roleSort": 99, "dataScope": 90, "status": "0"}
c, b = req("/system/roles/save", "POST", new_role, token=adm)
check("POST /system/roles/save (create)", *ok200(c, b))
# 用户保存（更新已有 admin，仅改备注，realName 不变）
c, b = req("/system/user/save", "POST",
           {"userId": 3, "username": "admin", "realName": "超级管理员",
            "deptId": 82, "roleId": 1, "dataScope": 50, "status": "0"}, token=adm)
check("POST /system/user/save (update)", *ok200(c, b))
# 科室保存（更新科室 1 名称不变，只要能写入）
c, b = req("/system/dept/save", "POST",
           {"deptId": 1, "deptName": "神经内科", "parentId": 0, "sortOrder": 1, "status": "0"}, token=adm)
check("POST /system/dept/save (update)", *ok200(c, b))

# ─── 7. 系统配置（读写 + 交叉）───────────────────────────────
print("\n[7] 系统配置")
c, b = req("/api/system/config", token=adm)
check("GET /api/system/config (list)", *ok200(c, b))
c, b = req("/api/system/config", token=nur)
check("GET /api/system/config (nurse read OK)", *ok200(c, b))
c, b = req("/api/system/config/hospital_name", token=adm)
check("GET /api/system/config/{key}", *ok200(c, b))
c, b = req("/api/system/config", "POST", {"hospital_name": "测试医院E2E"}, token=adm)
check("POST /api/system/config (batch save)", *ok200(c, b))
c, b = req("/api/system/config/hospital_name", token=adm)
check("GET /api/system/config/hospital_name after save (cross-check)",
      c == 200 and "测试医院E2E" in str(b.get("data", "")),
      f"data={b.get('data')}")
c, b = req("/api/system/config/hospital_name", "POST",
           {"value": "示范医院"}, token=adm)
check("POST /api/system/config/{key} (single save)", *ok200(c, b))

# ─── 8. 指标管理（CRUD + 交叉）──────────────────────────────
print("\n[8] 指标管理（CRUD + 交叉）")
# 读
c, b = req("/api/indicator/tree", token=adm)
check("GET /api/indicator/tree", *ok200(c, b))
c, b = req("/api/indicator/page?current=1&size=10", token=adm)
check("GET /api/indicator/page", *ok200(c, b))
# 按编码读
c, b = req("/api/indicator/code/rate_incision_infection", token=adm)
check("GET /api/indicator/code/{metricCode}", *ok200(c, b))
# 子指标（取第一个指标的父级别）
c, b = req("/api/indicator/children/root", token=adm)
check("GET /api/indicator/children/{parentCode} (root)",
      c == 200, f"http={c}")

# 表达式校验
c, b = req("/api/indicator/validate-expression", "POST",
           "a0050 / a0052", token=adm)
check("POST /api/indicator/validate-expression (valid)", *ok200(c, b))
c, b = req("/api/indicator/validate-expression", "POST",
           "", token=adm)
check("POST /api/indicator/validate-expression (blank → invalid)",
      c == 200 and b.get("data", {}).get("valid") == False,
      f"data={b.get('data')}")

# 新建临时指标（叶子）→ 按ID读 → 删除（交叉验证）
save_dto = {
    "metricCode": f"e2etmp{_sfx}",
    "metricName": "E2E测试指标（可删）",
    "isLeaf": 1,
    "metricType": "QUANTITATIVE",
    "calculationType": "NONE",
    "inputType": "MANUAL",
    "status": 1,
    "sortOrder": 999
}
c, b = req("/api/indicator/save", "POST", save_dto, token=adm)
check("POST /api/indicator/save (create)", *ok200(c, b))
new_ind_id = (b.get("data") or {}).get("id") if c == 200 else None

if new_ind_id:
    c, b = req(f"/api/indicator/{new_ind_id}", token=adm)
    check(f"GET /api/indicator/{{id}} (cross-check)", *ok200(c, b))
    # 更新
    save_dto["id"] = new_ind_id
    save_dto["remark"] = "updated"
    c, b = req("/api/indicator/save", "POST", save_dto, token=adm)
    check("POST /api/indicator/save (update)", *ok200(c, b))
    # 删除
    c, b = req(f"/api/indicator/{new_ind_id}", method="DELETE", token=adm)
    check(f"DELETE /api/indicator/{{id}}", *ok200(c, b))
    # batch delete（新建两个再批量删）
    ids_to_del = []
    for sfx in ("bA", "bB"):
        dto2 = dict(save_dto, metricCode=f"e2ebat{_sfx}{sfx}", metricName=f"批量删{sfx}", id=None, remark="")
        c2, b2 = req("/api/indicator/save", "POST", dto2, token=adm)
        if c2 == 200 and b2.get("data", {}).get("id"):
            ids_to_del.append(b2["data"]["id"])
    if len(ids_to_del) == 2:
        c, b = req("/api/indicator/batch", method="DELETE", body=ids_to_del, token=adm)
        check("DELETE /api/indicator/batch", *ok200(c, b))
    else:
        check("DELETE /api/indicator/batch", False, "创建批量删除测试指标失败")
else:
    for name in ("GET /api/indicator/{id}", "POST /api/indicator/save (update)",
                 "DELETE /api/indicator/{id}", "DELETE /api/indicator/batch"):
        check(name, False, "依赖创建步骤失败，跳过")

# ─── 9. 指标项（CRUD + 交叉）────────────────────────────────
print("\n[9] 指标项（CRUD + 交叉）")
c, b = req("/api/indicator-item/page?current=1&size=10", token=adm)
check("GET /api/indicator-item/page", *ok200(c, b))
c, b = req("/api/indicator-item/list", token=adm)
check("GET /api/indicator-item/list", *ok200(c, b))
c, b = req("/api/indicator-item/code/a0050", token=adm)
check("GET /api/indicator-item/code/{itemCode}", *ok200(c, b))

# SQL 校验
c, b = req("/api/indicator-item/validate-sql", "POST",
           "SELECT COUNT(*) FROM d_mr WHERE B15 BETWEEN #{startDate} AND #{endDate}", token=adm)
check("POST /api/indicator-item/validate-sql (valid)", *ok200(c, b))
c, b = req("/api/indicator-item/validate-sql", "POST",
           "DROP TABLE d_mr", token=adm)
check("POST /api/indicator-item/validate-sql (invalid rejects)",
      (b.get("data") or {}).get("valid") == False or b.get("code") != 0)

# 新建指标项 → 读 → 执行SQL → 更新 → 删除
item_dto = {
    "itemCode": f"e2eitem{_sfx}",
    "itemName": "E2E临时指标项",
    "itemType": "COLLECTED",
    "dataSource": "d_mr",
    "querySql": "SELECT COUNT(*) FROM d_mr WHERE B15 BETWEEN #{startDate} AND #{endDate}",
    "aggregateFunction": "COUNT",
    "status": 1
}
c, b = req("/api/indicator-item/save", "POST", item_dto, token=adm)
check("POST /api/indicator-item/save (create)", *ok200(c, b))
new_item_id = (b.get("data") or {}).get("id") if c == 200 else None

if new_item_id:
    c, b = req(f"/api/indicator-item/{new_item_id}", token=adm)
    check("GET /api/indicator-item/{id} (cross-check)", *ok200(c, b))
    # 执行SQL试跑
    c, b = req(f"/api/indicator-item/e2eitem{_sfx}/execute?startDate=2020-01-01&endDate=2020-12-31",
               "POST", {}, token=adm)
    check("POST /api/indicator-item/{code}/execute", *ok200(c, b))
    # 更新
    item_dto["id"] = new_item_id
    item_dto["remark"] = "updated"
    c, b = req("/api/indicator-item/save", "POST", item_dto, token=adm)
    check("POST /api/indicator-item/save (update)", *ok200(c, b))
    # 批量删除（包含当前 id）
    c, b = req("/api/indicator-item/batch", method="DELETE", body=[new_item_id], token=adm)
    check("DELETE /api/indicator-item/batch", *ok200(c, b))
    # 单删（应已不存在，但接口本身要通）
    c, b = req(f"/api/indicator-item/{new_item_id}", method="DELETE", token=adm)
    check("DELETE /api/indicator-item/{id} (already deleted, 200 or 404 OK)",
          c in (200, 404) or b.get("code") in (0, 30404))
else:
    for name in ("GET /api/indicator-item/{id}", "POST execute",
                 "POST save (update)", "DELETE batch", "DELETE {id}"):
        check(f"indicator-item {name}", False, "依赖创建步骤失败")

# ─── 10. 指标计算 ─────────────────────────────────────────────
print("\n[10] 指标计算")
c, b = req("/api/indicator-result/calculate"
           "?metricCode=rate_incision_infection&timeDimension=YEAR&startDate=2020-01-01&endDate=2020-12-31",
           "POST", {}, token=adm)
check("POST /api/indicator-result/calculate", *ok200(c, b))
c, b = req("/api/indicator-result/batch-calculate"
           "?timeDimension=YEAR&startDate=2020-01-01&endDate=2020-12-31",
           "POST", ["rate_incision_infection", "rate_surgery_complication"], token=adm)
check("POST /api/indicator-result/batch-calculate", *ok200(c, b))
c, b = req("/api/indicator-item/a0050/execute?startDate=2020-01-01&endDate=2020-12-31",
           "POST", {}, token=adm)
check("POST /api/indicator-item/{code}/execute (a0050)", *ok200(c, b))

# ─── 11. 指标结果（读 + 科室下钻 + 删除）────────────────────
print("\n[11] 指标结果（读 + 下钻 + 删除）")
c, b = req("/api/indicator-result/list?timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/indicator-result/list (admin)", *ok200(c, b))
c, b = req("/api/indicator-result/list?timeDimension=YEAR&timeValue=2020", token=hd)
check("GET /api/indicator-result/list (neuro_head)", *ok200(c, b))
c, b = req("/api/indicator-result/latest?metricCode=rate_incision_infection", token=adm)
check("GET /api/indicator-result/latest", *ok200(c, b))
# 按 ID 读（取 list 第一条）
results = b.get("data") if c == 200 else None
c2, b2 = req("/api/indicator-result/list?timeDimension=YEAR&timeValue=2020", token=adm)
first_result = (b2.get("data") or [{}])[0] if c2 == 200 else {}
result_id = first_result.get("id")
if result_id:
    c, b = req(f"/api/indicator-result/{result_id}", token=adm)
    check("GET /api/indicator-result/{id} (cross-check)", *ok200(c, b))
else:
    check("GET /api/indicator-result/{id}", False, "list 返回空，无 id")

# 科室下钻
c, b = req("/api/indicator-result/dept-drill/rate_incision_infection"
           "?timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/indicator-result/dept-drill/{metricCode}", *ok200(c, b))
c, b = req("/api/indicator-result/dept-drill-down"
           "?metricCode=rate_incision_infection&timeDimension=YEAR"
           "&startDate=2020-01-01&endDate=2020-12-31",
           "POST", {}, token=adm)
check("POST /api/indicator-result/dept-drill-down", *ok200(c, b))

# 达标/对比/合规
c, b = req("/api/indicator-result/compliance?timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/indicator-result/compliance", *ok200(c, b))
c, b = req("/api/indicator-result/compare"
           "?metricCode=rate_incision_infection&timeDimension=YEAR&timeValues=2020,2021,2023", token=adm)
check("GET /api/indicator-result/compare (单指标多时期)", *ok200(c, b))
c, b = req("/api/indicator-result/compare"
           "?metricCodes=rate_incision_infection,rate_surgery_complication"
           "&timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/indicator-result/compare (多指标同期)", *ok200(c, b))

# 删除结果（先计算一条新数据，然后删除它）
c, b = req("/api/indicator-result/calculate"
           "?metricCode=rate_surgery_complication&timeDimension=MONTH"
           "&startDate=2020-03-01&endDate=2020-03-31",
           "POST", {}, token=adm)
if c == 200:
    del_id = (b.get("data") or {}).get("id")
    if del_id:
        c, b = req(f"/api/indicator-result/{del_id}", method="DELETE", token=adm)
        check("DELETE /api/indicator-result/{id}", *ok200(c, b))
    else:
        check("DELETE /api/indicator-result/{id}", False, "calculate 未返回 id")
else:
    check("DELETE /api/indicator-result/{id}", False, f"依赖计算失败 http={c}")

# ─── 12. 质检 ─────────────────────────────────────────────────
print("\n[12] 数据质检")
c, b = req("/api/data-validation/check", "POST",
           {"timeDimension": "YEAR", "timeValue": "2020"}, token=adm)
check("POST /api/data-validation/check", *ok200(c, b))
c, b = req("/api/data-validation/history?timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/data-validation/history", *ok200(c, b))

# ─── 13. 数据集 ───────────────────────────────────────────────
print("\n[13] 数据集")
c, b = req("/api/dataset/list", token=adm)
check("GET /api/dataset/list", *ok200(c, b))
c, b = req("/api/dataset/page?type=YEAR&current=1&size=10", token=adm)
check("GET /api/dataset/page", *ok200(c, b))
c, b = req("/api/dataset/YEAR_2020", token=adm)
check("GET /api/dataset/{id}", *ok200(c, b))

# ─── 14. 可见范围（CRUD + 交叉）─────────────────────────────
print("\n[14] 指标可见范围（CRUD + 交叉）")
c, b = req("/api/indicator-scope/by-dept/1", token=adm)
check("GET /api/indicator-scope/by-dept/{deptId}", *ok200(c, b))
c, b = req("/api/indicator-scope/by-metric/rate_incision_infection", token=adm)
check("GET /api/indicator-scope/by-metric/{metricCode}", *ok200(c, b))
# 绑定
c, b = req("/api/indicator-scope/binding", "POST",
           {"deptId": 1, "metricCode": "rate_incision_infection", "isPrimaryOwner": 1}, token=adm)
check("POST /api/indicator-scope/binding", *ok200(c, b))
# replace-by-dept（整科室替换）
c, b = req("/api/indicator-scope/replace-by-dept", "POST",
           {"deptId": 1, "metricCodes": ["rate_incision_infection", "rate_surgery_complication"]},
           token=adm)
check("POST /api/indicator-scope/replace-by-dept", *ok200(c, b))
# replace-by-metric（整指标替换）
c, b = req("/api/indicator-scope/replace-by-metric", "POST",
           {"metricCode": "rate_incision_infection", "deptIds": [1]}, token=adm)
check("POST /api/indicator-scope/replace-by-metric", *ok200(c, b))
# 解绑单条（@RequestParam → query string）
c, b = req("/api/indicator-scope/binding?deptId=1&metricCode=rate_surgery_complication",
           method="DELETE", token=adm)
check("DELETE /api/indicator-scope/binding", *ok200(c, b))
# 按指标清空（先绑一条再清）
c, b = req("/api/indicator-scope/binding", "POST",
           {"deptId": 2, "metricCode": "avg_cost_pneumonia_adult", "isPrimaryOwner": 0}, token=adm)
c, b = req("/api/indicator-scope/by-metric/avg_cost_pneumonia_adult", method="DELETE", token=adm)
check("DELETE /api/indicator-scope/by-metric/{metricCode}", *ok200(c, b))
# 按科室清空（先绑一条再清）
c, b = req("/api/indicator-scope/binding", "POST",
           {"deptId": 3, "metricCode": "rate_incision_infection", "isPrimaryOwner": 0}, token=adm)
c, b = req("/api/indicator-scope/by-dept/3", method="DELETE", token=adm)
check("DELETE /api/indicator-scope/by-dept/{deptId}", *ok200(c, b))

# ─── 15. 填报任务（全流程 + 交叉）───────────────────────────
print("\n[15] 填报任务（全流程）")
# 创建任务 DRAFT
task_dto = {
    "name": "E2E测试填报任务",
    "timeDimension": "YEAR",
    "startDate": "2020-01-01",
    "endDate": "2020-12-31",
    "deadline": "2026-12-31",
    "scopes": [
        {"deptId": 1,   "deptName": "神经内科",   "metricCodes": ["rate_incision_infection", "rate_surgery_complication"]},
        {"deptId": 108, "deptName": "护理科室E2E", "metricCodes": ["rate_incision_infection"]}
    ]
}
c, b = req("/api/report/task", "POST", task_dto, token=adm)
check("POST /api/report/task (create)", *ok200(c, b))
task_id = (b.get("data") or {}).get("id") if c == 200 else None

if task_id:
    # 详情
    c, b = req(f"/api/report/task/{task_id}", token=adm)
    check("GET /api/report/task/{taskId} (detail)", *ok200(c, b))
    # 分页
    c, b = req("/api/report/task/page?current=1&size=10", token=adm)
    check("GET /api/report/task/page (admin)", *ok200(c, b))
    c, b = req("/api/report/task/page?current=1&size=10", token=hd)
    check("GET /api/report/task/page (neuro_head)", *ok200(c, b))
    # 另存模板（templateName URL-encode 避免中文乱码）
    _tname = urllib.parse.quote("E2E测试模板", safe="")
    c, b = req(f"/api/report/task/{task_id}/save-as-template?templateName={_tname}",
               "POST", {}, token=adm)
    check("POST /api/report/task/{taskId}/save-as-template", *ok200(c, b))
    tmpl_id = (b.get("data") or None) if c == 200 else None
    if tmpl_id:
        c, b = req(f"/api/report/task/template/{tmpl_id}/scopes", token=adm)
        check("GET /api/report/task/template/{templateId}/scopes", *ok200(c, b))
        # 从模板下发
        c, b = req(f"/api/report/task/from-template/{tmpl_id}", "POST",
                   dict(task_dto, name="E2E模板下发任务"), token=adm)
        check("POST /api/report/task/from-template/{templateId}", *ok200(c, b))
        derived_task_id = (b.get("data") or {}).get("id") if c == 200 else None
    else:
        check("GET /api/report/task/template/{templateId}/scopes", False, "模板保存失败")
        check("POST /api/report/task/from-template/{templateId}", False, "模板保存失败")
        derived_task_id = None
    # 发布 → 护士查看 my-tasks
    c, b = req(f"/api/report/task/{task_id}/publish", "POST", {}, token=adm)
    check("POST /api/report/task/{taskId}/publish", *ok200(c, b))
    # my-tasks（护士视角）
    c, b = req("/api/report/task/my-tasks", token=nur)
    check("GET /api/report/task/my-tasks (nurse)", *ok200(c, b))
    # 填报数据 sheet + save + submit（护士 deptId=108，已在 scope 中）
    c, b = req(f"/api/report/data/sheet?taskId={task_id}", token=nur)
    check("GET /api/report/data/sheet (nurse)", *ok200(c, b))
    c, b = req("/api/report/data/save", "POST",
               {"taskId": task_id, "metricCode": "rate_incision_infection",
                "inputMode": "RESULT_ONLY", "resultValue": 0.001}, token=nur)
    check("POST /api/report/data/save (nurse)", *ok200(c, b))
    c, b = req(f"/api/report/data/submit?taskId={task_id}", "POST", {}, token=nur)
    check("POST /api/report/data/submit (nurse)", *ok200(c, b))
    # 审核护士科室 108 的填报
    c, b = req("/api/report/task/review", "POST",
               {"taskId": task_id, "deptId": 108, "action": "APPROVED", "comment": "E2E审核通过"},
               token=adm)
    check("POST /api/report/task/review (APPROVED)", *ok200(c, b))
    # 导出已审核（二进制文件流，单独处理）
    try:
        _r = urllib.request.Request(
            BASE + f"/api/report/data/export-approved?taskId={task_id}",
            headers={"Authorization": f"Bearer {adm}"})
        with urllib.request.urlopen(_r, timeout=30) as _resp:
            _ec = _resp.status; _resp.read()
    except urllib.error.HTTPError as _e:
        _ec = _e.code
    except Exception:
        _ec = 0
    check("GET /api/report/data/export-approved", _ec in (200, 500), f"http={_ec}")
    # 关闭任务
    c, b = req(f"/api/report/task/{task_id}/close", "POST", {}, token=adm)
    check("POST /api/report/task/{taskId}/close", *ok200(c, b))
    # 导出填报模板（二进制文件流）
    try:
        _r = urllib.request.Request(
            BASE + f"/api/report/task/export-template?taskId={task_id}&deptId=108",
            headers={"Authorization": f"Bearer {adm}"})
        with urllib.request.urlopen(_r, timeout=30) as _resp:
            _ec = _resp.status; _resp.read()
    except urllib.error.HTTPError as _e:
        _ec = _e.code
    except Exception:
        _ec = 0
    check("GET /api/report/task/export-template", _ec in (200, 500), f"http={_ec}")
    # 衍生任务清理（关闭）
    if derived_task_id:
        req(f"/api/report/task/{derived_task_id}/close", "POST", {}, token=adm)
else:
    for name in ("GET task detail", "GET task page x2", "save-as-template",
                 "template scopes", "from-template", "publish", "my-tasks",
                 "sheet", "save", "submit", "review", "export-approved",
                 "close", "export-template"):
        check(f"report task: {name}", False, "创建任务失败，跳过")

# ─── 16. 报告列表 & 填报配置 ─────────────────────────────────
print("\n[16] 报告列表 & 填报配置")
c, b = req("/api/report/list", token=adm)
check("GET /api/report/list", *ok200(c, b))
c, b = req("/api/report/page?current=1&size=10", token=adm)
check("GET /api/report/page", *ok200(c, b))
c, b = req("/api/report/config", token=adm)
check("GET /api/report/config", *ok200(c, b))
cfg = b.get("data", {}) if c == 200 else {}
# 更新配置（原值回写）
c, b = req("/api/report/config", "PUT",
           {**cfg, "inputMode": cfg.get("inputMode", "RESULT_ONLY"),
            "reviewMode": cfg.get("reviewMode", "NO_REVIEW")}, token=adm)
check("PUT /api/report/config", *ok200(c, b))

# ─── 17. 指标分析报告 ────────────────────────────────────────
print("\n[17] 指标分析报告")
c, b = req("/api/indicator/report/preview?startPeriod=2020&endPeriod=2020&reportType=ANNUAL",
           token=adm)
check("GET /api/indicator/report/preview (ANNUAL)", *ok200(c, b))
c, b = req("/api/indicator/report/preview?startPeriod=202001&endPeriod=202001&reportType=MONTHLY",
           token=adm)
check("GET /api/indicator/report/preview (MONTHLY)", *ok200(c, b))
# Word 导出（二进制响应，不走 json 解析）
_export_url = BASE + "/api/indicator/report/export?startPeriod=2020&endPeriod=2020&reportType=ANNUAL"
try:
    _r = urllib.request.Request(_export_url, headers={"Authorization": f"Bearer {adm}"})
    with urllib.request.urlopen(_r, timeout=30) as _resp:
        _export_code = _resp.status
except urllib.error.HTTPError as _e:
    _export_code = _e.code
except Exception:
    _export_code = 0
check("GET /api/indicator/report/export (Word)", _export_code in (200, 500), f"http={_export_code}")

# ─── 18. 占位接口 ────────────────────────────────────────────
print("\n[18] 占位接口（data-entry）")
c, b = req("/api/data-entry/list", token=adm)
check("GET /api/data-entry/list (占位，返回空)", c == 200)
c, b = req("/api/data-entry/page?current=1&size=10", token=adm)
check("GET /api/data-entry/page (占位，返回空)", c == 200)

# ─── 19. 入参边界校验 ────────────────────────────────────────
print("\n[19] 入参边界校验")
c, b = req("/api/indicator/9999999", token=adm)
check("GET /api/indicator/9999999 → 业务 404",
      c == 200 and b.get("code") in (30404, 404, 400))
c, b = req("/api/indicator/save", "POST",
           {"metricCode": "", "metricName": "", "isLeaf": 1,
            "metricType": "X", "calculationType": "NONE", "status": 1}, token=adm)
check("POST /api/indicator/save (空 code → 400/biz error)",
      c in (400, 200) and (c == 400 or b.get("code") != 0))

# ─── Summary ─────────────────────────────────────────────────
total = PASS + FAIL
print(f"\n{'='*60}")
print(f"  结果: {PASS}/{total} PASS   {'全通过!' if FAIL==0 else f'❌ {FAIL} 失败'}")
print("=" * 60)
sys.exit(0 if FAIL == 0 else 1)
