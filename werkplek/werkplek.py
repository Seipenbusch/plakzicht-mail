"""Plakzicht Mail-app voor een werkplek: een eigen venster naar de centrale Plakzicht Mail-server.

Er draait op deze pc verder niets; alle mail en instellingen staan op de server. De app kent twee adressen:
- lokaal:   het adres in het bedrijfsnetwerk, bijvoorbeeld http://192.168.1.20:8765
- internet: het adres via Cloudflare, bijvoorbeeld https://mail.plakzicht.nl
Bij het starten probeert de app eerst het lokale adres (snel, op kantoor) en anders het internetadres.

Instellingen: werkplek.json (per gebruiker; bij de geïnstalleerde versie in %APPDATA%\\Plakzicht Mail).
De installatie kan standaardadressen meegeven in werkplek-standaard.json naast het programma.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
USER_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Plakzicht Mail") if FROZEN else APP_DIR
CONF = os.path.join(USER_DIR, "werkplek.json")
DEFAULTS = os.path.join(APP_DIR, "werkplek-standaard.json")
LOCAL_TIMEOUT, NET_TIMEOUT = 1.5, 8


# ---------------------------------------------------------------- instellingen
def normalize(url):
    """'192.168.1.20:8765' -> http://..., 'mail.plakzicht.nl' -> https://... (een naam zonder poort is meestal internet)."""
    url = (url or "").strip().rstrip("/")
    if url and not re.match(r"^https?://", url, re.I):
        host = url.split("/")[0]
        url = ("http://" if re.match(r"^(\d+\.\d+\.\d+\.\d+|localhost)(:\d+)?$", host) or ":" in host else "https://") + url
    return url


