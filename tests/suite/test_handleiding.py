"""Handleiding: opbouw van de teksten, elke instellingen- en beheerpagina heeft uitleg, zoeken (ook met tikfouten),
beheerdersdeel alleen voor beheerders, 'Afspraken' die alleen de beheerder schrijft, ?-knoppen, F1 en de telefoon."""
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import ROOT, Client, Server, expect_error, ok, stop_all  # noqa: E402

HELP = os.path.join(ROOT, "ui", "help")
APP = open(os.path.join(ROOT, "ui", "app.js"), encoding="utf-8").read()


def articles(name):
    text = re.sub(r"<!--[\s\S]*?-->", "", open(os.path.join(HELP, name), encoding="utf-8").read())
    out = []
    for m in re.finditer(r"^## (.+?)\s*\{#([\w-]+)\}\s*\n(?:trefwoorden: (.*)\n)?(?:plek: (.*)\n)?([\s\S]*?)(?=^#{1,2} |\Z)", text, re.M):
        out.append({"title": m[1], "id": m[2], "keys": m[3] or "", "plek": [x.strip() for x in (m[4] or "").split(",") if x.strip()], "body": m[5]})
    return out


gewoon, beheer = articles("handleiding.md"), articles("beheer.md")
alle = gewoon + beheer
ids = [a["id"] for a in alle]
assert len(ids) == len(set(ids)), "dubbele id's"
assert len(gewoon) >= 40, len(gewoon)
for a in alle:
    assert a["keys"].strip(), f"{a['id']}: trefwoorden ontbreken"
    assert len(a["body"].strip()) > 80, f"{a['id']}: te weinig tekst"
    for link in re.findall(r"\]\(#([\w-]+)\)", a["body"]):
        assert link in ids, f"{a['id']}: link naar onbekend artikel #{link}"
ok(f"{len(gewoon)} artikelen voor iedereen, {len(beheer)} voor beheerders; elk met trefwoorden; alle verwijzingen kloppen")

# Elke pagina in Mijn instellingen en Beheer heeft een artikel (nieuwe pagina = ook uitleg schrijven)
secs = re.findall(r"\['(\w+)', '[^']+'\]", re.search(r"const secs = \[(.*?)\];", APP).group(1))
tabs = re.findall(r"\['(\w+)', '[^']+'\]", re.search(r"const tabs = \[\['users'(.*?)\];", APP).group(0))
pleks = {p for a in alle for p in a["plek"]}
missing = [f"my:{s}" for s in secs if f"my:{s}" not in pleks] + [f"adm:{t}" for t in tabs if f"adm:{t}" not in pleks]
assert not missing, f"Geen uitleg voor: {missing}"
for p in re.findall(r"helpBtn\('([\w:-]+)'[,)]", APP):
    assert p in pleks, f"?-knop naar onbekende plek {p}"
for p in {p for a in gewoon for p in a["plek"]}:
    assert not p.startswith("adm:"), f"beheerplek {p} in de gewone handleiding"
ok(f"uitleg voor alle {len(secs)} pagina's van Mijn instellingen en {len(tabs)} van Beheer; alle ?-knoppen wijzen naar een artikel")

