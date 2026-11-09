"""Kolombreedtes per gebruiker en per scherm. Een smal venster, de telefoon of het in- en uitklappen van de zijbalk mag de
bewaarde breedtes nooit overschrijven; alleen zelf slepen (of dubbelklikken / pijltjestoetsen / knoppen) slaat iets op."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import Client, Server, ok, stop_all  # noqa: E402

srv = Server()
try:
    c = Client(srv.base)
    c.call("login", "medewerker-b", "demo")
    lay = c.call("set_layout", {"screen": "1920x1080", "widths": {"list": 1300, "side": 9999, "colw": {"from": 300, "raar": 5}}})
    assert lay["screens"]["1920x1080"]["list"] == 1300 and lay["screens"]["1920x1080"]["side"] == 360
    assert lay["screens"]["1920x1080"]["colw"] == {"from": 300}
    lay = c.call("set_layout", {"collapsed": True})
    assert lay["collapsed"] is True and lay["screens"]["1920x1080"]["list"] == 1300  # samengevoegd, niets kwijt
    lay = c.call("set_layout", {"screen": "1920x1080", "widths": {"pz": 300}})
    assert lay["screens"]["1920x1080"]["list"] == 1300 and lay["screens"]["1920x1080"]["pz"] == 300
    c.call("set_layout", {"screen": "../etc", "widths": {"list": 500}})
    for i in range(14):
        c.call("set_layout", {"screen": f"{1000 + i}x800", "widths": {"list": 400}})
    lay = c.call("set_layout", {"screen": "1920x1080", "widths": {"list": 1300}})
    assert len(lay["screens"]) == 12 and "../etc" not in lay["screens"] and "1920x1080" in lay["screens"]
    lay = c.call("set_layout", {"screen": "1920x1080", "widths": None})
    assert "1920x1080" not in lay["screens"]
    c.call("set_layout", {"collapsed": False})
    ok("server: breedtes per scherm (tot 1400 px), samengevoegd, grenzen bewaakt, oudste scherm vervalt, wissen kan")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  – Playwright niet geïnstalleerd: rest overgeslagen")
        print("OK")
        sys.exit(0)

    errors = []

    def login(ctx, user="medewerker-a", scr=(1920, 1080)):
        pg = ctx.new_page()
        # het scherm blijft hetzelfde als het venster smaller wordt (Playwright zou het anders meeveranderen)
        pg.add_init_script("(() => { const w = %d, h = %d; Object.defineProperty(screen, 'width', { get: () => w }); Object.defineProperty(screen, 'height', { get: () => h }); })()" % scr)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(srv.base + "/")
        pg.wait_for_selector("#keepbox:not([hidden])")
        pg.fill("[name=username]", user); pg.fill("[name=password]", "demo"); pg.click("button[type=submit]")
        pg.wait_for_selector("#list .mrow")
        pg.wait_for_timeout(300)
        return pg

    def drag(pg, sel, dx, dy=200):
        r = pg.locator(sel).bounding_box()
        x, y = r["x"] + r["width"] / 2, r["y"] + min(dy, r["height"] / 2)
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + dx / 2, y, steps=4); pg.mouse.move(x + dx, y, steps=4); pg.mouse.up()
        pg.wait_for_timeout(700)  # opslaan gebeurt na 0,4 s

    width = lambda pg, sel: round(pg.locator(sel).bounding_box()["width"])

    def screens():
        cl = Client(srv.base); cl.call("login", "medewerker-a", "demo")
        return cl.call("state")["user"]["layout"].get("screens", {})

    with sync_playwright() as p:
        b = p.chromium.launch()
        big = dict(viewport={"width": 1800, "height": 950}, screen={"width": 1920, "height": 1080})
        ctx = b.new_context(**big)
        pg = login(ctx)
        w0 = width(pg, "#list")
        drag(pg, '.gutter[data-g="list"]', 150)
        w1 = width(pg, "#list")
        assert w1 > w0 + 100, (w0, w1)
        assert abs(screens()["1920x1080"]["list"] - w1) <= 2, screens()
        ok(f"slepen bewaart de breedte voor dit scherm ({w0} → {w1} px, scherm 1920 × 1080)")

        # smal venster + zijbalk in- en uitklappen + Plakzicht verbergen: getoond smaller, bewaard blijft gelijk
        pg.set_viewport_size({"width": 1180, "height": 800}); pg.wait_for_timeout(300)
        assert width(pg, "#list") < w1
        pg.click("#btn-collapse"); pg.wait_for_timeout(200); pg.click("#btn-collapse"); pg.wait_for_timeout(200)
        pg.evaluate("setLayout({ pz_hidden: true })"); pg.wait_for_timeout(200); pg.evaluate("setLayout({ pz_hidden: false })")
        pg.wait_for_timeout(800)
        assert abs(screens()["1920x1080"]["list"] - w1) <= 2, screens()
        pg.set_viewport_size({"width": 1800, "height": 950}); pg.wait_for_timeout(300)
        assert abs(width(pg, "#list") - w1) <= 2
        ok("smal venster, zijbalk in-/uitklappen en Plakzicht verbergen overschrijven de bewaarde breedte niet; breed = terug")

        # kolom in de lijst slepen: ook per scherm
        pg.evaluate("setListview('kolommen')"); pg.wait_for_timeout(400)
        cw0 = pg.evaluate("colW('from')")
        drag(pg, '#list .ch[data-col="from"] .rz', 60)
        cw1 = pg.evaluate("colW('from')")
        assert cw1 >= cw0 + 40 and screens()["1920x1080"]["colw"]["from"] == cw1, (cw0, cw1, screens())
        pg.close()

        # opnieuw openen, ook met een smal opstartvenster (zoals de Windows-app vóór maximaliseren)
        small = b.new_context(viewport={"width": 900, "height": 700}, screen={"width": 1920, "height": 1080})
        pg = login(small)
        pg.evaluate("setLayout({ collapsed: true }); setLayout({ collapsed: false })"); pg.wait_for_timeout(800)
        pg.set_viewport_size({"width": 1800, "height": 950}); pg.wait_for_timeout(300)
        assert abs(width(pg, "#list") - w1) <= 2 and pg.evaluate("colW('from')") == cw1
        ok("na opnieuw openen (ook vanuit een smal venster): lijst- en kolombreedtes zijn er nog")
        small.close()

        # ander scherm: start met het meest gelijkende scherm, eigen wijziging raakt het eerste scherm niet
        ctx2 = b.new_context(viewport={"width": 2400, "height": 1300}, screen={"width": 2560, "height": 1440})
        pg = login(ctx2, scr=(2560, 1440))
        assert abs(width(pg, "#list") - w1) <= 2
        drag(pg, '.gutter[data-g="list"]', -200)
        w2 = width(pg, "#list")
        s = screens()
        assert abs(s["2560x1440"]["list"] - w2) <= 2 and abs(s["1920x1080"]["list"] - w1) <= 2, s
        ok(f"ander scherm (2560 × 1440): begint met de breedtes van 1920 × 1080, daarna een eigen instelling ({w2} px)")

        # herstellen op dit scherm
        pg.evaluate("openMySettings(undefined, 'view')"); pg.wait_for_timeout(300)
        assert "2560 × 1440" in pg.inner_text("#mybody")
        pg.click("#w-reset"); pg.wait_for_timeout(800)
        s = screens()
        assert "2560x1440" not in s and "1920x1080" in s, s
        ok("Mijn instellingen › Weergave: kolombreedtes op dit scherm herstellen")
        ctx2.close()

        # telefoon: verandert niets aan de bewaarde breedtes
        before = screens()
        ph = b.new_context(viewport={"width": 390, "height": 760}, screen={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        pg = login(ph, scr=(390, 844))
        pg.evaluate("setLayout({ pz_hidden: true }); setLayout({ pz_hidden: false })"); pg.wait_for_timeout(800)
        assert screens() == before
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        ok("telefoon: bewaarde breedtes van de computerschermen blijven ongemoeid")
        b.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