def _read(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def load_conf():
    """Eigen instellingen, anders die van de installatie. Oude werkplek.json met alleen 'server' telt als lokaal adres."""
    d = _read(CONF) or _read(DEFAULTS)
    return {"lokaal": normalize(d.get("lokaal") or d.get("server")), "internet": normalize(d.get("internet"))}


def save_conf(lokaal, internet):
    os.makedirs(USER_DIR, exist_ok=True)
    conf = {"lokaal": normalize(lokaal), "internet": normalize(internet)}
    with open(CONF, "w", encoding="utf-8") as f:
        json.dump(conf, f, indent=2)
    return conf


# ---------------------------------------------------------------- server kiezen
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def probe(base, timeout):
    """'ok' = Plakzicht Mail antwoordt; 'gate' = er antwoordt iets (bijv. de aanmeldpagina van Cloudflare Access);
    None = niet bereikbaar."""
    if not base:
        return None
    op = urllib.request.build_opener(_NoRedirect)
    try:
        with op.open(base + "/health", timeout=timeout) as r:
            try:
                return "ok" if json.loads(r.read(2000)).get("app") == "plakzicht-mail" else "gate"
            except ValueError:
                return "gate"
    except urllib.error.HTTPError:
        return "gate"  # 302/401/403: Cloudflare Access vraagt eerst om aanmelden; het venster toont dat
    except (urllib.error.URLError, OSError, ValueError):
        return None


def choose(conf, probe_fn=probe):
    """Eerst lokaal (alleen als het echt Plakzicht Mail is), dan internet. Geeft (adres, uitleg) of (None, foutmelding)."""
    lok, net = conf.get("lokaal"), conf.get("internet")
    if not lok and not net:
        return None, ""
    if lok and probe_fn(lok, LOCAL_TIMEOUT) == "ok":
        return lok, "lokaal"
    if net and probe_fn(net, NET_TIMEOUT):
        return net, "internet"
    if lok and not net and probe_fn(lok, NET_TIMEOUT) == "ok":  # alleen lokaal ingevuld: iets langer wachten
        return lok, "lokaal"
    parts = [a for a in (lok, net) if a]
    return None, ("De server is niet bereikbaar op " + " en ".join(parts) +
                  ". Staat de server aan en heb je internet? Controleer anders de adressen.")


# ---------------------------------------------------------------- venster
SETUP_HTML = """<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Plakzicht Mail</title><style>
:root{color-scheme:light dark;--bg:#f4f6f5;--card:#fff;--ink:#1d2421;--muted:#5f6b66;--line:#d7ddda;--acc:#1f6f54;--bad:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#161a18;--card:#1f2421;--ink:#e6ebe8;--muted:#9aa7a1;--line:#343c38;--acc:#4fb38c;--bad:#f2b8b5}}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:14px/1.45 "Segoe UI",system-ui,sans-serif;padding:16px}
form{width:min(460px,100%);background:var(--card);border:1px solid var(--line);border-radius:12px;padding:26px;display:grid;gap:14px}
h1{margin:0;font-size:20px}h1 span{color:var(--acc)}p{margin:0;color:var(--muted)}label{display:grid;gap:4px;font-size:13px;color:var(--muted)}
input{font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:7px;background:transparent;color:var(--ink)}
button{font:inherit;padding:9px 14px;border-radius:7px;border:0;background:var(--acc);color:#fff;font-weight:600;cursor:pointer}button:disabled{opacity:.6}
.err{color:var(--bad)}.row{display:flex;gap:8px;align-items:center}.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:400}
</style></head><body><form id="f"><h1>Plakzicht <span>Mail</span></h1>
<p>Vul het adres van de Plakzicht Mail-server in. De app gebruikt op kantoor het adres in het netwerk en anders het internetadres. Je beheerder weet de adressen.</p>
<label>Adres in het bedrijfsnetwerk<input name="lokaal" placeholder="http://192.168.1.20:8765"></label>
<label>Internetadres (via Cloudflare)<input name="internet" placeholder="https://mail.plakzicht.nl"></label>
<p class="err" id="err" hidden></p>
<div class="row"><button id="go">Verbinden</button><button type="button" class="ghost" id="cancel" hidden>Annuleren</button></div></form>
<script>
const f=document.getElementById('f'),err=document.getElementById('err'),go=document.getElementById('go');
function ready(fn){ if(window.pywebview&&window.pywebview.api) fn(); else window.addEventListener('pywebviewready',fn); }
ready(async()=>{ const c=await window.pywebview.api.current();
  f.lokaal.value=c.lokaal||''; f.internet.value=c.internet||''; if(c.error){err.textContent=c.error;err.hidden=false;}
  if(c.back){const b=document.getElementById('cancel');b.hidden=false;b.onclick=()=>window.pywebview.api.back();} });
f.onsubmit=async e=>{e.preventDefault(); if(!f.lokaal.value.trim()&&!f.internet.value.trim()){err.textContent='Vul minstens een adres in.';err.hidden=false;return;}
  go.disabled=true; go.textContent='Verbinden…'; err.hidden=true;
  const r=await window.pywebview.api.connect(f.lokaal.value,f.internet.value);
  if(r&&r.error){err.textContent=r.error;err.hidden=false;go.disabled=false;go.textContent='Verbinden';} };
</script></body></html>"""


class Bridge:
    """Functies die de pagina via window.pywebview.api mag aanroepen."""

    def __init__(self):
        self.base = None
        self.error = ""
        self.window = None

    # -- instellscherm
    def current(self):
        return {**load_conf(), "error": self.error, "back": bool(self.base)}

    def connect(self, lokaal, internet):
        conf = save_conf(lokaal, internet)
        base, why = choose(conf)
        if not base:
            return {"error": why or "Vul minstens een adres in."}
        self.base, self.error = base, ""
        try:
            self.window.resize(1400, 880)
        except Exception:  # noqa: BLE001 - niet elk platform kan dat
            pass
        self.window.load_url(base + "/index.html")
        return {"ok": True}

    def back(self):
        if self.base:
            self.window.load_url(self.base + "/index.html")
        return True

    def client_settings(self):
        """Vanuit Plakzicht Mail: de serveradressen van deze app wijzigen."""
        self.window.load_html(SETUP_HTML)
        return True

    def client_info(self):
        return {**load_conf(), "current": self.base}

    # -- zoals voorheen
    def popout(self, mail_id, title="Mail"):
        import webview
        webview.create_window(f"{title} - Plakzicht Mail", f"{self.base}/index.html?popout={urllib.parse.quote(str(mail_id))}",
                              js_api=self, width=1000, height=780, min_size=(640, 480))
        return True

    def open_external(self, url):
        if re.match(r"^https?://", url or ""):
            webbrowser.open(url)
            return True
        return False

    def close_window(self):
        import webview
        w = webview.active_window()
        if w is not None and webview.windows and w is not webview.windows[0]:
            w.destroy()
        return True


def main():
    bridge = Bridge()
    base, why = choose(load_conf())
    bridge.base, bridge.error = base, why
    try:
        import webview
    except ImportError:  # zonder pywebview: in de gewone browser
        if base:
            webbrowser.open(base + "/index.html")
        else:
            print(why or "Vul het serveradres in werkplek.json in, bijvoorbeeld {\"lokaal\": \"http://192.168.1.20:8765\"}.")
        return
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True
    except (AttributeError, TypeError):
        pass
    if base:
        win = webview.create_window("Plakzicht Mail", base + "/index.html", js_api=bridge, width=1400, height=880, min_size=(1000, 640))
    else:
        win = webview.create_window("Plakzicht Mail", html=SETUP_HTML, js_api=bridge, width=620, height=560, min_size=(420, 460))
    bridge.window = win
    # cookies bewaren (ingelogd blijven) in een eigen map per gebruiker
    storage = os.path.join(USER_DIR, "venster")
    os.makedirs(storage, exist_ok=True)
    webview.start(private_mode=False, storage_path=storage)


if __name__ == "__main__":
    main()
