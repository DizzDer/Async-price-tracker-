"""Docker-only smoke test; uses demo data and never sends external messages."""
import json
import subprocess
import time
from urllib.request import Request, urlopen

def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request('http://127.0.0.1:8000' + path, data=data,
                  headers={'X-API-Key':'ci-api-key','Content-Type':'application/json'})
    with urlopen(req, timeout=3) as response:
        return json.load(response)

def eventually(check):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            if check(): return
        except (OSError, ValueError):
            pass
        time.sleep(2)
    raise AssertionError('Timed out waiting for integration state')

if __name__ == '__main__':
    eventually(lambda: request('/health')['status'] == 'ok')
    pid = request('/products', {'name':'Coffee','url':'demo://coffee','target':'20.00'})['id']
    subprocess.run(['docker','compose','exec','-T','worker','celery','-A','tracker.worker','call','tracker.poll'],check=True)
    eventually(lambda: len(request(f'/products/{pid}/history')) >= 1)
    assert request('/alerts')[0]['product_id'] == pid
    print('PostgreSQL persistence, Redis queue, worker, migration and API passed')
