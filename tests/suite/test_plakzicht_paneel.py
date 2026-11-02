"""Plakzicht-paneel bij een echte koppeling: de ordergegevens komen apart na de mail. Bij verversen (collega, terugkomen in
het venster, elke minuut) mag het paneel niet steeds 'ophalen…' tonen en terugspringen (flitsen)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import Server, ok, stop_all  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("  – Playwright niet geïnstalleerd: overgeslagen")
    sys.exit(0)

# Zoals bij een echte Plakzicht: get_mail geeft 'pending', mail_plakzicht komt na een tijdje met de gegevens.
LIVE = """() => {
  const real = window.api;
  window.api = async (name, ...args) => {
    const r = await real(name, ...args);
    if (name === 'get_mail' && r && r.plakzicht) { window._pz = r.plakzicht; return { ...r, plakzicht: { pending: true, live: true } }; }
    if (name === 'mail_plakzicht') { await new Promise(res => setTimeout(res, 250)); return window._pz; }
    return r;
  };
  window._flits = 0; window._kort = 0;
  new MutationObserver(() => { if (/ophalen/.test(document.querySelector('#pz').textContent)) window._flits++; })
    .observe(document.querySelector('#pz'), { childList: true, subtree: true, characterData: true });
}"""

errors = []
srv = Server()
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, vp in (("computer", {"width": 1500, "height": 860}), ("telefoon", {"width": 390, "height": 760})):
            ctx = b.new_context(viewport=vp, is_mobile=vp["width"] < 500, has_touch=vp["width"] < 500)
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(srv.base + "/")
            pg.wait_for_selector("#keepbox:not([hidden])")
            pg.fill("[name=username]", "medewerker-a"); pg.fill("[name=password]", "demo"); pg.click("button[type=submit]")
            pg.wait_for_selector("#list .mrow")
            pg.evaluate(LIVE)
            first = pg.evaluate("[...document.querySelectorAll('#list .mrow')][0].dataset.id")
            pg.evaluate("id => openMail(id)", first)
            pg.wait_for_function("() => /Gekoppelde order/.test(document.querySelector('#pz').textContent)")
            assert pg.evaluate("window._flits") >= 1  # de eerste keer mag 'ophalen…' kort te zien zijn
            pg.evaluate("window._flits = 0")
            bar = pg.inner_text("#pzbar") if name == "telefoon" else ""
            for _ in range(6):  # verversen zoals bij een wijziging van een collega of terugkomen in het venster
                pg.evaluate("id => openMail(id, true)", first)
                pg.wait_for_timeout(350)
            assert pg.evaluate("window._flits") == 0, pg.evaluate("window._flits")
            assert "Gekoppelde order" in pg.inner_text("#pz")
            if name == "telefoon":
                assert pg.inner_text("#pzbar") == bar and "ophalen" not in bar
            ok(f"{name}: bij verversen blijft het Plakzicht-paneel staan (geen 'ophalen…'-flits)")
            ctx.close()
        b.close()
    assert not errors, errors
    print("OK")
finally:
    srv.close()
    stop_all()
