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
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
USER_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Plakzicht Mail") if FROZEN else APP_DIR
CONF = os.path.join(USER_DIR, "werkplek.json")
DEFAULTS = os.path.join(APP_DIR, "werkplek-standaard.json")
LOG = os.path.join(USER_DIR, "werkplek.log")
LOCAL_TIMEOUT, NET_TIMEOUT = 1.5, 8
T0 = time.time()


def log(msg):
    """Logbestand met tijden per stap (werkplek.log), zodat zichtbaar is waar het opstarten blijft hangen."""
    try:
        os.makedirs(USER_DIR, exist_ok=True)
        if os.path.exists(LOG) and os.path.getsize(LOG) > 200_000:
            os.replace(LOG, LOG + ".1")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} +{time.time() - T0:5.2f}s  {msg}\n")
    except OSError:
        pass


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


def probe(base, timeout, local=False):
    """'ok' = Plakzicht Mail antwoordt; 'gate' = er antwoordt iets (bijv. de aanmeldpagina van Cloudflare Access);
    None = niet bereikbaar. Lokaal zonder proxy: Windows-proxyinstellingen kunnen anders seconden kosten."""
    if not base:
        return None
    handlers = [_NoRedirect] + ([urllib.request.ProxyHandler({})] if local else [])
    op = urllib.request.build_opener(*handlers)
    t = time.time()
    try:
        with op.open(base + "/health", timeout=timeout) as r:
            try:
                res = "ok" if json.loads(r.read(2000)).get("app") == "plakzicht-mail" else "gate"
            except ValueError:
                res = "gate"
    except urllib.error.HTTPError as e:
        res = "gate"  # 302/401/403: Cloudflare Access vraagt eerst om aanmelden; het venster toont dat
        log(f"{base}: HTTP {e.code}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        res = None
        log(f"{base}: niet bereikbaar ({getattr(e, 'reason', e)})")
    log(f"{base}: {res or 'geen antwoord'} in {time.time() - t:.2f}s")
    return res


def choose(conf, probe_fn=probe):
    """Beide adressen tegelijk proberen. Het netwerkadres wint als het binnen LOCAL_TIMEOUT echt Plakzicht Mail is,
    anders het internetadres. Geeft (adres, 'lokaal'/'internet') of (None, foutmelding)."""
    lok, net = conf.get("lokaal"), conf.get("internet")
    if not lok and not net:
        return None, ""
    res, done = {}, {k: threading.Event() for k in ("lokaal", "internet")}

    def run(k, url, timeout):
        try:
            res[k] = probe_fn(url, timeout, local=True) if k == "lokaal" else probe_fn(url, timeout)
        except TypeError:  # probe zonder local-argument (tests)
            res[k] = probe_fn(url, timeout)
        finally:
            done[k].set()
    for k, url in (("lokaal", lok), ("internet", net)):
        if url:
            threading.Thread(target=run, args=(k, url, LOCAL_TIMEOUT if (k == "lokaal" and net) else NET_TIMEOUT), daemon=True).start()
        else:
            done[k].set()
    if lok:
        done["lokaal"].wait(NET_TIMEOUT + 1)
        if res.get("lokaal") == "ok":
            return lok, "lokaal"
    if net:
        done["internet"].wait(NET_TIMEOUT + 1)
        if res.get("internet"):
            return net, "internet"
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
<div class="row"><button id="go">Verbinden</button><button type="button" class="ghost" id="cancel" hidden>Annuleren</button>
<button type="button" class="ghost" id="logb" hidden>Logbestand openen</button></div></form>
<script>
const f=document.getElementById('f'),err=document.getElementById('err'),go=document.getElementById('go');
function ready(fn){ if(window.pywebview&&window.pywebview.api) fn(); else window.addEventListener('pywebviewready',fn); }
ready(async()=>{ const c=await window.pywebview.api.current();
  f.lokaal.value=c.lokaal||''; f.internet.value=c.internet||''; if(c.error){err.textContent=c.error;err.hidden=false;go.textContent='Opnieuw proberen';
    const l=document.getElementById('logb');l.hidden=false;l.onclick=()=>window.pywebview.api.open_log();}
  if(c.back){const b=document.getElementById('cancel');b.hidden=false;b.onclick=()=>window.pywebview.api.back();} });
f.onsubmit=async e=>{e.preventDefault(); if(!f.lokaal.value.trim()&&!f.internet.value.trim()){err.textContent='Vul minstens een adres in.';err.hidden=false;return;}
  go.disabled=true; go.textContent='Verbinden…'; err.hidden=true;
  const r=await window.pywebview.api.connect(f.lokaal.value,f.internet.value);
  if(r&&r.error){err.textContent=r.error;err.hidden=false;go.disabled=false;go.textContent='Verbinden';} };
</script></body></html>"""


LOADING_HTML = """<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>Plakzicht Mail</title><style>
:root{color-scheme:light dark;--bg:#f4f6f5;--ink:#1d2421;--muted:#5f6b66;--acc:#1f6f54}
@media (prefers-color-scheme:dark){:root{--bg:#0c0f0e;--ink:#e6ebe8;--muted:#9aa7a1;--acc:#5cc49b}}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:14px/1.5 "Segoe UI",system-ui,sans-serif}
.b{display:grid;justify-items:center;gap:14px;text-align:center}h1{margin:0;font-size:22px}h1 span{color:var(--acc)}
.sp{width:28px;height:28px;border:3px solid color-mix(in srgb,var(--acc) 25%,transparent);border-top-color:var(--acc);border-radius:50%;animation:r .8s linear infinite}
@keyframes r{to{transform:rotate(360deg)}}p{margin:0;color:var(--muted)}#a{font-size:12.5px}
</style></head><body><div class="b"><h1>Plakzicht <span>Mail</span></h1><div class="sp"></div><p>Verbinden met de server…</p><p id="a"></p></div>
<script>function ready(fn){ if(window.pywebview&&window.pywebview.api) fn(); else window.addEventListener('pywebviewready',fn); }
ready(async()=>{ const c=await window.pywebview.api.current(); document.getElementById('a').textContent=[c.lokaal,c.internet].filter(Boolean).join('  ·  '); });</script></body></html>"""


def close_splash():
    """Het opstartplaatje van de installatie (PyInstaller) sluiten zodra het venster er is."""
    try:
        import pyi_splash  # alleen in de geïnstalleerde versie
        pyi_splash.close()
    except Exception:  # noqa: BLE001
        pass


class Bridge:
    """Functies die de pagina via window.pywebview.api mag aanroepen."""

    def __init__(self):
        # Alles zonder '_' geeft pywebview door aan de pagina; het doorloopt daarvoor bij elke pagina alle eigenschappen.
        # Het venster zelf hoort daar nooit bij: dat doorzoeken wacht op de pagina en de pagina op het doorzoeken,
        # waardoor het venster vastliep. Daarom privé (_window) en de rest alleen tekst.
        self.base = None
        self.error = ""
        self._window = None

    # -- instellscherm
    def current(self):
        return {**load_conf(), "error": self.error, "back": bool(self.base)}

    def connect_now(self):
        """Verbinden met de opgeslagen adressen (bij het starten en bij 'Opnieuw proberen')."""
        base, why = choose(load_conf())
        if not base:
            log("geen server bereikbaar")
            self.error = why
            self._window.load_html(SETUP_HTML)
            return False
        log(f"verbonden via {why}: {base}")
        self.base, self.error = base, ""
        self._window.load_url(base + "/index.html")
        return True

    def open_log(self):
        try:
            os.startfile(LOG)  # noqa: S606 - alleen op Windows
        except (AttributeError, OSError):
            webbrowser.open("file://" + LOG)
        return True

    def connect(self, lokaal, internet):
        conf = save_conf(lokaal, internet)
        base, why = choose(conf)
        if not base:
            log("geen server bereikbaar met de ingevulde adressen")
            return {"error": why or "Vul minstens een adres in."}
        log(f"verbonden via {why}: {base}")
        self.base, self.error = base, ""
        try:
            self._window.resize(1400, 880)
        except Exception:  # noqa: BLE001 - niet elk platform kan dat
            pass
        self._window.load_url(base + "/index.html")
        return {"ok": True}

    def back(self):
        if self.base:
            self._window.load_url(self.base + "/index.html")
        return True

    def client_settings(self):
        """Vanuit Plakzicht Mail: de serveradressen van deze app wijzigen."""
        self._window.load_html(SETUP_HTML)
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
    log(f"start ({'geïnstalleerd' if FROZEN else 'vanuit de broncode'})")
    conf = load_conf()
    bridge = Bridge()
    try:
        import webview
    except ImportError:  # zonder pywebview: in de gewone browser
        base, why = choose(conf)
        if base:
            webbrowser.open(base + "/index.html")
        else:
            print(why or "Vul het serveradres in werkplek.json in, bijvoorbeeld {\"lokaal\": \"http://192.168.1.20:8765\"}.")
        return
    log("vensteronderdelen geladen")
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True
    except (AttributeError, TypeError):
        pass
    has = bool(conf["lokaal"] or conf["internet"])
    # Meteen een venster ('Verbinden met de server…'); het verbinden gebeurt daarna, zodat de app nooit lijkt vast te hangen.
    win = webview.create_window("Plakzicht Mail", html=LOADING_HTML if has else SETUP_HTML, js_api=bridge,
                                width=1400 if has else 620, height=880 if has else 560, min_size=(420, 460))
    bridge._window = win
    try:  # in het logbestand: is de pagina echt geladen?
        win.events.loaded += lambda *a: log("pagina geladen: " + str(win.get_current_url() or "")[:80])
        win.events.closed += lambda *a: log("venster gesloten")
    except Exception:  # noqa: BLE001 - oudere pywebview of nagebootst venster
        pass

    def started():
        close_splash()
        log("venster zichtbaar")
        if has:
            bridge.connect_now()

    storage = os.path.join(USER_DIR, "venster")  # cookies bewaren (ingelogd blijven), per gebruiker
    os.makedirs(storage, exist_ok=True)
    webview.start(started, private_mode=False, storage_path=storage)
    log("afgesloten")


if __name__ == "__main__":
    main()
