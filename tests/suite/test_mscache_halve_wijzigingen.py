"""Synchronisatie: Microsoft stuurt bij een wijziging soms alleen de gewijzigde velden; onderwerp en datum moeten blijven."""
import sys, json, tempfile, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mscache import MailCache
from graph import GraphError
db = os.path.join(tempfile.mkdtemp(), 'c.db')
FULL = {"m1": {"id": "m1", "subject": "Offerte stickers", "from": {"emailAddress": {"name": "Jan", "address": "jan@x.nl"}},
               "receivedDateTime": "2026-10-30T10:00:00Z", "isRead": False, "bodyPreview": "hoi", "categories": [], "flag": {"flagStatus": "notFlagged"}},
        "m2": {"id": "m2", "subject": "Nieuwe order", "from": {"emailAddress": {"name": "Piet", "address": "p@x.nl"}},
               "receivedDateTime": "2026-10-31T09:00:00Z", "isRead": False, "bodyPreview": "", "categories": []}}
pages = []
class MS:
    def delta_start(self, a, f, since): return "start"
    def delta_page(self, url): return pages.pop(0)
    def get(self, a, mid, full=True):
        if mid in FULL: return dict(FULL[mid])
        raise GraphError(404, "ErrorItemNotFound", "weg")
new = []
mc = MailCache(lambda: db, None, None, on_new=lambda mb, m: new.extend(m)); mc.init()
mb = {"id": 1, "address": "info@x.nl"}
pages.append({"value": [FULL["m1"]], "@odata.deltaLink": "d1"})
mc._sync_delta(mb, MS(), "inbox")
# wijziging: alleen 'gelezen' + een nieuw bericht dat ook half binnenkomt
pages.append({"value": [{"id": "m1", "isRead": True}, {"id": "m2", "isRead": False}], "@odata.deltaLink": "d2"})
mc._sync_delta(mb, MS(), "inbox")
d, _ = mc.get(1, "m1"); assert d["subject"] == "Offerte stickers" and d["receivedDateTime"] and d["isRead"] is True, d; print("  ✓ halve wijziging: onderwerp en datum blijven, gelezen bijgewerkt")
d, _ = mc.get(1, "m2"); assert d and d["subject"] == "Nieuwe order"; print("  ✓ half binnengekomen nieuwe mail los opgehaald")
# oude kapotte regel uit eerdere versie wordt hersteld / opgeruimd
with mc.conn() as c:
    c.execute("UPDATE ms_msgs SET received='', data=? WHERE id='m2'", (json.dumps({"id": "m2", "isRead": True}),))
    c.execute("INSERT INTO ms_msgs(mailbox_id,id,folder_id,received,is_read,flagged,cats,search,data) VALUES(1,'gone','inbox','',0,0,'||','','{}')")
pages.append({"value": [], "@odata.deltaLink": "d3"})
mc._sync_delta(mb, MS(), "inbox")
d, _ = mc.get(1, "m2"); assert d["subject"] == "Nieuwe order" and mc.get(1, "gone")[0] is None; print("  ✓ eerder kapotte regels hersteld of opgeruimd")
print("OK")
