"""Favorieten bovenin de zijbalk (mappen, mailboxen, labels; per gebruiker; volgorde; ook op de telefoon) en links in mails
(openen in een nieuw tabblad, mailto opent een nieuwe mail, waarschuwing bij een misleidende link, geen scripts)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import Client, Server, ok, stop_all  # noqa: E402

srv = Server()
try:
    c = Client(srv.base)
    c.call("login", "medewerker-a", "demo")
    c.call("set_prefs", {"favorites": ["f:1:inbox", "m:2", "l:3", "l:3", "x:1", "f:abc", 5]})
    assert c.call("state")["user"]["prefs"]["favorites"] == ["f:1:inbox", "m:2", "l:3"]
    c.call("set_prefs", {"favorites": []})
    ok("favorieten per gebruiker; ongeldige of dubbele worden geweigerd")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  – Playwright niet geïnstalleerd: rest overgeslagen")
        print("OK")
        sys.exit(0)

    errors = []
    BODY = ('<p>Zie <a href="https://example.org/track?x=1">onze site</a>, mail <a href="mailto:klant@voorbeeld.nl?subject=Vraag&cc=b@x.nl">ons</a>,'
            ' <a href="https://evil.example/login">www.rabobank.nl</a> en <a href="javascript:alert(1)">dit</a>.</p>'
            '<script>parent.document.title = "gehackt"</script><img src=x onerror="parent.document.title=\'gehackt\'">')

    def login(ctx, user="medewerker-a"):
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(srv.base + "/")
        pg.wait_for_selector("#keepbox:not([hidden])")
        pg.fill("[name=username]", user); pg.fill("[name=password]", "demo"); pg.click("button[type=submit]")
        pg.wait_for_selector("#list .mrow")
        return pg

    def menu_click(pg, text):
        pg.locator(".cmenu button", has_text=text).first.click()
        pg.wait_for_timeout(350)

    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1500, "height": 860})
        pg = login(ctx)
        assert pg.locator("#side .favsec").count() == 0
        pg.locator("#side .si.fi", has_text="Archief").first.click(button="right"); menu_click(pg, "Toevoegen aan favorieten")
        pg.locator("#side .si[data-label]:not(.fav)", has_text="Nieuwe aanvragen").click(button="right"); menu_click(pg, "Toevoegen aan favorieten")
        pg.locator("#side .mbname", has_text="info@").click(button="right"); menu_click(pg, "Toevoegen aan favorieten")
        assert pg.evaluate("P().favorites") == ["f:1:archive", "l:1", "m:1"], pg.evaluate("P().favorites")
        names = pg.locator("#side .favsec .si.fav").all_inner_texts()
        assert "Archief" in names[0] and "info@" in names[0] and "Nieuwe aanvragen" in names[1] and "Postvak IN" in names[2], names
        assert pg.locator("#side .si.fi", has_text="Archief").count() == 2   # ook nog op de eigen plek
        ok("rechtermuisknop › Toevoegen aan favorieten voor map, label en mailbox; bovenin én op de eigen plek")

        pg.locator("#side .favsec .si.fav", has_text="Nieuwe aanvragen").click(); pg.wait_for_timeout(500)
        assert pg.evaluate("S.view") == {"label_id": 1}
        pg.locator("#side .favsec .si.fav", has_text="Postvak IN").click(); pg.wait_for_timeout(500)
        assert pg.evaluate("S.view") == {"mailbox_id": 1, "folder": "inbox"} and pg.locator("#side .favsec .si.fav.on").count() == 1
        ok("favoriet aanklikken opent de map, het label of het Postvak IN van de mailbox")

        src, dst = pg.locator("#side .favsec .si.fav").nth(2), pg.locator("#side .favsec .si.fav").nth(0)
        src.drag_to(dst, target_position={"x": 30, "y": 2}); pg.wait_for_timeout(500)
        assert pg.evaluate("P().favorites") == ["m:1", "f:1:archive", "l:1"], pg.evaluate("P().favorites")
        pg.locator("#side .favsec .si.fav").nth(0).click(button="right"); menu_click(pg, "Omlaag")
        assert pg.evaluate("P().favorites") == ["f:1:archive", "m:1", "l:1"]
        ok("volgorde: verslepen en via het menu (omhoog/omlaag)")

        mid = pg.evaluate("[...document.querySelectorAll('#list .mrow')][0].dataset.id")
        pg.locator(f'#list .mrow[data-id="{mid}"]').drag_to(pg.locator("#side .favsec .si.fav", has_text="Archief")); pg.wait_for_timeout(900)
        assert not pg.evaluate(f"S.mails.some(m => m.id === '{mid}')")
        ok("mail naar een favoriet slepen verplaatst hem naar die map")

        pg.locator("#side .favsec .si.fav", has_text="Nieuwe aanvragen").click(button="right"); menu_click(pg, "Verwijderen uit favorieten")
        assert pg.evaluate("P().favorites") == ["f:1:archive", "m:1"]
        pg.click("#fav-tog"); pg.wait_for_timeout(300)
        assert pg.locator("#side .favsec .si.fav").count() == 0 and pg.evaluate("P().fav_open") is False
        pg.click("#fav-tog"); pg.wait_for_timeout(300)
        pg.reload(); pg.wait_for_selector("#list .mrow")
        assert pg.locator("#side .favsec .si.fav").count() == 2
        ok("verwijderen, kopje in- en uitklappen; bewaard na herladen")

        pg.evaluate("setLayout({ collapsed: true }); renderSide()"); pg.wait_for_timeout(300)
        assert pg.locator("#side .favrail .ri").count() == 2
        pg.evaluate("setLayout({ collapsed: false }); renderSide()")
        ok("ingeklapte zijbalk: favorieten bovenaan als icoon")

        # ---------- links in de mail
        pg.evaluate("body => { const real = window.api; window.api = async (n, ...a) => { const r = await real(n, ...a); if (n === 'get_mail') r.body = body; return r; }; }", BODY)
        pg.locator("#list .mrow").first.click(); pg.wait_for_timeout(800)
        fr = pg.frame_locator("#reader iframe.rbody")
        assert fr.locator("a").nth(0).get_attribute("title") == "https://example.org/track?x=1"
        assert "Let op" in fr.locator("a").nth(2).get_attribute("title")
        assert pg.evaluate("document.title") != "gehackt"
        with ctx.expect_page() as newp:
            fr.locator("a").nth(0).click()
        assert newp.value.url.startswith("https://example.org/") or newp.value.url.startswith("chrome-error")
        newp.value.close()
        ok("link opent in een nieuw tabblad; echt adres bij de muis; scripts in de mail doen niets")
        fr.locator("a").nth(1).click(); pg.wait_for_timeout(600)
        assert pg.evaluate("[S.cmp.to, S.cmp.cc, S.cmp.subj]") == ["klant@voorbeeld.nl", "b@x.nl", "Vraag"]
        ok("mailto-link opent een nieuwe mail in Plakzicht Mail met adres, cc en onderwerp")
        pg.evaluate("stashCompose(); S.cmp = null; renderReader()"); pg.wait_for_timeout(500)
        asked = []
        pg.on("dialog", lambda d: (asked.append(d.message), d.dismiss()))
        n0 = len(ctx.pages)
        pg.frame_locator("#reader iframe.rbody").locator("a").nth(2).click(); pg.wait_for_timeout(400)
        pg.frame_locator("#reader iframe.rbody").locator("a").nth(3).click(); pg.wait_for_timeout(400)
        assert asked and "rabobank.nl" in asked[0] and len(ctx.pages) == n0
        ok("misleidende link: eerst een vraag (geannuleerd = niet geopend); javascript:-links worden niet uitgevoerd")
        ctx.close()

        # ---------- telefoon: lang drukken op een map en een label
        ctx = b.new_context(viewport={"width": 390, "height": 760}, is_mobile=True, has_touch=True)
        pg = login(ctx)
        pg.click("#m-menu"); pg.wait_for_timeout(300)
        assert pg.locator("#side .favsec .si.fav").count() == 2
        LP = """sel => new Promise(res => { const b = [...document.querySelectorAll('#side .si')].find(x => x.textContent.includes(sel) && !x.classList.contains('fav')); const r = b.getBoundingClientRect();
          b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerType: 'touch', clientX: r.left + 20, clientY: r.top + 10 }));
          setTimeout(() => { b.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerType: 'touch' })); b.click(); res(); }, 600); })"""
        pg.evaluate(LP, "Medewerker A"); pg.wait_for_timeout(300)
        assert "label medewerker a" in pg.inner_text(".cmenu.sheet").lower()
        menu_click(pg, "Toevoegen aan favorieten")
        assert pg.evaluate("P().favorites")[-1] == "l:3" and pg.locator("#side .favsec .si.fav").count() == 3
        ok("telefoon: lang drukken op een label of map › Toevoegen aan favorieten")
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        b.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
