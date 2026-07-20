# -*- coding: utf-8 -*-
"""
E2E Self-Test  --  indicator-mtr  port 8075
根据实际 Controller @RequestMapping 路径生成
"""
import sys, urllib.request, urllib.parse, json, time

sys.stdout.reconfigure(encoding="utf-8")

BASE   = "http://localhost:8075"
PASS   = 0
FAIL   = 0
TOKENS = {}


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
        with urllib.request.urlopen(r, timeout=15) as resp:
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
    check(f"login {username}", ok, f"code={code} body={body}")
    return body.get("data", {}).get("token", "") if ok else ""


# ─────────────────────────────────────────────
print("=" * 55)
print("  indicator-mtr  E2E  Self-Test")
print(f"  Target: {BASE}")
print("=" * 55)

# ── 1. API Docs ───────────────────────────────
print("\n[1] API Docs")
code, _ = req("/v3/api-docs")
check("GET /v3/api-docs", code == 200)

# ── 2. Login ──────────────────────────────────
print("\n[2] Login")
TOKENS["admin"]       = login("admin",       "Admin@123")
TOKENS["neuro_head"]  = login("neuro_head",  "Dept@123")
TOKENS["neuro_nurse"] = login("neuro_nurse", "Nurse@123")

adm = TOKENS["admin"]
hd  = TOKENS["neuro_head"]
nur = TOKENS["neuro_nurse"]

# ── 3. User Info & Menu ───────────────────────
print("\n[3] User Info & Menu")
code, body = req("/auth/userInfo", token=adm)
check("GET /auth/userInfo (admin)", code == 200 and body.get("data"))
code, body = req("/auth/userInfo", token=hd)
check("GET /auth/userInfo (neuro_head)", code == 200)
code, body = req("/auth/menus", token=adm)
check("GET /auth/menus (admin)", code == 200)

# ── 4. Permission Boundary ────────────────────
print("\n[4] Permission Boundary")
code, body = req("/system/roles/save", "POST", {}, token=nur)
nurse_blocked = (code in (401, 403)) or (body.get("code") in (30401, 30403, 401, 403))
check("nurse blocked from POST /system/roles/save", nurse_blocked, f"code={code} body_code={body.get('code')}")
code, body = req("/api/system/config", "POST", {}, token=nur)
nurse_blocked2 = (code in (401, 403)) or (body.get("code") in (30401, 30403, 401, 403))
check("nurse blocked from POST /api/system/config", nurse_blocked2, f"code={code}")

# ── 5. System Management ─────────────────────
print("\n[5] System Management")
code, body = req("/system/users", token=adm)
check("GET /system/users (admin)", code == 200)
code, body = req("/system/depts", token=adm)
check("GET /system/depts (admin)", code == 200)
code, body = req("/system/roles", token=adm)
check("GET /system/roles (admin)", code == 200)
code, body = req("/system/dept/tree", token=adm)
check("GET /system/dept/tree (admin)", code == 200)

# ── 6. Indicator Management ───────────────────
print("\n[6] Indicator Management")
code, body = req("/api/indicator/tree", token=adm)
check("GET /api/indicator/tree", code == 200)
code, body = req("/api/indicator/page?current=1&size=10", token=adm)
check("GET /api/indicator/page", code == 200 and isinstance(body.get("data", {}).get("records"), list))
code, body = req("/api/indicator-item/page?current=1&size=10", token=adm)
check("GET /api/indicator-item/page", code == 200)

code, body = req("/api/indicator-item/validate-sql",
                 "POST", {"sql": "SELECT COUNT(*) FROM d_mr WHERE B15 BETWEEN #{startDate} AND #{endDate}"}, token=adm)
check("POST /api/indicator-item/validate-sql (valid)", code == 200)
code, body = req("/api/indicator-item/validate-sql",
                 "POST", {"sql": "DROP TABLE d_mr"}, token=adm)
check("POST /api/indicator-item/validate-sql (invalid rejects)", body.get("code") != 0 or not body.get("data"))

# ── 7. Indicator Calculation ──────────────────
print("\n[7] Indicator Calculation")
code, body = req("/api/indicator-result/calculate"
                 "?metricCode=rate_incision_infection&timeDimension=YEAR&startDate=2020-01-01&endDate=2020-12-31",
                 "POST", {}, token=adm)
check("POST calculate rate_incision_infection 2020", code == 200, f"{body.get('msg','')}")

code, body = req("/api/indicator-item/a0050/execute?startDate=2020-01-01&endDate=2020-12-31",
                 "POST", {}, token=adm)
check("POST /api/indicator-item/a0050/execute", code == 200, f"{body.get('msg','')}")

