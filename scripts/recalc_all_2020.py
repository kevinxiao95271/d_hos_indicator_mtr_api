import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer '+tok}

# 分批触发全年（每次最多3个月）
batches = [
    ('2020-02-01', '2020-04-30'),
    ('2020-05-01', '2020-07-31'),
    ('2020-08-01', '2020-10-31'),
    ('2020-11-01', '2020-12-31'),
]
for start, end in batches:
    print(f'计算 {start}~{end} ...', end=' ', flush=True)
    r = requests.post(ROOT+'/api/indicator-result/batch-calculate', headers=hdr,
        params={'timeDimension':'MONTH','startDate':start,'endDate':end}, timeout=300)
    d = r.json()
    print(d.get('message',''))
    time.sleep(1)

# 查结果趋势
print('\n── 重算后指标月度趋势 ───────────────────────────────')
results = requests.get(ROOT+'/api/indicator-result/list', headers=hdr,
    params={'timeDimension':'MONTH'}).json().get('data') or []

WATCH = [
    'avg_cost_pneumonia_adult',
    'mortality_copd',
    'avg_stay_ami',
    '10.3.1',
    'rate_incision_infection',
]
months = [f'2020-{m:02d}' for m in range(1,13)]
print(f'{"指标代码":38}', ' '.join(m[5:] for m in months))
for code in WATCH:
    vals = {r['timeValue']: r['resultValue'] for r in results if r['metricCode']==code}
    row = []
    for m in months:
        v = vals.get(m)
        row.append(f'{float(v):7.4f}' if v is not None else '   ——  ')
    print(f'{code:38}', ' '.join(row))
