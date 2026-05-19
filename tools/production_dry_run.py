# -*- coding: utf-8 -*-
"""
Expert Smart Production Dry-Run
Phases 2-7: env setup, boot, probes, tooling validation, cleanup.
Run from repo root with: python tools/production_dry_run.py
"""
import os, sys, time, subprocess, socket, json, sqlite3, tempfile, pathlib, shutil

# ── Paths (derived from script location — not hardcoded) ─────────────────────
TOOLS_DIR   = pathlib.Path(__file__).resolve().parent
REPO_ROOT   = TOOLS_DIR.parent
CORE_ENGINE = REPO_ROOT / "core_engine"

# ── Fixed dry-run secrets (session-only, not stored anywhere) ─────────────────
DR_JWT_SECRET  = "DryRunJWT2026Xk7mP9qN3vL8wR2tS5yU1zA4bC6dE0fGH"  # 48 chars
DR_GOVT_KEY    = "DryRunGovt2026Yp4nQ8rM2xK5wJ1sB6cD0eF3gH7iJK"   # 46 chars
DR_ADMIN       = "dryrun-admin@local"

# ── All temp artifacts land in OS temp — nothing touches production data ──────
_TMP        = pathlib.Path(tempfile.gettempdir())
DR_DB       = _TMP / "dryrun_reports.db"
DR_AUDIT_DB = DR_DB                               # audit uses same temp DB (fix for probe #9)
DR_BACKUP_DIR  = _TMP / "dryrun_backups"
DR_EXPORT_FILE = _TMP / "dryrun_export.json"
RESULTS_FILE   = _TMP / "dryrun_results.json"

# Remove any stale temp DB from a previous run
DR_DB.unlink(missing_ok=True)

env = os.environ.copy()
env.update({
    "JWT_SECRET":        DR_JWT_SECRET,
    "GOVT_SIGNING_KEY":  DR_GOVT_KEY,
    "AUDIT_ENABLED":     "true",
    "RATE_LIMIT_ENABLED":"true",
    "ADMIN_USER_IDS":    DR_ADMIN,
    "JWT_TTL_SECONDS":   "300",
    "REPORTS_DB_PATH":   str(DR_DB),
    "AUDIT_DB_PATH":     str(DR_AUDIT_DB),  # fix: audit writes to dry-run temp DB (probe #9)
    "ENVIRONMENT":       "dryrun",
})

report = {
    "env": {},
    "boot": {},
    "probes": [],
    "tooling": [],
    "boot_time_s": None,
}

# ── Phase 2: env check ────────────────────────────────────────────────────────
print("\n=== Phase 2: Environment ===")
env_checks = [
    ("JWT_SECRET set (>=32 chars)",        len(DR_JWT_SECRET) >= 32),
    ("GOVT_SIGNING_KEY set (>=32 chars)",   len(DR_GOVT_KEY) >= 32),
    ("AUDIT_ENABLED=true",                  env["AUDIT_ENABLED"] == "true"),
    ("RATE_LIMIT_ENABLED=true",             env["RATE_LIMIT_ENABLED"] == "true"),
    ("ADMIN_USER_IDS set",                  bool(env["ADMIN_USER_IDS"])),
    ("REPORTS_DB_PATH set (temp)",          str(DR_DB).startswith(tempfile.gettempdir())),
    ("AUDIT_DB_PATH set (temp)",            str(DR_AUDIT_DB).startswith(tempfile.gettempdir())),
]
for name, ok in env_checks:
    print(f"  {'OK' if ok else 'FAIL'} - {name}")
    report["env"][name] = ok

# ── Phase 3: boot server ──────────────────────────────────────────────────────
print("\n=== Phase 3: Boot ===")
srv = subprocess.Popen(
    [sys.executable, "bridge_api.py"],
    cwd=str(CORE_ENGINE),
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
)
print(f"  Server PID: {srv.pid}")

