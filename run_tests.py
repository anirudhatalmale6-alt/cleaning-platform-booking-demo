"""Runs every suite and reports a single pass/fail.

    python3 run_tests.py
"""
import subprocess, sys, pathlib

HERE = pathlib.Path(__file__).parent
SUITES = ["test_booking.py", "test_customer.py", "test_cleaner.py", "test_admin.py"]

results = []
for s in SUITES:
    print("=" * 64)
    print(s)
    print("=" * 64)
    r = subprocess.run([sys.executable, str(HERE / s)], cwd=HERE)
    results.append((s, r.returncode))
    print()

print("=" * 64)
bad = [s for s, code in results if code != 0]
for s, code in results:
    print(f"  {'PASS' if code == 0 else 'FAIL'}  {s}")
print("=" * 64)
sys.exit(1 if bad else 0)
