"""Nagebootste Microsoft Graph voor tests (alleen wat Plakzicht Mail gebruikt).

FG_PARTIAL=1: bij wijzigingen alleen id en isRead terugsturen (zoals Microsoft soms doet)."""
import json, os, re, sys, uuid, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = []
WK = {"inbox": "Postvak IN", "drafts": "Concepten", "sentitems": "Verzonden items", "deleteditems": "Verwijderde items",
      "archive": "Archief", "junkemail": "Ongewenste e-mail"}
DB = {}  # adres -> {folders: {id: {...}}, wk: {name: id}, msgs: {id: {...}}, atts: {msgid: [..]}}
DENY = {"geheim@jouwbedrijf.nl"}
CODES = {}
RTS = set()
RTUSER = {}
DEVICE = {}
CALS = {}
# welk account bij welke mailbox mag (account zonder regel: overal)
ACCESS = {"anna@jouwbedrijf.nl": {"anna@jouwbedrijf.nl", "verkoop@jouwbedrijf.nl"},
          "sven@jouwbedrijf.nl": {"sven@jouwbedrijf.nl", "info@jouwbedrijf.nl"}}
SEQ = [0]
DELTA_SINCE = {}
DELTA_DENY = {'verkoop@jouwbedrijf.nl'}
TOMB = {}  # (addr, folder) -> [(seq, id)]


def nid():
    return "AAMk" + uuid.uuid4().hex + "="


def box(addr):
    if addr not in DB:
        b = {"folders": {}, "wk": {}, "msgs": {}, "atts": {}}
        for k, n in WK.items():
            fid = nid()
            b["folders"][fid] = {"id": fid, "displayName": n, "parentFolderId": "root"}
            b["wk"][k] = fid
        DB[addr] = b
        inbox = b["wk"]["inbox"]
        for i, (subj, frm) in enumerate([("Vraag over order 000000412", "inkoop@brouwerijdehop.nl"),
                                         ("Factuur met bijlage", "facturen@vinylgroothandel.nl"),
                                         ("Re: Offerte OFF-2026-121", "hallo@koffiebarbonen.nl"),
                                         ("Oud: offerte stickers 2025", "oud@klant.nl"),
                                         ("Oud: jaaroverzicht 2024", "boekhouding@klant.nl")]):
            mid = nid()
            b["msgs"][mid] = {"id": mid, "subject": subj, "parentFolderId": inbox, "isRead": i == 2,
                              "from": {"emailAddress": {"name": frm.split("@")[0], "address": frm}},
                              "toRecipients": [{"emailAddress": {"address": addr}}], "ccRecipients": [],
                              "receivedDateTime": ["2026-10-28", "2026-10-27", "2026-10-26", "2025-11-03", "2024-12-15"][i] + "T09:00:00Z",
                              "sentDateTime": ["2026-10-28", "2026-10-27", "2026-10-26", "2025-11-03", "2024-12-15"][i] + "T08:59:00Z",
                              "bodyPreview": subj + " tekst", "body": {"contentType": "html", "content": f"<p>{subj}</p><img src=\"cid:logo1\">"},
                              "categories": [], "flag": {"flagStatus": "notFlagged"}, "hasAttachments": i == 1}
            bump(b["msgs"][mid])
            if i == 1:
                b["atts"][mid] = [{"@odata.type": "#microsoft.graph.fileAttachment", "id": "att1", "name": "factuur.pdf",
                                   "contentType": "application/pdf", "size": 10, "contentBytes": "JVBERi0=", "isInline": False},
                                  {"@odata.type": "#microsoft.graph.fileAttachment", "id": "att2", "name": "logo.png",
                                   "contentType": "image/png", "size": 5, "contentBytes": "iVBOR", "isInline": True, "contentId": "logo1"}]
    return DB[addr]


def bump(m):
    SEQ[0] += 1; m["_seq"] = SEQ[0]


def tomb(addr, folder, mid):
    SEQ[0] += 1; TOMB.setdefault((addr, folder), []).append((SEQ[0], mid))


def clean(m):
    return {k: v for k, v in m.items() if not k.startswith("_") and k != "body"}


def folder_view(b, f):
    kids = [x for x in b["folders"].values() if x["parentFolderId"] == f["id"]]
    msgs = [m for m in b["msgs"].values() if m["parentFolderId"] == f["id"]]
    return {**f, "childFolderCount": len(kids), "unreadItemCount": sum(not m["isRead"] for m in msgs), "totalItemCount": len(msgs)}


