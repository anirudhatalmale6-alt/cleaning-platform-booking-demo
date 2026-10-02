"""Worker document uploads, and everything they have to refuse.

These are ID copies and police clearances. The interesting tests are not
the ones where a valid PDF goes in and comes back out; they are the ones
where somebody tries to put a PHP file on the server, read a file they do
not own, or fetch a document without being an admin.

    python3 test_uploads.py --base http://127.0.0.1:8000 \
                            --mysql "--socket=/var/run/mysqld/mysqld.sock -u root"

Reload seed.sql first.
"""
import io, json, mimetypes, os, shlex, subprocess, sys, urllib.error, urllib.request
import http.cookiejar, uuid, zlib, struct, pathlib

BASE  = "http://127.0.0.1:8000"
MYSQL = ["--socket=/var/run/mysqld/mysqld.sock", "-u", "root"]
for i, a in enumerate(sys.argv):
    if a == "--base":
        BASE = sys.argv[i + 1].rstrip("/")
    if a == "--mysql":
        MYSQL = shlex.split(sys.argv[i + 1])

API = BASE + "/api"
fails = []


def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label}: {got}" + ("" if ok else f"  (expected {want})"))
    if not ok:
        fails.append(label)


def sql(query):
    p = subprocess.run(["mysql", *MYSQL, "sparrow", "--batch", "--raw", "-e", query],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    lines = p.stdout.rstrip("\n").split("\n")
    if len(lines) < 2:
        return []
    head = [h.lower() for h in lines[0].split("\t")]
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:]]


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))

    def call(self, path, payload=None, method=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(API + path, data=data,
                                     method=method or ("POST" if data else "GET"),
                                     headers={"Content-Type": "application/json"})
        try:
            with self.opener.open(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw[:200].decode("utf8", "replace")}

    def upload(self, fields, filename, content, field_type="application/octet-stream"):
        """multipart/form-data, hand-built so the exact bytes are controlled."""
        boundary = "----sparrow" + uuid.uuid4().hex
        body = io.BytesIO()
        for k, v in fields.items():
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
            body.write(f"{v}\r\n".encode())
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                   .encode())
        body.write(f"Content-Type: {field_type}\r\n\r\n".encode())
        body.write(content)
        body.write(f"\r\n--{boundary}--\r\n".encode())
        req = urllib.request.Request(
            API + "/employee/documents", data=body.getvalue(), method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with self.opener.open(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw[:300].decode("utf8", "replace")}

    def raw_get(self, url):
        try:
            with self.opener.open(urllib.request.Request(url)) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()


# ------------------------------------------------------------ fixtures
def png_bytes(w=400, h=400):
    """A real PNG, built here so the test does not depend on a file on disk."""
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + bytes([(x * 7) % 256 for x in range(w * 3)]) for _ in range(h))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


PDF = (b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
       b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
       b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
       b"trailer<</Root 1 0 R>>\n%%EOF\n")

APPLICANT = {
    "first_name": "Upload", "last_name": "Tester",
    "email": "upload.tester@example.co.za", "phone": "082 555 0144",
    "date_of_birth": "1994-03-18", "id_type": "sa_id",
    # Fictional, but structurally valid: the birth date inside it matches
    # date_of_birth and the check digit is right. The first version of this
    # file had an invented number, and the API correctly threw it out.
    "id_number": "9403185800080",
    "service_group": "indoor", "years_experience": 3,
    "languages": ["English"], "areas": [{"province": "Western Cape", "city": "Cape Town"}],
}

anon = Client()

print("1. The server says whether storage is sitting in the public folder")
st, h = anon.call("/health")
check("health answers", st, 200)
check("and reports on the upload folder", "storage_exposed" in h, True)
check("and on the limit a worker will really hit", h.get("upload_mb", 0) > 0, True)
if h.get("storage_exposed"):
    print("       note: storage IS inside the web root on this install. Fine for a")
    print("       dev run, must be moved on a real host. Tested below either way.")

print("\n2. An application hands back a one-time upload token")
sql(f"DELETE FROM employees WHERE email = '{APPLICANT['email']}'")
st, created = anon.call("/employee/apply", APPLICANT)
check("the application is created", st, 201)
check("it is pending", created.get("account_status"), "pending")
check("a token comes back", len(created.get("upload_token", "")) >= 32, True)
check("the token is not stored in the clear",
      sql(f"SELECT upload_token_hash h FROM employees WHERE id={created['id']}")[0]["h"]
      != created["upload_token"], True)
emp_id, token = created["id"], created["upload_token"]

print("\n3. A real document uploads")
st, doc = anon.upload({"doc_type": "id", "employee_id": emp_id, "upload_token": token},
                      "my id copy.pdf", PDF, "application/pdf")
