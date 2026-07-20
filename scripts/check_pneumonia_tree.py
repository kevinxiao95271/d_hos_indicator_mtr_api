import sys, requests, json
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer '+tok}

# 1. 搜索肺炎相关指标（分页，名称含"肺炎"）
r = requests.get(ROOT+'/api/indicator/page', headers=hdr, params={
    'current':1,'size':50,'metricName':'肺炎'
}).json()
items = r.get('data',{}).get('records',[])
print(f'含"肺炎"指标共 {len(items)} 个：\n')
for x in items:
    print(f"  {x['metricCode']:35} isLeaf={x['isLeaf']} parent={x.get('parentCode') or '(根)'}")
    print(f"    名称: {x['metricName']}")
    print()
