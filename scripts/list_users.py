import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
R = 'http://localhost:8070/dgear'
accounts = [
    ('admin', 'Admin@123'),
    ('neuro_head', 'Dept@123'),
    ('neuro_nurse', 'Nurse@123'),
    ('geri_head', 'Dept@123'),
]
print('=== 登录验证 ===')
for u, p in accounts:
    try:
        r = requests.post(R+'/auth/login', params={'username':u,'password':p}, timeout=10).json()
        if r.get('code')==200:
            user = r['data'].get('user') or {}
            print(f"OK  {u:15} / {p:12}  dataScope={user.get('dataScope')}  deptId={user.get('deptId')}  {user.get('realName')}")
        else:
            print(f"FAIL {u:15}  {r.get('message')}")
    except Exception as e:
        print(f"ERR  {u}: {e}")

t = requests.post(R+'/auth/login', params={'username':'admin','password':'Admin@123'}).json()['data']['token']
users = requests.get(R+'/system/users', headers={'Authorization':'Bearer '+t}).json().get('data') or []
print('\n=== 系统全部账号（admin 可见）===')
for x in users:
    print(f"  {x.get('username'):15} deptId={x.get('deptId')}  dataScope={x.get('dataScope')}  roleId={x.get('roleId')}  {x.get('realName')}")
