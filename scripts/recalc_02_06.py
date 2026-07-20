import sys, requests, time, calendar
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer '+tok}

# 分两批触发 02-06
batches = [
    ('2020-02-01', '2020-04-30'),
    ('2020-05-01', '2020-06-30'),
]

for start, end in batches:
    print(f'触发计算 {start} ~ {end} ...', end=' ', flush=True)
    r = requests.post(ROOT+'/api/indicator-result/batch-calculate', headers=hdr,
        params={'timeDimension':'MONTH','startDate':start,'endDate':end},
        timeout=300)
    d = r.json()
    print(f'code={d.get("code")} {d.get("message")}')
    time.sleep(2)

# 最终汇总验证
print('\n── 月度趋势验证（关键指标）─────────────────────────────────')
from collections import Counter
results = requests.get(ROOT+'/api/indicator-result/list', headers=hdr,
    params={'timeDimension':'MONTH'}).json().get('data') or []
cnt = Counter(r['timeValue'] for r in results if r['timeValue'].startswith('2020'))
print('2020 各月结果条数:')
for tv in sorted(cnt):
    print(f'  {tv}  {cnt[tv]:3} 条')

WATCH = ['avg_cost_pneumonia_adult', 'mortality_copd', 'avg_stay_ami', '10.3.1']
months_2020 = [f'2020-{m:02d}' for m in range(1,13)]
print(f'\n{"指标":38}', '  '.join(months_2020))
for code in WATCH:
    vals = {r['timeValue']: r['resultValue'] for r in results if r['metricCode']==code}
    row = [f'{vals.get(m, "—"):>9}' for m in months_2020]
    print(f'{code:38}', ' '.join(row))
