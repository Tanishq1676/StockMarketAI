"""Combined job: start backend + dev server, wait, then run final_verify."""

import os
import subprocess
import sys
import time
import urllib.request

PY = os.environ.get("LOCALAPPDATA", "") + r"\Programs\Python\Python312\python.exe"
ROOT = os.environ.get("PROJECT_ROOT", os.getcwd())


def start():
    p1 = subprocess.Popen([PY, "-m", "uvicorn", "--app-dir", "backend", "app.main:app",
                           "--host", "127.0.0.1", "--port", "8000"],
                          cwd=ROOT,
                          stdout=open("backend/uvicorn.log", "ab"), stderr=subprocess.STDOUT)
    os.chdir(os.path.join(ROOT, "frontend"))
    p2 = subprocess.Popen([PY, "-m", "node", "node_modules/next/dist/bin/next", "dev", "-p", "3000",
                           "--hostname", "127.0.0.1"],
                          cwd=ROOT,
                          stdout=open("frontend/next-dev.log", "ab"), stderr=subprocess.STDOUT)
    return p1, p2


def wait_up(url, timeout=150):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main():
    p1, p2 = start()
    print("processes:", p1.pid, p2.pid, flush=True)
    ok_b = wait_up("http://127.0.0.1:8000/api/health")
    print("backend up:", ok_b, flush=True)
    os.chdir(ROOT)
    ok_f = wait_up("http://127.0.0.1:3000/", timeout=180)
    print("frontend up:", ok_f, flush=True)
    r = subprocess.run([PY, "final_verify.py"], cwd=ROOT, capture_output=True, text=True, timeout=600)
    print("=== final_verify output ===")
    print(r.stdout[-2500:])
    if r.stderr:
        print("=== stderr tail ===")
        print(r.stderr[-800:])


if __name__ == "__main__":
    main()