def resolve(b, fid):
    return b["wk"].get(fid.lower(), fid)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj=None):
        data = json.dumps(obj).encode() if obj is not None else b""
        self.send_response(code)
        if obj is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def err(self, code, c, msg):
        self.send(code, {"error": {"code": c, "message": msg}})

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def handle_any(self, method):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        path = urllib.parse.unquote(u.path)
        LOG.append((method, path, q))
        if path.endswith("/oauth2/v2.0/devicecode"):
            n = int(self.headers.get("Content-Length") or 0); self.rfile.read(n)
            dc = "dc-" + uuid.uuid4().hex; uc = uuid.uuid4().hex[:8].upper()
            DEVICE[dc] = {"user": uc, "approved": None}
            return self.send(200, {"device_code": dc, "user_code": uc, "verification_uri": "https://microsoft.com/devicelogin",
                                   "interval": 1, "expires_in": 900})
        if path == "/approve":  # test: code goedkeuren als account q[upn]
            for d in DEVICE.values():
                if d["user"] == q["code"]:
                    d["approved"] = q["upn"]
            return self.send(200, {"ok": True})
        if path.endswith("/oauth2/v2.0/authorize"):
            if q.get("client_id") != "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee":
                return self.send(400, {"error": "unauthorized_client", "error_description": "AADSTS700016: app not found"})
            code = "code-" + uuid.uuid4().hex
            CODES[code] = (q["code_challenge"], q["redirect_uri"])
            loc = q["redirect_uri"] + "?" + urllib.parse.urlencode({"code": code, "state": q["state"]})
            self.send_response(302); self.send_header("Location", loc); self.send_header("Content-Length", "0"); self.end_headers(); return
        if path.endswith("/oauth2/v2.0/token"):
            n = int(self.headers.get("Content-Length") or 0)
            form = dict(urllib.parse.parse_qsl(self.rfile.read(n).decode()))
            g = form.get("grant_type")
            if g == "urn:ietf:params:oauth:grant-type:device_code":
                d = DEVICE.get(form.get("device_code"))
                if not d or not d["approved"]:
                    return self.send(400, {"error": "authorization_pending", "error_description": "AADSTS70016: pending"})
                import base64
                upn = d["approved"]; rt = "rt-" + uuid.uuid4().hex; RTS.add(rt); RTUSER[rt] = upn
                claims = base64.urlsafe_b64encode(json.dumps({"name": upn.split("@")[0].title(), "preferred_username": upn}).encode()).decode().rstrip("=")
                DEVICE.pop(form["device_code"])
                return self.send(200, {"access_token": "tok:" + upn, "refresh_token": rt, "expires_in": 3600, "id_token": "x." + claims + ".y"})
            if g == "authorization_code":
                import hashlib, base64
                ch, ru = CODES.pop(form.get("code"), (None, None))
                calc = base64.urlsafe_b64encode(hashlib.sha256(form.get("code_verifier", "").encode()).digest()).decode().rstrip("=")
                if ch != calc or ru != form.get("redirect_uri"):
                    return self.send(400, {"error": "invalid_grant", "error_description": "AADSTS70008: bad code"})
                rt = "rt-" + uuid.uuid4().hex; RTS.add(rt)
                claims = base64.urlsafe_b64encode(json.dumps({"name": "Sven Beheerder", "preferred_username": "sven@jouwbedrijf.nl"}).encode()).decode().rstrip("=")
                return self.send(200, {"access_token": "tok", "refresh_token": rt, "expires_in": 3600, "id_token": "x." + claims + ".y"})
            if g == "refresh_token":
                rt = form.get("refresh_token")
                if os.environ.get("FG_ANYRT") and rt and rt.startswith("rt-") and rt not in RTS:
                    RTS.add(rt)
                if rt not in RTS:
                    return self.send(400, {"error": "invalid_grant", "error_description": "AADSTS50173: The provided grant has expired"})
                RTS.discard(rt); new = "rt-" + uuid.uuid4().hex; RTS.add(new); upn = RTUSER.pop(rt, "sven@jouwbedrijf.nl"); RTUSER[new] = upn
                return self.send(200, {"access_token": "tok:" + upn, "refresh_token": new, "expires_in": 3600})
            if form.get("client_secret") != "goed-geheim":
                return self.send(401, {"error": "invalid_client", "error_description": "AADSTS7000215: Invalid client secret provided."})
            return self.send(200, {"access_token": "tok", "expires_in": 3600})
        auth = self.headers.get("Authorization") or ""
        if not auth.startswith("Bearer tok"):
            return self.err(401, "InvalidAuthenticationToken", "no")
        who = auth[len("Bearer tok:"):] if auth.startswith("Bearer tok:") else None
        if path.startswith("/v1.0/me/calendars") or path.startswith("/v1.0/me/events"):
            cals = CALS.setdefault(who, {"cal-" + who: {"id": "cal-" + who, "name": "Agenda", "hexColor": "", "canEdit": True, "isDefaultCalendar": True, "events": {}}})
            p2 = path[len("/v1.0/me/"):].split("/")
            allev = {eid: (c, e) for c in cals.values() for eid, e in c["events"].items()}
            if p2[0] == "calendars" and len(p2) == 1:
                return self.send(200, {"value": [{k: v for k, v in c.items() if k != "events"} for c in cals.values()]})
            if p2[0] == "calendars" and p2[2] == "calendarView":
                c = cals.get(p2[1]) or {"events": {}}
                st, en = q.get("startDateTime", ""), q.get("endDateTime", "")
                v = [e for e in c["events"].values() if e["start"]["dateTime"] < en and e["end"]["dateTime"] > st]
                return self.send(200, {"value": sorted(v, key=lambda e: e["start"]["dateTime"])})
            if p2[0] == "calendars" and p2[2] == "events" and method == "POST":
                d = self.body(); eid = "ev" + uuid.uuid4().hex[:10]
                d.update({"id": eid, "isOrganizer": True, "organizer": {"emailAddress": {"name": who, "address": who}},
                          "bodyPreview": re.sub("<[^>]+>", "", (d.get("body") or {}).get("content", ""))[:100], "type": "singleInstance"})
                cals[p2[1]]["events"][eid] = d
                return self.send(201, d)
            if p2[0] == "events":
                if p2[1] not in allev:
                    return self.err(404, "ErrorItemNotFound", "not found")
                c, e = allev[p2[1]]
                if method == "GET":
                    return self.send(200, e)
                if method == "PATCH":
                    e.update(self.body()); return self.send(200, e)
                if method == "DELETE":
                    c["events"].pop(p2[1]); return self.send(204)
        if path == "/v1.0/me":
            return self.send(200, {"id": "oid-" + (who or "app"), "mail": (who or "").replace("@jouwbedrijf.nl", "@mail.jouwbedrijf.nl"),
                                   "userPrincipalName": who, "displayName": who})
        if path.startswith("/v1.0/users/oid-"):
            path = path.replace("/users/oid-", "/users/", 1)
        m = re.match(r"^/v1\.0/users/([^/]+)(/.*)$", path)
        if not m:
            return self.err(404, "ResourceNotFound", "?")
        addr, rest = m.group(1), m.group(2)
        if who and ACCESS.get(who) is not None and addr not in ACCESS[who]:
            return self.err(403, "ErrorAccessDenied", "Access is denied. Check credentials and try again.")
        if addr in DENY:
            return self.err(403, "ErrorAccessDenied", "Access is denied.")
        if not addr.endswith("@jouwbedrijf.nl"):
            return self.err(404, "ErrorInvalidUser", "The requested user is invalid.")
        b = box(addr)
        p = rest.strip("/").split("/")
        # mailFolders
        if p[0] == "mailFolders":
            if len(p) == 1:
                if method == "GET":
                    return self.send(200, {"value": [folder_view(b, f) for f in b["folders"].values() if f["parentFolderId"] == "root"]})
                if method == "POST":
                    d = self.body(); fid = nid()
                    if any(f["displayName"] == d["displayName"] and f["parentFolderId"] == "root" for f in b["folders"].values()):
                        return self.err(409, "ErrorFolderExists", "exists")
                    b["folders"][fid] = {"id": fid, "displayName": d["displayName"], "parentFolderId": "root"}
                    return self.send(201, folder_view(b, b["folders"][fid]))
            fid = resolve(b, p[1])
            if fid not in b["folders"]:
                return self.err(404, "ErrorItemNotFound", "folder not found")
            f = b["folders"][fid]
            if len(p) == 2:
                if method == "GET":
                    return self.send(200, folder_view(b, f))
                if method == "PATCH":
                    f["displayName"] = self.body()["displayName"]; return self.send(200, folder_view(b, f))
                if method == "DELETE":
                    def rm(x):
                        for k in [k for k, v in b["folders"].items() if v["parentFolderId"] == x]:
                            rm(k)
                        for mm in b["msgs"].values():
                            if mm["parentFolderId"] == x:
                                mm["parentFolderId"] = b["wk"]["deleteditems"]
                        b["folders"].pop(x, None)
                    rm(fid); return self.send(204)
            if p[2] == "childFolders":
                if method == "GET":
                    return self.send(200, {"value": [folder_view(b, x) for x in b["folders"].values() if x["parentFolderId"] == fid]})
                d = self.body(); nf = nid()
                if any(x["displayName"] == d["displayName"] and x["parentFolderId"] == fid for x in b["folders"].values()):
                    return self.err(409, "ErrorFolderExists", "exists")
                b["folders"][nf] = {"id": nf, "displayName": d["displayName"], "parentFolderId": fid}
                return self.send(201, folder_view(b, b["folders"][nf]))
            if p[2] == "move":
                dest = self.body()["destinationId"]
                f["parentFolderId"] = "root" if dest == "msgfolderroot" else resolve(b, dest)
                return self.send(201, folder_view(b, f))
            if p[2] == "messages" and len(p) > 3 and p[3] == "delta" and (addr in DELTA_DENY or b["folders"][fid]["displayName"] == "Ongewenste e-mail"):
                return self.err(403, "ErrorAccessDenied", "Access is denied. Check credentials and try again.")
            if p[2] == "messages" and len(p) > 3 and p[3] == "delta":
                t = int(q.get("$deltatoken", "0") or 0)
                since = ""
                mm2 = re.search(r"receivedDateTime ge (\S+)", q.get("$filter", ""))
                if mm2: since = mm2.group(1)
                if not t and since: DELTA_SINCE[(addr, fid)] = since
                since = DELTA_SINCE.get((addr, fid), "") if t else since
                items = [clean(m) for m in b["msgs"].values() if m["parentFolderId"] == fid and m.get("_seq", 0) > t
                         and (t or (m.get("receivedDateTime") or "") >= since)]
                if t and os.environ.get("FG_PARTIAL"):  # zoals Microsoft soms doet: alleen id en gewijzigde velden
                    items = [{"id": x["id"], "isRead": x.get("isRead")} for x in items]
                if t:
                    items += [{"id": mid, "@removed": {"reason": "deleted"}} for s2, mid in TOMB.get((addr, fid), [])
                              if s2 > t and (mid not in b["msgs"] or b["msgs"][mid]["parentFolderId"] != fid)]
                base = f"http://127.0.0.1:{self.server.server_port}/v1.0/users/{addr}/mailFolders/{fid}/messages/delta"
                return self.send(200, {"value": items, "@odata.deltaLink": base + "?$deltatoken=" + str(SEQ[0])})
            if p[2] == "messages":
                if method == "POST":
                    d = self.body(); mid = nid()
                    props = {x["id"]: x["value"] for x in d.get("singleValueExtendedProperties", [])}
                    assert props.get("Integer 0x0E07") == "1", props
                    msg = {"id": mid, "parentFolderId": fid, "isRead": True, "bodyPreview": "kopie",
                           "receivedDateTime": props.get("SystemTime 0x0E06"), "sentDateTime": props.get("SystemTime 0x0039"),
                           "hasAttachments": False, "categories": d.get("categories", []), "flag": d.get("flag", {"flagStatus": "notFlagged"}),
                           **{k: d[k] for k in ("subject", "body", "from", "toRecipients", "ccRecipients") if k in d}}
                    b["msgs"][mid] = msg; bump(msg)
                    return self.send(201, msg)
                if b["folders"][fid]["displayName"] == "Ongewenste e-mail":
                    return self.err(403, "ErrorAccessDenied", "Access is denied.")
                items = [x for x in b["msgs"].values() if x["parentFolderId"] == fid]
                flt = q.get("$filter", "")
                mm3 = re.search(r"receivedDateTime lt (\S+)", flt)
                if mm3:
                    items = [x for x in items if (x.get("receivedDateTime") or "") < mm3.group(1)]
                if "isRead eq false" in flt:
                    items = [x for x in items if not x["isRead"]]
                if "flagged" in flt:
                    items = [x for x in items if x["flag"]["flagStatus"] == "flagged"]
                if "$search" in q:
                    t = q["$search"].strip('"').lower()
                    items = [x for x in items if t in x["subject"].lower()]
                items.sort(key=lambda x: x.get("receivedDateTime") or "", reverse=True)
                mm4 = re.search(r"receivedDateTime ge (\S+)", flt)
                if mm4:
                    items = [x for x in items if (x.get("receivedDateTime") or "") >= mm4.group(1)]
                if "$expand" in q:
                    return self.send(200, {"value": [{"id": x["id"], "singleValueExtendedProperties": [{"id": "Integer 0x0E08", "value": str(len(json.dumps(x)) + 2048)}]} for x in items]})
                return self.send(200, {"value": [{k: v for k, v in x.items() if k != "body"} for x in items]})
        if p[0] == "messages":
            if len(p) == 1:
                flt = q.get("$filter", "")
                mm = re.search(r"c eq '(.*)'\)", flt)
                items = [x for x in b["msgs"].values() if mm and mm.group(1).replace("''", "'") in x["categories"]]
                return self.send(200, {"value": items})
            mid = p[1]
            if mid not in b["msgs"]:
                return self.err(404, "ErrorItemNotFound", "The specified object was not found in the store.")
            msg = b["msgs"][mid]
            if len(p) == 2:
                if method == "GET":
                    return self.send(200, msg)
                if method == "PATCH":
                    d = self.body()
                    if "flag" in d:
                        msg["flag"] = d["flag"]
                    for k in ("isRead", "categories"):
                        if k in d:
                            msg[k] = d[k]
                    bump(msg)
                    return self.send(200, msg)
                if method == "DELETE":
                    tomb(addr, msg["parentFolderId"], mid); del b["msgs"][mid]; return self.send(204)
            if p[2] == "move":
                dest = resolve(b, self.body()["destinationId"])
                if dest not in b["folders"]:
                    return self.err(404, "ErrorFolderNotFound", "dest not found")
                # Microsoft geeft een verplaatst bericht een nieuw id
                tomb(addr, msg["parentFolderId"], mid)
                del b["msgs"][mid]; new = dict(msg); new["id"] = nid(); new["parentFolderId"] = dest; b["msgs"][new["id"]] = new
                if mid in b["atts"]:
                    b["atts"][new["id"]] = b["atts"].pop(mid)
                bump(new)
                return self.send(201, new)
            if p[2] == "$value":
                mime = f"From: {msg['from']['emailAddress']['address']}\r\nSubject: {msg['subject']}\r\nContent-Type: text/html\r\n\r\n{msg['body']['content']}".encode()
                self.send_response(200); self.send_header("Content-Type", "text/plain"); self.send_header("Content-Length", str(len(mime))); self.end_headers(); self.wfile.write(mime); return
            if p[2] == "attachments":
                if method == "GET":
                    return self.send(200, {"value": b["atts"].get(mid, [])})
                d = self.body(); b["atts"].setdefault(mid, []).append(d); msg["hasAttachments"] = True
                return self.send(201, d)
        if p[0] == "sendMail":
            d = self.body()["message"]; mid = nid()
            b["msgs"][mid] = {"id": mid, "subject": d["subject"], "parentFolderId": b["wk"]["sentitems"], "isRead": True,
                              "from": {"emailAddress": {"address": addr}}, "toRecipients": d["toRecipients"], "ccRecipients": d.get("ccRecipients", []),
                              "receivedDateTime": "2026-10-29T12:00:00Z", "bodyPreview": "verzonden", "body": d["body"],
                              "categories": [], "flag": {"flagStatus": "notFlagged"}, "hasAttachments": bool(d.get("attachments")),
                              "_atts": d.get("attachments")}
            bump(b["msgs"][mid])
            return self.send(202)
        return self.err(400, "BadRequest", "onbekend: " + method + " " + path)

    def do_GET(self): self.handle_any("GET")
    def do_POST(self): self.handle_any("POST")
    def do_PATCH(self): self.handle_any("PATCH")
    def do_DELETE(self): self.handle_any("DELETE")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8790), H).serve_forever()