def wait_for_port(host, port, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False

t0 = time.time()
booted = wait_for_port("127.0.0.1", 5000, timeout=25)
boot_time = round(time.time() - t0, 1)
report["boot_time_s"] = boot_time

if not booted:
    err = srv.stderr.read(2000).decode(errors="replace")
    print(f"  FAIL — server did not boot in 25s\n  stderr: {err[:500]}")
    report["boot"]["started"] = False
    srv.kill()
    sys.exit(1)

print(f"  PASS — port open after {boot_time}s")
report["boot"]["started"] = True
report["boot"]["boot_time_s"] = boot_time
time.sleep(1)  # let waitress settle

# ── Phase 4: HTTP probes ──────────────────────────────────────────────────────
print("\n=== Phase 4: HTTP Probes ===")
import urllib.request, urllib.error

def http(method, path, headers=None, body=None, timeout=8):
    url = f"http://127.0.0.1:5000{path}"
    req = urllib.request.Request(url, method=method, headers=headers or {})
    if body:
        req.data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return f"ERR:{e}"

import time as _time
try:
    import jwt as _pyjwt
    def make_token(user, ttl=300):
        now = int(_time.time())
        return _pyjwt.encode(
            {"sub": user, "iat": now, "exp": now + ttl},
            DR_JWT_SECRET, algorithm="HS256"
        )
except ImportError:
    import base64, hmac, hashlib
    def make_token(user, ttl=300):
        now = int(_time.time())
        hdr = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b'=').decode()
        pay = base64.urlsafe_b64encode(json.dumps({"sub":user,"iat":now,"exp":now+ttl},separators=(',',':')).encode()).rstrip(b'=').decode()
        msg = f"{hdr}.{pay}".encode()
        sig = base64.urlsafe_b64encode(hmac.new(DR_JWT_SECRET.encode(), msg, hashlib.sha256).digest()).rstrip(b'=').decode()
        return f"{hdr}.{pay}.{sig}"

tok_user  = make_token("dryrun-user")
tok_alice = make_token("alice")
tok_admin = make_token(DR_ADMIN)

def probe(num, name, expected_codes, method, path, headers=None, body=None, timeout=8):
    code = http(method, path, headers=headers, body=body, timeout=timeout)
    ok = code in expected_codes if isinstance(expected_codes, (list, tuple)) else code == expected_codes
    status = "PASS" if ok else "FAIL"
    expected_str = "/".join(str(c) for c in (expected_codes if isinstance(expected_codes, (list, tuple)) else [expected_codes]))
    print(f"  [{status}] #{num} {name}: expected={expected_str} got={code}")
    report["probes"].append({"num": num, "name": name, "expected": expected_str, "got": str(code), "passed": ok})
    return ok

probe(1, "GET / (index)",                     [200], "GET", "/")
probe(2, "GET /api/reports (no token)",        [401], "GET", "/api/reports")
probe(3, "GET /api/reports (valid token)",     [200], "GET", "/api/reports",
      headers={"Authorization": f"Bearer {tok_user}"})
probe(4, "GET /api/reports (bad token)",       [401], "GET", "/api/reports",
      headers={"Authorization": "Bearer invalid.token.here"})
probe(5, "GET /api/reports/<bad-id> (token)",  [404], "GET", "/api/reports/nonexistent-id-dryrun",
      headers={"Authorization": f"Bearer {tok_alice}"})
probe(6, "GET /api/admin/audit (non-admin)",   [403], "GET", "/api/admin/audit",
      headers={"Authorization": f"Bearer {tok_alice}"})
probe(7, "GET /api/admin/audit (admin token)", [200], "GET", "/api/admin/audit",
      headers={"Authorization": f"Bearer {tok_admin}"})

# #8 — Rate limit: 31 rapid requests must trigger 429
print("  [....] #8 Rate limit (31x /api/reports) — sending...", end="", flush=True)
last_code = None
for _ in range(31):
    last_code = http("GET", "/api/reports", headers={"Authorization": f"Bearer {tok_alice}"})
rl_ok = last_code == 429
status = "PASS" if rl_ok else "FAIL"
print(f"\r  [{status}] #8 Rate limit 31x /api/reports: expected=429 got={last_code}")
report["probes"].append({"num": "8", "name": "Rate limit 31x /api/reports (last req)", "expected": "429", "got": str(last_code), "passed": rl_ok})