check("accepted", st, 201)
check("the type was read from the bytes, not the request", doc.get("mime"), "application/pdf")
rows = sql(f"SELECT * FROM employee_documents WHERE employee_id={emp_id}")
check("one row written", len(rows), 1)
check("the original name is kept for display", rows[0]["original_name"], "my id copy.pdf")
check("but the stored name is ours, not theirs",
      "my id copy.pdf" in rows[0]["file_path"], False)
check("and it is under this employee's own folder",
      rows[0]["file_path"].startswith(f"employees/{emp_id}/"), True)

print("\n4. A photo uploads, and its dimensions are recorded")
st, doc = anon.upload({"doc_type": "photo", "employee_id": emp_id, "upload_token": token},
                      "selfie.png", png_bytes(400, 300), "image/png")
check("accepted", st, 201)
r = sql(f"SELECT * FROM employee_documents WHERE employee_id={emp_id} AND doc_type='photo'")[0]
check("width recorded", int(r["width_px"]), 400)
check("height recorded", int(r["height_px"]), 300)

print("\n5. Uploading the same kind again replaces it, it does not pile up")
old_path = r["file_path"]
st, _ = anon.upload({"doc_type": "photo", "employee_id": emp_id, "upload_token": token},
                    "better-selfie.png", png_bytes(500, 500), "image/png")
check("accepted", st, 201)
rows = sql(f"SELECT * FROM employee_documents WHERE employee_id={emp_id} AND doc_type='photo'")
check("still one photo, not two", len(rows), 1)
check("and it is the new one", rows[0]["original_name"], "better-selfie.png")

print("\n6. What it refuses")
# A PHP file renamed to .pdf. This is the one that matters: if it lands on
# disk somewhere the server will execute, the site is gone.
st, r6 = anon.upload({"doc_type": "criminal_check", "employee_id": emp_id, "upload_token": token},
                     "clearance.pdf", b"<?php system($_GET['c']); ?>", "application/pdf")
check("a PHP script renamed to .pdf is refused", st, 422)
check("and the message names what it really was", "php" in r6["error"].lower()
      or "text" in r6["error"].lower(), True)

# Valid PNG magic bytes, rubbish after them.
st, r6b = anon.upload({"doc_type": "photo", "employee_id": emp_id, "upload_token": token},
                      "fake.png", b"\x89PNG\r\n\x1a\n" + b"not an image at all" * 20, "image/png")
check("a file that only starts like a PNG is refused", st, 422)

st, r6c = anon.upload({"doc_type": "photo", "employee_id": emp_id, "upload_token": token},
                      "tiny.png", png_bytes(40, 40), "image/png")
check("an image too small to identify anyone is refused", st, 422)

st, r6d = anon.upload({"doc_type": "photo", "employee_id": emp_id, "upload_token": token},
                      "doc.pdf", PDF, "application/pdf")
check("a PDF as a profile photo is refused", st, 422)
check("with a reason that makes sense to a person",
      "picture" in r6d["error"], True)

# Comfortably over both the app's setting and PHP's own ceiling, whichever
# is lower on this install. The two produce different messages, and both
# have to tell the person something they can act on.
st, limits = anon.call("/health")
big = PDF + b"0" * int((limits["upload_mb"] + 3) * 1024 * 1024)
st, r6e = anon.upload({"doc_type": "id", "employee_id": emp_id, "upload_token": token},
                      "huge.pdf", big, "application/pdf")
check("a file over the size limit is refused", st, 422)
check("and the message states a limit in MB", "MB" in r6e["error"], True)
if limits["upload_capped_by_php"]:
    check("php.ini is the real ceiling here, and the message says so",
          "php.ini" in r6e["error"], True)
    print("       note: php.ini caps uploads at",
          limits["upload_mb"], "MB, below the", 
          sql("SELECT setting_value v FROM settings WHERE setting_key='max_upload_mb'")[0]["v"],
          "MB in settings. Raise upload_max_filesize and post_max_size.")

st, r6f = anon.upload({"doc_type": "not_a_type", "employee_id": emp_id, "upload_token": token},
                      "x.pdf", PDF, "application/pdf")
check("an unknown document type is refused", st, 422)

print("\n7. A filename cannot escape the folder")
st, r7 = anon.upload({"doc_type": "work_permit", "employee_id": emp_id, "upload_token": token},
                     "../../../../index.php", PDF, "application/pdf")
check("accepted (the name is not used as a path)", st, 201)
row = sql(f"SELECT * FROM employee_documents WHERE employee_id={emp_id} "
          "AND doc_type='work_permit'")[0]
check("nothing traversed out of the employee folder",
      row["file_path"].startswith(f"employees/{emp_id}/") and ".." not in row["file_path"], True)
check("the displayed name has the path stripped off it",
      "/" not in row["original_name"], True)

print("\n8. The token is the only way in, and only for that one application")
st, r8 = anon.upload({"doc_type": "id", "employee_id": emp_id, "upload_token": "wrong"},
                     "x.pdf", PDF, "application/pdf")
