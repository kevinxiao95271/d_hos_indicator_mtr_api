# -*- coding: utf-8 -*-
"""
专项测试：新增两个接口
  DELETE /system/user/{userId}
  GET    /api/indicator-result/export
"""
import sys, urllib.request, urllib.parse, urllib.error, json
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8075"
PASS = 0; FAIL = 0


def login(u, p):
    data = urllib.parse.urlencode({"username": u, "password": p}).encode()
    r = urllib.request.Request(BASE + "/auth/login", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read())["data"]["token"]


def req(path, method="GET", body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as ex:
        return 0, {"_err": str(ex)}


def chk(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        print(f"  [PASS] {name}")
        PASS += 1
    else:
        print(f"  [FAIL] {name}  {detail}")
        FAIL += 1


adm = login("admin", "Admin@123")
nur = login("neuro_nurse", "Nurse@123")

# ─── 1. DELETE /system/user/{userId} ─────────────────────────
print("=" * 50)
print("1. DELETE /system/user/{userId}")
print("=" * 50)

# 先创建临时用户
c, b = req("/system/user/save", "POST",
    {"username": "e2e_del_tmp", "realName": "E2E临时用户",
     "deptId": 1, "roleId": 4, "dataScope": 90, "status": "0"}, token=adm)
chk("POST /system/user/save (create temp)", c == 200 and b.get("data") == True,
    f"http={c} biz={b.get('code')}")

# 找到新建用户的 ID
c2, b2 = req("/system/user/list", token=adm)
uid = next((u["userId"] for u in (b2.get("data") or [])
            if u.get("username") == "e2e_del_tmp"), None)
chk("GET /system/user/list (find temp user)", uid is not None)

if uid:
    # 护士无权删除
    c, b = req(f"/system/user/{uid}", "DELETE", token=nur)
    chk("DELETE /{userId} — nurse blocked",
        c in (401, 403) or b.get("code") in (30401, 30403, 401, 403),
        f"http={c} biz={b.get('code')}")
    # admin 正常删除
    c, b = req(f"/system/user/{uid}", "DELETE", token=adm)
    chk("DELETE /{userId} — admin OK",
        c == 200 and b.get("code") in (0, 200),
        f"http={c} biz={b.get('code')}")
    # 再次删除 → 404
    c, b = req(f"/system/user/{uid}", "DELETE", token=adm)
    chk("DELETE /{userId} — already deleted → 404",
        b.get("code") in (30404, 404),
        f"biz={b.get('code')}")
    # 不能删自己（admin id=3）
    c, b = req("/system/user/3", "DELETE", token=adm)
    chk("DELETE /3 — cannot delete self",
        b.get("code") in (30400, 400) or c == 400,
        f"http={c} biz={b.get('code')}")
else:
    for n in ("nurse blocked", "admin OK", "already deleted 404", "cannot delete self"):
        chk(f"DELETE {n}", False, "uid not found, skipped")

# ─── 2. GET /api/indicator-result/export ─────────────────────
print()
print("=" * 50)
print("2. GET /api/indicator-result/export")
print("=" * 50)

def get_blob(path, token):
    r = urllib.request.Request(BASE + path, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), \
                   resp.headers.get("Content-Disposition", ""), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, "", "", b""
    except Exception as ex:
        return 0, "", "", str(ex).encode()


# 全量导出
status, ct, cd, body = get_blob("/api/indicator-result/export?timeDimension=YEAR&timeValue=2020", adm)
chk("GET /export (YEAR 2020) → xlsx stream",
    status == 200 and "spreadsheetml" in ct and len(body) > 0,
    f"http={status} CT={ct} size={len(body)}")
chk("GET /export Content-Disposition contains attachment",
    "attachment" in cd, f"CD={cd}")

# 按指标过滤
status, ct, cd, body = get_blob(
    "/api/indicator-result/export?metricCode=rate_incision_infection&timeDimension=YEAR", adm)
chk("GET /export (metricCode filter)", status == 200, f"http={status}")

# 护士 dataScope 过滤后正常返回
status, ct, cd, body = get_blob(
    "/api/indicator-result/export?timeDimension=YEAR&timeValue=2020", nur)
chk("GET /export (nurse, scoped)", status == 200, f"http={status}")

# 无过滤（全量，应有内容）
status, ct, cd, body = get_blob("/api/indicator-result/export", adm)
chk("GET /export (no filter, full export)", status == 200 and len(body) > 0,
    f"http={status} size={len(body)}")

# ─── Summary ─────────────────────────────────────────────────
print()
print("=" * 50)
print(f"  结果: {PASS}/{PASS+FAIL} PASS  {'全通过!' if FAIL == 0 else str(FAIL) + ' 失败'}")
print("=" * 50)
sys.exit(0 if FAIL == 0 else 1)
