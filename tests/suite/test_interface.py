"""Interface (Playwright): inloggen met 'ingelogd blijven', na herstart van de server nog ingelogd, Apparaten,
beheer en het app-profiel (manifest). Ook op telefoonbreedte (390 px). Slaat over als Playwright ontbreekt."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import Server, ok, stop_all  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  – Playwright niet geïnstalleerd: interfacetest overgeslagen")
    sys.exit(0)

errors = []
srv = Server()
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1500, "height": 900})
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(srv.base + "/")
        pg.wait_for_selector("#login:not([hidden])")
        pg.focus("[name=password]")  # meteen in het wachtwoordveld: de cursor mag niet terugspringen
        pg.wait_for_selector("#keepbox:not([hidden])")
        pg.wait_for_timeout(300)
        assert pg.evaluate("document.activeElement.name") == "password"
        ok("inlogscherm: cursor springt niet terug als je al in het wachtwoordveld zit")
        assert pg.is_checked("#keepbox input") and "30 dagen" in pg.inner_text("#keepbox")
        ok("inlogscherm: vinkje 'Ingelogd blijven' staat standaard aan")
        pg.fill("[name=username]", "medewerker-a"); pg.fill("[name=password]", "demo"); pg.click("button[type=submit]")
        pg.wait_for_selector("#list .mrow")

        srv.restart()
        pg.reload()
        pg.wait_for_selector("#list .mrow", timeout=15000)
        assert pg.is_hidden("#login")
        ok("na herstart van de server en herladen: direct in de mail, zonder inloggen")

        ctx2 = b.new_context(viewport={"width": 1500, "height": 900}, storage_state=ctx.storage_state())
        pg2 = ctx2.new_page()
        pg2.goto(srv.base + "/")
        pg2.wait_for_selector("#list .mrow", timeout=15000)
        ok("browser opnieuw gestart (alleen de bewaarde cookies): direct in de mail")
        ctx2.close()

        pg.evaluate("openMySettings(undefined, 'dev')")
        pg.wait_for_selector(".devtable")
        assert "dit apparaat" in pg.inner_text(".devtable") and "Linux · Chrome" in pg.inner_text(".devtable")
        ok("Mijn instellingen › Apparaten toont dit apparaat")

        man = pg.evaluate("fetch('manifest.webmanifest').then(r => r.json())")
        assert man["display"] == "standalone" and len(man["icons"]) == 3
        assert pg.evaluate("fetch('icons/icon-512.png').then(r => r.ok)")
        assert pg.evaluate("navigator.serviceWorker.getRegistration().then(r => !!r)")
        ok("app-profiel: manifest, iconen en service worker (installeren als app)")

        pg.evaluate("closeOverlay()")
        pg.click("#btn-logout")
        pg.wait_for_selector("#login:not([hidden])")
        pg.reload()
        pg.wait_for_selector("#login:not([hidden])")
        ok("uitloggen: na herladen weer het inlogscherm")

        # beheerder
        pg.fill("[name=username]", "beheerder"); pg.fill("[name=password]", "demo"); pg.click("button[type=submit]")
        pg.wait_for_selector("#list .mrow")
        pg.evaluate("openAdmin('server')")
        pg.wait_for_selector("#keepform")
        pg.fill("#keepform [name=days]", "14"); pg.click("#keepform button")
        pg.wait_for_timeout(600)
        assert pg.input_value("#keepform [name=days]") == "14"
        pg.evaluate("openAdmin('users')")
        pg.wait_for_selector("#uform")
        assert "1 apparaat" in pg.inner_text("#admbody table")
        pg.click("[data-u] >> text=Medewerker A")
        pg.wait_for_selector("#u-off")
        ok("beheer: duur instellen, apparaten per gebruiker, knop 'Overal afmelden'")

        # telefoonbreedte
        ph = b.new_context(viewport={"width": 390, "height": 800}).new_page()
        ph.on("pageerror", lambda e: errors.append(str(e)))
        ph.goto(srv.base + "/")
        ph.wait_for_selector("#keepbox:not([hidden])")
        w = ph.evaluate("document.documentElement.scrollWidth")
        assert w <= 390, w
        ok("telefoonbreedte: inlogscherm past (geen horizontaal scrollen)")
        b.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
