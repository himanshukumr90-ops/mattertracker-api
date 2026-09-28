"""Tests for the /health endpoint.

Two failure modes matter, in this order:
  1. It says everything is fine while alerts have stopped -- the alarm is then
     worse than none, because it is trusted.
  2. It cries outside court hours -- the alarm gets muted, and a muted alarm
     is worth nothing. Today's incident proves nobody watches by accident.
"""
import datetime, os, sys, unittest.mock as mock
os.environ.setdefault("BASE44_APP_ID","x"); os.environ.setdefault("BASE44_API_KEY","x")
sys.path.insert(0, "api")
import index as A

ok=fail=0
def check(l,c,d=""):
    global ok,fail
    if c: ok+=1; print(f"  ✅ {l}")
    else: fail+=1; print(f"  ❌ {l}  {d}")

def ist(y,m,d,hh,mm):
    return datetime.datetime(y,m,d,hh,mm)

print("1. When are courts considered sitting?")
for label, when, want in [
    ("Mon 09:44 before",   ist(2026,9,28,9,44),  False),
    ("Mon 09:45 opens",    ist(2026,9,28,9,45),  True),
    ("Mon 14:22 (today's outage)", ist(2026,9,28,14,22), True),
    ("Mon 16:29 last min", ist(2026,9,28,16,29), True),
    ("Mon 16:30 closes",   ist(2026,9,28,16,30), False),
    ("Mon 03:00 night",    ist(2026,9,28,3,0),   False),
    ("Sat 11:00 weekend",  ist(2026,10,3,11,0),  False),
]:
    check(label, A._courts_are_sitting(when) is want)

def call(sitting, board_age, phhc_code):
    """Drive the endpoint with a given world."""
    class BR:
        status_code = 200
        @staticmethod
        def json():
            if board_age is None: return []
            t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=board_age)
            return [{"last_updated": t.isoformat().replace("+00:00","Z")}]
    class PR:
        status_code = phhc_code
    def fake_get(url, **kw):
        return BR() if "base44" in url else PR()
    with A.app.test_request_context("/health"), \
         mock.patch.object(A, "_courts_are_sitting", lambda *a: sitting), \
         mock.patch.object(A.requests, "get", side_effect=fake_get):
        resp, code = A.health_check()
        return code, resp.get_json()

print("\n2. TODAY'S INCIDENT — would it have fired?")
code, body = call(sitting=True, board_age=4200, phhc_code=403)
check(f"court down + board 70 min stale -> 503 (got {code})", code == 503)
check("and the message names the cause", "court's own systems" in body["status"],
      body["status"])

print("\n3. Healthy court day stays quiet")
code, body = call(sitting=True, board_age=45, phhc_code=200)
check(f"fresh board + court reachable -> 200 (got {code})", code == 200)

print("\n4. The scraper dying, with the court fine")
code, body = call(sitting=True, board_age=3000, phhc_code=200)
check(f"board 50 min stale -> 503 (got {code})", code == 503)
check("message blames the scraper, not the court",
      "scraper is not updating" in body["status"], body["status"])

print("\n5. It must NOT cry outside court hours")
for label, age, phhc in [("night, board hours old", 20000, 200),
                         ("night, court unreachable", 20000, 403),
                         ("weekend, everything down", 99999, 500)]:
    code, body = call(sitting=False, board_age=age, phhc_code=phhc)
    check(f"{label} -> 200 (got {code})", code == 200)

print("\n6. A brief blip does not trip it")
code, body = call(sitting=True, board_age=540, phhc_code=200)   # 9 min, under the 10 min rule
check(f"board 9 min stale during a deploy -> 200 (got {code})", code == 200)
code, body = call(sitting=True, board_age=660, phhc_code=200)
check(f"board 11 min stale -> 503 (got {code})", code == 503)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