check("a wrong token is refused", st, 403)
st, r8b = anon.upload({"doc_type": "id", "employee_id": 1, "upload_token": token},
                      "x.pdf", PDF, "application/pdf")
check("the right token for somebody else's id is refused", st, 403)
st, r8c = anon.upload({"doc_type": "id", "employee_id": emp_id},
                      "x.pdf", PDF, "application/pdf")
check("no token at all is refused", st, 403)
check("all three give the same answer, so ids cannot be probed",
      r8["error"] == r8b["error"] == r8c["error"], True)

print("\n9. An expired token stops working")
sql(f"UPDATE employees SET upload_token_expires = DATE_SUB(NOW(), INTERVAL 1 MINUTE) "
    f"WHERE id = {emp_id}")
st, _ = anon.upload({"doc_type": "id", "employee_id": emp_id, "upload_token": token},
                    "x.pdf", PDF, "application/pdf")
check("refused once it has expired", st, 403)
sql(f"UPDATE employees SET upload_token_expires = DATE_ADD(NOW(), INTERVAL 2 HOUR) "
    f"WHERE id = {emp_id}")

print("\n10. The files are not reachable over the web")
paths = sql(f"SELECT file_path FROM employee_documents WHERE employee_id={emp_id}")
for p in paths:
    for prefix in ("/backend/storage/", "/storage/"):
        code, _, _ = anon.raw_get(BASE + prefix + p["file_path"])
        check(f"{prefix}… is not served", code in (403, 404), True)

print("\n11. Only an admin can download one, and it comes back as an attachment")
doc_id = sql(f"SELECT id FROM employee_documents WHERE employee_id={emp_id} "
             "AND doc_type='id'")[0]["id"]
code, _, _ = anon.raw_get(f"{API}/admin/documents/{doc_id}")
check("a stranger cannot", code, 401)

emp = Client()
emp.call("/employee/login", {"email": "nomsa.m@example.co.za", "password": "demo1234"})
code, _, _ = emp.raw_get(f"{API}/admin/documents/{doc_id}")
check("nor can a signed-in cleaner", code, 401)

cust = Client()
cust.call("/customer/login", {"email": "thandi.m@example.co.za", "password": "demo1234"})
code, _, _ = cust.raw_get(f"{API}/admin/documents/{doc_id}")
check("nor a customer", code, 401)

adm = Client()
adm.call("/admin/login", {"email": "lebo@sparrow.co.za", "password": "demo1234"})
code, headers, body = adm.raw_get(f"{API}/admin/documents/{doc_id}")
check("an admin can", code, 200)
check("and gets the file itself", body[:5], b"%PDF-")
check("served as a download, never rendered in place",
      headers.get("Content-Disposition", "").startswith("attachment"), True)
check("with sniffing turned off", headers.get("X-Content-Type-Options"), "nosniff")
check("and never cached", "no-store" in (headers.get("Cache-Control") or ""), True)

print("\n12. An approved cleaner can replace her own photo, and only her own")
st, _ = emp.upload({"doc_type": "photo"}, "nomsa.png", png_bytes(600, 600), "image/png")
check("her own photo uploads with no token", st, 201)
nomsa_id = sql("SELECT id FROM employees WHERE email='nomsa.m@example.co.za'")[0]["id"]
rows = sql(f"SELECT * FROM employee_documents WHERE employee_id={nomsa_id} AND doc_type='photo'")
check("it landed on her record", rows[0]["original_name"], "nomsa.png")
# the id in the form is ignored for a signed-in worker: the session decides
st, _ = emp.upload({"doc_type": "photo", "employee_id": emp_id, "upload_token": token},
                   "hijack.png", png_bytes(300, 300), "image/png")
other = sql(f"SELECT original_name FROM employee_documents WHERE employee_id={emp_id} "
            "AND doc_type='photo'")[0]
check("she cannot write to another worker's record by passing their id",
      other["original_name"], "better-selfie.png")

print("\n13. The admin screen lists what was actually uploaded")
st, apps = adm.call("/admin/applications")
mine = next((a for a in apps["applications"] if a["id"] == str(emp_id)
             or a["id"] == emp_id), None)
check("the application is in the queue", mine is not None, True)
check("with its documents attached", len(mine["documents"]) >= 3, True)
check("and the ID number still masked", "*" in mine["id_number"], True)

print("\n14. Deleting a worker takes their files' rows with them")
before = len(sql(f"SELECT id FROM employee_documents WHERE employee_id={emp_id}"))
check("there were some", before > 0, True)
sql(f"DELETE FROM employees WHERE id = {emp_id}")
check("and none are left behind",
      len(sql(f"SELECT id FROM employee_documents WHERE employee_id={emp_id}")), 0)

print("\n" + "=" * 60)
if fails:
    print(f"{len(fails)} FAILED")
    for f in fails:
        print("  -", f)
    sys.exit(1)
print("all upload checks passed")
