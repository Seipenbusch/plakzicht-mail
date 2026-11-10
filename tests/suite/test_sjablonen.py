"""Sjablonen: eigen (alleen jij) en per mailbox (iedereen met toegang), rechten op de server, invulvelden met gegevens van
de ontvanger en uit Plakzicht, gele markering voor wat niet bekend is, bijlagen die echt meegaan, en nooit versturen zonder
dat iemand de mail heeft gezien."""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import ROOT, Client, Server, expect_error, ok, stop_all  # noqa: E402

PDF = base64.b64encode(b"%PDF-1.4 leveringsvoorwaarden").decode()

srv = Server()
try:
    a, b, adm = Client(srv.base), Client(srv.base), Client(srv.base)
    a.call("login", "medewerker-a", "demo"); b.call("login", "medewerker-b", "demo"); adm.call("login", "beheerder", "demo")
    own = a.call("save_template", {"name": "Mijn groet", "scope": "me", "subject": "", "html": "<p>Hoi {voornaam}<script>x()</script><img src=x onerror=alert(1)></p>"})
    info = a.call("save_template", {"name": "Drukproef", "scope": 1, "subject": "Drukproef order {ordernummer}",
                                    "html": "<p>Beste {voornaam},</p><p>De drukproef van order {ordernummer} staat klaar.</p>",
                                    "files": [{"name": "voorwaarden.pdf", "ctype": "application/pdf", "data": PDF}]})
    verkoop = a.call("save_template", {"name": "Offerte", "scope": 2, "html": "<p>Offerte</p>"})
    ta = {t["name"]: t for t in a.call("state")["templates"]}
    assert set(ta) == {"Mijn groet", "Drukproef", "Offerte"}
    assert "<script" not in ta["Mijn groet"]["html"] and "onerror" not in ta["Mijn groet"]["html"]
    assert ta["Drukproef"]["files"][0]["name"] == "voorwaarden.pdf" and "data" not in ta["Drukproef"]["files"][0]
    tb = {t["name"]: t for t in b.call("state")["templates"]}
    assert set(tb) == {"Drukproef"} and tb["Drukproef"]["can_edit"] is True, tb  # B heeft alleen info@
    ok("eigen sjabloon alleen voor jezelf; mailbox-sjabloon voor iedereen met die mailbox; scripts eruit")

    expect_error(lambda: b.call("save_template", {"name": "x", "scope": 2, "html": "x"}), "toegang")
    expect_error(lambda: b.call("save_template", {"id": own, "name": "x", "scope": "me", "html": "x"}), "niet wijzigen")
    expect_error(lambda: b.call("delete_template", verkoop), "niet verwijderen")
    b.call("save_template", {"id": info, "name": "Drukproef klaar", "scope": 1, "subject": "Drukproef order {ordernummer}",
                             "html": ta["Drukproef"]["html"], "files": [{"id": ta["Drukproef"]["files"][0]["id"]}]})
    t = next(x for x in a.call("templates") if x["id"] == info)
    assert t["name"] == "Drukproef klaar" and t["updated_by"] == "Medewerker B" and len(t["files"]) == 1
    assert len([x for x in adm.call("templates") if x["mailbox_id"]]) == 2 and not any(x["user_id"] for x in adm.call("templates"))
    ok("rechten op de server: geen andermans of onbekende mailbox; collega met toegang mag het mailbox-sjabloon wijzigen")

    big = base64.b64encode(b"x" * 2_000_000).decode()
    expect_error(lambda: a.call("save_template", {"name": "groot", "scope": "me", "html": "x", "files": [{"name": "a", "data": big}, {"name": "b", "data": big}]}), "te groot")
    expect_error(lambda: a.call("save_template", {"name": "", "scope": "me", "html": "x"}), "naam")
    fid = t["files"][0]["id"]
    expect_error(lambda: b.call("send_mail", {"mailbox_id": 1, "to": "k@x.nl", "subject": "s", "body": "b", "template_files": [99999]}), "niet (meer) beschikbaar")
    verk_file = a.call("save_template", {"id": verkoop, "name": "Offerte", "scope": 2, "html": "<p>Offerte</p>", "files": [{"name": "p.pdf", "data": PDF}]})
    vf = next(x for x in a.call("templates") if x["id"] == verkoop)["files"][0]["id"]
    expect_error(lambda: b.call("send_mail", {"mailbox_id": 1, "to": "k@x.nl", "subject": "s", "body": "b", "template_files": [vf]}), "niet (meer) beschikbaar")
    ok("grenzen: bijlagen samen hooguit 2,5 MB, naam verplicht, onbekende bijlage wordt geweigerd")

    # bijlagen gaan echt mee naar Microsoft (versturen met een nagebootste Graph)
    sys.path.insert(0, ROOT)
    import graph  # noqa: E402

    class G:
        def req(self, method, path, body=None, **kw):
            self.sent = body
    g = G(); mm = graph.MsMail(g)
    mm.send("info@jouwbedrijf.nl", "Onderwerp", "<p>tekst</p>", "klant@x.nl", "", [{"name": "voorwaarden.pdf", "ctype": "application/pdf", "data": b"%PDF"}])
    att = g.sent["message"]["attachments"]
    assert att == [{"@odata.type": "#microsoft.graph.fileAttachment", "name": "voorwaarden.pdf", "contentType": "application/pdf", "contentBytes": base64.b64encode(b"%PDF").decode()}], att
    ok("Microsoft: bijlage uit het sjabloon gaat als echte bijlage mee")

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

    with sync_playwright() as p:
        br = p.chromium.launch()
        ctx = br.new_context(viewport={"width": 1500, "height": 900})
        pg = login(ctx)
        # mail met een gekoppelde order: rechtermuisknop › Beantwoorden met sjabloon
        mid, order = pg.evaluate("(m => m ? [String(m.id), m.order_nr] : [null, null])(S.mails.find(m => m.order_nr && m.from_name))")
        assert mid, "demo heeft een mail met een order"
        pg.locator(f'#list .mrow[data-id="{mid}"]').click(button="right")
        pg.locator(".cmenu button", has_text="Beantwoorden met sjabloon").click()
        pg.wait_for_selector("dialog .tplpick")
        names = pg.locator("dialog .tplrow b").all_inner_texts()
        assert names == ["Mijn groet", "Drukproef klaar"], names  # eigen + van info@ (niet die van verkoop@)
        pg.fill("dialog [name=q]", "druk")
        assert pg.locator("dialog .tplrow:not([hidden])").count() == 1
        pg.keyboard.press("Enter"); pg.wait_for_timeout(900)
        ed = pg.locator("#editor")
        txt = ed.inner_text()
        # afzender 'Brouwerij De Hop' is de klant (bedrijfsnaam) uit Plakzicht: geen voornaam, dus geel om zelf in te vullen
        assert "Beste [Voornaam]," in txt and f"order {order} staat klaar" in txt, txt
        assert pg.evaluate("[...document.querySelectorAll('#editor mark[data-fill]')].map(m => m.dataset.fill)") == ["voornaam"]
        pg.keyboard.type("Jan"); pg.wait_for_timeout(200)  # de gele plek staat al geselecteerd
        assert "Beste Jan," in ed.inner_text(), repr(ed.inner_text()[:80])
        assert pg.input_value("#c-subj").lower().startswith("re:"), "bij beantwoorden blijft het onderwerp"
        assert "voorwaarden.pdf" in pg.inner_text("#c-files")
        ok("rechtermuisknop › Beantwoorden met sjabloon: zoeken, ordernummer ingevuld, bedrijfsnaam is geen voornaam (geel), bijlage erbij")

        # tweede sjabloon met een veld dat niet bekend is: gele markering, eerst een vraag bij versturen
        a.call("save_template", {"id": own, "name": "Mijn groet", "scope": "me", "html": "<p>Je offerte {offertenummer} volgt.</p>"})
        pg.evaluate("refreshState()"); pg.wait_for_timeout(400)
        pg.click(".cmp [data-c=tpl]"); pg.wait_for_selector("dialog .tplpick")
        pg.locator("dialog .tplrow", has_text="Mijn groet").click(); pg.wait_for_timeout(700)
        assert pg.locator("#editor mark[data-fill]").count() == 1 and "[Offertenummer]" in ed.inner_text()
        assert "drukproef van order" in ed.inner_text(), "eerdere tekst blijft staan"
        pg.click(".cmp [data-c=send]"); pg.wait_for_selector("dialog h2:has-text('Nog niet alles ingevuld')")
        pg.locator("dialog button", has_text="Terug en invullen").click(); pg.wait_for_timeout(300)
        assert pg.evaluate("!!S.cmp"), "niet verstuurd"
        pg.keyboard.type("OF-123"); pg.wait_for_timeout(200)
        assert "OF-123 volgt" in ed.inner_text()
        pg.click(".cmp [data-c=send]"); pg.wait_for_timeout(1200)
        assert pg.evaluate("!S.cmp"), "verstuurd na invullen"
        sent = a.call("list_mails", {"mailbox_id": 1, "folder": "sent"})
        body = a.call("get_mail", sent[0]["id"])["body"]
        assert "OF-123" in body and "<mark" not in body and "voorwaarden.pdf" in body, body[-300:]
        ok("niet ingevulde velden geel; versturen vraagt eerst; markering gaat niet mee; bijlage mee (demo: vermeld)")

        # nieuwe mail: onderwerp uit het sjabloon; Mijn instellingen › Sjablonen: nieuw sjabloon met invulveld en bijlage
        pg.evaluate("openMySettings(undefined, 'tpl')"); pg.wait_for_timeout(400)
        pg.click("#t-new"); pg.wait_for_timeout(200)
        pg.fill("#t-name", "Verzonden")
        pg.select_option("#t-scope", "1")
        pg.fill("#t-subj", "Je order is onderweg"); pg.click("#t-subj"); pg.click('[data-fld="ordernummer"]')
        pg.click("#t-edit"); pg.keyboard.press("Control+A"); pg.keyboard.type("Hallo "); pg.click('[data-fld="voornaam"]')
        pg.set_input_files("#t-file", files=[{"name": "factuur.pdf", "mimeType": "application/pdf", "buffer": b"%PDF factuur"}])
        pg.wait_for_timeout(300)
        assert "factuur.pdf" in pg.inner_text("#t-files")
        pg.click("#t-save"); pg.wait_for_timeout(700)
        t = next(x for x in b.call("templates") if x["name"] == "Verzonden")
        assert t["subject"] == "Je order is onderweg{ordernummer}" and "Hallo {voornaam}" in t["html"] and t["files"][0]["name"] == "factuur.pdf", t
        ok("Mijn instellingen › Sjablonen: maken met invulvelden (ook in het onderwerp) en een bijlage; collega ziet het")
        pg.evaluate("closeOverlay()")
        pg.evaluate("openCompose({ mode: 'new', to: 'klant@voorbeeld.nl' })"); pg.wait_for_timeout(500)
        pg.click(".cmp [data-c=tpl]"); pg.wait_for_selector("dialog .tplpick")
        pg.locator("dialog .tplrow", has_text="Verzonden").click(); pg.wait_for_timeout(700)
        assert pg.input_value("#c-subj") == "Je order is onderweg[Ordernummer]"
        ok("nieuwe mail: onderwerp uit het sjabloon, onbekend veld zichtbaar om in te vullen")
        # deze tekst opslaan als sjabloon
        pg.click(".cmp [data-c=tpl]"); pg.wait_for_selector("dialog .tplpick")
        pg.click("#tpl-save"); pg.wait_for_selector("dialog [name=name]")
        pg.fill("dialog [name=name]", "Snel opgeslagen"); pg.locator("dialog button", has_text="Opslaan").click(); pg.wait_for_timeout(700)
        snel = next(x for x in a.call("templates") if x["name"] == "Snel opgeslagen")
        assert snel["user_id"] and "Hallo" in snel["html"] and "data-sig" not in snel["html"]
        ok("opstelscherm: deze tekst opslaan als sjabloon (zonder handtekening)")
        ctx.close()

        # beheer › Sjablonen: alle mailbox-sjablonen, geen eigen sjablonen van anderen
        ctx = br.new_context(viewport={"width": 1500, "height": 900})
        pg = login(ctx, "beheerder")
        pg.evaluate("openAdmin('tpls')"); pg.wait_for_timeout(700)
        side = pg.inner_text("#admbody")
        assert "Offerte" in side and "Verzonden" in side and "Snel opgeslagen" not in side
        ctx.close()
        ok("Beheer › Sjablonen: alle sjablonen per mailbox")

        # telefoon: knop Sjabloon in het opstelscherm
        ctx = br.new_context(viewport={"width": 390, "height": 760}, is_mobile=True, has_touch=True)
        pg = login(ctx, "medewerker-b")
        pg.evaluate("openCompose({ mode: 'new' })"); pg.wait_for_timeout(500)
        pg.click(".cmp [data-c=tpl]"); pg.wait_for_selector("dialog .tplpick")
        assert pg.locator("dialog .tplrow").count() >= 2
        box = pg.locator("dialog").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390
        pg.screenshot(path=os.path.join(os.environ.get("SHOTS", "/tmp"), "sjabloon_telefoon.png"))
        pg.locator("dialog .tplrow", has_text="Verzonden").click(); pg.wait_for_timeout(600)
        assert "factuur.pdf" in pg.inner_text("#c-files") and pg.evaluate("document.documentElement.scrollWidth") <= 390
        ctx.close()
        ok("telefoon: sjabloon kiezen in het opstelscherm, past op het scherm")
        br.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
