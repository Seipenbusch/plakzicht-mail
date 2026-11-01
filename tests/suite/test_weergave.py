"""Weergave: licht/donker per gebruiker, tellers per map, voetregel onder de lijst, de kop van de lijst blijft bij scrollen
bovenop, genoeg kleurverschil in donker, en het totaal per map komt van Microsoft (ook buiten de lokale kopie)."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import ROOT, Client, Server, ok, stop_all  # noqa: E402

# totaal per map: van Microsoft, maar nooit minder dan de kopie
sys.path.insert(0, ROOT)
from mscache import MailCache  # noqa: E402

db = os.path.join(tempfile.mkdtemp(), "c.db")
mc = MailCache(lambda: db, None, None)
mc.init()
with mc.conn() as c:
    c.execute("INSERT INTO ms_folders VALUES(1,'inbox','Postvak IN',NULL,'inbox',9,120,0,0,0)")
    c.execute("INSERT INTO ms_folders VALUES(1,'sent','Verzonden',NULL,'sentitems',0,2,0,0,1)")
    c.execute("INSERT INTO ms_sync(mailbox_id,folder_id,delta,synced_at,days) VALUES(1,'inbox','d',0,30)")
    c.execute("INSERT INTO ms_sync(mailbox_id,folder_id,delta,synced_at,days) VALUES(1,'sent','d',0,30)")
    for i in range(5):
        c.execute("INSERT INTO ms_msgs(mailbox_id,id,folder_id,received,is_read,flagged,cats,search,data) VALUES(1,?,?,?,?,0,'||','','{}')",
                  (f"m{i}", "inbox", "2026-11-01", 1 if i < 3 else 0))
    for i in range(4):
        c.execute("INSERT INTO ms_msgs(mailbox_id,id,folder_id,received,is_read,flagged,cats,search,data) VALUES(1,?,?,?,1,0,'||','','{}')",
                  (f"s{i}", "sent", "2026-11-01"))
f = {x["id"]: x for x in mc.folders(1)}
assert (f["inbox"]["unread"], f["inbox"]["total"]) == (2, 120), f["inbox"]
assert f["sent"]["total"] == 4, f["sent"]
ok("totaal per map van Microsoft (120, ook oude mail); ongelezen uit de kopie (direct bij); nooit minder dan de kopie")

srv = Server()
try:
    c = Client(srv.base)
    c.call("login", "medewerker-a", "demo")
    p = c.call("state")["user"]["prefs"]
    assert p["theme"] == "auto" and p["counters"] == {}
    c.call("set_prefs", {"theme": "paars"})
    c.call("set_prefs", {"theme": "dark", "counters": {"1:inbox": "both", "1:sent": "raar", "1:archive": "total"}})
    p = c.call("state")["user"]["prefs"]
    assert p["theme"] == "dark" and p["counters"] == {"1:inbox": "both", "1:archive": "total"}, p
    c.call("set_prefs", {"counters": {"1:archive": None}})
    assert c.call("state")["user"]["prefs"]["counters"] == {"1:inbox": "both"}
    c.call("set_prefs", {"theme": "auto", "counters": {"1:inbox": None}})
    ok("licht/donker en tellers per gebruiker; onbekende waarden geweigerd; terug naar standaard kan")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  – Playwright niet geïnstalleerd: rest overgeslagen")
        print("OK")
        sys.exit(0)

    errors = []

    def login(ctx, user="medewerker-a"):
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(srv.base + "/")
        pg.wait_for_selector("#keepbox:not([hidden])")
        pg.fill("[name=username]", user); pg.fill("[name=password]", "demo"); pg.click("button[type=submit]")
        pg.wait_for_selector("#list .mrow")
        return pg

    def lum(rgb):
        r, g, b = [int(x) for x in rgb[rgb.index("(") + 1:rgb.index(")")].split(",")[:3]]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    side_n = lambda pg, name: pg.locator("#side .si.fi", has_text=name).first.locator(".n").inner_text().strip()

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        # computer
        ctx = b.new_context(viewport={"width": 1500, "height": 860})
        pg = login(ctx)
        assert pg.evaluate("document.documentElement.dataset.theme") is None
        pg.click("#btn-theme"); pg.locator(".cmenu button", has_text="Donker").click(); pg.wait_for_timeout(600)
        assert pg.evaluate("document.documentElement.dataset.theme") == "dark" and pg.evaluate("localStorage.getItem('pm-theme')") == "dark"
        assert "Donker" in pg.inner_text("#btn-theme")
        pg.reload(); pg.wait_for_selector("#list .mrow")
        assert pg.evaluate("document.documentElement.dataset.theme") == "dark"
        ok("licht/donker-knop: Donker gekozen, blijft na herladen")
        top = lum(pg.evaluate("getComputedStyle(document.querySelector('.topbar')).backgroundColor"))
        lst = lum(pg.evaluate("getComputedStyle(document.querySelector('#list')).backgroundColor"))
        side = lum(pg.evaluate("getComputedStyle(document.querySelector('#side')).backgroundColor"))
        assert lst - top >= 20 and lst - side >= 8, (top, side, lst)
        ok(f"donker: duidelijk verschil tussen navigatie en maillijst (helderheid {top:.0f} / {side:.0f} → {lst:.0f})")

        # tellers
        assert side_n(pg, "Postvak IN") == "3" and side_n(pg, "Verzonden") == ""
        pg.locator("#side .si.fi", has_text="Postvak IN").first.click(button="right")
        pg.locator(".cmenu button", has_text="Teller").hover(); pg.wait_for_timeout(200)
        pg.locator(".cmenu .cmenu.sub button", has_text="Beide").click(); pg.wait_for_timeout(500)
        assert side_n(pg, "Postvak IN").replace(" ", "") == "3/6"
        pg.evaluate("openMySettings(undefined, 'view')"); pg.wait_for_timeout(300)
        sel = pg.locator('#mybody select[data-cnt="1|sent"]')
        sel.select_option("total"); pg.wait_for_timeout(500)
        pg.evaluate("closeOverlay()"); pg.evaluate("renderSide()")
        assert side_n(pg, "Verzonden") == "1", side_n(pg, "Verzonden")
        assert pg.evaluate("P().counters") == {"1:inbox": "both", "1:sent": "total"}
        ok("tellers: standaard ongelezen, per map te kiezen (rechtermuisknop of Mijn instellingen)")

        # voetregel
        foot = lambda: " ".join(pg.inner_text("#list .lfoot").split())
        assert foot() == "6 mails · 3 ongelezen", foot()
        pg.evaluate("setFilter('ongelezen')"); pg.wait_for_timeout(500)
        assert foot() == "3 gevonden (filter Ongelezen) van 6", foot()
        ids = pg.evaluate("[...document.querySelectorAll('#list .mrow')].slice(0,2).map(r => r.dataset.id)")
        pg.click(f'#list .mrow[data-id="{ids[0]}"]'); pg.click(f'#list .mrow[data-id="{ids[1]}"]', modifiers=["Control"]); pg.wait_for_timeout(400)
        assert foot() == "2 geselecteerd · 3 gevonden (filter Ongelezen) van 6 Opheffen", foot()
        pg.click("#btn-selclear"); pg.wait_for_timeout(300)
        assert pg.evaluate("S.multi.size") == 0 and "Gekoppelde order" in pg.inner_text("#pz") or pg.locator("#pz .panel").count()
        pg.evaluate("setFilter('alle')"); pg.wait_for_timeout(400)
        box = pg.evaluate("(() => { const l = document.querySelector('#list').getBoundingClientRect(), f = document.querySelector('#list .lfoot').getBoundingClientRect(); return [l.bottom, f.bottom]; })()")
        assert abs(box[0] - box[1]) < 3, box
        ok("voetregel onderaan: aantal, ongelezen, gevonden met filter, geselecteerd met Opheffen")
        ctx.close()

        # telefoon
        ctx = b.new_context(viewport={"width": 390, "height": 700}, is_mobile=True, has_touch=True)
        pg = login(ctx)
        assert pg.evaluate("document.documentElement.dataset.theme") == "dark"  # van de gebruiker
        pg.evaluate("document.querySelector('#list').scrollTop = 300"); pg.wait_for_timeout(200)
        on_top = pg.evaluate("(() => { const r = document.querySelector('#list .listhead').getBoundingClientRect(); return [12, r.height - 8].every(dy => !!document.elementFromPoint(r.left + 60, r.top + dy).closest('.listhead')); })()")
        assert on_top
        ok("telefoon: bij scrollen blijft de kop van de lijst bovenop (geen mail eroverheen)")
        assert pg.is_visible("#list .lfoot") and "6 mails" in pg.inner_text("#list .lfoot")
        fab = pg.evaluate("document.querySelector('#fab').getBoundingClientRect().bottom"); ft = pg.evaluate("document.querySelector('#list .lfoot').getBoundingClientRect().top")
        assert fab <= ft, (fab, ft)
        pg.click("#m-theme"); pg.locator(".cmenu button", has_text="Licht").click(); pg.wait_for_timeout(500)
        assert pg.evaluate("document.documentElement.dataset.theme") == "light"
        ok("telefoon: voetregel onder de knop Nieuwe mail; thema-knop in de bovenbalk")
        # lang drukken op een map
        pg.click("#m-menu"); pg.wait_for_timeout(300)
        pg.evaluate("""() => new Promise(res => { const b = [...document.querySelectorAll('#side .si.fi')].find(x => x.textContent.includes('Archief')); const r = b.getBoundingClientRect();
          b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: 'touch', clientX: r.left + 20, clientY: r.top + 10 }));
          setTimeout(() => { b.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerType: 'touch' })); b.click(); res(); }, 600); })""")
        pg.wait_for_timeout(300)
        assert "teller bij archief" in pg.inner_text(".cmenu.sheet").lower() and "Postvak IN" in pg.inner_text("#m-title")
        pg.locator(".cmenu button", has_text="Totaal").click(); pg.wait_for_timeout(400)
        assert side_n(pg, "Archief") == "0"
        ok("telefoon: lang drukken op een map opent de teller (en opent de map niet)")
        ctx.close()

        # inlogscherm onthoudt het thema op dit apparaat
        ctx2 = b.new_context(viewport={"width": 1200, "height": 800}, color_scheme="light")
        pg = ctx2.new_page()
        pg.goto(srv.base + "/"); pg.evaluate("localStorage.setItem('pm-theme', 'dark')"); pg.reload(); pg.wait_for_selector("#login:not([hidden])")
        assert pg.evaluate("document.documentElement.dataset.theme") == "dark"
        bg = lum(pg.evaluate("getComputedStyle(document.body).backgroundColor"))
        assert bg < 40, bg
        ok("inlogscherm: laatste keuze op dit apparaat, zonder eerst licht op te lichten")
        b.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