# #9 — Audit rows: audit must write to the dry-run temp DB (AUDIT_DB_PATH fix)
time.sleep(1)
audit_count = 0; audit_table = "none"; audit_ok = False
try:
    conn = sqlite3.connect(str(DR_DB))
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    atbls = [t for t in tables if any(k in t.lower() for k in ("audit", "log", "access"))]
    if atbls:
        audit_table = atbls[0]
        audit_count = conn.execute(f"SELECT COUNT(*) FROM {audit_table}").fetchone()[0]
        audit_ok = audit_count > 0
    conn.close()
except Exception as e:
    audit_table = f"ERROR:{e}"
status = "PASS" if audit_ok else "FAIL"
print(f"  [{status}] #9 Audit rows (table:{audit_table}): expected=>0 got={audit_count}")
report["probes"].append({"num": "9", "name": f"Audit rows in DB (table:{audit_table})", "expected": ">0", "got": str(audit_count), "passed": audit_ok})

# #10 — POST /api/valuation: auth accepted + route reachable (timeout=30s for LLM path)
print("  [....] #10 POST /api/valuation (auth) — waiting up to 30s...", end="", flush=True)
code = http("POST", "/api/valuation",
    headers={"Authorization": f"Bearer {tok_user}"},
    body={"profile_key": "residential", "data": {"property_type": "apartment", "area": 120, "location": "Cairo"}},
    timeout=30)
ok = code in (200, 422, 400)
status = "PASS" if ok else "FAIL"
print(f"\r  [{status}] #10 POST /api/valuation (auth): expected=200/422/400 got={code}")
report["probes"].append({"num": "10", "name": "POST /api/valuation (auth token)", "expected": "200/422/400", "got": str(code), "passed": ok})

passed_probes = sum(1 for p in report["probes"] if p["passed"])
print(f"\n  Probes: {passed_probes}/{len(report['probes'])} passed")

# ── Phase 5: Tooling ──────────────────────────────────────────────────────────
print("\n=== Phase 5: Tooling ===")

def run_tool(name, cmd, cwd=None, env_extra=None):
    e = env.copy()
    if env_extra:
        e.update(env_extra)
    r = subprocess.run(cmd, cwd=cwd or str(REPO_ROOT), env=e,
                       capture_output=True, text=True, timeout=30)
    ok = r.returncode == 0
    print(f"  {'PASS' if ok else 'FAIL'} — {name}")
    if not ok:
        print(f"    stderr: {r.stderr[:300]}")
    report["tooling"].append({"name": name, "passed": ok, "stdout": r.stdout[:500], "stderr": r.stderr[:300]})
    return ok, r

DR_BACKUP_DIR.mkdir(exist_ok=True)
run_tool("backup_reports.py",
    [sys.executable, "tools/backup_reports.py",
     "--source", str(DR_DB),
     "--dest-dir", str(DR_BACKUP_DIR),
     "--retention-days", "30"])

run_tool("export_reports_json.py",
    [sys.executable, "tools/export_reports_json.py",
     "--db", str(DR_DB),
     "--out", str(DR_EXPORT_FILE),
     "--pretty"])

run_tool("apply_retention.py",
    [sys.executable, "tools/apply_retention.py",
     "--db", str(DR_DB)])

# ── Phase 7: Cleanup ──────────────────────────────────────────────────────────
print("\n=== Phase 7: Cleanup ===")
srv.terminate()
try:
    srv.wait(timeout=8)
except subprocess.TimeoutExpired:
    srv.kill()
print(f"  Server PID {srv.pid} stopped (exit={srv.returncode})")

for path in [DR_DB, DR_EXPORT_FILE]:
    try: path.unlink(missing_ok=True)
    except: pass
try: shutil.rmtree(DR_BACKUP_DIR, ignore_errors=True)
except: pass
print("  Temp files cleaned up")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n=== Summary ===")
all_pass = [p["passed"] for p in report["probes"]] + [t["passed"] for t in report["tooling"]]
all_pass += list(report["env"].values()) + [report["boot"]["started"]]
total_pass = sum(all_pass)
total = len(all_pass)
print(f"  Total checks: {total}  Pass: {total_pass}  Fail: {total - total_pass}")

json.dump(report, open(str(RESULTS_FILE), "w"), indent=2)
print(f"  Results saved to: {RESULTS_FILE}")
