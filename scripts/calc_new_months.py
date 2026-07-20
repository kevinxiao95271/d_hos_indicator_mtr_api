import sys, requests, time
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'http://localhost:8070/dgear'
tok = requests.post(ROOT+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
hdr = {'Authorization': 'Bearer '+tok}

months = ['2020-07','2020-08','2020-09','2020-10','2020-11','2020-12']

# 逐月触发计算（避免一次批量超过3个月的限制）
for i in range(0, len(months), 3):
    chunk = months[i:i+3]
    start = chunk[0] + '-01'
    # end: last day of last month in chunk
    import calendar
    ym = chunk[-1]
    y, m = int(ym[:4]), int(ym[5:7])
    last_day = calendar.monthrange(y, m)[1]
    end = f'{ym}-{last_day:02d}'

    print(f'触发计算 {start} ~ {end} ...')
    r = requests.post(ROOT+'/api/indicator-result/batch-calculate', headers=hdr,
        params={'timeDimension':'MONTH','startDate':start,'endDate':end},
        timeout=300)
    data = r.json()
    print(f'  code={data.get("code")} msg={data.get("message")} data={str(data.get("data"))[:80]}')
    time.sleep(2)

# 验证结果
print('\n── 月度结果分布 ─────────────────────────────')
from collections import Counter
results = requests.get(ROOT+'/api/indicator-result/list', headers=hdr,
    params={'timeDimension':'MONTH'}).json().get('data') or []
cnt = Counter(r['timeValue'] for r in results)
for tv in sorted(cnt):
    print(f'  {tv}  {cnt[tv]:3} 条')