code, body = req("/api/indicator-result/batch-calculate"
                 "?timeDimension=YEAR&startDate=2020-01-01&endDate=2020-12-31",
                 "POST",
                 ["rate_incision_infection", "rate_surgery_complication"],
                 token=adm)
check("POST batch-calculate", code == 200, f"{body.get('msg','')}")

# ── 8. Result Query ───────────────────────────
print("\n[8] Result Query")
code, body = req("/api/indicator-result/list?timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/indicator-result/list (admin)", code == 200)
code, body = req("/api/indicator-result/list?timeDimension=YEAR&timeValue=2020", token=hd)
check("GET /api/indicator-result/list (neuro_head)", code == 200)
code, body = req("/api/indicator-result/latest?metricCode=rate_incision_infection", token=adm)
check("GET /api/indicator-result/latest", code == 200)

# ── 9. Validation / Compliance / Compare ─────
print("\n[9] Validation & Compliance & Compare")
code, body = req("/api/data-validation/check",
                 "POST", {"timeDimension": "YEAR", "timeValue": "2020"}, token=adm)
check("POST /api/data-validation/check", code == 200, f"{body.get('msg','')}")

code, body = req("/api/indicator-result/compliance?timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/indicator-result/compliance", code == 200)

code, body = req("/api/indicator-result/compare"
                 "?metricCode=rate_incision_infection&timeDimension=YEAR&timeValues=2020,2021,2023", token=adm)
check("GET /api/indicator-result/compare (single)", code == 200)

code, body = req("/api/indicator-result/compare"
                 "?metricCodes=rate_incision_infection,rate_surgery_complication"
                 "&timeDimension=YEAR&timeValue=2020", token=adm)
check("GET /api/indicator-result/compare (multi)", code == 200)

# ── 10. Dataset ───────────────────────────────
print("\n[10] Dataset")
code, body = req("/api/dataset/page?type=YEAR&current=1&size=10", token=adm)
check("GET /api/dataset/page", code == 200)
code, body = req("/api/dataset/YEAR_2020", token=adm)
check("GET /api/dataset/YEAR_2020", code == 200)

# ── 11. Indicator Scope ───────────────────────
print("\n[11] Indicator Scope")
code, body = req("/api/indicator-scope/binding",
                 "POST",
                 {"deptId": 1, "metricCode": "rate_incision_infection", "isPrimaryOwner": 1},
                 token=adm)
check("POST /api/indicator-scope/binding", code == 200, f"{body.get('msg','')}")

# ── 12. Report Preview ────────────────────────
print("\n[12] Report Preview")
code, body = req("/api/indicator/report/preview?startPeriod=2020&endPeriod=2020&reportType=ANNUAL",
                 token=adm)
check("GET report preview ANNUAL", code == 200, f"{body.get('msg','')}")
code, body = req("/api/indicator/report/preview?startPeriod=202001&endPeriod=202001&reportType=MONTHLY",
                 token=adm)
check("GET report preview MONTHLY", code == 200, f"{body.get('msg','')}")

# ── 13. Manual Report ─────────────────────────
print("\n[13] Manual Report (hand-fill)")
code, body = req("/api/report/task/page?current=1&size=10", token=adm)
check("GET /api/report/task/page (admin)", code == 200)
code, body = req("/api/report/task/page?current=1&size=10", token=hd)
check("GET /api/report/task/page (neuro_head)", code == 200)
code, body = req("/api/report/data/sheet?taskId=1", token=nur)
check("GET /api/report/data/sheet?taskId=1 (nurse)", code == 200, f"{body.get('msg','')}")

# ── 14. System Config ─────────────────────────
print("\n[14] System Config")
code, body = req("/api/system/config", token=adm)
check("GET /api/system/config (admin)", code == 200)
code, body = req("/api/system/config", token=nur)
check("GET /api/system/config (nurse, read OK)", code == 200)

# ── 15. Input Validation ──────────────────────
print("\n[15] Input Validation")
code, body = req("/api/indicator/9999999", token=adm)
check("GET non-existent indicator → business 404", code == 200 and body.get("code") in (30404, 404, 400))
code, body = req("/auth/login", "POST", {"username": "x", "password": "bad"}, form=True)
check("login bad password → error", code != 200 or body.get("code") != 0)

# ── Summary ───────────────────────────────────
total = PASS + FAIL
print(f"\n{'='*55}")
print(f"  结果: {PASS}/{total} PASS   {'全通过!' if FAIL==0 else f'{FAIL} 失败'}")
print("=" * 55)
sys.exit(0 if FAIL == 0 else 1)
