import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer '+tok}

# 查所有 MONTH 维度的结果
results = requests.get(ROOT+'/api/indicator-result/list', headers=hdr,
    params={'timeDimension': 'MONTH'}).json().get('data') or []

# 按 timeValue 分组统计
from collections import Counter
cnt = Counter(r['timeValue'] for r in results)
print('现有月度数据分布:')
for tv in sorted(cnt):
    print(f'  {tv}  {cnt[tv]:3} 条')

print(f'\n共 {len(results)} 条月度结果')

# 看2020-01 有哪些指标
jan = [r for r in results if r['timeValue'] == '2020-01']
print(f'\n2020-01 有 {len(jan)} 条：')
for r in jan[:20]:
    print(f"  {r['metricCode']:40} {r['resultValue']}")
if len(jan) > 20:
    print(f'  ... 共 {len(jan)} 条')
