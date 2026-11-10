"""Werkplek-app: eerst het adres in het netwerk, anders het internetadres (ook als Cloudflare Access eerst om aanmelden vraagt)."""
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import ROOT, Server, free_port, ok, stop_all  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "werkplek"))
import werkplek as W  # noqa: E402
import tempfile  # noqa: E402
W.LOG = os.path.join(tempfile.mkdtemp(), "werkplek.log")  # nooit in de programmamap schrijven


class Access(BaseHTTPRequestHandler):
    """Doet zich voor als Cloudflare Access: stuurt door naar de aanmeldpagina."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "https://jouwbedrijf.cloudflareaccess.com/cdn-cgi/access/login")
        self.end_headers()


class Other(BaseHTTPRequestHandler):
    """Een ander programma op het lokale adres (geen Plakzicht Mail)."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = b"<html>router</html>"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


def serve(h):
    p = free_port()
    s = ThreadingHTTPServer(("127.0.0.1", p), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{p}"


assert W.normalize("192.168.1.20:8765") == "http://192.168.1.20:8765"
assert W.normalize("mail.plakzicht.nl/") == "https://mail.plakzicht.nl"
assert W.normalize("localhost:8765") == "http://localhost:8765"
assert W.normalize(" https://Mail.plakzicht.nl ") == "https://Mail.plakzicht.nl"
assert W.normalize("server:8765") == "http://server:8765"
ok("adressen worden aangevuld (http voor netwerk, https voor internet)")

srv = Server()
try:
    access, other = serve(Access), serve(Other)
    dead = f"http://127.0.0.1:{free_port()}"
    assert W.choose({"lokaal": srv.base, "internet": access}) == (srv.base, "lokaal")
    ok("op kantoor: het adres in het netwerk")
    assert W.choose({"lokaal": dead, "internet": access}) == (access, "internet")
    ok("thuis: via internet, ook als Cloudflare Access eerst om aanmelden vraagt")
    assert W.choose({"lokaal": other, "internet": srv.base}) == (srv.base, "internet")
    ok("ander apparaat op het lokale adres wordt niet aangezien voor de server")
    base, why = W.choose({"lokaal": dead, "internet": ""})
    assert base is None and dead in why
    assert W.choose({"lokaal": "", "internet": ""}) == (None, "")
    ok("niet bereikbaar of niets ingevuld: duidelijke melding / instelscherm")

    # instellingen: eigen bestand gaat voor dat van de installatie; oud formaat {"server": ...} werkt nog
    d = tempfile.mkdtemp()
    W.CONF, W.DEFAULTS, W.USER_DIR = os.path.join(d, "u", "werkplek.json"), os.path.join(d, "werkplek-standaard.json"), os.path.join(d, "u")
    W.LOG = os.path.join(d, "u", "werkplek.log")
    json.dump({"lokaal": "192.168.1.20:8765", "internet": "mail.plakzicht.nl"}, open(W.DEFAULTS, "w"))
    assert W.load_conf() == {"lokaal": "http://192.168.1.20:8765", "internet": "https://mail.plakzicht.nl"}
    W.save_conf("10.0.0.5:8765", "")
    assert W.load_conf() == {"lokaal": "http://10.0.0.5:8765", "internet": ""}
    json.dump({"server": "http://mailserver:8765"}, open(W.CONF, "w"))
    assert W.load_conf()["lokaal"] == "http://mailserver:8765"
    ok("standaardadressen van de installatie, eigen keuze gaat voor; oude werkplek.json werkt nog")

    # brug: verbinden laadt de server in het venster
    class Win:
        url = None

        def load_url(self, u):
            self.url = u

        def resize(self, w, h):
            pass

    b = W.Bridge()
    b._window = Win()
    assert "error" in b.connect(dead, "")
    assert b.connect(srv.base, "") == {"ok": True} and b._window.url == srv.base + "/index.html"
    ok("instelscherm: verbinden opent Plakzicht Mail")

    # pywebview doorloopt bij elke pagina alles van de brug zonder '_' (net als webview.util.inject_pywebview).
    # Een venster of ander object daarin liet de app vastlopen: alleen functies en gewone waarden mogen zichtbaar zijn.
    import inspect
    sys.path.insert(0, ROOT)
    import app as A  # noqa: E402
    for brug in (b, W.Bridge(), A.DesktopBridge("http://x")):
        for name in dir(brug):
            if name.startswith("_"):
                continue
            attr = getattr(brug, name)
            assert inspect.ismethod(attr) or attr is None or isinstance(attr, (str, int, float, bool)), (type(brug).__name__, name, type(attr))
    ok("brug naar de pagina: geen venster of ander object dat pywebview doorzoekt (oorzaak van het vastlopen)")

    # opstarten met een nagebootst venster: meteen 'Verbinden…', daarna de server of het foutscherm, en een logbestand
    import types
    calls = []

    class FakeWin:
        def __init__(self, **kw):
            self.kw, self.urls, self.htmls = kw, [], []

        def load_url(self, u):
            self.urls.append(u)

        def load_html(self, h):
            self.htmls.append(h)

        def resize(self, w, h):
            pass

        def get_current_url(self):
            return (self.urls or [""])[-1]

    class Ev(list):
        def __iadd__(self, fn):
            self.append(fn); return self

    fake = types.ModuleType("webview")
    fake.settings = {}
    fake.create_window = lambda title, url=None, html=None, js_api=None, **kw: calls.append(FakeWin(html=html, url=url, **kw)) or setattr(calls[-1], 'events', types.SimpleNamespace(loaded=Ev(), closed=Ev())) or calls[-1]
    fake.start = lambda func=None, *a, **kw: func and func()
    sys.modules["webview"] = fake
    W.save_conf(srv.base.replace("127.0.0.1", "127.0.0.1"), "")
    W.main()
    win = calls[-1]
    assert win.kw["html"] == W.LOADING_HTML and win.urls == [srv.base + "/index.html"], (win.kw.get("html", "")[:40], win.urls)
    for fn in win.events.loaded:
        fn()
    W.save_conf(dead, "")
    W.main()
    win = calls[-1]
    assert win.kw["html"] == W.LOADING_HTML and win.htmls == [W.SETUP_HTML] and not win.urls
    logtxt = open(W.LOG, encoding="utf-8").read()
    for want in ("start", "vensteronderdelen geladen", "venster zichtbaar", "verbonden via lokaal", "pagina geladen: " + srv.base, "geen server bereikbaar"):
        assert want in logtxt, want
    ok("opstarten: meteen een venster met 'Verbinden…', daarna de server of het foutscherm; tijden in werkplek.log")

    # beide adressen tegelijk: een traag netwerkadres houdt het internetadres niet op
    import time as _t
    slow = lambda url, timeout, local=False: (_t.sleep(timeout) or None) if url == "http://traag" else "gate"
    t0 = _t.time()
    assert W.choose({"lokaal": "http://traag", "internet": "https://net"}, slow) == ("https://net", "internet")
    assert _t.time() - t0 < W.LOCAL_TIMEOUT + 0.5
    ok("netwerkadres en internetadres tegelijk geprobeerd (thuis niet eerst wachten op het netwerkadres)")
    print("OK")
finally:
    srv.close()
    stop_all()
