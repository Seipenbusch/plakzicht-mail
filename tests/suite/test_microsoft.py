"""Microsoft 365 tegen een nagebootste Graph: aanmelden met een code, mailbox koppelen, synchroniseren,
en Microsoft die bij wijzigingen alleen de gewijzigde velden stuurt (mails mogen dan niet leeg worden)."""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import TESTS, Client, Server, free_port, ok, start_proc, stop_all  # noqa: E402

gport = free_port()
start_proc([sys.executable, os.path.join(TESTS, "fakegraph.py"), str(gport)], {"FG_PARTIAL": "1"}, gport)
G = f"http://127.0.0.1:{gport}"


def fg(method, path, body=None):
    rq = urllib.request.Request(G + "/v1.0" + path, method=method, data=json.dumps(body).encode() if body else None,
                                headers={"Content-Type": "application/json", "Authorization": "Bearer tok"})
    return json.loads(urllib.request.urlopen(rq).read() or b"{}")


def wait(fn, timeout=40, what=""):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = fn()
        if r:
            return r
        time.sleep(0.5)
    raise AssertionError("duurde te lang: " + what)


srv = Server(env={"PLAKZICHT_GRAPH_URL": G + "/v1.0", "PLAKZICHT_LOGIN_URL": G, "PLAKZICHT_DOCKER": "1"})
try:
    adm = Client(srv.base)
    adm.call("login", "beheerder", "demo")
    adm.call("save_ms_config", {"tenant": "11111111-2222-3333-4444-555555555555", "client_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "auth": "user"})
    cfg = adm.call("ms_config")
    assert cfg["local"] is False, "in Docker geen 'aanmelden via deze browser'"
    r = adm.call("ms_signin_start", "code")
    assert r["method"] == "code" and r["code"]
    urllib.request.urlopen(f"{G}/approve?code={r["code"]}&upn=sven@jouwbedrijf.nl").read()
    st = wait(lambda: (lambda s: s if s["state"] != "waiting" else None)(adm.call("ms_signin_status")), what="aanmelden")
    assert st["state"] == "ok", st
    conf = json.load(open(os.path.join(srv.data, "config.json")))
    assert conf["accounts"][0]["refresh"].startswith("enc1:"), "aanmelding versleuteld opgeslagen"
    ok("aanmelden met een code (zonder browser op de server); aanmelding versleuteld")

    adm.call("set_mode", "microsoft")
    adm = Client(srv.base)
    adm.call("login", "beheerder", "demo")
    try:
        adm.call("add_mailbox", "info@jouwbedrijf.nl", "gedeeld")
    except Exception as e:  # noqa: BLE001 - al gekoppeld als eigen mailbox is ook goed
        assert "bestaat" in str(e).lower() or "al" in str(e).lower(), e
    state = adm.call("state")
    mb = next(m for m in state["mailboxes"] if m["address"] == "info@jouwbedrijf.nl")
    inbox = next(f for f in mb["folders"] if f.get("wk") == "inbox")
    view = {"mailbox_id": mb["id"], "folder": inbox["id"]}
    mails = wait(lambda: adm.call("list_mails", view), what="eerste synchronisatie")
    assert all(m["subject"] and m["date"] for m in mails), mails
    ok(f"mailbox gesynchroniseerd ({len(mails)} mails)")

    # wijzigingen: Microsoft stuurt daarna alleen id + isRead
    adm.call("set_read", mails[0]["id"], True)
    adm.call("set_flag", mails[1]["id"], True)
    addr = "info@jouwbedrijf.nl"
    fid = fg("GET", f"/users/{addr}/mailFolders/inbox")["id"]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    fg("POST", f"/users/{addr}/mailFolders/{fid}/messages", {
        "subject": "Nieuwe aanvraag stickers", "from": {"emailAddress": {"name": "Klant", "address": "k@x.nl"}},
        "body": {"contentType": "HTML", "content": "<p>hoi</p>"},
        "singleValueExtendedProperties": [{"id": "Integer 0x0E07", "value": "1"}, {"id": "SystemTime 0x0E06", "value": now}]})
    after = wait(lambda: (lambda l: l if any(m["subject"] == "Nieuwe aanvraag stickers" for m in l) else None)(adm.call("list_mails", view)),
                 what="nieuwe mail")
    time.sleep(3)  # nog een synchronisatieronde met halve wijzigingen
    after = adm.call("list_mails", view)
    empty = [m for m in after if not m["subject"] or not m["date"] or not m["from_addr"]]
    assert not empty, empty
    byid = {m["id"]: m for m in after}
    assert byid[mails[0]["id"]]["is_read"] and byid[mails[1]["id"]]["flagged"]
    ok("halve wijzigingen van Microsoft: geen mails zonder onderwerp of datum, status klopt")
    print("OK")
finally:
    srv.close()
    stop_all()
