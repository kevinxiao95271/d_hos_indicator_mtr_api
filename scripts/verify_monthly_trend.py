import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer '+tok}

results = requests.get(ROOT+'/api/indicator-result/list', headers=hdr,
    params={'timeDimension':'MONTH'}).json().get('data') or []

# 取几个有代表性的叶子指标，看全年趋势
WATCH = ['avg_cost_pneumonia_adult', 'rate_incision_infection', 'mortality_copd',
         'avg_stay_ami', '10.3.1']

print(f'{"指标代码":38}', end='')
months_2020 = [f'2020-{m:02d}' for m in range(1,13)]
for m in months_2020:
    print(f'{m:>10}', end='')
print()

for code in WATCH:
    vals = {r['timeValue']: r['resultValue'] for r in results if r['metricCode'] == code}
    print(f'{code:38}', end='')
    for m in months_2020:
        v = vals.get(m)
        print(f'{v if v is not None else "—":>10}', end='')
    print()

print('\n全年月度数据已就绪，可用于折线图趋势分析。')
