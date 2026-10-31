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
    b.window = Win()
    assert "error" in b.connect(dead, "")
    assert b.connect(srv.base, "") == {"ok": True} and b.window.url == srv.base + "/index.html"
    ok("instelscherm: verbinden opent Plakzicht Mail")
    print("OK")
finally:
    srv.close()
    stop_all()
