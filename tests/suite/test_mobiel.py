"""Telefoon en tablet (Playwright): één scherm tegelijk, schuifmenu, Plakzicht-balk, vegen (instelbaar, met ongedaan maken),
lang drukken om te selecteren, schrijven met concept, terugknop, agenda als lijst, en de computer blijft zoals hij was."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import Client, Server, expect_error, ok, stop_all  # noqa: E402

srv = Server()
try:
    # de veeg-instelling wordt op de server gecontroleerd
    c = Client(srv.base)
    c.call("login", "medewerker-a", "demo")
    assert c.call("state")["user"]["prefs"]["swipe"] == {"left": "archive", "right": "read"}
    c.call("set_prefs", {"swipe": {"left": "delete", "right": "hack"}})
    assert c.call("state")["user"]["prefs"]["swipe"] == {"left": "delete", "right": "read"}
    c.call("set_prefs", {"swipe": {"left": "archive"}})
    ok("veeg-instelling per gebruiker; onbekende acties worden geweigerd")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  – Playwright niet geïnstalleerd: rest overgeslagen")
        print("OK")
        sys.exit(0)

    # veeg/lang drukken nabootsen met aanraak-pointer-events
    GESTURE = """([id, dx, hold]) => new Promise(res => {
      const r = document.querySelector(`#list .mrow[data-id="${id}"]`), b = r.getBoundingClientRect(), y = b.top + b.height / 2, x0 = b.left + b.width / 2;
      const ev = (t, x) => r.dispatchEvent(new PointerEvent(t, { bubbles: true, pointerId: 7, pointerType: 'touch', clientX: x, clientY: y, isPrimary: true }));
      const click = () => r.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      ev('pointerdown', x0);
      if (hold) { setTimeout(() => { ev('pointerup', x0); click(); res(); }, 600); return; }
      let i = 0;
      const t = setInterval(() => { i++; ev('pointermove', x0 + dx * i / 8); if (i === 8) { clearInterval(t); ev('pointerup', x0 + dx); click(); setTimeout(res, 300); } }, 16);
    })"""
    errors = []
    ids = lambda pg: pg.evaluate("[...document.querySelectorAll('#list .mrow')].map(r => r.dataset.id)")

    def login(ctx, user="medewerker-a"):
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(srv.base + "/")
        pg.wait_for_selector("#keepbox:not([hidden])")
        pg.fill("[name=username]", user); pg.fill("[name=password]", "demo"); pg.click("button[type=submit]")
        pg.wait_for_selector("#list .mrow")
        return pg

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        pg = login(ctx)
        assert pg.evaluate("document.body.classList.contains('mob')") and pg.evaluate("document.body.dataset.pane") == "list"
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        assert pg.is_visible("#fab") and pg.is_hidden("#ribbon") and pg.is_hidden("#reader")
        assert pg.inner_text("#m-title") == "info@ · Postvak IN"
        ok("telefoon: alleen de lijst, titel bovenin, knop Nieuwe mail, geen lint, niets breder dan 390 px")

        pg.click("#m-menu"); pg.wait_for_timeout(300)
        assert pg.evaluate("document.body.classList.contains('drawer')")
        pg.locator("#side .si", has_text="Verzonden").first.click(); pg.wait_for_timeout(500)
        assert not pg.evaluate("document.body.classList.contains('drawer')") and "Verzonden" in pg.inner_text("#m-title")
        pg.click("#m-menu"); pg.wait_for_timeout(200)
        pg.locator("#side .si", has_text="Postvak IN").first.click(); pg.wait_for_timeout(500)
        ok("schuifmenu: map kiezen sluit het menu")

        first = ids(pg)[0]
        pg.locator(f'#list .mrow[data-id="{first}"]').tap(); pg.wait_for_timeout(900)
        assert pg.evaluate("document.body.dataset.pane") == "read" and pg.is_hidden("#list") and pg.is_visible("#reader .rhead")
        assert pg.is_visible("#pzbar") and "Order #000000412" in pg.inner_text("#pzbar")
        assert pg.locator("#reader .rbar [data-act=archive]").count() == 1
        pg.click("#pzbar"); pg.wait_for_timeout(300)
        assert pg.is_visible("#pz") and "Gekoppelde order" in pg.inner_text("#pz")
        pg.click("#scrim", position={"x": 200, "y": 40}); pg.wait_for_timeout(200)
        assert pg.is_hidden("#pz")
        ok("mail lezen: volledig scherm, acties bovenin, Plakzicht als balk die uitklapt")

        pg.go_back(); pg.wait_for_timeout(400)
        assert pg.evaluate("document.body.dataset.pane") == "list" and pg.url.endswith("/index.html")
        ok("terugknop van de telefoon gaat terug naar de lijst (niet uit de app)")

        # lang drukken = selecteren
        a, c2 = ids(pg)[0], ids(pg)[2]
        pg.evaluate(GESTURE, [a, 0, True]); pg.wait_for_timeout(300)
        assert pg.evaluate("S.multi.size") == 1 and pg.evaluate("document.body.dataset.pane") == "list" and pg.is_visible("#mbulk") and pg.is_hidden("#fab")
        pg.locator(f'#list .mrow[data-id="{c2}"]').tap(); pg.wait_for_timeout(300)
        assert pg.evaluate("S.multi.size") == 2 and "2 geselecteerd" in pg.inner_text("#mbulk")
        pg.click("[data-mb-act=flag]"); pg.wait_for_timeout(1200)
        assert pg.evaluate(f"S.mails.find(m => m.id === '{a}').flagged") and pg.evaluate(f"S.mails.find(m => m.id === '{c2}').flagged")
        ok("lang drukken selecteert, tikken voegt toe, actie op de selectie")
        if pg.evaluate("S.multi.size"):
            pg.click("[data-mb-act=clear]")

        # vegen naar rechts (standaard: gelezen/ongelezen)
        r = ids(pg)[1]
        was = pg.evaluate(f"S.mails.find(m => m.id === '{r}').is_read")
        pg.evaluate(GESTURE, [r, 260, False]); pg.wait_for_timeout(1200)
        assert pg.evaluate(f"S.mails.find(m => m.id === '{r}').is_read") != was and pg.evaluate("document.body.dataset.pane") == "list"
        pg.evaluate(GESTURE, [r, -50, False]); pg.wait_for_timeout(400)
        assert pg.locator(f'#list .mrow[data-id="{r}"]').count() == 1
        ok("vegen naar rechts: gelezen/ongelezen; kort vegen doet niets")

        # vegen naar links (standaard: archiveren) met ongedaan maken
        pg.evaluate(GESTURE, [r, -300, False]); pg.wait_for_timeout(500)
        assert pg.locator(f'#list .mrow[data-id="{r}"]').count() == 0 and "Gearchiveerd" in pg.inner_text("#toast")
        pg.click("#toast .undo"); pg.wait_for_timeout(5600)
        assert pg.evaluate(f"S.mails.some(m => m.id === '{r}')")
        pg.evaluate(GESTURE, [r, -300, False]); pg.wait_for_timeout(6000)
        assert not pg.evaluate(f"S.mails.some(m => m.id === '{r}')")
        ok("vegen naar links: archiveren, 5 seconden ongedaan te maken")

        # instelling: links = verwijderen
        pg.evaluate("openMySettings(undefined, 'mob')"); pg.wait_for_timeout(400)
        pg.select_option("#mobform [name=left]", "delete"); pg.wait_for_timeout(700)
        pg.evaluate("closeOverlay()")
        d = ids(pg)[0]
        pg.evaluate(GESTURE, [d, -300, False]); pg.wait_for_timeout(500)
        assert "Verwijderd" in pg.inner_text("#toast")
        pg.wait_for_timeout(5600)
        assert not pg.evaluate(f"S.mails.some(m => m.id === '{d}')")
        ok("zelf gekozen: naar links vegen = verwijderen")

        # schrijven
        pg.click("#fab"); pg.wait_for_timeout(500)
        assert pg.evaluate("document.body.dataset.pane") == "read" and pg.locator("#reader .cmp").count() == 1
        pg.fill("#c-to", "klant@voorbeeld.nl"); pg.click("#reader .editor"); pg.keyboard.type("Test vanaf de telefoon"); pg.wait_for_timeout(1200)
        pg.click("#m-menu"); pg.wait_for_timeout(400)
        assert pg.evaluate("document.body.dataset.pane") == "list" and pg.evaluate("Object.keys(DRAFTS).length") == 1
        ok("schrijven op volledig scherm; terug bewaart het concept")

        # menu als blad, agenda als lijst
        pg.click("#m-me"); pg.wait_for_timeout(200)
        assert pg.locator(".cmenu.sheet").count() == 1
        pg.locator(".cmenu button", has_text="Agenda").click(); pg.wait_for_timeout(1000)
        assert pg.locator("#cal-main [data-view]").count() == 2 and pg.locator(".agl, #cal-main .empty").count() >= 1
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        pg.click("#cal-add"); pg.wait_for_timeout(400)
        assert pg.locator("#dlg[open]").count() == 1
        ok("menu als blad van onderen; agenda als lijst met knop voor een nieuwe afspraak")
        ctx.close()

        # tablet
        ctx = b.new_context(viewport={"width": 1024, "height": 768}, is_mobile=True, has_touch=True)
        pg = login(ctx)
        assert pg.evaluate("document.body.className") == "tab" and pg.evaluate("document.documentElement.scrollWidth") <= 1024
        pg.locator("#list .mrow").first.tap(); pg.wait_for_timeout(800)
        assert pg.is_visible("#list") and pg.is_visible("#reader .rhead") and pg.is_visible("#pzbar") and pg.is_hidden("#side .si >> nth=0")
        ok("tablet: lijst en mail naast elkaar, mappen in het schuifmenu, Plakzicht als balk")
        ctx.close()

        # computer: zoals voorheen
        pg = login(b.new_context(viewport={"width": 1500, "height": 900}))
        assert pg.evaluate("document.body.className") == "" and pg.is_visible("#side .si >> nth=0") and pg.is_visible("#ribbon")
        assert pg.is_hidden("#m-menu") and pg.is_hidden("#fab") and pg.is_hidden("#pzbar")
        ok("computer: zijbalk, lint en Plakzicht-paneel zoals altijd")
        b.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
