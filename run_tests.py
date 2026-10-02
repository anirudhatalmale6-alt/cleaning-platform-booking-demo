"""Runs every suite and reports a single pass/fail.

    python3 run_tests.py                    the five browser suites
    python3 run_tests.py --with-backend \
        --base http://127.0.0.1:8000 \
        --mysql "-u root -pSECRET"          ...plus the database ones

The five browser suites need nothing but Chromium: they drive the pages
off the filesystem with no server and no database, which is also how the
published demo runs.

The backend suites need MySQL loaded with schema.sql and seed.sql, and the
site being served with PHP. They are opt-in because without those they
would fail for the wrong reason.
"""
import subprocess, sys, pathlib

HERE = pathlib.Path(__file__).parent
SUITES = ["test_booking.py", "test_customer.py", "test_cleaner.py",
          "test_admin.py", "test_theme.py"]

args = sys.argv[1:]
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default

BASE  = opt("--base", "http://127.0.0.1:8000")
MYSQL = opt("--mysql", "-u root")

BACKEND = []
if "--with-backend" in args:
    BACKEND = [
        ("backend/test_schema.py",       MYSQL.split()),
        ("backend/tests/test_parity.py", ["--base", BASE]),
        ("backend/tests/test_api.py",    ["--base", BASE]),
        ("backend/tests/test_live.py",   ["--base", BASE, "--mysql", MYSQL]),
    ]

results = []
for s in SUITES:
    print("=" * 64)
    print(s)
    print("=" * 64)
    r = subprocess.run([sys.executable, str(HERE / s)], cwd=HERE)
    results.append((s, r.returncode))
    print()

for s, extra in BACKEND:
    print("=" * 64)
    print(s)
    print("=" * 64)
    # seed.sql is reloaded before each one: they book, approve and cancel
    # real rows, so a suite that ran first would change what the next sees.
    subprocess.run(["mysql", *MYSQL.split(), "sparrow"],
                   stdin=open(HERE / "backend" / "seed.sql"))
    r = subprocess.run([sys.executable, str(HERE / s), *extra], cwd=HERE)
    results.append((s, r.returncode))
    print()

print("=" * 64)
bad = [s for s, code in results if code != 0]
for s, code in results:
    print(f"  {'PASS' if code == 0 else 'FAIL'}  {s}")
print("=" * 64)
sys.exit(1 if bad else 0)
