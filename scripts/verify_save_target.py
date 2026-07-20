import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT + '/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}

code = 'rate_incision_infection'
ind = requests.get(ROOT + f'/api/indicator/code/{code}', headers=hdr).json()['data']
print('部署前 targetValue:', ind.get('targetValue'))

body = {
    'id': ind['id'], 'metricCode': code, 'metricName': ind['metricName'],
    'isLeaf': ind['isLeaf'], 'metricType': ind['metricType'],
    'calculationType': ind['calculationType'], 'status': ind['status'],
    'targetValue': 0.002, 'monitorDirection': 'DECREASE',
    'inputType': ind.get('inputType') or 'AUTO',
}
r = requests.post(ROOT + '/api/indicator/save', headers=hdr, json=body).json()
print('save code:', r.get('code'), r.get('message'))

ind2 = requests.get(ROOT + f'/api/indicator/code/{code}', headers=hdr).json()['data']
print('部署后 targetValue:', ind2.get('targetValue'), 'dir:', ind2.get('monitorDirection'))
print('API写目标值:', 'OK' if ind2.get('targetValue') == 0.002 else 'FAIL')

# 恢复原值
body['targetValue'] = 0.001
requests.post(ROOT + '/api/indicator/save', headers=hdr, json=body)
print('已恢复 targetValue=0.001')
