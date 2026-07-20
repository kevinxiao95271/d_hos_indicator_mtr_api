import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer '+tok, 'Content-Type': 'application/json'}

# 查 10.3.2 当前信息
ind = requests.get(ROOT+'/api/indicator/code/10.3.2', headers=hdr).json()['data']
print('修改前:', ind['metricCode'], ind['metricName'], 'isLeaf=', ind['isLeaf'])

# 更新 isLeaf=0
body = {
    'id': ind['id'],
    'metricCode': ind['metricCode'],
    'metricName': ind['metricName'],
    'parentCode': ind.get('parentCode'),
    'indicatorLevel': ind.get('indicatorLevel'),
    'isLeaf': 0,
    'metricType': ind.get('metricType', 'QUANTITATIVE'),
    'calculationType': 'NONE',
    'status': ind.get('status', 1),
    'sortOrder': ind.get('sortOrder'),
    'metricPool': ind.get('metricPool'),
    'inputType': ind.get('inputType') or 'AUTO',
    'unit': ind.get('unit'),
    'expression': ind.get('expression'),
    'relatedItems': ind.get('relatedItems'),
}
r = requests.post(ROOT+'/api/indicator/save', headers=hdr, json=body).json()
print('保存结果:', r.get('code'), r.get('message'))

# 验证
ind2 = requests.get(ROOT+'/api/indicator/code/10.3.2', headers=hdr).json()['data']
print('修改后:', ind2['metricCode'], ind2['metricName'], 'isLeaf=', ind2['isLeaf'])

# 顺带验证树结构 10.3 子节点
children = requests.get(ROOT+'/api/indicator/children/10.3', headers=hdr).json().get('data', [])
print('\n10.3 的子节点:')
for c in children:
    print(f"  {c['metricCode']:10} isLeaf={c['isLeaf']}  {c['metricName']}")

children2 = requests.get(ROOT+'/api/indicator/children/10.3.2', headers=hdr).json().get('data', [])
print('\n10.3.2 的子节点:')
for c in children2:
    print(f"  {c['metricCode']:10} isLeaf={c['isLeaf']}  {c['metricName']}")
