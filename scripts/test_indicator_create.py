import json
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8")

ROOT = "http://localhost:8070/dgear"
PREFIX = f"UT_CREATE_{int(time.time())}"


def call(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.request(
        method, ROOT + path, headers=headers, timeout=30, **kwargs
    )
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text}
    return response.status_code, body


status, login = call(
    "POST",
    "/auth/login",
    params={"username": "admin", "password": "Admin@123"},
)
token = login["data"]["token"]
_, nurse_login = call(
    "POST",
    "/auth/login",
    params={"username": "neuro_nurse", "password": "Nurse@123"},
)
nurse_token = (nurse_login.get("data") or {}).get("token")

cases = [
    (
        "父节点",
        {
            "metricCode": PREFIX,
            "metricName": "单元测试父节点",
            "parentCode": None,
            "indicatorLevel": 1,
            "isLeaf": 0,
            "metricType": "QUALITATIVE",
            "calculationType": "NONE",
            "status": 1,
            "sortOrder": 99990,
            "metricPool": "POOL_NATIONAL",
            "inputType": "AUTO",
            "businessDirection": "INPATIENT",
        },
    ),
    (
        "ITEM自动指标",
        {
            "metricCode": PREFIX + "_ITEM",
            "metricName": "单元测试ITEM指标",
            "parentCode": PREFIX,
            "indicatorLevel": 2,
            "isLeaf": 1,
            "metricType": "QUANTITATIVE",
            "calculationType": "ITEM",
            "expression": "a0050",
            "relatedItems": json.dumps(["a0050"]),
            "unit": "人",
            "supportDeptDrill": 1,
            "status": 1,
            "sortOrder": 99991,
            "metricPool": "POOL_NATIONAL",
            "inputType": "AUTO",
            "businessDirection": "INPATIENT",
        },
    ),
    (
        "EXPRESSION自动指标",
        {
            "metricCode": PREFIX + "_EXPR",
            "metricName": "单元测试表达式指标",
            "parentCode": PREFIX,
            "indicatorLevel": 2,
            "isLeaf": 1,
            "metricType": "QUANTITATIVE",
            "calculationType": "EXPRESSION",
            "expression": "a0052/a0050",
            "relatedItems": json.dumps(["a0050", "a0052"]),
            "unit": "天",
            "supportDeptDrill": 1,
            "status": 1,
            "sortOrder": 99992,
            "metricPool": "POOL_NATIONAL",
            "inputType": "AUTO",
        },
    ),
    (
        "MANUAL手工指标",
        {
            "metricCode": PREFIX + "_MANUAL",
            "metricName": "单元测试手工指标",
            "parentCode": PREFIX,
            "indicatorLevel": 2,
            "isLeaf": 1,
            "metricType": "QUANTITATIVE",
            "calculationType": "NONE",
            "status": 1,
            "sortOrder": 99993,
            "metricPool": "POOL_NATIONAL",
            "inputType": "MANUAL",
        },
    ),
]

created_ids = []
try:
    for name, payload in cases:
        http, body = call("POST", "/api/indicator/save", token, json=payload)
        data = body.get("data") or {}
        if data.get("id"):
            created_ids.append(data["id"])
        print(
            f"{name}: HTTP={http}, code={body.get('code')}, "
            f"msg={body.get('message')}, id={data.get('id')}, "
            f"level={data.get('indicatorLevel')}"
        )
        if name == "ITEM自动指标" and data.get("id"):
            _, detail = call("GET", f"/api/indicator/{data['id']}", token)
            saved = detail.get("data") or {}
            print(
                "  字段回读: "
                f"inputType={saved.get('inputType')}, "
                f"businessDirection={saved.get('businessDirection')}"
            )
            update_payload = dict(payload)
            update_payload["id"] = data["id"]
            update_payload["metricName"] = "单元测试ITEM指标（已更新）"
            update_payload["indicatorLevel"] = 99
            _, update_body = call(
                "POST", "/api/indicator/save", token, json=update_payload
            )
            updated = update_body.get("data") or {}
            print(
                f"  更新回归: code={update_body.get('code')}, "
                f"name={updated.get('metricName')}, "
                f"level={updated.get('indicatorLevel')}"
            )

    if nurse_token:
        http, body = call(
            "DELETE", f"/api/indicator/{created_ids[1]}", nurse_token
        )
        print(
            f"普通护士删除: HTTP={http}, code={body.get('code')}, "
            f"msg={body.get('message')}"
        )

    http, body = call("DELETE", f"/api/indicator/{created_ids[0]}", token)
    print(
        f"父节点提前删除: HTTP={http}, code={body.get('code')}, "
        f"msg={body.get('message')}"
    )

    duplicate = dict(cases[1][1])
    duplicate["metricName"] = "重复编码"
    http, body = call("POST", "/api/indicator/save", token, json=duplicate)
    print(
        f"重复编码: HTTP={http}, code={body.get('code')}, msg={body.get('message')}"
    )

    missing_parent = dict(cases[1][1])
    missing_parent["metricCode"] = PREFIX + "_ORPHAN"
    missing_parent["parentCode"] = PREFIX + "_NOT_EXISTS"
    http, body = call("POST", "/api/indicator/save", token, json=missing_parent)
    data = body.get("data") or {}
    if data.get("id"):
        created_ids.append(data["id"])
    print(
        f"不存在父级: HTTP={http}, code={body.get('code')}, "
        f"msg={body.get('message')}, id={data.get('id')}"
    )

    if nurse_token:
        unauthorized = dict(cases[1][1])
        unauthorized["metricCode"] = PREFIX + "_NURSE"
        unauthorized["metricName"] = "护士越权创建测试"
        http, body = call(
            "POST", "/api/indicator/save", nurse_token, json=unauthorized
        )
        data = body.get("data") or {}
        if data.get("id"):
            created_ids.append(data["id"])
        print(
            f"普通护士创建: HTTP={http}, code={body.get('code')}, "
            f"msg={body.get('message')}, id={data.get('id')}"
        )
finally:
    for indicator_id in reversed(created_ids):
        call("DELETE", f"/api/indicator/{indicator_id}", token)
