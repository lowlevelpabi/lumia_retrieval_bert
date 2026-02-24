import requests, os, sys

BASE = 'http://localhost:8000/api/v1'
pdfs = [
    'uploads/dummy_iot_ids_thesis.pdf',
    'uploads/dummy_student_performance_thesis.pdf',
    'uploads/dummy_linguacheck_capstone.pdf',
    'uploads/dummy_smartbridge_capstone.pdf',
]

ADMIN_USERS = [
    ('admin_test', 'admin123'),
    ('maruf', 'admin123'),
    ('admin_test', 'password'),
    ('maruf', 'password'),
]

token = None
for username, password in ADMIN_USERS:
    r = requests.post(f'{BASE}/auth/login', data={'username': username, 'password': password})
    if r.status_code == 200:
        token = r.json()['access_token']
        print(f'Logged in as: {username}')
        break

if not token:
    print('ERROR: Could not log in with any known admin credentials. Please pass your credentials.')
    print('Usage: set LUMIA_USER=username LUMIA_PASS=password and rerun')
    username = os.environ.get('LUMIA_USER', '')
    password = os.environ.get('LUMIA_PASS', '')
    if username and password:
        r = requests.post(f'{BASE}/auth/login', data={'username': username, 'password': password})
        if r.status_code == 200:
            token = r.json()['access_token']
        else:
            print('Still failed:', r.text)
            sys.exit(1)
    else:
        sys.exit(1)

headers = {'Authorization': f'Bearer {token}'}

for pdf_path in pdfs:
    if not os.path.exists(pdf_path):
        print(f'MISSING: {pdf_path}')
        continue
    with open(pdf_path, 'rb') as f:
        res = requests.post(
            f'{BASE}/papers/upload',
            headers=headers,
            files={'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        )
    if res.status_code == 200:
        d = res.json()
        print(f'OK  ID={d["id"]} | {d["title"][:55]}')
    else:
        print(f'ERR {res.status_code}: {res.text[:120]}')