srv = Server()
try:
    # handleiding alleen na inloggen en via de API; beheer.md alleen voor beheerders
    for path in ("/help/handleiding.md", "/help/beheer.md", "/help/", "/./help/beheer.md", "/help%2Fbeheer.md"):
        try:
            urllib.request.urlopen(srv.base + path)
            raise AssertionError(f"{path} is los op te halen")
        except urllib.error.HTTPError as e:
            assert e.code == 404, (path, e.code)
    a, adm = Client(srv.base), Client(srv.base)
    expect_error(lambda: a.call("help"), "")
    a.call("login", "medewerker-a", "demo"); adm.call("login", "beheerder", "demo")
    h = a.call("help")
    assert "{#zoeken}" in h["text"] and h["admin"] is None and h["can_edit"] is False
    assert "{#gebruikers}" in adm.call("help")["admin"] and adm.call("help")["can_edit"] is True
    expect_error(lambda: a.call("help_save_afspraak", {"title": "x", "body": "y"}), "beheerder")
    aid = adm.call("help_save_afspraak", {"title": "Wie pakt info@ op?", "keywords": "rooster, verdeling",
                                          "body": "Ochtend: **Medewerker A**.\n- Middag: Medewerker B\n<script>alert(1)</script>"})
    assert a.call("help")["afspraken"][0]["title"] == "Wie pakt info@ op?"
    expect_error(lambda: adm.call("help_save_afspraak", {"title": "", "body": "y"}), "titel")
    ok("handleiding alleen na inloggen; beheerdersdeel alleen voor beheerders; afspraken alleen door de beheerder")

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

    def search(pg, q):
        pg.fill("#h-q", q); pg.wait_for_timeout(350)
        return [t.split("\n")[0] for t in pg.locator("#h-nav .hres").all_inner_texts()]

    SHOTS = os.environ.get("SHOTS")
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1400, "height": 860})
        pg = login(ctx)
        pg.click("#btn-help"); pg.wait_for_selector("#helpov:not([hidden]) #h-art h2")
        assert pg.inner_text("#h-art h2") == "Wat is Plakzicht Mail?"
        assert "Beheer" not in pg.inner_text("#h-nav") and "Wie pakt info@ op?" in pg.inner_text("#h-nav")
        for q, want in (("sjabloon", "Sjablonen gebruiken"), ("sjabloom", "Sjablonen gebruiken"), ("hoe maak ik een map", "Mappen maken en beheren"),
                        ("afwezig", "Agenda"), ("vegen", "Vegen op de telefoon"), ("spam", "Ongewenste mail en phishing melden"),
                        ("wachtwoord vergeten", "Wachtwoord wijzigen"), ("dark mode", "Licht of donker"), ("ctrl r", "Sneltoetsen"),
                        ("rooster", "Wie pakt info@ op?")):
            r = search(pg, q)
            assert r and r[0] == want, (q, r[:3])
        assert search(pg, "xyzzyqq") == [] and "Niets gevonden" in pg.inner_text("#h-nav")
        ok("zoeken: op titel, trefwoorden en tekst, met tikfouten ('sjabloom'), gewone zinnen en eigen afspraken")
        search(pg, "sneltoetsen"); pg.locator("#h-nav .hres").first.click(); pg.wait_for_timeout(200)
        assert pg.locator("#h-art table kbd", has_text="Ctrl+R").count() == 1
        search(pg, ""); pg.locator("#h-nav .hlink", has_text="Wie pakt info@ op?").click(); pg.wait_for_timeout(200)
        body = pg.inner_html("#h-art .hbody")
        assert "<b>Medewerker A</b>" in body and "<li>Middag" in body and "<script" not in body and "&lt;script&gt;" in body
        assert pg.locator("#h-edit").count() == 0
        pg.locator("#h-nav .hlink", has_text="Concepten").click(); pg.wait_for_timeout(200)
        pg.locator("#h-art a[data-help]").count() == 0 or pg.locator("#h-art a[data-help]").first.click()
        pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
        assert pg.is_hidden("#helpov")
        ok("artikel: opmaak, tabel met toetsen, eigen afspraak veilig weergegeven; medewerker kan niet wijzigen; Esc sluit")

        # ?-knop op een pagina opent het juiste artikel, terug = weer op die pagina; F1
        pg.evaluate("openMySettings(undefined, 'tpl')"); pg.wait_for_timeout(400)
        pg.click("#overlay .ohead [data-helpplek]"); pg.wait_for_selector("#helpov:not([hidden]) #h-art h2")
        assert pg.inner_text("#h-art h2") == "Sjablonen maken"
        pg.click("#helpov [data-close]"); pg.wait_for_timeout(200)
        assert pg.is_visible("#mybody") and pg.is_hidden("#helpov")
        pg.keyboard.press("F1"); pg.wait_for_timeout(400)
        assert pg.inner_text("#h-art h2") == "Sjablonen maken"
        pg.keyboard.press("F1"); pg.wait_for_timeout(200)
        assert pg.is_hidden("#helpov")
        pg.evaluate("closeOverlay()")
        pg.evaluate("openCompose({ mode: 'new' })"); pg.wait_for_timeout(400)
        pg.click(".cmp [data-c=tpl]"); pg.wait_for_selector("dialog .tplpick")
        pg.click("dialog [data-helpplek]"); pg.wait_for_timeout(400)
        assert pg.inner_text("#h-art h2") == "Sjablonen gebruiken" and pg.evaluate("!!S.cmp")
        pg.click("#helpov [data-close]")
        ok("?-knop en F1 openen de uitleg van die pagina; terug kom je weer op dezelfde plek (ook met een mail in wording)")
        ctx.close()

        # beheerder: beheerdersdeel en afspraken schrijven
        ctx = b.new_context(viewport={"width": 1400, "height": 860})
        pg = login(ctx, "beheerder")
        pg.keyboard.press("F1"); pg.wait_for_selector("#helpov:not([hidden]) #h-nav")
        assert "Gebruikers beheren" in pg.inner_text("#h-nav")
        assert search(pg, "nieuwe collega toevoegen")[0] == "Gebruikers beheren"
        search(pg, "")
        pg.click("#h-new"); pg.fill("#h-form [name=title]", "Klachten"); pg.fill("#h-form [name=keywords]", "boos, ontevreden")
        pg.fill("#h-form [name=body]", "1. Bel de klant terug.\n2. Zet label **Klacht**.\n> Altijd binnen een dag.")
        assert "<ol>" in pg.inner_html("#h-prev")
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "handleiding_afspraak.png"))
        pg.click("#h-form .btn.primary"); pg.wait_for_timeout(600)
        assert pg.inner_text("#h-art h2") == "Klachten" and pg.locator("#h-edit").count() == 1
        assert search(pg, "ontevreden")[0] == "Klachten"
        pg.click("#h-nav .hres"); pg.click("#h-del"); pg.locator("dialog button", has_text="Verwijderen").click(); pg.wait_for_timeout(600)
        assert not any(x["title"] == "Klachten" for x in adm.call("help")["afspraken"])
        pg.click("#helpov [data-close]")
        pg.evaluate("openAdmin('detect')"); pg.wait_for_timeout(500)
        pg.click("#overlay .ohead [data-helpplek]"); pg.wait_for_timeout(400)
        assert pg.inner_text("#h-art h2") == "Plakzicht en herkenning" and "alleen beheerders" in pg.inner_text("#h-art")
        ctx.close()
        ok("beheerder: ziet het beheerdeel, maakt, vindt en verwijdert een afspraak (met voorbeeld van de opmaak)")

        # telefoon: via het menu, eerst de lijst, dan het artikel, terug
        ctx = b.new_context(viewport={"width": 390, "height": 760}, is_mobile=True, has_touch=True)
        pg = login(ctx)
        pg.click("#m-me"); pg.locator(".cmenu button", has_text="Handleiding").click(); pg.wait_for_timeout(500)
        assert pg.is_visible("#h-art") and pg.is_visible("#h-back")
        pg.click("#h-back"); pg.wait_for_timeout(200)
        assert pg.is_visible("#h-nav") and pg.is_hidden("#h-art")
        r = search(pg, "vegen")
        assert r[0] == "Vegen op de telefoon"
        pg.locator("#h-nav .hres").first.click(); pg.wait_for_timeout(300)
        assert pg.is_visible("#h-art") and "naar **links**" not in pg.inner_text("#h-art")
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390 and pg.evaluate("document.querySelector('#helpov').scrollWidth") <= 390
        if SHOTS:
            pg.screenshot(path=os.path.join(SHOTS, "handleiding_telefoon.png"))
        ctx.close()
        ok("telefoon: Handleiding in het menu, zoeken, artikel openen en terug; past op 390 px")
        b.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
