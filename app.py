"""Plakzicht Mail - testversie.

Start als desktopprogramma:   python app.py
Start in de browser:          python app.py --browser

Twee standen (te kiezen in Beheer > Microsoft-koppeling):
- Demo: alles nagebootst in mail_demo.db, er gaat niets naar Microsoft.
- Microsoft 365: echte mailboxen via Microsoft Graph (zie graph.py), eigen
  gegevens (gebruikers, labels, koppelingen met Plakzicht) in mail_microsoft.db.
Orders en offertes komen in beide standen nog uit een nagebootste Plakzicht.
"""
import base64
import datetime as dt
import hashlib
import html
import json
import os
import re
import secrets
import socket
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from graph import CAL_TZ, CALENDAR_SCOPES, DeviceSignIn, Graph, GraphError, MsCalendar, MsMail, SignIn, nl_error
from mscache import DEFAULT_DAYS, PERIODS, MailCache, cutoff
from plakzicht import PlakzichtApi, PlakzichtError

FROZEN = getattr(sys, "frozen", False)  # geïnstalleerde Windows-versie (setup.exe)
BASE = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
UI = os.path.join(BASE, "ui")
IN_DOCKER = os.environ.get("PLAKZICHT_DOCKER") == "1"


def _data_dir():
    """Waar gegevens staan: PLAKZICHT_DATA (Docker: /data), bij de Windows-installatie ProgramData, anders de programmamap."""
    d = os.environ.get("PLAKZICHT_DATA", "").strip()
    if not d and FROZEN:
        d = os.path.join(os.environ.get("PROGRAMDATA") or os.path.expanduser("~"), "Plakzicht Mail")
    d = d or os.path.dirname(os.path.abspath(__file__))
    os.makedirs(d, exist_ok=True)
    return d


DATA = _data_dir()
CONFIG = os.path.join(DATA, "config.json")
SECRETS_KEY = os.path.join(DATA, "secrets.key")
DBS = {"demo": os.path.join(DATA, "mail_demo.db"), "microsoft": os.path.join(DATA, "mail_microsoft.db")}
try:  # bij de Windows-installatie ingebakken door de bouwstap
    from versie_build import PLAKZICHT_VERSION as _BUILT_VERSION
except ImportError:
    _BUILT_VERSION = ""
VERSION = os.environ.get("PLAKZICHT_VERSION", "").strip() or _BUILT_VERSION or "ontwikkel"
DB = DBS["demo"]
DENSITIES = ("smal", "middel", "breed")
FOLDERS = (("inbox", "Postvak IN"), ("sent", "Verzonden"), ("archive", "Archief"), ("junk", "Ongewenste e-mail"), ("deleted", "Verwijderde items"))
RULE_FIELDS = ("from", "to", "subject", "body", "any", "order")
RULE_OPS = ("contains", "not_contains", "is", "starts", "has", "none")
DEFAULT_SETTINGS = {
    "order_pattern": r"\b\d{9}\b",
    "offerte_pattern": r"\bOFF-\d{4}-\d{3}\b",
    "plakzicht_url": "",
    "remember_days": "30",   # ingelogd blijven: maximaal zoveel dagen zonder gebruik (0 = uit)
}
_lock = threading.Lock()
LIST_COLS = ("imp", "rem", "type", "att", "from", "subj", "date", "size", "cats", "mention", "flag", "order", "claim", "mailbox")
SORT_KEYS = ("date", "from", "to", "subject", "size", "importance", "due", "read", "att", "cats", "mention", "flag", "order", "claim", "mailbox")
DEFAULT_PREFS = {
    "listview": "kolommen", "groups": True, "reply_in": "pane",
    "cols": ["imp", "rem", "type", "att", "from", "subj", "date", "size", "cats", "mention", "flag"],
    "colw": {}, "sort": {"key": "date", "dir": "desc"},
    "claude": {"tone": "zakelijk", "aanhef": "u", "lang": "mail", "extra": ""},
    "notify": {"on": True, "sound": True, "desktop": True, "mute": []},
}
CLAUDE_URL = os.environ.get("PLAKZICHT_CLAUDE_URL", "https://api.anthropic.com/v1/messages")
CLAUDE_MODELS = [("claude-sonnet-5-5", "Claude Sonnet 5.5 (aanbevolen)"), ("claude-haiku-5-5", "Claude Haiku 5.5 (snel en goedkoop)"),
                 ("claude-opus-5-5", "Claude Opus 5.5 (krachtigst)")]


# ---------------------------------------------------------------- instellingen en geheim
def _dpapi(data, protect):
    """Windows-versleuteling van oudere versies (DPAPI); alleen nog nodig om oude waarden om te zetten."""
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    inp, out = Blob(len(data), buf), Blob()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)):
        raise OSError("DPAPI mislukt")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


ENC = "enc1:"
_FERNET = []


def _fernet():
    """Sleutel uit PLAKZICHT_SECRETS_KEY of secrets.key in de datamap (wordt de eerste keer gemaakt).
    Zonder die sleutel zijn de opgeslagen geheimen in config.json en in back-ups niet te lezen."""
    if not _FERNET:
        from cryptography.fernet import Fernet
        key = os.environ.get("PLAKZICHT_SECRETS_KEY", "").strip()
        if not key:
            if not os.path.exists(SECRETS_KEY):
                fd = os.open(SECRETS_KEY, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as f:
                    f.write(Fernet.generate_key().decode())
            with open(SECRETS_KEY, encoding="utf-8") as f:
                key = f.read().strip()
        _FERNET.append(Fernet(key.encode()))
    return _FERNET[0]


def _protect(secret):
    if not secret:
        return ""
    return ENC + _fernet().encrypt(secret.encode()).decode()


class SecretUnreadable(RuntimeError):
    pass


def _unprotect(stored):
    if not stored:
        return ""
    kind, _, val = stored.partition(":")
    if kind == "enc1":
        from cryptography.fernet import InvalidToken
        try:
            return _fernet().decrypt(val.encode()).decode()
        except (InvalidToken, ValueError):
            raise SecretUnreadable("Een opgeslagen geheim is niet te lezen: secrets.key hoort niet bij deze config.json. "
                                   "Zet de juiste secrets.key terug of vul het geheim opnieuw in.") from None
    if kind == "dpapi":
        if sys.platform != "win32":
            raise SecretUnreadable("Dit geheim is nog met Windows versleuteld en kan hier niet gelezen worden. "
                                   "Start de nieuwe versie eerst één keer op de oude Windows-pc, of vul het opnieuw in.")
        return _dpapi(base64.b64decode(val), False).decode()
    return val  # plain:


def _is_protected(stored):
    return (stored or "").startswith((ENC, "dpapi:"))


def _secret_refs(cfg):
    """Alle plekken in config.json waar een geheim staat: (dict, sleutel)."""
    refs = [(cfg, "secret"), (cfg, "claude_key")]
    refs += [(a, "refresh") for a in cfg.get("accounts") or []]
    if isinstance(cfg.get("plakzicht"), dict):
        refs.append((cfg["plakzicht"], "key"))
    return [(d, k) for d, k in refs if d.get(k)]


def migrate_secrets(cfg):
    """Oude Windows-versleuteling (dpapi:) en onversleutelde waarden (plain:) omzetten naar enc1:. Geeft het aantal."""
    n = 0
    for d, k in _secret_refs(cfg):
        if str(d[k]).startswith(ENC):
            continue
        try:
            d[k] = _protect(_unprotect(d[k]))
            n += 1
        except (SecretUnreadable, OSError):
            pass  # blijft staan; de foutmelding volgt bij gebruik
    return n


def load_config():
    cfg = {"mode": "demo", "auth": "user", "tenant": "", "client_id": "", "secret": "", "accounts": [],
           "host": "0.0.0.0", "port": 8765}
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    if cfg["mode"] not in DBS:
        cfg["mode"] = "demo"
    if cfg["auth"] not in ("user", "app"):
        cfg["auth"] = "user"
    if cfg.get("refresh") and not cfg["accounts"]:  # oude instelling met één account omzetten
        cfg["accounts"] = [{"id": secrets.token_hex(4), "upn": cfg.get("account", ""), "name": cfg.get("account_name", ""),
                            "refresh": cfg["refresh"], "added": dt.date.today().isoformat()}]
    for k in ("refresh", "account", "account_name", "signin_id"):
        cfg.pop(k, None)
    if cfg["auth"] == "app" and cfg["accounts"] and not cfg["secret"]:
        cfg["auth"] = "user"  # aangemeld met accounts maar per ongeluk op 'app met clientgeheim'
    return cfg


def save_config(cfg):
    tmp = CONFIG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG)


_cfg_lock = threading.Lock()


def set_db_for_mode(mode):
    global DB
    DB = DBS[mode]


CFG = load_config()
if migrate_secrets(CFG):
    save_config(CFG)
SESSIONS = {}      # sessie-id -> {"api": Api, "last": tijd}
SIGNIN = None      # lopende aanmelding bij Microsoft
_CLIENTS = {}
_clients_lock = threading.Lock()


def _conn_for(path):
    c = sqlite3.connect(path, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def _quiet(fn):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- Microsoft-accounts
def add_account(result):
    """Aangemeld account bewaren (zelfde account opnieuw aanmelden = token vervangen). Geeft het account-ID."""
    with _cfg_lock:
        CFG["auth"] = "user"  # aanmelden met een account = deze manier gebruiken
        upn = (result["account"] or "").lower()
        for a in CFG["accounts"]:
            if a["upn"].lower() == upn:
                a.update({"refresh": _protect(result["refresh_token"]), "name": result["name"], "error": None})
                break
        else:
            CFG["accounts"].append({"id": secrets.token_hex(4), "upn": result["account"], "name": result["name"],
                                    "refresh": _protect(result["refresh_token"]), "added": dt.date.today().isoformat()})
        save_config(CFG)
        aid = next(a["id"] for a in CFG["accounts"] if a["upn"].lower() == upn)
    drop_clients()
    try:  # eigen mailbox van dit account opzoeken (ID en hoofdadres), en of de agenda mag
        g = client_for_account(aid).g
        me = g.req("GET", "/me", params={"$select": "id,mail,userPrincipalName,displayName"})
        cal = any(x.lower().startswith("calendars.readwrite") for x in g.scopes())
        with _cfg_lock:
            for a in CFG["accounts"]:
                if a["id"] == aid:
                    a.update({"oid": me.get("id"), "mail": me.get("mail") or me.get("userPrincipalName") or a["upn"], "cal": cal})
            save_config(CFG)
        drop_clients()
    except GraphError:
        pass
    return aid


def add_own_mailbox(aid):
    """De eigen mailbox van een aangemeld account koppelen (in de Microsoft-stand). Geeft het mailbox-ID of None."""
    acct = next((a for a in CFG["accounts"] if a["id"] == aid), None)
    if not acct or CFG["mode"] != "microsoft" or DB != DBS["microsoft"]:
        return None
    if not acct.get("oid"):
        try:
            me = client_for_account(aid).g.req("GET", "/me", params={"$select": "id,mail,userPrincipalName"})
            acct.update({"oid": me.get("id"), "mail": me.get("mail") or me.get("userPrincipalName") or acct["upn"]})
            with _cfg_lock:
                save_config(CFG)
        except GraphError:
            return None
    address = (acct.get("mail") or acct["upn"]).lower()
    with _lock, _conn() as c:
        row = c.execute("SELECT id FROM mailboxes WHERE lower(address)=? OR graph_id=?", (address, acct["oid"])).fetchone()
        if row:
            c.execute("UPDATE mailboxes SET graph_id=coalesce(graph_id, ?), ms_account=coalesce(ms_account, ?) WHERE id=?", (acct["oid"], aid, row[0]))
            return row[0]
        mid = c.execute("INSERT INTO mailboxes(address,display,kind,ms_account,graph_id) VALUES(?,?,?,?,?)",
                        (address, address.split("@")[0] + "@", "persoonlijk", aid, acct["oid"])).lastrowid
    CACHE.kick(mid)
    return mid


def drop_clients():
    with _clients_lock:
        _CLIENTS.clear()


def client_for_account(account_id):
    """MsMail voor een aangemeld account (of voor de app met clientgeheim als account_id None is)."""
    if CFG["auth"] == "app":
        key = ("app", CFG["tenant"], CFG["client_id"], CFG["secret"])
    else:
        acct = next((a for a in CFG["accounts"] if a["id"] == account_id), None)
        if not acct:
            raise GraphError(0, "config", "Dit Microsoft-account is niet (meer) aangemeld. Meld het opnieuw aan in Beheer › Microsoft-koppeling.")
        key = ("user", CFG["tenant"], CFG["client_id"], account_id)
    with _clients_lock:
        if key not in _CLIENTS:
            if CFG["auth"] == "app":
                g = Graph(CFG["tenant"], CFG["client_id"], secret=_unprotect(CFG["secret"]) or "")
            else:
                def store(token, aid=account_id):
                    with _cfg_lock:
                        for a in CFG["accounts"]:
                            if a["id"] == aid:
                                a["refresh"] = _protect(token)
                        save_config(CFG)
                g = Graph(CFG["tenant"], CFG["client_id"], refresh_token=_unprotect(acct["refresh"]) or None, on_refresh=store,
                          scope=CALENDAR_SCOPES if acct.get("cal") else None)
            _CLIENTS[key] = MsMail(g)
        return _CLIENTS[key]


def client_for_mailbox(mb):
    if CFG["auth"] == "app":
        return client_for_account(None)
    aid = mb.get("ms_account")
    if not aid and len(CFG["accounts"]) == 1:
        aid = CFG["accounts"][0]["id"]
    if not aid:
        raise GraphError(0, "config", "Aan deze mailbox is nog geen Microsoft-account gekoppeld (Beheer › Microsoft-mailboxen).")
    return client_for_account(aid)


def _gmb(row):
    """Mailbox voor Graph-aanroepen: 'address' wordt het Microsoft-ID als dat bekend is
    (werkt ook als het mailadres een alias is of afwijkt van de inlognaam)."""
    d = dict(row)
    d["mail_address"] = d["address"]
    if d.get("graph_id"):
        d["address"] = d["graph_id"]
    return d


def _all_mailboxes():
    if CFG["mode"] != "microsoft" or not os.path.exists(DBS["microsoft"]):
        return []
    with _conn_for(DBS["microsoft"]) as c:
        return [_gmb(r) for r in c.execute("SELECT * FROM mailboxes ORDER BY id")]


def _new_mail(mb_id, msgs):
    """Nieuwe mail in een Postvak IN: melding naar iedereen die bij die mailbox kan."""
    try:
        with _conn() as c:
            r = c.execute("SELECT display FROM mailboxes WHERE id=?", (mb_id,)).fetchone()
    except sqlite3.Error:
        r = None
    for m in msgs[:10]:
        frm = (m.get("from") or {}).get("emailAddress") or {}
        BUS.publish({"t": "newmail", "mb": [mb_id], "key": f"{mb_id}:{m['id']}", "mailbox": r[0] if r else "",
                     "from": frm.get("name") or frm.get("address") or "", "subject": m.get("subject") or "",
                     "preview": (m.get("bodyPreview") or "")[:140], "high": m.get("importance") == "high"}, [mb_id])


CACHE = MailCache(lambda: DBS["microsoft"], client_for_mailbox, _all_mailboxes,
                  on_change=lambda mb, kind="mail": BUS.publish({"t": kind, "mb": [mb], "by": None}, [mb]), on_new=_new_mail)


def start_sync():
    if CFG["mode"] == "microsoft":
        CACHE.init()
        CACHE.start()
        CACHE.kick()


# ---------------------------------------------------------------- helpers
def _hash(pw, salt=None):
    salt = salt or secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()
    return salt + "$" + h


def _check(pw, stored):
    salt = stored.split("$", 1)[0]
    return secrets.compare_digest(_hash(pw, salt), stored)


def _now(days=0, hours=0, minutes=0):
    t = dt.datetime.now() + dt.timedelta(days=days, hours=hours, minutes=minutes)
    return t.replace(microsecond=0).isoformat(timespec="minutes")


def _text(html):
    t = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html or "", flags=re.I)
    t = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return re.sub(r"[ \t]+", " ", t).strip()


def _conn():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT UNIQUE NOT NULL,
  pw TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'gebruiker', density TEXT NOT NULL DEFAULT 'middel');
CREATE TABLE IF NOT EXISTS mailboxes(
  id INTEGER PRIMARY KEY, address TEXT UNIQUE NOT NULL, display TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'gedeeld');
CREATE TABLE IF NOT EXISTS user_mailboxes(
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  mailbox_id INTEGER REFERENCES mailboxes(id) ON DELETE CASCADE, PRIMARY KEY(user_id, mailbox_id));
CREATE TABLE IF NOT EXISTS mails(
  id INTEGER PRIMARY KEY, mailbox_id INTEGER REFERENCES mailboxes(id) ON DELETE CASCADE,
  folder TEXT NOT NULL DEFAULT 'inbox', from_name TEXT, from_addr TEXT, to_addr TEXT, cc TEXT,
  subject TEXT, body TEXT, date TEXT, is_read INTEGER DEFAULT 0,
  order_nr TEXT, offerte_nr TEXT, link_mode TEXT DEFAULT 'auto', flagged INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS labels(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, color TEXT NOT NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS mail_labels(
  mail_id INTEGER REFERENCES mails(id) ON DELETE CASCADE,
  label_id INTEGER REFERENCES labels(id) ON DELETE CASCADE, PRIMARY KEY(mail_id, label_id));
CREATE TABLE IF NOT EXISTS signatures(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, html TEXT NOT NULL,
  mailbox_id INTEGER REFERENCES mailboxes(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS remember(
  id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, hash TEXT NOT NULL,
  created REAL, last REAL, device TEXT, ip TEXT);
CREATE TABLE IF NOT EXISTS rules(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, active INTEGER DEFAULT 1, position INTEGER DEFAULT 0,
  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
  mailbox_id INTEGER REFERENCES mailboxes(id) ON DELETE CASCADE,
  conditions TEXT NOT NULL, actions TEXT NOT NULL, stop INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS demo_folders(
  id INTEGER PRIMARY KEY, mailbox_id INTEGER REFERENCES mailboxes(id) ON DELETE CASCADE,
  parent TEXT, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ms_links(
  key TEXT PRIMARY KEY, mailbox_id INTEGER, msg_id TEXT, order_nr TEXT, offerte_nr TEXT,
  link_mode TEXT DEFAULT 'auto', subject TEXT, from_name TEXT, from_addr TEXT, to_addr TEXT, date TEXT, outgoing INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS mail_activity(
  id INTEGER PRIMARY KEY, key TEXT, user_id INTEGER, user_name TEXT, action TEXT, detail TEXT, at REAL);
CREATE INDEX IF NOT EXISTS mail_activity_key ON mail_activity(key, at);
CREATE TABLE IF NOT EXISTS mail_claims(key TEXT PRIMARY KEY, user_id INTEGER, user_name TEXT, at REAL);
CREATE TABLE IF NOT EXISTS move_jobs(
  id INTEGER PRIMARY KEY, user_id INTEGER, user_name TEXT, key TEXT, subject TEXT, src_mb INTEGER, dst_mb INTEGER,
  folder TEXT, status TEXT, error TEXT, attempts INTEGER DEFAULT 0, retry_at REAL, created REAL, done REAL, new_key TEXT);
CREATE TABLE IF NOT EXISTS quicksteps(
  id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE, name TEXT NOT NULL,
  color TEXT, actions TEXT NOT NULL, position INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS claude_usage(
  id INTEGER PRIMARY KEY, user_id INTEGER, at REAL, feature TEXT, in_tok INTEGER, out_tok INTEGER, ok INTEGER);
CREATE TABLE IF NOT EXISTS demo_events(
  id INTEGER PRIMARY KEY, subject TEXT, start TEXT, end TEXT, allday INTEGER DEFAULT 0, location TEXT, body TEXT,
  attendees TEXT, reminder INTEGER, show_as TEXT, organizer TEXT);
CREATE TABLE IF NOT EXISTS pz_orders(
  nr TEXT PRIMARY KEY, klant TEXT, email TEXT, materiaal TEXT, meters REAL, due TEXT,
  proof TEXT, steps TEXT, offerte_nr TEXT);
CREATE TABLE IF NOT EXISTS pz_offertes(
  nr TEXT PRIMARY KEY, klant TEXT, email TEXT, omschrijving TEXT, status TEXT);
"""

LOGO = "data:image/svg+xml;base64," + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 72 72">'
    b'<rect width="72" height="72" rx="10" fill="#1f6f54"/>'
    b'<text x="36" y="46" font-family="Arial" font-size="30" font-weight="700" fill="#fff" text-anchor="middle">LOGO</text></svg>'
    .replace(b'font-size="30"', b'font-size="17"')).decode()


def _seed(c):
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return
    for k, v in DEFAULT_SETTINGS.items():
        c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
    users = [("Beheerder", "beheerder", "beheerder", "middel"),
             ("Medewerker A", "medewerker-a", "gebruiker", "breed"),
             ("Medewerker B", "medewerker-b", "gebruiker", "smal")]
    for n, u, r, d in users:
        c.execute("INSERT INTO users(name,username,pw,role,density) VALUES(?,?,?,?,?)", (n, u, _hash("demo"), r, d))
    for a, d, k in [("info@jouwbedrijf.nl", "info@", "gedeeld"),
                    ("verkoop@jouwbedrijf.nl", "verkoop@", "gedeeld"),
                    ("naam@jouwbedrijf.nl", "naam@", "persoonlijk")]:
        c.execute("INSERT INTO mailboxes(address,display,kind) VALUES(?,?,?)", (a, d, k))
    for uid, mids in [(1, (1, 2, 3)), (2, (1, 2)), (3, (1,))]:
        for m in mids:
            c.execute("INSERT INTO user_mailboxes VALUES(?,?)", (uid, m))
    for n, col, uid in [("Nieuwe aanvragen", "#b26a00", None), ("Algemeen", "#6b726d", None),
                        ("Medewerker A", "#1f6fb2", 2), ("Medewerker B", "#6a3fa0", 3)]:
        c.execute("INSERT INTO labels(name,color,user_id) VALUES(?,?,?)", (n, col, uid))
    _seed_rules(c)
    sig = ('<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:13px;color:#1d2320"><tr>'
           f'<td style="padding-right:14px;vertical-align:top"><img src="{LOGO}" width="64" height="64" alt="Logo"></td>'
           '<td style="vertical-align:top;line-height:1.45"><strong>{naam}</strong><br>{bedrijf}<br>'
           '<span style="color:#6b726d">[telefoon] · www.jouwbedrijf.nl</span></td></tr></table>')
    c.execute("INSERT INTO signatures(name,html,mailbox_id) VALUES(?,?,?)",
              ("Standaard info@", sig.replace("{naam}", "Team Jouwbedrijf").replace("{bedrijf}", "Klantenservice"), 1))
    c.execute("INSERT INTO signatures(name,html,mailbox_id) VALUES(?,?,?)",
              ("Verkoop", sig.replace("{naam}", "Verkoopteam").replace("{bedrijf}", "Offertes en advies"), 2))
    c.execute("INSERT INTO signatures(name,html,mailbox_id) VALUES(?,?,?)",
              ("Persoonlijk", sig.replace("{naam}", "[Jouw naam]").replace("{bedrijf}", "Jouwbedrijf"), 3))
    _seed_pz(c)
    p = lambda *xs: "".join(f"<p>{x}</p>" for x in xs)
    mails = [
        (1, "inbox", "Brouwerij De Hop", "inkoop@brouwerijdehop.nl", "Vraag over order 000000412",
         p("Goedemorgen,", "Kunnen jullie laten weten wanneer onze order 000000412 verzonden wordt? We willen de etiketten graag voor de proeverij gebruiken.", "Met vriendelijke groet,<br>Inge van Dam<br>Brouwerij De Hop"),
         _now(minutes=-35), 0, [1]),
        (1, "inbox", "Koffiebar Bonen", "hallo@koffiebarbonen.nl", "Re: Offerte OFF-2026-121",
         p("Hoi,", "Bedankt voor de offerte. Kan de levertijd nog iets korter? We openen over drie weken.", "Groet,<br>Koffiebar Bonen"),
         _now(hours=-1), 0, [1]),
        (1, "inbox", "Camping Maasoever", "receptie@campingmaasoever.nl", "Akkoord",
         p("Beste,", "Hierbij akkoord op de offerte voor de raamstickers en borden. Graag een proef per mail.", "Met vriendelijke groet,<br>Receptie Camping Maasoever"),
         _now(days=-1), 1, [3]),
        (1, "inbox", "Bakkerij De Vries", "info@bakkerijdevries.nl", "Proef bekeken",
         p("Hallo,", "De proef ziet er goed uit, alleen het logo mag iets groter. Kunnen jullie een nieuwe proef sturen?", "Bakkerij De Vries"),
         _now(days=-2), 1, [4]),
        (1, "inbox", "Nieuwe klant", "m.bakker@voorbeeld.nl", "Prijs voor raamstickers?",
         p("Goedemiddag,", "Wat kost een set van 10 raamstickers van 30 x 30 cm met ons logo?", "Mvg, M. Bakker"),
         _now(days=-2, hours=-3), 0, [1]),
        (1, "inbox", "Leverancier Vinyl", "orders@vinylgroothandel.nl", "Orderbevestiging inkoop 7781",
         p("Geachte klant,", "Hierbij bevestigen wij uw bestelling van 4 rollen wit vinyl glans. Levering donderdag.", "Vinylgroothandel"),
         _now(days=-3), 1, [2]),
        (2, "inbox", "Sportclub Oost", "secretaris@sportcluboost.nl", "Bestelling clubstickers",
         p("Beste verkoop,", "Is ordernummer 000000415 al in productie? De stickers zijn voor ons jubileum.", "Groet, de secretaris"),
         _now(hours=-4), 0, []),
        (2, "inbox", "Drukkerij Partner", "planning@drukkerijpartner.nl", "Samenwerking 2027",
         p("Hallo,", "Zullen we binnenkort de samenwerking voor volgend jaar bespreken?", "Planning, Drukkerij Partner"),
         _now(days=-4), 1, [2]),
        (3, "inbox", "Jan Jansen", "jan.jansen@voorbeeld.nl", "Bedankt!",
         p("Hoi,", "De stickers zien er top uit, bedankt voor het snelle werk.", "Jan"),
         _now(days=-1, hours=-2), 0, []),
        (1, "sent", "info@", "info@jouwbedrijf.nl", "Orderbevestiging 000000412",
         p("Beste Inge,", "Bedankt voor uw bestelling. Hierbij de bevestiging van order 000000412.", "Met vriendelijke groet,<br>Team Jouwbedrijf"),
         _now(days=-8), 1, []),
    ]
    for mb, folder, fn, fa, subj, body, date, read, labels in mails:
        to = "info@jouwbedrijf.nl" if mb == 1 else ("verkoop@jouwbedrijf.nl" if mb == 2 else "naam@jouwbedrijf.nl")
        if folder == "sent":
            fn, fa, to = "info@", "info@jouwbedrijf.nl", "inkoop@brouwerijdehop.nl"
        cur = c.execute("INSERT INTO mails(mailbox_id,folder,from_name,from_addr,to_addr,cc,subject,body,date,is_read) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?)", (mb, folder, fn, fa, to, "", subj, body, date, read))
        for l in labels:
            c.execute("INSERT INTO mail_labels VALUES(?,?)", (cur.lastrowid, l))
        _autolink(c, cur.lastrowid)
    c.execute("UPDATE mails SET flagged=1 WHERE subject IN ('Proef bekeken', 'Bestelling clubstickers')")
    c.execute("UPDATE mails SET due=? WHERE subject='Proef bekeken'", (dt.date.today().isoformat(),))
    c.execute("UPDATE mails SET importance='high' WHERE subject IN ('Vraag over order 000000412', 'Bestelling clubstickers')")
    c.execute("UPDATE mails SET importance='low' WHERE subject LIKE 'Samenwerking%'")


def _seed_pz(c):
    if c.execute("SELECT COUNT(*) FROM pz_orders").fetchone()[0]:
        return
    d = lambda n: (dt.date.today() + dt.timedelta(days=n)).isoformat()
    orders = [
        ("000000412", "Brouwerij De Hop", "inkoop@brouwerijdehop.nl", "Wit vinyl glans", 180, d(6), "ok",
         {"print": "d", "lam": "p", "plot": "", "cut": ""}, "OFF-2026-104"),
        ("000000415", "Sportclub Oost", "secretaris@sportcluboost.nl", "Wit vinyl mat", 95, d(4), "ok",
         {"print": "p", "lam": None, "plot": "", "cut": ""}, None),
        ("000000418", "Bakkerij De Vries", "info@bakkerijdevries.nl", "Transparant vinyl", 140, d(9), "wacht",
         {"print": "", "lam": "", "plot": "", "cut": None}, None),
        ("000000423", "Camping Maasoever", "receptie@campingmaasoever.nl", "Polyester zilver", 210, d(13), "ok",
         {"print": "", "lam": "", "plot": "", "cut": ""}, "OFF-2026-118"),
        ("000000430", "Jan Jansen", "jan.jansen@voorbeeld.nl", "Wit vinyl glans", 3.2, d(2), "ok",
         {"print": "d", "lam": None, "plot": "d", "cut": "p"}, None),
    ]
    for o in orders:
        c.execute("INSERT INTO pz_orders VALUES(?,?,?,?,?,?,?,?,?)", (*o[:7], json.dumps(o[7]), o[8]))
    for o in [("OFF-2026-104", "Brouwerij De Hop", "inkoop@brouwerijdehop.nl", "Etiketten op rol, 4 varianten", "geaccepteerd"),
              ("OFF-2026-118", "Camping Maasoever", "receptie@campingmaasoever.nl", "Raamstickers en borden", "geaccepteerd"),
              ("OFF-2026-121", "Koffiebar Bonen", "hallo@koffiebarbonen.nl", "2.000 etiketten op rol", "verstuurd")]:
        c.execute("INSERT INTO pz_offertes VALUES(?,?,?,?,?)", o)


def _seed_microsoft(c):
    """Eerste start in Microsoft-stand: gebruikers, labels, handtekeningen en instellingen
    overnemen uit de demo (zonder demo-mailboxen en demo-mails)."""
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
        return
    copied = False
    if os.path.exists(DBS["demo"]):
        d = sqlite3.connect(DBS["demo"])
        d.row_factory = sqlite3.Row
        try:
            for r in d.execute("SELECT id,name,username,pw,role,density FROM users"):
                c.execute("INSERT INTO users(id,name,username,pw,role,density) VALUES(?,?,?,?,?,?)", tuple(r))
            for r in d.execute("SELECT id,name,color,user_id FROM labels"):
                c.execute("INSERT INTO labels(id,name,color,user_id) VALUES(?,?,?,?)", tuple(r))
            scols = [r[1] for r in d.execute("PRAGMA table_info(signatures)")]
            for r in d.execute("SELECT name,html," + ("user_id" if "user_id" in scols else "NULL") + " FROM signatures"):
                c.execute("INSERT INTO signatures(name,html,mailbox_id,user_id) VALUES(?,?,NULL,?)", tuple(r))
            for r in d.execute("SELECT key,value FROM settings"):
                c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", tuple(r))
            copied = True
        except sqlite3.Error:
            copied = False
        finally:
            d.close()
    if not copied:
        c.execute("DELETE FROM users")
        c.execute("INSERT INTO users(name,username,pw,role) VALUES(?,?,?,?)", ("Beheerder", "beheerder", _hash("demo"), "beheerder"))
        for n, col in [("Nieuwe aanvragen", "#b26a00"), ("Algemeen", "#6b726d")]:
            c.execute("INSERT INTO labels(name,color) VALUES(?,?)", (n, col))
    for k, v in DEFAULT_SETTINGS.items():
        c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
    _seed_pz(c)


def _merge_prefs(raw):
    try:
        p = json.loads(raw or "{}")
    except ValueError:
        p = {}
    out = json.loads(json.dumps(DEFAULT_PREFS))
    for k, v in p.items():
        if k in ("claude", "notify") and isinstance(v, dict):
            out[k].update(v)
        elif k in out:
            out[k] = v
    return out


def _demo_new(mb_id, mid, folder, is_read, display, frm, subject, body):
    if folder == "inbox" and not is_read:
        threading.Timer(0.3, lambda: BUS.publish({"t": "newmail", "mb": [mb_id], "key": str(mid), "mailbox": display, "from": frm,
                                                  "subject": subject, "preview": _text(body)[:140]}, [mb_id])).start()


def _month_start():
    d = dt.date.today().replace(day=1)
    return time.mktime(d.timetuple())


def _paras_html(text):
    """Platte tekst van Claude naar veilige HTML-alinea's."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]
    return "".join("<p>" + html.escape(p).replace("\n", "<br>") + "</p>" for p in paras)


def _lines_html(text):
    lines = [l.strip().lstrip("-•* ").strip() for l in (text or "").splitlines() if l.strip()]
    return "<ul>" + "".join("<li>" + html.escape(l) + "</li>" for l in lines) + "</ul>"


def _json_from(text):
    m = re.search(r"\{.*\}", text or "", flags=re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}


def _seed_events(c):
    """Demo-agenda: een paar afspraken rond vandaag."""
    t = dt.date.today()
    mon = t - dt.timedelta(days=t.weekday())
    d = lambda n, h, m=0: (mon + dt.timedelta(days=n)).isoformat() + f"T{h:02d}:{m:02d}"
    for subj, s_, e_, allday, loc, body in [
            ("Proef bespreken met Brouwerij De Hop", d(1, 10), d(1, 11), 0, "Telefonisch", "<p>Proef voor order 000000412 doorlopen.</p>"),
            ("Overleg productieplanning", d(2, 8, 30), d(2, 9, 15), 0, "Productiehal", "<p>Weekplanning printen en lamineren.</p>"),
            ("Bezoek Koffiebar Bonen", d(3, 14), d(3, 15, 30), 0, "Bij de klant", "<p>Offerte OFF-2026-121 en levertijd bespreken.</p>"),
            ("Levering vinyl", d(4, 0), d(5, 0), 1, "", "<p>4 rollen wit vinyl glans.</p>")]:
        c.execute("INSERT INTO demo_events(subject,start,end,allday,location,body,show_as,organizer,reminder) VALUES(?,?,?,?,?,?,?,?,?)",
                  (subj, s_, e_, allday, loc, body, "busy", "Beheerder", 15))


def _seed_quicksteps(c):
    """Snelle stappen voor iedereen (zoals in Outlook)."""
    for i, (name, color, acts) in enumerate([
            ("Behandeld", "#1f6f54", {"read": True, "flag": "complete", "claim": "release", "move": {"mb": None, "folder": "wk:archive"}}),
            ("Aan manager", "#6a3fa0", {"forward_to": ""}),
            ("E-mail aan team", "#1f6fb2", {"new_to": ""}),
            ("Ik pak deze op", "#0f766e", {"claim": "claim", "read": True})]):
        c.execute("INSERT INTO quicksteps(user_id,name,color,actions,position) VALUES(NULL,?,?,?,?)", (name, color, json.dumps(acts), i))


def _demo_folders(c, mailbox_id):
    """Mappen van een demo-mailbox in dezelfde vorm als bij Microsoft."""
    def counts(fid):
        r = c.execute("SELECT SUM(is_read=0), COUNT(*) FROM mails WHERE mailbox_id=? AND folder=?", (mailbox_id, fid)).fetchone()
        return (r[0] or 0), (r[1] or 0)
    custom = _rows(c.execute("SELECT id,parent,name FROM demo_folders WHERE mailbox_id=?", (mailbox_id,)))
    kids = {}
    for f in custom:
        kids.setdefault(f["parent"], []).append(f)
    out = []

    def walk(parent, depth):
        for f in sorted(kids.get(parent, []), key=lambda x: x["name"].lower()):
            fid = "f" + str(f["id"])
            un, tot = counts(fid)
            out.append({"id": fid, "name": f["name"], "parent": parent, "wk": "", "unread": un, "total": tot,
                        "depth": depth, "has_children": bool(kids.get(fid))})
            walk(fid, depth + 1)

    for k, n in FOLDERS:
        un, tot = counts(k)
        out.append({"id": k, "name": n, "parent": None, "wk": k, "unread": un, "total": tot, "depth": 0,
                    "has_children": bool(kids.get(k))})
        walk(k, 1)
    walk(None, 0)
    return out


def _settings(c):
    s = dict(DEFAULT_SETTINGS)
    s.update({r["key"]: r["value"] for r in c.execute("SELECT key,value FROM settings")})
    return s


# ---------------------------------------------------------------- Plakzicht: echt (API) of nagebootst
OFFERTE_PATTERN_LIVE = "Offertenummer[\\s:\"'#]*(\\d+)"
_PZ = {"api": None, "sig": None}


def pz_api():
    """De echte Plakzicht (alleen in de Microsoft-stand, als adres en sleutel zijn ingevuld); anders None = nagebootst."""
    p = CFG.get("plakzicht") or {}
    if CFG["mode"] != "microsoft" or not p.get("url") or not p.get("key"):
        return None
    sig = (p["url"], p["key"])
    if _PZ["sig"] != sig:
        _PZ["api"], _PZ["sig"] = PlakzichtApi(p["url"], _unprotect(p["key"])), sig
    return _PZ["api"]


def pz_open(path):
    """Volledig adres om een pagina in Plakzicht te openen (in de browser)."""
    p = CFG.get("plakzicht") or {}
    base = (p.get("open") or p.get("url") or "").rstrip("/")
    return base + path if base and path else None


PZ_STEPS = [("print", "P", "Printen"), ("lam", "L", "Lamineren"), ("plot", "Pl", "Plotten"), ("cut", "S", "Snijden/Stansen")]


def pz_order_view(c, nr):
    """Order in één vorm voor het scherm (echt of nagebootst), of None."""
    api = pz_api()
    if api:
        j = api.order(nr)
        if not j:
            return None
        v = j.get("verzending") or {}
        return {"nr": j["nummer"], "klant": j.get("klant") or "", "email": j.get("email") or "", "status": j.get("status") or "",
                "due": j.get("uiterlijk_verzenden"), "leverdatum": j.get("leverdatum"), "omschrijving": j.get("omschrijving") or "",
                "spoed": bool(j.get("spoed")), "bedrag": j.get("bedrag"), "openstaand": j.get("openstaand"),
                "proof": j.get("drukproef"), "productie": j.get("productie"), "on_hold": j.get("on_hold"),
                "verzending": v if (v.get("stand") not in (None, "", "open") or v.get("track_url")) else None,
                "regels": j.get("regels") or [], "offertes": j.get("offertes") or [], "url": pz_open(j.get("pad")), "bron": "plakzicht"}
    o = c.execute("SELECT * FROM pz_orders WHERE nr=?", (str(nr).strip(),)).fetchone()
    if not o:
        return None
    steps = json.loads(o["steps"] or "{}")
    st = lambda v: "niet nodig" if v is None else {"d": "klaar", "p": "gepland"}.get(v, "nog te doen")
    return {"nr": o["nr"], "klant": o["klant"], "email": o["email"], "status": "in productie", "due": o["due"], "leverdatum": None,
            "omschrijving": f"{o['materiaal']} · ±{str(o['meters']).replace('.', ',')} m", "spoed": False, "bedrag": None, "openstaand": None,
            "proof": {"status": "goedgekeurd", "tekst": "goedgekeurd"} if o["proof"] == "ok" else {"status": "open", "tekst": "wacht op klant"},
            "productie": [{"stap": k, "kort": sh, "naam": n, "status": st(steps.get(k))} for k, sh, n in PZ_STEPS],
            "on_hold": None, "verzending": None, "regels": [], "offertes": [o["offerte_nr"]] if o["offerte_nr"] else [], "url": None, "bron": "demo"}


def pz_quote_view(c, nr):
    api = pz_api()
    if api:
        j = api.quote(nr)
        if not j:
            return None
        return {"nr": j["nummer"], "klant": j.get("klant") or "", "email": j.get("email") or "", "status": j.get("status") or "",
                "omschrijving": (f"{j['regels']} regel{'s' if j.get('regels') != 1 else ''}" if j.get("regels") else ""),
                "bedrag": j.get("bedrag"), "datum": j.get("datum"), "geldig_tot": j.get("geldig_tot"),
                "orders": [o["nummer"] for o in j.get("orders") or []], "url": pz_open(j.get("pad")), "bron": "plakzicht"}
    r = c.execute("SELECT * FROM pz_offertes WHERE upper(nr)=upper(?)", (str(nr).strip(),)).fetchone()
    if not r:
        return None
    return {"nr": r["nr"], "klant": r["klant"], "email": r["email"], "status": r["status"], "omschrijving": r["omschrijving"],
            "bedrag": None, "datum": None, "geldig_tot": None, "url": None, "bron": "demo",
            "orders": [x[0] for x in c.execute("SELECT nr FROM pz_orders WHERE offerte_nr=?", (r["nr"],))]}


def pz_kind(c, nr):
    """('order'|'offerte', officieel nummer) of None. Eerst order, dan offerte."""
    nr = str(nr or "").strip().lstrip("#").upper()
    if not nr:
        return None
    if pz_api() and len(nr) < 9:  # korte nummers zijn offertes (338), ordernummers hebben 9 cijfers
        q = pz_quote_view(c, nr)
        if q:
            return "offerte", q["nr"]
    o = pz_order_view(c, nr) if (not pz_api() or nr.isdigit()) else None
    if o:
        return "order", o["nr"]
    q = pz_quote_view(c, nr)
    if q:
        return "offerte", q["nr"]
    return None


def _detect(c, subject, body):
    s = _settings(c)
    text = (subject or "") + "\n" + _text(body)
    out = {"order_nr": None, "offerte_nr": None}
    for key, pat, table in (("order_nr", s["order_pattern"], "pz_orders"), ("offerte_nr", s["offerte_pattern"], "pz_offertes")):
        try:
            found = re.findall(pat, text, flags=re.I)
        except re.error:
            found = []
        for f in found:
            f = f if isinstance(f, str) else f[0]
            if pz_api():  # echte Plakzicht: alleen het patroon; of het bestaat blijkt bij openen (geen verzoek per mail in de lijst)
                out[key] = f.upper()
                break
            if c.execute(f"SELECT 1 FROM {table} WHERE upper(nr)=upper(?)", (f,)).fetchone():
                out[key] = f.upper()
                break
    return out


def _autolink(c, mail_id):
    m = c.execute("SELECT * FROM mails WHERE id=?", (mail_id,)).fetchone()
    if not m or m["link_mode"] != "auto":
        return
    d = _detect(c, m["subject"], m["body"])
    c.execute("UPDATE mails SET order_nr=?, offerte_nr=? WHERE id=?", (d["order_nr"], d["offerte_nr"], mail_id))


def _seed_rules(c):
    rules = [
        ("Leveranciers: label Algemeen en gelezen", None,
         [{"field": "from", "op": "contains", "value": "@vinylgroothandel.nl"}],
         {"label_ids": [2], "mark_read": True}),
        ("Offerteaanvragen naar verkoop@", 1,
         [{"field": "subject", "op": "contains", "value": "offerte"}, {"field": "order", "op": "none", "value": ""}],
         {"move_mailbox": 2, "move_folder": "inbox", "label_ids": [1]}),
        ("Nieuwsbrieven naar Archief", None,
         [{"field": "subject", "op": "contains", "value": "nieuwsbrief"}],
         {"move_folder": "archive", "mark_read": True}),
    ]
    admin = c.execute("SELECT id FROM users WHERE role='beheerder' ORDER BY id").fetchone()
    for i, (n, mb, conds, acts) in enumerate(rules):
        c.execute("INSERT INTO rules(name,active,position,user_id,mailbox_id,conditions,actions,stop) VALUES(?,?,?,?,?,?,?,0)",
                  (n, 1, i, admin[0] if admin else None, mb, json.dumps(conds), json.dumps(acts)))


def _mailbox_scope(c, user_id):
    u = c.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
    if not u:
        return []
    if u["role"] == "beheerder":
        return [r[0] for r in c.execute("SELECT id FROM mailboxes ORDER BY id")]
    return [r[0] for r in c.execute("SELECT mailbox_id FROM user_mailboxes WHERE user_id=?", (user_id,))]


def _cond_ok(m, cond):
    f, op, val = cond.get("field"), cond.get("op"), (cond.get("value") or "").strip().lower()
    if f == "order":
        has = bool(m["order_nr"] or m["offerte_nr"])
        return has if op == "has" else not has
    texts = {"from": (m["from_name"] or "") + " " + (m["from_addr"] or ""),
             "to": (m["to_addr"] or "") + " " + (m["cc"] or ""),
             "subject": m["subject"] or "", "body": _text(m["body"]),
             "any": (m["subject"] or "") + "\n" + _text(m["body"])}
    t = texts.get(f, "").lower()
    if op == "contains":
        return val in t
    if op == "not_contains":
        return val not in t
    if op == "is":
        return t.strip() == val or (f == "from" and (m["from_addr"] or "").lower() == val)
    if op == "starts":
        return t.startswith(val)
    return False


def _run_rules(c, mail_id, only_rule=None):
    """Voer actieve regels uit op een mail in Postvak IN. Geeft de namen van toegepaste regels terug."""
    applied = []
    q = "SELECT * FROM rules WHERE active=1" + (" AND id=?" if only_rule else "") + " ORDER BY position, id"
    for r in c.execute(q, (only_rule,) if only_rule else ()).fetchall():
        m = c.execute("SELECT * FROM mails WHERE id=?", (mail_id,)).fetchone()
        if not m or m["folder"] != "inbox":
            break
        scope = _mailbox_scope(c, r["user_id"])
        if m["mailbox_id"] not in scope or (r["mailbox_id"] and m["mailbox_id"] != r["mailbox_id"]):
            continue
        conds = json.loads(r["conditions"] or "[]")
        if not conds or not all(_cond_ok(m, x) for x in conds):
            continue
        a = json.loads(r["actions"] or "{}")
        for lid in a.get("label_ids") or []:
            if c.execute("SELECT 1 FROM labels WHERE id=?", (lid,)).fetchone():
                c.execute("INSERT OR IGNORE INTO mail_labels VALUES(?,?)", (mail_id, lid))
        if a.get("mark_read"):
            c.execute("UPDATE mails SET is_read=1 WHERE id=?", (mail_id,))
        if a.get("flag"):
            c.execute("UPDATE mails SET flagged=1 WHERE id=?", (mail_id,))
        mb, folder = a.get("move_mailbox"), a.get("move_folder")
        if folder:
            mb = mb if mb in scope else m["mailbox_id"]
            if mb != m["mailbox_id"] or folder != "inbox":
                c.execute("UPDATE mails SET mailbox_id=?, folder=? WHERE id=?", (mb, folder, mail_id))
        applied.append(r["name"])
        if r["stop"]:
            break
    return applied


INCOMING = [
    ("Brouwerij De Hop", "inkoop@brouwerijdehop.nl", "Nog een vraag over 000000412",
     "<p>Hallo,</p><p>Kunnen we bij order 000000412 nog 50 extra etiketten bijbestellen?</p><p>Groet, Inge</p>"),
    ("Restaurant Het Anker", "info@hetanker.nl", "Offerte voor menukaartstickers",
     "<p>Goedemiddag,</p><p>Wij willen graag een offerte voor 500 stickers voor onze menukaarten.</p><p>Met vriendelijke groet, Het Anker</p>"),
    ("Leverancier Vinyl", "facturen@vinylgroothandel.nl", "Factuur 2026-1188",
     "<p>Geachte klant,</p><p>In de bijlage vindt u factuur 2026-1188.</p><p>Vinylgroothandel</p>"),
    ("Printvakblad", "nieuws@printvakblad.nl", "Nieuwsbrief november",
     "<p>Het laatste nieuws uit de printwereld.</p>"),
    ("Koffiebar Bonen", "hallo@koffiebarbonen.nl", "Akkoord op OFF-2026-121",
     "<p>Hoi,</p><p>We gaan akkoord met offerte OFF-2026-121. Wanneer kunnen jullie starten?</p><p>Groet, Koffiebar Bonen</p>"),
]


def init_db():
    with _lock, _conn() as c:
        c.executescript(SCHEMA)
        cols = [r[1] for r in c.execute("PRAGMA table_info(users)")]
        if "layout" not in cols:  # oudere demodatabase bijwerken
            c.execute("ALTER TABLE users ADD COLUMN layout TEXT")
        if "flagged" not in [r[1] for r in c.execute("PRAGMA table_info(mails)")]:
            c.execute("ALTER TABLE mails ADD COLUMN flagged INTEGER DEFAULT 0")
        mcols = [r[1] for r in c.execute("PRAGMA table_info(mailboxes)")]
        if "ms_account" not in mcols:
            c.execute("ALTER TABLE mailboxes ADD COLUMN ms_account TEXT")
        if "graph_id" not in mcols:
            c.execute("ALTER TABLE mailboxes ADD COLUMN graph_id TEXT")
        if "cache_days" not in mcols:
            c.execute(f"ALTER TABLE mailboxes ADD COLUMN cache_days INTEGER DEFAULT {DEFAULT_DAYS}")
        ucols = [r[1] for r in c.execute("PRAGMA table_info(users)")]
        for col, ddl in (("prefs", "TEXT"), ("claude_on", "INTEGER DEFAULT 0"), ("claude_limit", "INTEGER DEFAULT 200")):
            if col not in ucols:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
        mlcols = [r[1] for r in c.execute("PRAGMA table_info(mails)")]
        for col, ddl in (("importance", "TEXT DEFAULT 'normal'"), ("due", "TEXT"), ("flag_done", "INTEGER DEFAULT 0")):
            if col not in mlcols:
                c.execute(f"ALTER TABLE mails ADD COLUMN {col} {ddl}")
        if not c.execute("SELECT COUNT(*) FROM quicksteps").fetchone()[0]:
            _seed_quicksteps(c)
        if DB == DBS["demo"] and not c.execute("SELECT COUNT(*) FROM demo_events").fetchone()[0]:
            _seed_events(c)
        if "user_id" not in [r[1] for r in c.execute("PRAGMA table_info(signatures)")]:
            c.execute("ALTER TABLE signatures ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        if DB == DBS["microsoft"]:
            _seed_microsoft(c)
            cur = c.execute("SELECT value FROM settings WHERE key='offerte_pattern'").fetchone()
            if not cur or cur[0] == DEFAULT_SETTINGS["offerte_pattern"]:  # echte Plakzicht: 'Offertenummer 338'
                c.execute("INSERT OR REPLACE INTO settings VALUES('offerte_pattern', ?)", (OFFERTE_PATTERN_LIVE,))
            c.commit()
            CACHE.init()
            return
        fresh = not c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        _seed(c)
        if not fresh and not c.execute("SELECT COUNT(*) FROM rules").fetchone()[0]:
            _seed_rules(c)


# ---------------------------------------------------------------- API
class Api:
    """Alles wat de interface mag aanroepen. Namen met _ zijn niet zichtbaar."""

    def __init__(self):
        self._uid = None
        self._ip = None  # adres van de pc die het verzoek doet (door de server ingevuld)
        self._keep_id = None   # 'ingelogd blijven' van dit apparaat (door de server ingevuld)
        self._keep_req = None

    # -- intern
    def _user(self, c, admin=False):
        if not self._uid:
            raise PermissionError("Niet ingelogd.")
        u = c.execute("SELECT id,name,username,role,density,layout,prefs,claude_on,claude_limit FROM users WHERE id=?", (self._uid,)).fetchone()
        if not u:
            self._uid = None
            raise PermissionError("Niet ingelogd.")
        if admin and u["role"] != "beheerder":
            raise PermissionError("Alleen voor beheerders.")
        u = dict(u)
        try:
            u["layout"] = json.loads(u["layout"] or "{}")
        except ValueError:
            u["layout"] = {}
        u["prefs"] = _merge_prefs(u.get("prefs"))
        return u

    def _mb_ids(self, c, u):
        if u["role"] == "beheerder":
            return [r[0] for r in c.execute("SELECT id FROM mailboxes ORDER BY id")]
        return [r[0] for r in c.execute("SELECT mailbox_id FROM user_mailboxes WHERE user_id=? ORDER BY mailbox_id", (u["id"],))]

    def _mail_ok(self, c, u, mail_id):
        m = c.execute("SELECT * FROM mails WHERE id=?", (mail_id,)).fetchone()
        if not m:
            raise Gone("intussen verplaatst of verwijderd")
        if m["mailbox_id"] not in self._mb_ids(c, u):
            raise PermissionError("Geen toegang tot deze mail.")
        return m

    def _labels_of(self, c, ids):
        out = {i: [] for i in ids}
        if ids:
            q = ",".join("?" * len(ids))
            for r in c.execute(f"SELECT ml.mail_id, l.id, l.name, l.color FROM mail_labels ml JOIN labels l ON l.id=ml.label_id "
                               f"WHERE ml.mail_id IN ({q}) ORDER BY l.name", ids):
                out[r[0]].append({"id": r[1], "name": r[2], "color": r[3]})
        return out

    def _order(self, c, nr):
        return pz_order_view(c, nr)

    # -- sessie
    def app_info(self):
        with _conn() as c:
            days = _remember_days(c)
        return {"mode": CFG["mode"], "remember": days, "version": VERSION}

    def login(self, username, password, remember=False, device=""):
        with _conn() as c:
            u = c.execute("SELECT * FROM users WHERE username=?", ((username or "").strip().lower(),)).fetchone()
            if not u or not _check(password or "", u["pw"]):
                raise PermissionError("Gebruikersnaam of wachtwoord klopt niet.")
            self._uid = u["id"]
        self._keep_req = (bool(remember), str(device or "")[:80])  # de server zet daarna het cookie
        return self.state()

    # -- ingelogd blijven: apparaten
    def my_devices(self):
        with _conn() as c:
            u = self._user(c)
            rows = _rows(c.execute("SELECT id, device, ip, created, last FROM remember WHERE user_id=? ORDER BY last DESC", (u["id"],)))
            days = _remember_days(c)
        for r in rows:
            r["current"] = r["id"] == self._keep_id
        return {"devices": rows, "days": days, "current_kept": bool(self._keep_id)}

    def device_logout(self, kid):
        """Eén apparaat afmelden, of 'others' = alle andere apparaten."""
        with _lock, _conn() as c:
            u = self._user(c)
            if kid == "others":
                c.execute("DELETE FROM remember WHERE user_id=? AND id IS NOT ?", (u["id"], self._keep_id))
                _drop_sessions(u["id"], keep_api=self)
            else:
                c.execute("DELETE FROM remember WHERE user_id=? AND id=?", (u["id"], kid))
                _drop_sessions(u["id"], keep_ids={kid}, keep_api=self)
        return self.my_devices()

    def user_logout_all(self, uid):
        """Beheer: een medewerker op alle apparaten afmelden (bijvoorbeeld bij een verloren laptop)."""
        with _lock, _conn() as c:
            me = self._user(c, admin=True)
            uid = int(uid)
            c.execute("DELETE FROM remember WHERE user_id=?", (uid,))
        _drop_sessions(uid, keep_api=self if uid == me["id"] else None)
        return True

    def logout(self):
        self._uid = None
        return True

    def state(self):
        with _conn() as c:
            u = self._user(c)
            ids = self._mb_ids(c, u)
            mbs = []
            for mid in ids:
                m = dict(c.execute("SELECT * FROM mailboxes WHERE id=?", (mid,)).fetchone())
                try:
                    m["folders"], m["error"] = self._folders(c, m), None
                except GraphError as e:
                    m["folders"], m["error"] = [], nl_error(e)
                mbs.append(m)
            labels = _rows(c.execute("SELECT l.*, u.name AS user_name FROM labels l LEFT JOIN users u ON u.id=l.user_id ORDER BY l.user_id IS NOT NULL, l.name"))
            q = ",".join("?" * len(ids)) or "NULL"
            for l in labels:
                if self._is_ms():
                    l["count"] = 0
                    continue
                l["count"] = c.execute(f"SELECT COUNT(*) FROM mail_labels ml JOIN mails m ON m.id=ml.mail_id "
                                       f"WHERE ml.label_id=? AND m.mailbox_id IN ({q})", (l["id"], *ids)).fetchone()[0]
            # algemene handtekeningen + die van deze gebruiker
            sigs = _rows(c.execute("SELECT * FROM signatures WHERE user_id IS NULL OR user_id=? ORDER BY user_id IS NULL, name", (u["id"],)))
            s = _settings(c)
            qs = self._quicksteps(c, u)
            claude = self._claude_status(c, u)
        return {"user": u, "mailboxes": mbs, "labels": labels, "signatures": sigs,
                "plakzicht_url": s["plakzicht_url"], "folders": [{"key": k, "name": n} for k, n in FOLDERS],
                "mode": CFG["mode"], "periods": PERIODS, "quicksteps": qs, "claude": claude, "plakzicht_live": bool(pz_api())}

    def set_density(self, density):
        if density not in DENSITIES:
            raise ValueError("Onbekende weergave.")
        with _lock, _conn() as c:
            u = self._user(c)
            c.execute("UPDATE users SET density=? WHERE id=?", (density, u["id"]))
        return density

    def set_layout(self, layout):
        """Kolombreedtes en ingeklapte zijbalk, per gebruiker."""
        clean = {}
        for key, lo, hi in (("side", 160, 360), ("list", 240, 760), ("pz", 220, 520)):
            v = layout.get(key)
            if isinstance(v, (int, float)):
                clean[key] = int(min(hi, max(lo, v)))
        clean["collapsed"] = bool(layout.get("collapsed"))
        clean["pz_hidden"] = bool(layout.get("pz_hidden"))
        with _lock, _conn() as c:
            u = self._user(c)
            c.execute("UPDATE users SET layout=? WHERE id=?", (json.dumps(clean), u["id"]))
        return clean

    def set_prefs(self, patch):
        """Weergave-instellingen per gebruiker: kolommen, sorteren, scheidingsbalken, antwoorden, Claude."""
        with _lock, _conn() as c:
            u = self._user(c)
            p = u["prefs"]
            for k, v in (patch or {}).items():
                if k == "listview" and v in ("kolommen", "compact"):
                    p[k] = v
                elif k == "groups":
                    p[k] = bool(v)
                elif k == "reply_in" and v in ("pane", "window"):
                    p[k] = v
                elif k == "cols" and isinstance(v, list):
                    cols = [x for x in v if x in LIST_COLS]
                    for need in ("from", "subj"):
                        if need not in cols:
                            cols.append(need)
                    p[k] = list(dict.fromkeys(cols))
                elif k == "colw" and isinstance(v, dict):
                    p[k] = {kk: int(min(600, max(18, vv))) for kk, vv in v.items() if kk in LIST_COLS and isinstance(vv, (int, float))}
                elif k == "sort" and isinstance(v, dict) and v.get("key") in SORT_KEYS:
                    p[k] = {"key": v["key"], "dir": "asc" if v.get("dir") == "asc" else "desc"}
                elif k == "notify" and isinstance(v, dict):
                    n = p["notify"]
                    for kk in ("on", "sound", "desktop"):
                        if kk in v:
                            n[kk] = bool(v[kk])
                    if isinstance(v.get("mute"), list):
                        n["mute"] = [int(x) for x in v["mute"] if str(x).isdigit()][:100]
                elif k == "claude" and isinstance(v, dict):
                    cl = p["claude"]
                    if v.get("tone") in ("zakelijk", "formeel", "informeel", "kort"):
                        cl["tone"] = v["tone"]
                    if v.get("aanhef") in ("u", "je"):
                        cl["aanhef"] = v["aanhef"]
                    if v.get("lang") in ("mail", "nl"):
                        cl["lang"] = v["lang"]
                    if "extra" in v:
                        cl["extra"] = str(v["extra"] or "")[:1000]
            c.execute("UPDATE users SET prefs=? WHERE id=?", (json.dumps(p), u["id"]))
        return p

    # -- mail
    def _demo_list_mails(self, view):
        """view = {mailbox_id, folder} of {label_id}, plus filter en zoek."""
        with _conn() as c:
            u = self._user(c)
            ids = self._mb_ids(c, u)
            if not ids:
                return []
            where, args = [f"m.mailbox_id IN ({','.join('?' * len(ids))})"], list(ids)
            if view.get("label_id"):
                where.append("m.id IN (SELECT mail_id FROM mail_labels WHERE label_id=?)")
                args.append(view["label_id"])
            elif view.get("mailbox_id"):
                where.append("m.mailbox_id=? AND m.folder=?")
                args += [view["mailbox_id"], view.get("folder") or "inbox"]
            f = view.get("filter")
            if f == "ongelezen":
                where.append("m.is_read=0")
            elif f == "gemarkeerd":
                where.append("m.flagged=1")
            elif f == "zonder_order":
                where.append("m.order_nr IS NULL AND m.offerte_nr IS NULL")
            elif f == "bijlage":
                where.append("0")  # demo-mails hebben geen bijlagen
            if view.get("search"):
                where.append("(m.subject LIKE ? OR m.from_name LIKE ? OR m.from_addr LIKE ? OR m.body LIKE ? OR m.order_nr LIKE ?)")
                args += ["%" + view["search"] + "%"] * 5
            rows = _rows(c.execute(
                "SELECT m.id,m.mailbox_id,m.folder,m.from_name,m.from_addr,m.to_addr,m.subject,m.body,m.date,m.is_read,"
                "m.order_nr,m.offerte_nr,m.flagged,m.cc,m.importance,m.due AS flag_due,m.flag_done,length(m.body)+900 AS size,"
                "mb.display AS mailbox FROM mails m JOIN mailboxes mb ON mb.id=m.mailbox_id "
                f"WHERE {' AND '.join(where)} ORDER BY m.date DESC", args))
            labs = self._labels_of(c, [r["id"] for r in rows])
        for r in rows:
            r["snippet"] = _text(r.pop("body"))[:160]
            r["labels"] = labs[r["id"]]
            r["has_attachments"] = False
            r["importance"] = r["importance"] or "normal"
            r["flag_done"] = bool(r["flag_done"])
        return rows

    def _demo_get_mail(self, mail_id):
        with _lock, _conn() as c:
            u = self._user(c)
            m = dict(self._mail_ok(c, u, mail_id))
            c.execute("UPDATE mails SET is_read=1 WHERE id=?", (mail_id,))
            m["is_read"] = 1
            m["flag_due"], m["flag_done"] = m.get("due"), bool(m.get("flag_done"))
            m["importance"] = m.get("importance") or "normal"
            m["size"] = len(m["body"] or "") + 900
            m["labels"] = self._labels_of(c, [mail_id])[mail_id]
            m["mailbox"] = c.execute("SELECT display FROM mailboxes WHERE id=?", (m["mailbox_id"],)).fetchone()[0]
            m["plakzicht"] = self._pz_for(c, m)
        return m

    def _pz_for(self, c, m):
        info = {"order": None, "offerte": None, "klant": None, "how": None, "error": None, "missing": [], "live": bool(pz_api())}
        how = "handmatig gekoppeld" if m.get("link_mode") == "manual" else "herkend in de mail"
        addr = ((m["to_addr"] if (m.get("folder_wk") or m.get("folder")) == "sent" else m["from_addr"]) or "").split(",")[0].strip().lower()
        try:
            if m.get("order_nr"):
                info["order"], info["how"] = pz_order_view(c, m["order_nr"]), how
                if not info["order"]:
                    info["missing"].append("order " + m["order_nr"])
            if m.get("offerte_nr"):
                info["offerte"], info["how"] = pz_quote_view(c, m["offerte_nr"]), info["how"] or how
                if not info["offerte"]:
                    info["missing"].append("offerte " + m["offerte_nr"])
            if addr:
                info["klant"] = self._pz_klant(c, addr)
        except PlakzichtError as e:
            info["error"] = str(e)
        return info

    def _pz_klant(self, c, addr):
        n_mails = c.execute("SELECT COUNT(*) FROM ms_links WHERE lower(from_addr)=? OR lower(to_addr) LIKE ?" if self._is_ms() else
                            "SELECT COUNT(*) FROM mails WHERE lower(from_addr)=? OR lower(to_addr) LIKE ?", (addr, "%" + addr + "%")).fetchone()[0]
        api = pz_api()
        if api:
            j = api.customer(addr)
            if not j:
                return None
            return {"naam": j.get("naam") or addr, "orders": [{"nr": o["nummer"], "due": o.get("uiterlijk_verzenden"), "status": o.get("status")} for o in j.get("orders") or []],
                    "offertes": [{"nr": q["nummer"], "status": q.get("status")} for q in j.get("offertes") or []],
                    "n_orders": j.get("aantal_orders"), "n_offertes": j.get("aantal_offertes"), "mails": n_mails}
        orders = _rows(c.execute("SELECT nr,due FROM pz_orders WHERE lower(email)=? ORDER BY nr DESC", (addr,)))
        offs = _rows(c.execute("SELECT nr,status FROM pz_offertes WHERE lower(email)=?", (addr,)))
        name = c.execute("SELECT klant FROM pz_orders WHERE lower(email)=? UNION SELECT klant FROM pz_offertes WHERE lower(email)=?",
                         (addr, addr)).fetchone()
        if not name:
            return None
        return {"naam": name[0], "orders": orders, "offertes": offs, "mails": n_mails}

    def _demo_move_mail(self, mail_id, mailbox_id, folder="inbox"):
        with _lock, _conn() as c:
            u = self._user(c)
            self._mail_ok(c, u, mail_id)
            if int(mailbox_id) not in self._mb_ids(c, u):
                raise PermissionError("Geen toegang tot die mailbox.")
            if not any(f["id"] == folder for f in _demo_folders(c, int(mailbox_id))):
                raise ValueError("Onbekende map.")
            # Bij Microsoft is verplaatsen tussen mailboxen: kopiëren en daarna verwijderen.
            c.execute("UPDATE mails SET mailbox_id=?, folder=? WHERE id=?", (mailbox_id, folder, mail_id))
        return True

    def _demo_set_label(self, mail_id, label_id, on):
        with _lock, _conn() as c:
            u = self._user(c)
            self._mail_ok(c, u, mail_id)
            if on:
                c.execute("INSERT OR IGNORE INTO mail_labels VALUES(?,?)", (mail_id, label_id))
            else:
                c.execute("DELETE FROM mail_labels WHERE mail_id=? AND label_id=?", (mail_id, label_id))
        return True

    def _demo_delete_mail(self, mail_id):
        """Eerst naar Verwijderde items; daar nog eens verwijderen = definitief."""
        with _lock, _conn() as c:
            u = self._user(c)
            m = self._mail_ok(c, u, mail_id)
            if m["folder"] == "deleted":
                c.execute("DELETE FROM mails WHERE id=?", (mail_id,))
                return "definitief"
            c.execute("UPDATE mails SET folder='deleted' WHERE id=?", (mail_id,))
        return "verwijderde items"

    def _demo_set_read(self, mail_id, read):
        with _lock, _conn() as c:
            u = self._user(c)
            self._mail_ok(c, u, mail_id)
            c.execute("UPDATE mails SET is_read=? WHERE id=?", (1 if read else 0, mail_id))
        return True

    def _demo_set_flag(self, mail_id, on):
        with _lock, _conn() as c:
            u = self._user(c)
            self._mail_ok(c, u, mail_id)
            c.execute("UPDATE mails SET flagged=? WHERE id=?", (1 if on else 0, mail_id))
        return True

    # -- regels
    def list_rules(self):
        with _conn() as c:
            u = self._user(c)
            q = "SELECT r.*, us.name AS owner FROM rules r LEFT JOIN users us ON us.id=r.user_id"
            if u["role"] == "beheerder":
                rows = _rows(c.execute(q + " ORDER BY r.position, r.id"))
            else:
                rows = _rows(c.execute(q + " WHERE r.user_id=? ORDER BY r.position, r.id", (u["id"],)))
        for r in rows:
            r["conditions"] = json.loads(r["conditions"])
            r["actions"] = json.loads(r["actions"])
        return rows

    def _rule_ok(self, c, u, rid):
        r = c.execute("SELECT * FROM rules WHERE id=?", (rid,)).fetchone()
        if not r or (u["role"] != "beheerder" and r["user_id"] != u["id"]):
            raise PermissionError("Geen toegang tot deze regel.")
        return r

    def save_rule(self, data):
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Geef de regel een naam.")
        conds = []
        for x in data.get("conditions") or []:
            f, op, v = x.get("field"), x.get("op"), (x.get("value") or "").strip()
            if f not in RULE_FIELDS or op not in RULE_OPS:
                raise ValueError("Onbekende voorwaarde.")
            if f == "order":
                op, v = ("has" if op == "has" else "none"), ""
            elif op in ("has", "none") or not v:
                raise ValueError("Vul bij elke voorwaarde een waarde in.")
            conds.append({"field": f, "op": op, "value": v})
        if not conds:
            raise ValueError("Voeg minstens één voorwaarde toe.")
        a = data.get("actions") or {}
        acts = {"label_ids": [int(i) for i in a.get("label_ids") or []], "mark_read": bool(a.get("mark_read")),
                "flag": bool(a.get("flag"))}
        if a.get("move_folder"):
            if not re.fullmatch(r"[A-Za-z0-9=_\-+/]{1,400}", str(a["move_folder"])):
                raise ValueError("Onbekende map.")
            acts["move_folder"] = a["move_folder"]
            acts["move_mailbox"] = int(a["move_mailbox"]) if a.get("move_mailbox") else None
        if not (acts["label_ids"] or acts["mark_read"] or acts["flag"] or acts.get("move_folder")):
            raise ValueError("Kies minstens één actie.")
        with _lock, _conn() as c:
            u = self._user(c)
            mine = self._mb_ids(c, u)
            mb = int(data["mailbox_id"]) if data.get("mailbox_id") else None
            if mb and mb not in mine:
                raise PermissionError("Geen toegang tot die mailbox.")
            if acts.get("move_mailbox") and acts["move_mailbox"] not in mine:
                raise PermissionError("Geen toegang tot de doelmailbox.")
            vals = (name, 1 if data.get("active", True) else 0, mb, json.dumps(conds), json.dumps(acts), 1 if data.get("stop") else 0)
            if data.get("id"):
                self._rule_ok(c, u, data["id"])
                c.execute("UPDATE rules SET name=?, active=?, mailbox_id=?, conditions=?, actions=?, stop=? WHERE id=?", (*vals, data["id"]))
                return data["id"]
            pos = (c.execute("SELECT MAX(position) FROM rules").fetchone()[0] or 0) + 1
            return c.execute("INSERT INTO rules(name,active,mailbox_id,conditions,actions,stop,user_id,position) VALUES(?,?,?,?,?,?,?,?)",
                             (*vals, u["id"], pos)).lastrowid

    def toggle_rule(self, rid, active):
        with _lock, _conn() as c:
            u = self._user(c)
            self._rule_ok(c, u, rid)
            c.execute("UPDATE rules SET active=? WHERE id=?", (1 if active else 0, rid))
        return True

    def move_rule(self, rid, direction):
        with _lock, _conn() as c:
            u = self._user(c)
            self._rule_ok(c, u, rid)
            ids = [r[0] for r in c.execute("SELECT id FROM rules ORDER BY position, id")]
            i = ids.index(rid)
            j = i + (1 if direction > 0 else -1)
            if 0 <= j < len(ids):
                ids[i], ids[j] = ids[j], ids[i]
            for pos, x in enumerate(ids):
                c.execute("UPDATE rules SET position=? WHERE id=?", (pos, x))
        return True

    def delete_rule(self, rid):
        with _lock, _conn() as c:
            u = self._user(c)
            self._rule_ok(c, u, rid)
            c.execute("DELETE FROM rules WHERE id=?", (rid,))
        return True

    def run_rule_now(self, rid):
        """Pas één regel toe op alle mails in Postvak IN die binnen bereik vallen."""
        if self._is_ms():
            raise RuntimeError("In deze testversie werken regels nog alleen in de demo-stand.")
        with _lock, _conn() as c:
            u = self._user(c)
            r = self._rule_ok(c, u, rid)
            if not r["active"]:
                raise ValueError("Zet de regel eerst aan.")
            ids = [x[0] for x in c.execute("SELECT id FROM mails WHERE folder='inbox'")]
            return sum(1 for mid in ids if _run_rules(c, mid, only_rule=rid))

    def simulate_incoming(self, mailbox_id=None):
        """Demo: laat een nieuwe mail binnenkomen, zodat je de regels ziet werken."""
        if self._is_ms():
            raise RuntimeError("Testmail laten binnenkomen kan alleen in de demo-stand.")
        with _lock, _conn() as c:
            u = self._user(c)
            mine = self._mb_ids(c, u)
            if not mine:
                raise PermissionError("Geen mailbox.")
            mb = int(mailbox_id) if mailbox_id and int(mailbox_id) in mine else mine[0]
            n = c.execute("SELECT COALESCE(MAX(id), 0) FROM mails").fetchone()[0]
            fn, fa, subj, body = INCOMING[n % len(INCOMING)]
            to = c.execute("SELECT address FROM mailboxes WHERE id=?", (mb,)).fetchone()[0]
            mid = c.execute("INSERT INTO mails(mailbox_id,folder,from_name,from_addr,to_addr,cc,subject,body,date,is_read) "
                            "VALUES(?,?,?,?,?,?,?,?,?,0)", (mb, "inbox", fn, fa, to, "", subj, body, _now())).lastrowid
            _autolink(c, mid)
            applied = _run_rules(c, mid)
            m = c.execute("SELECT m.folder, m.mailbox_id, m.is_read, mb.display FROM mails m JOIN mailboxes mb ON mb.id=m.mailbox_id WHERE m.id=?", (mid,)).fetchone()
        _demo_new(m["mailbox_id"], mid, m["folder"], m["is_read"], m["display"], fn, subj, body)
        return {"id": mid, "subject": subj, "from": fn, "rules": applied, "folder": m["folder"], "mailbox": m["display"]}

    def _demo_link_mail(self, mail_id, nr):
        """Koppel handmatig aan een order of offerte; lege nr = ontkoppelen."""
        nr = (nr or "").strip().upper()
        with _lock, _conn() as c:
            u = self._user(c)
            self._mail_ok(c, u, mail_id)
            if not nr:
                c.execute("UPDATE mails SET order_nr=NULL, offerte_nr=NULL, link_mode='none' WHERE id=?", (mail_id,))
                return True
            if c.execute("SELECT 1 FROM pz_orders WHERE nr=?", (nr,)).fetchone():
                c.execute("UPDATE mails SET order_nr=?, offerte_nr=NULL, link_mode='manual' WHERE id=?", (nr, mail_id))
            elif c.execute("SELECT 1 FROM pz_offertes WHERE upper(nr)=?", (nr,)).fetchone():
                c.execute("UPDATE mails SET offerte_nr=?, order_nr=NULL, link_mode='manual' WHERE id=?", (nr, mail_id))
            else:
                raise ValueError(f"{nr} bestaat niet in Plakzicht.")
        return True

    def _demo_send_mail(self, msg):
        to = (msg.get("to") or "").strip()
        if not to:
            raise ValueError("Vul een ontvanger in.")
        with _lock, _conn() as c:
            u = self._user(c)
            mb = int(msg["mailbox_id"])
            if mb not in self._mb_ids(c, u):
                raise PermissionError("Geen toegang tot die mailbox.")
            box = c.execute("SELECT * FROM mailboxes WHERE id=?", (mb,)).fetchone()
            order = (msg.get("order_nr") or "").strip().upper() or None
            mode = "manual" if order else "auto"
            cur = c.execute(
                "INSERT INTO mails(mailbox_id,folder,from_name,from_addr,to_addr,cc,subject,body,date,is_read,link_mode) "
                "VALUES(?,?,?,?,?,?,?,?,?,1,?)",
                (mb, "sent", u["name"], box["address"], to, msg.get("cc", ""), msg.get("subject", ""),
                 msg.get("body", ""), _now(), mode))
            sent_id = cur.lastrowid
            if order:
                col = "order_nr" if c.execute("SELECT 1 FROM pz_orders WHERE nr=?", (order,)).fetchone() else "offerte_nr"
                c.execute(f"UPDATE mails SET {col}=? WHERE id=?", (order, sent_id))
            else:
                _autolink(c, sent_id)
            # Demo: mail naar een eigen mailbox komt daar direct binnen.
            for addr in re.split(r"[;,\s]+", to + "," + (msg.get("cc") or "")):
                tgt = c.execute("SELECT id FROM mailboxes WHERE lower(address)=?", (addr.lower(),)).fetchone()
                if tgt:
                    cur = c.execute(
                        "INSERT INTO mails(mailbox_id,folder,from_name,from_addr,to_addr,cc,subject,body,date,is_read) "
                        "VALUES(?,?,?,?,?,?,?,?,?,0)",
                        (tgt[0], "inbox", u["name"], box["address"], to, msg.get("cc", ""), msg.get("subject", ""),
                         msg.get("body", ""), _now()))
                    _autolink(c, cur.lastrowid)
                    _run_rules(c, cur.lastrowid)
                    nm = c.execute("SELECT m.folder, m.mailbox_id, m.is_read, mb.display FROM mails m JOIN mailboxes mb ON mb.id=m.mailbox_id WHERE m.id=?",
                                   (cur.lastrowid,)).fetchone()
                    _demo_new(nm["mailbox_id"], cur.lastrowid, nm["folder"], nm["is_read"], nm["display"], u["name"], msg.get("subject", ""), msg.get("body", ""))
        return sent_id

    # -- Plakzicht (nagebootst)
    def search_plakzicht(self, q):
        api = pz_api()
        if api:
            with _conn() as c:
                self._user(c)
            if len((q or "").strip()) < 2:
                return []
            try:
                j = api.search(q.strip())
            except PlakzichtError as e:
                raise RuntimeError(str(e)) from None
            return ([{"nr": o["nummer"], "klant": o.get("klant") or "", "soort": "order"} for o in j.get("orders") or []]
                    + [{"nr": x["nummer"], "klant": x.get("klant") or "", "soort": "offerte"} for x in j.get("offertes") or []])
        q = "%" + (q or "").strip() + "%"
        with _conn() as c:
            self._user(c)
            orders = _rows(c.execute("SELECT nr, klant, 'order' AS soort FROM pz_orders WHERE nr LIKE ? OR klant LIKE ? ORDER BY nr", (q, q)))
            offs = _rows(c.execute("SELECT nr, klant, 'offerte' AS soort FROM pz_offertes WHERE nr LIKE ? OR klant LIKE ? ORDER BY nr", (q, q)))
        return orders + offs

    def _pz_page(self, nr):
        """Gegevens voor de orderpagina: soort, gegevens (echt of nagebootst) en de gekoppelde mails."""
        with _conn() as c:
            u = self._user(c)
            try:
                k = pz_kind(c, nr)
                if not k:
                    raise ValueError(f"{nr} niet gevonden in Plakzicht.")
                kind, nr = k
                data = pz_order_view(c, nr) if kind == "order" else pz_quote_view(c, nr)
            except PlakzichtError as e:
                raise RuntimeError(str(e)) from None
            ids = self._mb_ids(c, u)
            col = "order_nr" if kind == "order" else "offerte_nr"
            if not self._is_ms():
                mails = _rows(c.execute(
                    f"SELECT m.id,m.mailbox_id,m.folder,m.from_name,m.to_addr,m.subject,m.date,m.is_read,mb.display AS mailbox "
                    f"FROM mails m JOIN mailboxes mb ON mb.id=m.mailbox_id WHERE upper(m.{col})=upper(?) ORDER BY m.date DESC", (nr,)))
                for m in mails:
                    m["toegang"] = m["mailbox_id"] in ids
            else:
                rows = _rows(c.execute(f"SELECT l.*, mb.display AS mailbox FROM ms_links l LEFT JOIN mailboxes mb ON mb.id=l.mailbox_id "
                                       f"WHERE upper(l.{col})=upper(?) ORDER BY l.date DESC", (nr,)))
                mails = [{"id": x["key"], "mailbox_id": x["mailbox_id"], "folder": "sent" if x["outgoing"] else "inbox",
                          "from_name": x["from_name"], "to_addr": x["to_addr"], "subject": x["subject"], "date": x["date"],
                          "is_read": 1, "mailbox": x["mailbox"] or "?", "toegang": x["mailbox_id"] in ids} for x in rows]
        return {"soort": kind, "data": data, "mails": mails}

    # ================================================================ stand: demo of Microsoft 365
    def _is_ms(self):
        return CFG["mode"] == "microsoft"

    def _ms_for(self, mb):
        return client_for_mailbox(mb)

    def _mb(self, c, u, mailbox_id):
        mailbox_id = int(mailbox_id)
        if mailbox_id not in self._mb_ids(c, u):
            raise PermissionError("Geen toegang tot die mailbox.")
        return _gmb(c.execute("SELECT * FROM mailboxes WHERE id=?", (mailbox_id,)).fetchone())

    def _folders(self, c, mb):
        if not self._is_ms():
            return _demo_folders(c, mb["id"])
        fl = CACHE.folders(mb["id"])
        if not fl:  # eerste keer: mappen direct ophalen, berichten volgen op de achtergrond
            CACHE.refresh_folders(mb, self._ms_for(mb))
            CACHE.kick(mb["id"])
            fl = CACHE.folders(mb["id"])
        return fl

    def _split(self, c, u, mail_id):
        """Microsoft-id = '<mailbox-id>:<bericht-id>'."""
        mb_id, _, gid = str(mail_id).partition(":")
        if not gid:
            raise PermissionError("Onbekende mail.")
        return self._mb(c, u, mb_id), gid

    def _labelmap(self, c):
        return {l["name"].lower(): l for l in _rows(c.execute("SELECT id,name,color FROM labels"))}

    def _link_row(self, c, mb, gid):
        r = c.execute("SELECT * FROM ms_links WHERE key=?", (f"{mb['id']}:{gid}",)).fetchone()
        return dict(r) if r else None

    def _ms_to_mail(self, c, mb, m, fmap, lmap, body=None):
        f = fmap.get(m.get("parentFolderId")) or {}
        frm = (m.get("from") or {}).get("emailAddress") or {}
        rc = lambda k: ", ".join((r.get("emailAddress") or {}).get("address", "") for r in m.get(k) or [])
        cats = m.get("categories") or []
        labels = [{"id": lmap[x.lower()]["id"], "name": lmap[x.lower()]["name"], "color": lmap[x.lower()]["color"]}
                  if x.lower() in lmap else {"id": None, "name": x, "color": "#9aa39d"} for x in cats]
        link = self._link_row(c, mb, m["id"])
        if link:
            order_nr, offerte_nr, mode = link["order_nr"], link["offerte_nr"], link["link_mode"]
        else:
            d = _detect(c, m.get("subject"), body if body is not None else m.get("bodyPreview"))
            order_nr, offerte_nr, mode = d["order_nr"], d["offerte_nr"], "auto"
        out = {"id": f"{mb['id']}:{m['id']}", "mailbox_id": mb["id"], "mailbox": mb["display"],
               "folder": m.get("parentFolderId"), "folder_wk": f.get("wk", ""), "folder_name": f.get("name", ""),
               "from_name": frm.get("name") or frm.get("address", ""), "from_addr": frm.get("address", ""),
               "to_addr": rc("toRecipients"), "cc": rc("ccRecipients"), "subject": m.get("subject") or "",
               "date": m.get("receivedDateTime"), "is_read": 1 if m.get("isRead") else 0,
               "flagged": 1 if (m.get("flag") or {}).get("flagStatus") == "flagged" else 0,
               "order_nr": order_nr, "offerte_nr": offerte_nr, "link_mode": mode, "labels": labels,
               "categories": cats, "has_attachments": bool(m.get("hasAttachments")),
               "snippet": (m.get("bodyPreview") or "")[:160], "importance": m.get("importance") or "normal",
               "size": m.get("_size") or None, "flag_done": (m.get("flag") or {}).get("flagStatus") == "complete",
               "flag_due": (((m.get("flag") or {}).get("dueDateTime") or {}).get("dateTime") or "")[:10] or None}
        if body is not None:
            out["body"] = body
        return out

    def _save_link(self, c, mb, mail, mode, order_nr, offerte_nr):
        own = {a.lower() for (a,) in c.execute("SELECT address FROM mailboxes")}
        c.execute("INSERT OR REPLACE INTO ms_links(key,mailbox_id,msg_id,order_nr,offerte_nr,link_mode,subject,from_name,"
                  "from_addr,to_addr,date,outgoing) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (mail["id"], mb["id"], mail["id"].split(":", 1)[1], order_nr, offerte_nr, mode, mail["subject"],
                   mail["from_name"], mail["from_addr"], mail["to_addr"], mail["date"],
                   1 if (mail["from_addr"] or "").lower() in own else 0))

    def _relink(self, c, old_key, new_mb, new_id):
        c.execute("UPDATE ms_links SET key=?, msg_id=?, mailbox_id=? WHERE key=?", (f"{new_mb}:{new_id}", new_id, new_mb, old_key))

    def _annotate_demo(self, c, rows):
        cache = {}
        for r in rows:
            if r["mailbox_id"] not in cache:
                cache[r["mailbox_id"]] = {f["id"]: f for f in _demo_folders(c, r["mailbox_id"])}
            f = cache[r["mailbox_id"]].get(r["folder"]) or {}
            r["folder_wk"], r["folder_name"] = f.get("wk", ""), f.get("name", "")
        return rows

    def _ms_call(self, fn):
        try:
            return fn()
        except GraphError as e:
            if e.status == 404 and e.code in ("ErrorItemNotFound", "ResourceNotFound", ""):
                raise Gone("intussen verplaatst of verwijderd") from None
            raise RuntimeError(nl_error(e)) from None

    # -- mail: zelfde functies voor beide standen
    def list_mails(self, view):
        out = self._list_raw(view)
        pend = pending_keys()
        out = [m for m in out if str(m["id"]) not in pend]  # wordt op de achtergrond verplaatst
        with _conn() as c:
            info = collab_info(c, [m["id"] for m in out], self._uid)
            me = c.execute("SELECT name FROM users WHERE id=?", (self._uid,)).fetchone()
        first = (me[0].split()[0].lower() if me and me[0] else "")
        for m in out:
            m.update(info.get(str(m["id"]), {}))
            m["mention"] = bool(first) and ("@" + first) in (m.get("snippet") or "").lower()
        f = view.get("filter")
        if f == "mijn":
            out = [m for m in out if (m.get("claim") or {}).get("mine")]
        elif f == "vrij":
            out = [m for m in out if not m.get("claim")]
        elif f == "vermeld":
            out = [m for m in out if m["mention"]]
        return out

    def _list_raw(self, view):
        if not self._is_ms():
            rows = self._demo_list_mails(view)
            with _conn() as c:
                return self._annotate_demo(c, rows)
        with _conn() as c:
            u = self._user(c)
            lmap = self._labelmap(c)
            mbs = {mid: self._mb(c, u, mid) for mid in self._mb_ids(c, u)}
            fmaps = {}

            def fmap(mid):
                if mid not in fmaps:
                    fmaps[mid] = {f["id"]: f for f in CACHE.folders(mid)}
                return fmaps[mid]
            out = []
            so = view.get("sort") or {}
            srt = {"sort": so.get("key") if so.get("key") in SORT_KEYS else "date", "desc": so.get("dir") != "asc"}
            if view.get("label_id"):
                lab = c.execute("SELECT name FROM labels WHERE id=?", (view["label_id"],)).fetchone()
                if lab and mbs:
                    for mid, m in CACHE.list(list(mbs), category=lab[0], filt=view.get("filter"), search=view.get("search"), **srt):
                        out.append(self._ms_to_mail(c, mbs[mid], m, fmap(mid), lmap))
            else:
                mb = self._mb(c, u, view["mailbox_id"])
                fid = view.get("folder") or "inbox"
                CACHE.touch(mb["id"], fid)
                if CACHE.is_synced(mb["id"], fid):
                    items = [m for _, m in CACHE.list([mb["id"]], folder_id=fid, filt=view.get("filter"), search=view.get("search"), **srt)]
                else:  # nog niet in de lokale kopie: rechtstreeks ophalen en de map voorrang geven
                    items = self._ms_call(lambda: self._ms_for(mb).list(mb["address"], fid, view.get("filter"), view.get("search")))
                    CACHE.kick(mb["id"], fid)
                out = [self._ms_to_mail(c, mb, m, fmap(mb["id"]), lmap) for m in items]
        if view.get("filter") == "zonder_order":
            out = [m for m in out if not (m["order_nr"] or m["offerte_nr"])]
        return out

    def get_mail(self, mail_id):
        m = self._get_raw(mail_id)
        if str(m["id"]) in pending_keys():
            raise Gone("intussen")
        with _conn() as c:
            m.update(collab_info(c, [m["id"]], self._uid).get(str(m["id"]), {}))
            m["activity"] = [dict(r) for r in c.execute(
                "SELECT user_name, action, detail, at FROM mail_activity WHERE key=? ORDER BY at DESC LIMIT 8", (str(m["id"]),))]
        return m

    def _get_raw(self, mail_id, mark_read=True):
        if not self._is_ms():
            m = self._demo_get_mail(int(mail_id))
            with _conn() as c:
                return self._annotate_demo(c, [m])[0]
        with _conn() as c:
            u = self._user(c)
            mb, gid = self._split(c, u, mail_id)
            ms = self._ms_for(mb)
            data, body = CACHE.get(mb["id"], gid)
            if body is None:  # niet in de kopie: ophalen en bewaren
                raw = self._ms_call(lambda: ms.get(mb["address"], gid))
                body = ms.inline_images(mb["address"], gid, (raw.get("body") or {}).get("content", ""))
                data = raw
                with CACHE.conn() as cc:
                    CACHE._upsert(cc, mb["id"], raw, body=body)
            if mark_read and not data.get("isRead"):
                data["isRead"] = True
                CACHE.patch(mb["id"], gid, {"isRead": True})
                threading.Thread(target=lambda: _quiet(lambda: ms.patch(mb["address"], gid, {"isRead": True})), daemon=True).start()
            m = self._ms_to_mail(c, mb, data, {f["id"]: f for f in CACHE.folders(mb["id"])}, self._labelmap(c), body=body)
            if not self._link_row(c, mb, gid) and (m["order_nr"] or m["offerte_nr"]):
                self._save_link(c, mb, m, "auto", m["order_nr"], m["offerte_nr"])
            m["plakzicht"] = {"pending": True, "live": True} if pz_api() else self._pz_for(c, m)
        return m

    def mail_plakzicht(self, mail_id):
        """Plakzicht-gegevens bij een mail apart ophalen, zodat de mail zelf direct opent."""
        m = self._get_raw(mail_id, mark_read=False)
        if (m.get("plakzicht") or {}).get("pending"):
            with _conn() as c:
                m["plakzicht"] = self._pz_for(c, m)
        return m["plakzicht"]

    def move_mail(self, mail_id, mailbox_id, folder="inbox"):
        if not self._is_ms():
            return self._demo_move_mail(int(mail_id), mailbox_id, folder)
        with _conn() as c:
            u = self._user(c)
            src, gid = self._split(c, u, mail_id)
            dst = self._mb(c, u, mailbox_id)
            if src["id"] == dst["id"]:
                new = self._ms_call(lambda: self._ms_for(src).move(src["address"], gid, folder))
                CACHE.moved(src["id"], gid, new)
                self._relink(c, f"{src['id']}:{gid}", dst["id"], new["id"])
                return {"id": f"{dst['id']}:{new['id']}", "warnings": []}
            # Tussen mailboxen: op de achtergrond (wachtrij op de server), zodat je direct verder kunt.
            key = f"{src['id']}:{gid}"
            if c.execute("SELECT 1 FROM move_jobs WHERE key=? AND status IN ('wacht','bezig')", (key,)).fetchone():
                raise Gone("intussen")
            subj = (CACHE.get(src["id"], gid)[0] or {}).get("subject") or "(geen onderwerp)"
            c.execute("INSERT INTO move_jobs(user_id,user_name,key,subject,src_mb,dst_mb,folder,status,created) VALUES(?,?,?,?,?,?,?,?,?)",
                      (u["id"], u["name"], key, subj, src["id"], dst["id"], folder, "wacht", time.time()))
        _jobs_wake.set()
        return {"queued": True, "id": f"{src['id']}:{gid}", "warnings": []}

    def _move_cross_now(self, mail_id, mailbox_id, folder):
        """Daadwerkelijk verplaatsen naar een andere mailbox (door de wachtrij aangeroepen)."""
        with _conn() as c:
            u = self._user(c)
            src, gid = self._split(c, u, mail_id)
            dst = self._mb(c, u, mailbox_id)
            s_ms, d_ms = self._ms_for(src), self._ms_for(dst)
            nid, warnings = self._ms_call(lambda: s_ms.copy_to_other_mailbox(src["address"], gid, dst["address"], folder, target=d_ms))
            if warnings:
                warnings.append("Het origineel is daarom in de oude mailbox blijven staan.")
            else:
                new = self._ms_call(lambda: s_ms.move(src["address"], gid, "deleteditems"))
                CACHE.moved(src["id"], gid, new)
            self._relink(c, f"{src['id']}:{gid}", dst["id"], nid)
        CACHE.kick(dst["id"], folder)
        return {"id": f"{dst['id']}:{nid}", "warnings": warnings}

    def archive_mail(self, mail_id):
        if not self._is_ms():
            with _conn() as c:
                u = self._user(c)
                m = self._mail_ok(c, u, mail_id)
            return self._demo_move_mail(int(mail_id), m["mailbox_id"], "archive")
        with _conn() as c:
            u = self._user(c)
            mb, gid = self._split(c, u, mail_id)
            try:
                new = self._ms_for(mb).move(mb["address"], gid, "archive")
            except GraphError as e:
                if e.status in (400, 404) and "olderNotFound" in (e.code or "") + str(e):
                    raise RuntimeError("Deze mailbox heeft (nog) geen Archief-map. Maak die in Outlook aan of verplaats naar een andere map.")
                raise RuntimeError(nl_error(e)) from None
            CACHE.moved(mb["id"], gid, new)
            self._relink(c, f"{mb['id']}:{gid}", mb["id"], new["id"])
        return True

    def delete_mail(self, mail_id):
        if not self._is_ms():
            return self._demo_delete_mail(int(mail_id))
        with _conn() as c:
            u = self._user(c)
            mb, gid = self._split(c, u, mail_id)
            ms = self._ms_for(mb)
            data, _ = CACHE.get(mb["id"], gid)
            parent = (data or {}).get("parentFolderId") or self._ms_call(lambda: ms.get(mb["address"], gid, full=False)).get("parentFolderId")
            wk = self._ms_call(lambda: ms.wellknown(mb["address"]))
            if wk.get(parent) == "deleted":
                self._ms_call(lambda: ms.delete(mb["address"], gid))
                CACHE.removed(mb["id"], gid)
                c.execute("DELETE FROM ms_links WHERE key=?", (f"{mb['id']}:{gid}",))
                return "definitief"
            new = self._ms_call(lambda: ms.move(mb["address"], gid, "deleteditems"))
            CACHE.moved(mb["id"], gid, new)
            self._relink(c, f"{mb['id']}:{gid}", mb["id"], new["id"])
        return "verwijderde items"

    def set_read(self, mail_id, read):
        if not self._is_ms():
            return self._demo_set_read(int(mail_id), read)
        with _conn() as c:
            mb, gid = self._split(c, self._user(c), mail_id)
        self._ms_call(lambda: self._ms_for(mb).patch(mb["address"], gid, {"isRead": bool(read)}))
        CACHE.patch(mb["id"], gid, {"isRead": bool(read)})
        return True

    def mark_unread(self, mail_id):
        return self.set_read(mail_id, False)

    def set_flag(self, mail_id, on):
        if not self._is_ms():
            return self._demo_set_flag(int(mail_id), on)
        with _conn() as c:
            mb, gid = self._split(c, self._user(c), mail_id)
        flag = {"flagStatus": "flagged" if on else "notFlagged"}
        self._ms_call(lambda: self._ms_for(mb).patch(mb["address"], gid, {"flag": flag}))
        CACHE.patch(mb["id"], gid, {"flag": flag})
        return True

    def set_label(self, mail_id, label_id, on):
        """Bij Microsoft worden labels Outlook-categorieën met dezelfde naam."""
        if not self._is_ms():
            return self._demo_set_label(int(mail_id), label_id, on)
        with _conn() as c:
            mb, gid = self._split(c, self._user(c), mail_id)
            lab = c.execute("SELECT name FROM labels WHERE id=?", (label_id,)).fetchone()
        if not lab:
            raise ValueError("Onbekend label.")
        ms = self._ms_for(mb)

        def run():
            raw = ms.get(mb["address"], gid, full=False)
            cats = [x for x in raw.get("categories") or [] if x.lower() != lab[0].lower()]
            if on:
                cats.append(lab[0])
            ms.patch(mb["address"], gid, {"categories": cats})
            return cats
        CACHE.patch(mb["id"], gid, {"categories": self._ms_call(run)})
        return True

    def link_mail(self, mail_id, nr):
        if not self._is_ms():
            return self._demo_link_mail(int(mail_id), nr)
        nr = (nr or "").strip().upper()
        with _conn() as c:
            u = self._user(c)
            mb, gid = self._split(c, u, mail_id)
            raw, _ = CACHE.get(mb["id"], gid)
            raw = raw or self._ms_call(lambda: self._ms_for(mb).get(mb["address"], gid, full=False))
            mail = self._ms_to_mail(c, mb, raw, {}, {})
            if not nr:
                self._save_link(c, mb, mail, "none", None, None)
            else:
                try:
                    k = pz_kind(c, nr)
                except PlakzichtError as e:
                    raise RuntimeError(str(e)) from None
                if not k:
                    raise ValueError(f"{nr} bestaat niet in Plakzicht.")
                self._save_link(c, mb, mail, "manual", k[1] if k[0] == "order" else None, k[1] if k[0] == "offerte" else None)
        return True

    def send_mail(self, msg):
        res = self._send_raw(msg)
        ref = msg.get("reply_to")
        if ref:  # in het logboek van de oorspronkelijke mail: wie heeft beantwoord
            with _conn() as c:
                u = self._user(c)
            log_activity(str(ref), u["id"], u["name"], "doorgestuurd" if msg.get("mode") == "forward" else "beantwoord",
                         "aan " + (msg.get("to") or "")[:120])
            mb = _mailbox_of_key(ref)
            with _plock:
                (PRESENCE.get(str(ref)) or {}).pop(u["id"], None)
            BUS.publish({"t": "mail", "mb": [mb], "key": str(ref), "by": u["id"]}, [mb])
        return res

    def _send_raw(self, msg):
        if not self._is_ms():
            return self._demo_send_mail(msg)
        if not (msg.get("to") or "").strip():
            raise ValueError("Vul een ontvanger in.")
        with _conn() as c:
            mb = self._mb(c, self._user(c), msg["mailbox_id"])
        self._ms_call(lambda: self._ms_for(mb).send(mb["address"], msg.get("subject", ""), msg.get("body", ""), msg.get("to"), msg.get("cc")))
        sent = next((f["id"] for f in CACHE.folders(mb["id"]) if f["wk"] == "sent"), None)
        CACHE.kick(mb["id"], sent)
        return True

    # -- samenwerken
    def presence(self, mail_id, state=None):
        """Ik lees ('leest') of beantwoord ('antwoordt') deze mail; None = gestopt. Geeft wie er verder mee bezig is."""
        key = str(mail_id)
        with _conn() as c:
            u = self._user(c)
        mb = _mailbox_of_key(key)
        changed = False
        with _plock:
            who = PRESENCE.setdefault(key, {})
            if state in ("leest", "antwoordt"):
                old = who.get(u["id"])
                changed = not old or old["state"] != state
                who[u["id"]] = {"name": u["name"], "state": state, "t": time.time(), "mb": mb}
            elif who.pop(u["id"], None):
                changed = True
            if not who:
                PRESENCE.pop(key, None)
        if changed and mb:
            BUS.publish({"t": "presence", "mb": [mb], "key": key, "by": u["id"]}, [mb])
        return presence_of([key], exclude_uid=u["id"]).get(key, [])

    def claim_mail(self, mail_id, on=True):
        """Mail oppakken ('ik doe deze') of vrijgeven."""
        key = str(mail_id)
        with _conn() as c:
            u = self._user(c)
            cur = c.execute("SELECT user_id, user_name FROM mail_claims WHERE key=?", (key,)).fetchone()
            if on:
                if cur and cur["user_id"] != u["id"]:
                    raise RuntimeError(f"{cur['user_name']} heeft deze mail al opgepakt.")
                c.execute("INSERT OR REPLACE INTO mail_claims VALUES(?,?,?,?)", (key, u["id"], u["name"], time.time()))
            else:
                if cur and cur["user_id"] != u["id"] and u["role"] != "beheerder":
                    raise RuntimeError(f"Alleen {cur['user_name']} (of een beheerder) kan deze mail vrijgeven.")
                c.execute("DELETE FROM mail_claims WHERE key=?", (key,))
        log_activity(key, u["id"], u["name"], "opgepakt" if on else "vrijgegeven")
        mb = _mailbox_of_key(key)
        BUS.publish({"t": "mail", "mb": [mb], "key": key, "by": u["id"]}, [mb])
        return True

    def jobs(self):
        """Mijn lopende en recente verplaatsingen naar andere mailboxen."""
        with _conn() as c:
            u = self._user(c)
            return _rows(c.execute("SELECT id, subject, status, error, created, done FROM move_jobs WHERE user_id=? AND created>? ORDER BY id DESC LIMIT 20",
                                   (u["id"], time.time() - 3600)))

    def download_eml(self, mail_id):
        """Geeft (bestandsnaam, inhoud) van een mail als .eml."""
        with _conn() as c:
            u = self._user(c)
            if self._is_ms():
                mb, gid = self._split(c, u, mail_id)
                data = self._ms_call(lambda: self._ms_for(mb).mime(mb["address"], gid))
                subj = (CACHE.get(mb["id"], gid)[0] or {}).get("subject") or "mail"
            else:
                m = self._mail_ok(c, u, int(mail_id))
                subj = m["subject"] or "mail"
                from email.message import EmailMessage
                from email.utils import format_datetime
                em = EmailMessage()
                em["From"] = f'{m["from_name"]} <{m["from_addr"]}>'
                em["To"], em["Subject"] = m["to_addr"] or "", subj
                if m["cc"]:
                    em["Cc"] = m["cc"]
                try:
                    em["Date"] = format_datetime(dt.datetime.fromisoformat(m["date"]).astimezone())
                except (TypeError, ValueError):
                    pass
                em.set_content(_text(m["body"]))
                em.add_alternative(m["body"] or "", subtype="html")
                data = em.as_bytes()
        name = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", subj).strip()[:80] or "mail"
        return name + ".eml", data

    def get_order(self, nr):
        return self._pz_page(nr)

    # -- mappen maken, hernoemen, verwijderen
    def _check_folder_name(self, name):
        name = (name or "").strip()
        if not name or len(name) > 120 or any(ch in name for ch in "/\\"):
            raise ValueError("Geef een mapnaam (zonder / of \\).")
        return name

    def _after_folder_change(self, mb):
        _quiet(lambda: CACHE.refresh_folders(mb, self._ms_for(mb)))
        CACHE.kick(mb["id"])

    def create_folder(self, mailbox_id, parent_id, name):
        name = self._check_folder_name(name)
        with _conn() as c:
            mb = self._mb(c, self._user(c), mailbox_id)
            if self._is_ms():
                fid = self._ms_call(lambda: self._ms_for(mb).create_folder(mb["address"], parent_id or None, name))
                self._after_folder_change(mb)
                return fid
            fl = _demo_folders(c, mb["id"])
            if parent_id and not any(f["id"] == parent_id for f in fl):
                raise ValueError("Onbekende bovenliggende map.")
            if any(f["parent"] == (parent_id or None) and f["name"].lower() == name.lower() for f in fl):
                raise ValueError("Er bestaat al een map met die naam op deze plek.")
            return "f" + str(c.execute("INSERT INTO demo_folders(mailbox_id,parent,name) VALUES(?,?,?)",
                                       (mb["id"], parent_id or None, name)).lastrowid)

    def rename_folder(self, mailbox_id, folder_id, name):
        name = self._check_folder_name(name)
        with _conn() as c:
            mb = self._mb(c, self._user(c), mailbox_id)
            if self._is_ms():
                ms = self._ms_for(mb)
                if self._ms_call(lambda: ms.wellknown(mb["address"])).get(folder_id):
                    raise ValueError("Standaardmappen kun je niet hernoemen.")
                self._ms_call(lambda: ms.rename_folder(mb["address"], folder_id, name))
                self._after_folder_change(mb)
                return True
            if not str(folder_id).startswith("f"):
                raise ValueError("Standaardmappen kun je niet hernoemen.")
            c.execute("UPDATE demo_folders SET name=? WHERE id=? AND mailbox_id=?", (name, int(folder_id[1:]), mb["id"]))
        return True

    def delete_folder(self, mailbox_id, folder_id):
        with _conn() as c:
            u = self._user(c, admin=True)
            mb = self._mb(c, u, mailbox_id)
            if self._is_ms():
                ms = self._ms_for(mb)
                if self._ms_call(lambda: ms.wellknown(mb["address"])).get(folder_id):
                    raise ValueError("Standaardmappen kun je niet verwijderen.")
                self._ms_call(lambda: ms.delete_folder(mb["address"], folder_id))
                self._after_folder_change(mb)
                return True
            if not str(folder_id).startswith("f"):
                raise ValueError("Standaardmappen kun je niet verwijderen.")
            fl = _demo_folders(c, mb["id"])
            gone, changed = {folder_id}, True
            while changed:
                changed = False
                for f in fl:
                    if f["parent"] in gone and f["id"] not in gone:
                        gone.add(f["id"]); changed = True
            for fid in gone:  # zoals bij Microsoft: de inhoud gaat naar Verwijderde items
                c.execute("UPDATE mails SET folder='deleted' WHERE mailbox_id=? AND folder=?", (mb["id"], fid))
                c.execute("DELETE FROM demo_folders WHERE id=?", (int(fid[1:]),))
        return True

    def move_folder(self, mailbox_id, folder_id, dest_id):
        """Map verplaatsen binnen dezelfde mailbox (dest_id leeg = bovenste niveau)."""
        with _conn() as c:
            mb = self._mb(c, self._user(c), mailbox_id)
            if folder_id == dest_id:
                raise ValueError("Een map kan niet in zichzelf.")
            if self._is_ms():
                ms = self._ms_for(mb)
                if self._ms_call(lambda: ms.wellknown(mb["address"])).get(folder_id):
                    raise ValueError("Standaardmappen kun je niet verplaatsen.")
                self._ms_call(lambda: ms.move_folder(mb["address"], folder_id, dest_id or "msgfolderroot"))
                self._after_folder_change(mb)
                return True
            if not str(folder_id).startswith("f"):
                raise ValueError("Standaardmappen kun je niet verplaatsen.")
            fl = {f["id"]: f for f in _demo_folders(c, mb["id"])}
            p = dest_id
            while p:
                if p == folder_id:
                    raise ValueError("Een map kan niet in een van zijn eigen submappen.")
                p = (fl.get(p) or {}).get("parent")
            c.execute("UPDATE demo_folders SET parent=? WHERE id=?", (dest_id or None, int(folder_id[1:])))
        return True

    def refresh_now(self, mailbox_id=None):
        """Nu bijwerken vanaf Microsoft (knop Vernieuwen)."""
        with _conn() as c:
            u = self._user(c)
            ids = [self._mb(c, u, mailbox_id)["id"]] if mailbox_id else self._mb_ids(c, u)
        if self._is_ms():
            for mid in ids:
                CACHE.kick(mid)
        return True

    # -- beheer: Microsoft-koppeling
    def _accounts_public(self):
        return [{"id": a["id"], "upn": a["upn"], "name": a["name"], "added": a.get("added"), "mail": a.get("mail"),
                 "protected": _is_protected(a["refresh"]), "error": a.get("error"), "cal": bool(a.get("cal"))} for a in CFG["accounts"]]

    def ms_config(self):
        with _conn() as c:
            self._user(c, admin=True)
        return {"mode": CFG["mode"], "auth": CFG["auth"], "tenant": CFG["tenant"], "client_id": CFG["client_id"],
                "has_secret": bool(CFG["secret"]), "secret_protected": _is_protected(CFG["secret"]),
                "accounts": self._accounts_public(), "local": self._is_local(), "calendar": bool(CFG.get("calendar")),
                "ready": bool(CFG["tenant"] and CFG["client_id"] and (CFG["accounts"] if CFG["auth"] == "user" else CFG["secret"])),
                "microsoft_db_exists": os.path.exists(DBS["microsoft"])}

    def _is_local(self):
        return not IN_DOCKER and self._ip in ("127.0.0.1", "::1", "localhost", None)

    def ms_signin_start(self, method="code"):
        """method 'code': aanmelden met een code op microsoft.com/devicelogin (vanaf elke pc);
        'browser': aanmelden in de browser op de server zelf (alleen als je op de server werkt)."""
        with _conn() as c:
            self._user(c, admin=True)
        global SIGNIN
        if SIGNIN:
            SIGNIN.stop()
        try:
            if method == "browser":
                if not self._is_local():
                    raise RuntimeError("Aanmelden via de browser kan alleen op de pc waar de server draait. Gebruik aanmelden met een code.")
                SIGNIN = SignIn(CFG["tenant"], CFG["client_id"], scope=CALENDAR_SCOPES if CFG.get("calendar") else None)
                return {"method": "browser", "url": SIGNIN.start()}
            SIGNIN = DeviceSignIn(CFG["tenant"], CFG["client_id"], scope=CALENDAR_SCOPES if CFG.get("calendar") else None)
            return {"method": "code", **SIGNIN.start()}
        except GraphError as e:
            SIGNIN = None
            raise RuntimeError(nl_error(e)) from None

    def ms_signin_status(self):
        with _conn() as c:
            self._user(c, admin=True)
        global SIGNIN
        si = SIGNIN
        if not si:
            return {"state": "none"}
        st = dict(si.status)
        if st["state"] == "ok" and si.result:
            aid = add_account(si.result)
            si.result = None
            if self._is_ms() and add_own_mailbox(aid):
                st["message"] += " De eigen mailbox van dit account is gekoppeld."
        if st["state"] != "waiting":
            SIGNIN = None
        return st

    def link_own_mailbox(self, account_id):
        with _conn() as c:
            self._user(c, admin=True)
        if not self._is_ms():
            raise RuntimeError("Schakel eerst over naar Microsoft 365; daarna kun je mailboxen koppelen.")
        mid = add_own_mailbox(account_id)
        if not mid:
            raise RuntimeError("De eigen mailbox van dit account kon niet worden opgehaald. Meld het account opnieuw aan.")
        return mid

    def ms_signin_cancel(self):
        with _conn() as c:
            self._user(c, admin=True)
        global SIGNIN
        if SIGNIN:
            SIGNIN.stop()
            SIGNIN = None
        return True

    def ms_remove_account(self, account_id):
        """Account vergeten op deze server. Mailboxen die het gebruikten, krijgen een ander account of geen."""
        with _conn() as c:
            self._user(c, admin=True)
        with _cfg_lock:
            CFG["accounts"] = [a for a in CFG["accounts"] if a["id"] != account_id]
            save_config(CFG)
        drop_clients()
        if os.path.exists(DBS["microsoft"]):
            with _conn_for(DBS["microsoft"]) as c:
                c.execute("UPDATE mailboxes SET ms_account=NULL WHERE ms_account=?", (account_id,))
        return True

    def save_ms_config(self, data):
        with _conn() as c:
            self._user(c, admin=True)
        tenant, client = (data.get("tenant") or "").strip(), (data.get("client_id") or "").strip()
        guid = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
        if tenant and not (re.fullmatch(guid, tenant) or re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", tenant.lower())):
            raise ValueError("Tenant-ID moet een GUID zijn (of je domein, bijv. jouwbedrijf.onmicrosoft.com).")
        if client and not re.fullmatch(guid, client):
            raise ValueError("Client-ID (toepassings-ID) moet een GUID zijn.")
        with _cfg_lock:
            if (tenant, client) != (CFG["tenant"], CFG["client_id"]) and CFG["accounts"]:
                CFG["accounts"] = []  # andere app-registratie = accounts opnieuw aanmelden
            CFG.update({"tenant": tenant, "client_id": client})
            if data.get("auth") in ("user", "app"):
                CFG["auth"] = data["auth"]
            if data.get("secret"):
                CFG["secret"] = _protect(data["secret"].strip())
            save_config(CFG)
        drop_clients()
        if CFG["auth"] == "user" and self._is_ms():  # eigen mailboxen van de aangemelde accounts koppelen
            for a in list(CFG["accounts"]):
                _quiet(lambda aid=a["id"]: add_own_mailbox(aid))
        return self.ms_config()

    def test_ms(self, address=None, account_id=None):
        """Test de koppeling: token ophalen en (als opgegeven) een mailbox openen."""
        with _conn() as c:
            self._user(c, admin=True)
        if CFG["auth"] == "app":
            accts = [None]
        else:
            accts = [a for a in CFG["accounts"] if not account_id or a["id"] == account_id]
            if not accts:
                return {"ok": False, "message": "Er is nog geen Microsoft-account aangemeld."}
        address = (address or "").strip().lower()
        own = lambda a: a and address in (a["upn"].lower(), (a.get("mail") or "").lower())
        if address and not account_id:  # eigen account eerst proberen
            accts.sort(key=lambda a: 0 if own(a) else 1)
        msgs = []
        for a in accts:
            who = f"als {a['name'] or a['upn']}" if a else "met de app"
            try:
                ms = client_for_account(a["id"] if a else None)
                ms.g.token()
                if not address:
                    msgs.append(f"Verbinding lukt {who}.")
                    continue
                target = a["oid"] if own(a) and a.get("oid") else address  # eigen mailbox via het Microsoft-ID
                box = ms.check_mailbox(target)
                n = len(ms.folders(target, max_age=0))
                return {"ok": True, "account": a["id"] if a else None, "graph_id": target if target != address else None,
                        "message": f"{address} is bereikbaar {who}: {box.get('displayName', 'Postvak IN')}, {n} mappen."}
            except GraphError as e:
                msgs.append((who, nl_error(e)))
        if not address:
            fails = [x for x in msgs if isinstance(x, tuple)]
            return {"ok": not fails, "message": " ".join(x if isinstance(x, str) else f"{x[0].capitalize()}: {x[1]}" for x in msgs)}
        texts = {m for _, m in msgs}
        if CFG["auth"] == "app" and CFG["accounts"]:
            return {"ok": False, "message": f"{address} is niet bereikbaar met de app. Het programma staat op 'App met clientgeheim'; "
                                            "kies in Beheer › Microsoft-koppeling 'Aanmelden met Microsoft' en klik op Opslaan om je aangemelde accounts te gebruiken."}
        if len(texts) == 1:  # zelfde melding voor alle accounts: één keer tonen
            names = ", ".join(w.replace("als ", "") for w, _ in msgs)
            return {"ok": False, "message": f"{address} is niet bereikbaar ({'geprobeerd ' if len(msgs) > 1 else ''}{names}). {texts.pop()}"}
        return {"ok": False, "message": " ".join(f"{w.capitalize()}: {m}" for w, m in msgs)}

    def set_mailbox_cache(self, mailbox_id, days):
        """Hoeveel mail van deze mailbox offline bewaard wordt (dagen; 0 = alles)."""
        days = int(days)
        if days not in [d for d, _ in PERIODS]:
            raise ValueError("Onbekende periode.")
        with _conn() as c:
            self._user(c, admin=True)
            c.execute("UPDATE mailboxes SET cache_days=? WHERE id=?", (days, int(mailbox_id)))
            mb = dict(c.execute("SELECT * FROM mailboxes WHERE id=?", (int(mailbox_id),)).fetchone())
        if self._is_ms():
            CACHE.reset_window(mb["id"])
            CACHE.prune(mb)
            CACHE.kick(mb["id"])
        return True

    def list_older(self, mailbox_id, folder, before=None, search=None, filt=None):
        """Mails van vóór de bewaarperiode rechtstreeks bij Microsoft ophalen (50 per keer)."""
        if not self._is_ms():
            return []
        with _conn() as c:
            u = self._user(c)
            mb = self._mb(c, u, mailbox_id)
            if not before and not search:
                before = cutoff(CACHE.days_of(mb))
            items = self._ms_call(lambda: self._ms_for(mb).list(mb["address"], folder, filt, search, top=50, before=None if search else before))
            fmap = {f["id"]: f for f in CACHE.folders(mb["id"])}
            out = [self._ms_to_mail(c, mb, m, fmap, self._labelmap(c)) for m in items]
        if filt == "zonder_order":
            out = [m for m in out if not (m["order_nr"] or m["offerte_nr"])]
        return {"mails": out, "more": len(items) == 50 and not search}

    def set_mailbox_account(self, mailbox_id, account_id):
        with _conn() as c:
            self._user(c, admin=True)
            if account_id and not any(a["id"] == account_id for a in CFG["accounts"]):
                raise ValueError("Onbekend account.")
            c.execute("UPDATE mailboxes SET ms_account=? WHERE id=?", (account_id or None, int(mailbox_id)))
        if self._is_ms():
            CACHE.clear(int(mailbox_id))
            CACHE.kick(int(mailbox_id))
        return True

    def sync_status(self):
        with _conn() as c:
            u = self._user(c)
            ids = self._mb_ids(c, u)
        if not self._is_ms():
            return {}
        return {mid: CACHE.status(mid) for mid in ids}

    def clear_cache(self, mailbox_id):
        with _conn() as c:
            self._user(c, admin=True)
        if self._is_ms():
            CACHE.clear(int(mailbox_id))
            CACHE.kick(int(mailbox_id))
        return True

    def set_mode(self, mode):
        if mode not in DBS:
            raise ValueError("Onbekende stand.")
        with _conn() as c:
            self._user(c, admin=True)
        if mode == "microsoft":
            t = self.test_ms()
            if not t["ok"]:
                raise RuntimeError("Nog niet overgeschakeld: " + t["message"])
        CFG["mode"] = mode
        save_config(CFG)
        set_db_for_mode(mode)
        init_db()
        start_sync()
        if mode == "microsoft" and CFG["auth"] == "user":
            for a in list(CFG["accounts"]):
                _quiet(lambda aid=a["id"]: add_own_mailbox(aid))
        SESSIONS.clear()  # iedereen opnieuw inloggen
        self._uid = None
        return mode

    def backup_info(self):
        with _conn() as c:
            self._user(c, admin=True)
            days = _remember_days(c)
        return {"dir": BACKUP_DIR, "list": backups_list()[:BACKUP_KEEP], "data": DATA, "docker": IN_DOCKER, "frozen": FROZEN,
                "version": VERSION, "remember_days": days, "trust_proxy": TRUST_PROXY}

    def backup_make(self):
        with _conn() as c:
            self._user(c, admin=True)
        return backup_now()

    def admin_data(self):
        with _conn() as c:
            self._user(c, admin=True)
            users = _rows(c.execute("SELECT id,name,username,role,density,claude_on,claude_limit FROM users ORDER BY id"))
            for u in users:
                u["mailboxes"] = [r[0] for r in c.execute("SELECT mailbox_id FROM user_mailboxes WHERE user_id=?", (u["id"],))]
                u["devices"] = c.execute("SELECT COUNT(*) FROM remember WHERE user_id=?", (u["id"],)).fetchone()[0]
            mbs = _rows(c.execute("SELECT * FROM mailboxes ORDER BY id"))
            if self._is_ms():
                for m in mbs:
                    m["sync"] = CACHE.status(m["id"])
            return {"users": users, "mailboxes": mbs, "accounts": self._accounts_public(), "auth": CFG["auth"], "periods": PERIODS,
                    "labels": _rows(c.execute("SELECT * FROM labels ORDER BY name")),
                    "signatures": _rows(c.execute("SELECT s.*, u.name AS user_name FROM signatures s LEFT JOIN users u ON u.id=s.user_id ORDER BY s.user_id IS NOT NULL, u.name, s.name")),
                    "settings": _settings(c)}

    def save_user(self, data):
        name = (data.get("name") or "").strip()
        username = (data.get("username") or "").strip().lower()
        if not name or not re.fullmatch(r"[a-z0-9._-]{2,40}", username):
            raise ValueError("Vul een naam en een gebruikersnaam in (kleine letters, cijfers, - . _).")
        role = "beheerder" if data.get("role") == "beheerder" else "gebruiker"
        with _lock, _conn() as c:
            me = self._user(c, admin=True)
            if data.get("id"):
                uid = int(data["id"])
                if uid == me["id"] and role != "beheerder":
                    raise ValueError("Je kunt jezelf geen beheerrechten afnemen.")
                c.execute("UPDATE users SET name=?, username=?, role=? WHERE id=?", (name, username, role, uid))
                if data.get("password"):
                    c.execute("UPDATE users SET pw=? WHERE id=?", (_hash(data["password"]), uid))
                    if uid != me["id"]:  # nieuw wachtwoord: overal opnieuw inloggen
                        c.execute("DELETE FROM remember WHERE user_id=?", (uid,))
                        _drop_sessions(uid)
            else:
                if not data.get("password"):
                    raise ValueError("Geef de nieuwe gebruiker een wachtwoord.")
                try:
                    uid = c.execute("INSERT INTO users(name,username,pw,role) VALUES(?,?,?,?)",
                                    (name, username, _hash(data["password"]), role)).lastrowid
                except sqlite3.IntegrityError:
                    raise ValueError("Die gebruikersnaam bestaat al.")
            c.execute("DELETE FROM user_mailboxes WHERE user_id=?", (uid,))
            for mid in data.get("mailboxes") or []:
                c.execute("INSERT OR IGNORE INTO user_mailboxes VALUES(?,?)", (uid, int(mid)))
        return uid

    def delete_user(self, uid):
        with _lock, _conn() as c:
            me = self._user(c, admin=True)
            if int(uid) == me["id"]:
                raise ValueError("Je kunt jezelf niet verwijderen.")
            c.execute("DELETE FROM users WHERE id=?", (uid,))
        _drop_sessions(int(uid))
        return True

    def add_mailbox(self, address, kind):
        address = (address or "").strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", address):
            raise ValueError("Geen geldig mailadres.")
        acct = gid = None
        if self._is_ms():  # bestaat hij, en met welk aangemeld account kunnen we erbij?
            t = self.test_ms(address)
            if not t["ok"]:
                raise RuntimeError(t["message"])
            acct, gid = t.get("account"), t.get("graph_id")
        with _lock, _conn() as c:
            self._user(c, admin=True)
            try:
                mid = c.execute("INSERT INTO mailboxes(address,display,kind,ms_account,graph_id) VALUES(?,?,?,?,?)",
                                (address, address.split("@")[0] + "@", kind if kind in ("gedeeld", "persoonlijk") else "gedeeld", acct, gid)).lastrowid
            except sqlite3.IntegrityError:
                raise ValueError("Deze mailbox is al gekoppeld.")
            if self._is_ms():
                c.commit()
                CACHE.kick(mid)
                return mid
            c.execute("INSERT INTO mails(mailbox_id,folder,from_name,from_addr,to_addr,subject,body,date,is_read) VALUES(?,?,?,?,?,?,?,?,0)",
                      (mid, "inbox", "Plakzicht Mail", "demo@jouwbedrijf.nl", address, "Mailbox gekoppeld",
                       "<p>Deze mailbox is gekoppeld. In de echte versie komen hier de mails uit Microsoft 365.</p>", _now()))
        return mid

    def remove_mailbox(self, mid):
        with _lock, _conn() as c:
            self._user(c, admin=True)
            c.execute("DELETE FROM mailboxes WHERE id=?", (mid,))
        if self._is_ms():
            CACHE.clear(int(mid))
        return True

    def save_label(self, data):
        name = (data.get("name") or "").strip()
        color = data.get("color") or "#6b726d"
        if not name:
            raise ValueError("Geef het label een naam.")
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Ongeldige kleur.")
        uid = data.get("user_id") or None
        with _lock, _conn() as c:
            self._user(c)  # iedereen mag labels maken
            if data.get("id"):
                self._user(c, admin=True)
                c.execute("UPDATE labels SET name=?, color=?, user_id=? WHERE id=?", (name, color, uid, data["id"]))
                return data["id"]
            return c.execute("INSERT INTO labels(name,color,user_id) VALUES(?,?,?)", (name, color, uid)).lastrowid

    def delete_label(self, lid):
        with _lock, _conn() as c:
            self._user(c, admin=True)
            c.execute("DELETE FROM labels WHERE id=?", (lid,))
        return True

    def save_signature(self, data):
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Geef de handtekening een naam.")
        html = data.get("html") or ""
        if len(html) > 3_000_000:
            raise ValueError("De handtekening is te groot; gebruik een kleinere afbeelding.")
        html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I)
        html = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s>]+)", "", html, flags=re.I)
        mb = int(data["mailbox_id"]) if data.get("mailbox_id") else None
        with _lock, _conn() as c:
            u = self._user(c)
            admin = u["role"] == "beheerder"
            # Beheerder: algemeen of voor een gebruiker. Gebruiker: alleen eigen handtekeningen.
            want = data.get("user_id")
            owner = u["id"] if (not admin or want == "me") else (int(want) if want else None)
            if mb and mb not in self._mb_ids(c, u):
                raise PermissionError("Geen toegang tot die mailbox.")
            if data.get("id"):
                old = c.execute("SELECT user_id FROM signatures WHERE id=?", (int(data["id"]),)).fetchone()
                if not old or (not admin and old["user_id"] != u["id"]):
                    raise PermissionError("Je kunt alleen je eigen handtekeningen wijzigen.")
                c.execute("UPDATE signatures SET name=?, html=?, mailbox_id=?, user_id=? WHERE id=?", (name, html, mb, owner, int(data["id"])))
                return int(data["id"])
            return c.execute("INSERT INTO signatures(name,html,mailbox_id,user_id) VALUES(?,?,?,?)", (name, html, mb, owner)).lastrowid

    def delete_signature(self, sid):
        with _lock, _conn() as c:
            u = self._user(c)
            old = c.execute("SELECT user_id FROM signatures WHERE id=?", (int(sid),)).fetchone()
            if not old or (u["role"] != "beheerder" and old["user_id"] != u["id"]):
                raise PermissionError("Je kunt alleen je eigen handtekeningen verwijderen.")
            c.execute("DELETE FROM signatures WHERE id=?", (int(sid),))
        return True

    def change_password(self, old, new):
        if len(new or "") < 8:
            raise ValueError("Kies een wachtwoord van minstens 8 tekens.")
        with _lock, _conn() as c:
            u = self._user(c)
            row = c.execute("SELECT pw FROM users WHERE id=?", (u["id"],)).fetchone()
            if not _check(old or "", row["pw"]):
                raise PermissionError("Het huidige wachtwoord klopt niet.")
            c.execute("UPDATE users SET pw=? WHERE id=?", (_hash(new), u["id"]))
            # andere apparaten afmelden; dit apparaat blijft ingelogd
            c.execute("DELETE FROM remember WHERE user_id=? AND id IS NOT ?", (u["id"], self._keep_id))
        _drop_sessions(u["id"], keep_api=self)
        return True

    def save_settings(self, data):
        with _lock, _conn() as c:
            self._user(c, admin=True)
            for k in ("order_pattern", "offerte_pattern"):
                try:
                    re.compile(data.get(k) or "")
                except re.error:
                    raise ValueError(f"Patroon voor {'order' if k == 'order_pattern' else 'offerte'} is ongeldig.")
            url = (data.get("plakzicht_url") or "").strip()
            if url and not re.match(r"^https?://", url):
                raise ValueError("Het Plakzicht-adres moet met http:// of https:// beginnen.")
            for k, v in (("order_pattern", data.get("order_pattern")), ("offerte_pattern", data.get("offerte_pattern")),
                         ("plakzicht_url", url)):
                c.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, v or ""))
            if "remember_days" in data:
                self._save_remember(c, data["remember_days"])
            for (mid,) in c.execute("SELECT id FROM mails WHERE link_mode='auto'").fetchall():
                _autolink(c, mid)
        return True

    @staticmethod
    def _save_remember(c, days):
        try:
            days = int(days)
        except (TypeError, ValueError):
            raise ValueError("Vul een aantal dagen in (0 = uit).") from None
        if not 0 <= days <= 365:
            raise ValueError("Ingelogd blijven kan hooguit 365 dagen.")
        c.execute("INSERT OR REPLACE INTO settings VALUES('remember_days', ?)", (str(days),))
        if days == 0:  # uitgezet: niemand blijft nog ingelogd
            c.execute("DELETE FROM remember")

    def save_remember(self, days):
        with _lock, _conn() as c:
            self._user(c, admin=True)
            self._save_remember(c, days)
        return True

    def reset_demo(self):
        if self._is_ms():
            raise RuntimeError("Terugzetten kan alleen in de demo-stand.")
        with _conn() as c:
            self._user(c, admin=True)
        with _lock:
            os.remove(DB)
        init_db()
        self._uid = None
        return True

    # -- opvolgen (vlag met datum), melden, map leegmaken
    @staticmethod
    def _due_for(when):
        """Opvolgdatum zoals in Outlook: vandaag, morgen, deze week, volgende week, of een datum."""
        today = dt.date.today()
        if when == "today":
            return today, today
        if when == "tomorrow":
            d = today + dt.timedelta(days=1)
            return d, d
        if when == "thisweek":
            fri = today + dt.timedelta(days=max(0, 4 - today.weekday()))
            return today, fri
        if when == "nextweek":
            mon = today + dt.timedelta(days=7 - today.weekday())
            return mon, mon + dt.timedelta(days=4)
        if when == "nodate":
            return None, None
        try:
            d = dt.date.fromisoformat(str(when))
        except ValueError:
            raise ValueError("Onbekende opvolgdatum.") from None
        return min(today, d), d

    def set_followup(self, mail_id, when):
        """when: today, tomorrow, thisweek, nextweek, nodate, JJJJ-MM-DD, complete of clear."""
        if when not in ("complete", "clear"):
            start, due = self._due_for(when)
        if not self._is_ms():
            with _lock, _conn() as c:
                u = self._user(c)
                self._mail_ok(c, u, int(mail_id))
                if when == "clear":
                    c.execute("UPDATE mails SET flagged=0, due=NULL, flag_done=0 WHERE id=?", (int(mail_id),))
                elif when == "complete":
                    c.execute("UPDATE mails SET flagged=0, flag_done=1 WHERE id=?", (int(mail_id),))
                else:
                    c.execute("UPDATE mails SET flagged=1, flag_done=0, due=? WHERE id=?", (due.isoformat() if due else None, int(mail_id)))
            return True
        with _conn() as c:
            mb, gid = self._split(c, self._user(c), mail_id)
        if when == "clear":
            flag = {"flagStatus": "notFlagged"}
        elif when == "complete":
            flag = {"flagStatus": "complete"}
        else:
            flag = {"flagStatus": "flagged"}
            if due:
                tz = "W. Europe Standard Time"
                flag["startDateTime"] = {"dateTime": start.isoformat() + "T08:00:00", "timeZone": tz}
                flag["dueDateTime"] = {"dateTime": due.isoformat() + "T17:00:00", "timeZone": tz}
        self._ms_call(lambda: self._ms_for(mb).patch(mb["address"], gid, {"flag": flag}))
        if when == "complete":
            flag["completedDateTime"] = {"dateTime": dt.datetime.now().isoformat(timespec="seconds"), "timeZone": "UTC"}
        CACHE.patch(mb["id"], gid, {"flag": flag})
        return True

    def report_junk(self, mail_id, kind="junk"):
        """Melden als ongewenst of phishing (naar Ongewenste e-mail), of terugzetten naar Postvak IN."""
        dest_demo, dest_ms = ("inbox", "inbox") if kind == "notjunk" else ("junk", "junkemail")
        if not self._is_ms():
            with _conn() as c:
                m = self._mail_ok(c, self._user(c), int(mail_id))
            self._demo_move_mail(int(mail_id), m["mailbox_id"], dest_demo)
            return {"id": str(mail_id)}
        with _conn() as c:
            u = self._user(c)
            mb, gid = self._split(c, u, mail_id)
            new = self._ms_call(lambda: self._ms_for(mb).move(mb["address"], gid, dest_ms))
            CACHE.moved(mb["id"], gid, new)
            self._relink(c, f"{mb['id']}:{gid}", mb["id"], new["id"])
        return {"id": f"{mb['id']}:{new['id']}"}

    def empty_folder(self, mailbox_id, folder_id):
        """Verwijderde items of Ongewenste e-mail leegmaken (definitief)."""
        with _conn() as c:
            u = self._user(c)
            mb = self._mb(c, u, mailbox_id)
            if not self._is_ms():
                if folder_id not in ("deleted", "junk"):
                    raise ValueError("Alleen Verwijderde items en Ongewenste e-mail kun je leegmaken.")
                with _lock:
                    n = c.execute("DELETE FROM mails WHERE mailbox_id=? AND folder=?", (mb["id"], folder_id)).rowcount
                BUS.publish({"t": "mail", "mb": [mb["id"]], "by": u["id"]}, [mb["id"]])
                return n
        f = next((x for x in CACHE.folders(mb["id"]) if x["id"] == folder_id), None)
        if not f or f["wk"] not in ("deleted", "junk"):
            raise ValueError("Alleen Verwijderde items en Ongewenste e-mail kun je leegmaken.")
        ms = self._ms_for(mb)
        items = self._ms_call(lambda: ms.list_since(mb["address"], folder_id, None))
        n = 0
        for m in items[:5000]:
            try:
                ms.delete(mb["address"], m["id"])
                n += 1
            except GraphError as e:
                if e.status != 404:
                    raise RuntimeError(f"{n} mails verwijderd, daarna: " + nl_error(e)) from None
            CACHE.removed(mb["id"], m["id"])
        CACHE.kick(mb["id"], folder_id)
        BUS.publish({"t": "mail", "mb": [mb["id"]], "by": self._uid}, [mb["id"]])
        return n

    # -- toewijzen aan een collega
    def colleagues(self, mail_id):
        """Wie kan bij de mailbox van deze mail (om toe te wijzen)."""
        mb = _mailbox_of_key(str(mail_id)) if self._is_ms() else None
        with _conn() as c:
            u = self._user(c)
            if not self._is_ms():
                mb = self._mail_ok(c, u, int(mail_id))["mailbox_id"]
            rows = _rows(c.execute("SELECT id, name, role FROM users WHERE role='beheerder' OR id IN "
                                   "(SELECT user_id FROM user_mailboxes WHERE mailbox_id=?) ORDER BY name", (mb,)))
        return [{"id": r["id"], "name": r["name"], "me": r["id"] == u["id"]} for r in rows]

    def assign_mail(self, mail_id, user_id):
        """Mail op naam van een collega zetten (zoals 'oppakken', maar voor iemand anders)."""
        key = str(mail_id)
        with _conn() as c:
            u = self._user(c)
            if not any(x["id"] == int(user_id) for x in self.colleagues(mail_id)):
                raise PermissionError("Die collega kan niet bij deze mailbox.")
            who = c.execute("SELECT id, name FROM users WHERE id=?", (int(user_id),)).fetchone()
            cur = c.execute("SELECT user_id, user_name FROM mail_claims WHERE key=?", (key,)).fetchone()
            if cur and cur["user_id"] not in (u["id"], who["id"]) and u["role"] != "beheerder":
                raise RuntimeError(f"{cur['user_name']} heeft deze mail al opgepakt.")
            c.execute("INSERT OR REPLACE INTO mail_claims VALUES(?,?,?,?)", (key, who["id"], who["name"], time.time()))
        log_activity(key, u["id"], u["name"], "toegewezen", "aan " + who["name"])
        mb = _mailbox_of_key(key)
        BUS.publish({"t": "mail", "mb": [mb], "key": key, "by": u["id"]}, [mb])
        if who["id"] != u["id"]:
            subj = ""
            try:
                subj = self._list_subject(key)
            except Exception:  # noqa: BLE001
                pass
            BUS.publish({"t": "assign", "key": key, "mb": [mb], "msg": f"{u['name']} heeft een mail aan je toegewezen: {subj}".strip(": ")},
                        None, only_uid=who["id"])
        return True

    def _list_subject(self, key):
        if not self._is_ms():
            with _conn() as c:
                r = c.execute("SELECT subject FROM mails WHERE id=?", (int(key),)).fetchone()
            return r[0] if r else ""
        mb, _, gid = key.partition(":")
        return (CACHE.get(int(mb), gid)[0] or {}).get("subject") or ""

    # -- adresboek: adressen uit mail en klanten uit Plakzicht
    def address_book(self, q=""):
        q = (q or "").strip().lower()
        found = {}

        def add(name, addr, src, n=1):
            addr = (addr or "").strip().lower()
            if "@" not in addr or (q and q not in addr and q not in (name or "").lower()):
                return
            e = found.setdefault(addr, {"address": addr, "name": "", "source": src, "count": 0})
            e["count"] += n
            if name and not e["name"] and name.lower() != addr:
                e["name"] = name
            if src == "Plakzicht-klant":
                e["source"] = src
        with _conn() as c:
            u = self._user(c)
            ids = self._mb_ids(c, u)
            own = {r[0].lower() for r in c.execute("SELECT address FROM mailboxes")}
            api = pz_api()
            if api:
                if len(q) >= 3:
                    try:
                        j = api.search(q)
                        for x in (j.get("orders") or []) + (j.get("offertes") or []):
                            add(x.get("klant"), x.get("email"), "Plakzicht-klant", 3)
                    except PlakzichtError:
                        pass
            else:
                for r in c.execute("SELECT klant, email FROM pz_orders UNION SELECT klant, email FROM pz_offertes"):
                    add(r[0], r[1], "Plakzicht-klant", 3)
            if self._is_ms():
                if ids:
                    args = list(ids) + (["%" + q + "%"] if q else [])
                    for (data,) in CACHE.conn().execute(
                            f"SELECT data FROM ms_msgs WHERE mailbox_id IN ({','.join('?' * len(ids))})"
                            + (" AND search LIKE ?" if q else "") + " ORDER BY received DESC LIMIT 1500", args):
                        m = json.loads(data)
                        for r in [m.get("from")] + (m.get("toRecipients") or []) + (m.get("ccRecipients") or []):
                            ea = (r or {}).get("emailAddress") or {}
                            add(ea.get("name"), ea.get("address"), "Mail")
            elif ids:
                for r in c.execute(f"SELECT from_name, from_addr, to_addr, cc FROM mails WHERE mailbox_id IN ({','.join('?' * len(ids))})", ids):
                    add(r[0], r[1], "Mail")
                    for a in re.split(r"[;,\s]+", (r[2] or "") + "," + (r[3] or "")):
                        add("", a, "Mail")
        out = [e for a, e in found.items() if a not in own]
        out.sort(key=lambda e: (-e["count"], e["name"] or e["address"]))
        return out[:60]

    # -- snelle stappen
    def _quicksteps(self, c, u):
        rows = _rows(c.execute("SELECT * FROM quicksteps WHERE user_id IS NULL OR user_id=? ORDER BY user_id IS NOT NULL, position, id", (u["id"],)))
        for r in rows:
            r["actions"] = json.loads(r["actions"] or "{}")
            r["shared"] = r["user_id"] is None
        return rows

    def save_quickstep(self, data):
        name = (data.get("name") or "").strip()[:60]
        if not name:
            raise ValueError("Geef de snelle stap een naam.")
        a = data.get("actions") or {}
        clean = {}
        if a.get("read") in (True, False):
            clean["read"] = a["read"]
        if a.get("flag") in ("on", "off", "complete", "today", "tomorrow", "thisweek", "nextweek"):
            clean["flag"] = a["flag"]
        if a.get("claim") in ("claim", "release"):
            clean["claim"] = a["claim"]
        if a.get("labels"):
            clean["labels"] = [int(x) for x in a["labels"]]
        mv = a.get("move") or {}
        if mv.get("folder"):
            clean["move"] = {"mb": int(mv["mb"]) if mv.get("mb") else None, "folder": str(mv["folder"])}
        for k in ("forward_to", "new_to"):
            if k in a:
                clean[k] = str(a[k] or "").strip()[:300]
        if a.get("reply"):
            clean["reply"] = True
        if a.get("text"):
            clean["text"] = str(a["text"])[:20000]
        if not clean:
            raise ValueError("Kies minstens één actie.")
        color = data.get("color") if re.fullmatch(r"#[0-9a-fA-F]{6}", data.get("color") or "") else "#44504a"
        with _lock, _conn() as c:
            u = self._user(c)
            owner = None if (data.get("shared") and u["role"] == "beheerder") else u["id"]
            if data.get("id"):
                r = c.execute("SELECT user_id FROM quicksteps WHERE id=?", (int(data["id"]),)).fetchone()
                if not r or (r[0] != u["id"] and u["role"] != "beheerder"):
                    raise PermissionError("Je kunt alleen je eigen snelle stappen wijzigen.")
                c.execute("UPDATE quicksteps SET name=?, color=?, actions=?, user_id=? WHERE id=?",
                          (name, color, json.dumps(clean), owner, int(data["id"])))
                return int(data["id"])
            pos = c.execute("SELECT COALESCE(MAX(position),0)+1 FROM quicksteps").fetchone()[0]
            return c.execute("INSERT INTO quicksteps(user_id,name,color,actions,position) VALUES(?,?,?,?,?)",
                             (owner, name, color, json.dumps(clean), pos)).lastrowid

    def delete_quickstep(self, qid):
        with _lock, _conn() as c:
            u = self._user(c)
            r = c.execute("SELECT user_id FROM quicksteps WHERE id=?", (int(qid),)).fetchone()
            if not r or (r[0] != u["id"] and u["role"] != "beheerder"):
                raise PermissionError("Je kunt alleen je eigen snelle stappen verwijderen.")
            c.execute("DELETE FROM quicksteps WHERE id=?", (int(qid),))
        return True

    # -- Claude
    def _claude_key(self):
        try:
            return _unprotect(CFG.get("claude_key") or "")
        except Exception:  # noqa: BLE001
            return ""

    def _claude_status(self, c, u):
        used = c.execute("SELECT COUNT(*) FROM claude_usage WHERE user_id=? AND ok=1 AND feature<>'test' AND at>=?",
                         (u["id"], _month_start())).fetchone()[0]
        return {"configured": bool(CFG.get("claude_key")), "on": bool(u.get("claude_on")),
                "used": used, "limit": u.get("claude_limit") or 0}

    def claude_admin(self):
        with _conn() as c:
            self._user(c, admin=True)
            ms = _month_start()
            users = _rows(c.execute(
                "SELECT u.id, u.name, u.claude_on, u.claude_limit, COUNT(cu.id) AS req, COALESCE(SUM(cu.in_tok),0) AS tin, "
                "COALESCE(SUM(cu.out_tok),0) AS tout FROM users u LEFT JOIN claude_usage cu ON cu.user_id=u.id AND cu.ok=1 AND cu.feature<>'test' AND cu.at>=? "
                "GROUP BY u.id ORDER BY u.name", (ms,)))
        key = self._claude_key()
        return {"configured": bool(key), "hint": ("…" + key[-4:]) if key else "", "model": CFG.get("claude_model") or CLAUDE_MODELS[0][0],
                "models": CLAUDE_MODELS, "price_in": CFG.get("claude_price_in") or "", "price_out": CFG.get("claude_price_out") or "",
                "users": users, "protected": _is_protected(CFG.get("claude_key"))}

    def save_claude_config(self, data):
        with _conn() as c:
            self._user(c, admin=True)
        with _cfg_lock:
            key = (data.get("key") or "").strip()
            if data.get("remove"):
                CFG.pop("claude_key", None)
            elif key:
                if not key.startswith("sk-"):
                    raise ValueError("Dit lijkt geen Anthropic API-sleutel (die begint met sk-ant-).")
                CFG["claude_key"] = _protect(key)
            model = (data.get("model") or "").strip()
            if model:
                if not re.fullmatch(r"[a-z0-9.\-]{3,80}", model):
                    raise ValueError("Ongeldige modelnaam.")
                CFG["claude_model"] = model
            for k in ("price_in", "price_out"):
                v = str(data.get(k) or "").replace(",", ".").strip()
                if v:
                    try:
                        float(v)
                    except ValueError:
                        raise ValueError("Prijs moet een getal zijn (dollar per miljoen tokens).") from None
                CFG["claude_" + k] = v
            save_config(CFG)
        return self.claude_admin()

    def set_user_claude(self, uid, on, limit=None):
        with _lock, _conn() as c:
            self._user(c, admin=True)
            lim = max(0, min(100000, int(limit))) if limit not in (None, "") else 200
            c.execute("UPDATE users SET claude_on=?, claude_limit=? WHERE id=?", (1 if on else 0, lim, int(uid)))
        return True

    def claude_test(self):
        with _conn() as c:
            self._user(c, admin=True)
        text, _ = self._claude_call("Antwoord met precies één woord.", "Zeg: werkt", 20, feature="test")
        return f"Verbinding met Claude werkt (model {CFG.get('claude_model') or CLAUDE_MODELS[0][0]}). Antwoord: {text.strip()[:60]}"

    def _claude_call(self, system, prompt, max_tokens=1200, feature="?", user=None):
        key = self._claude_key()
        if not key:
            raise RuntimeError("Claude is nog niet ingesteld. De beheerder vult de API-sleutel in onder Beheer › Claude.")
        body = json.dumps({"model": CFG.get("claude_model") or CLAUDE_MODELS[0][0], "max_tokens": max_tokens,
                           "system": system, "messages": [{"role": "user", "content": prompt}]}).encode()
        rq = urllib.request.Request(CLAUDE_URL, data=body, method="POST", headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        uid = (user or {}).get("id") or self._uid
        try:
            with urllib.request.urlopen(rq, timeout=90) as r:
                j = json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read()).get("error", {}).get("message", "")
            except Exception:  # noqa: BLE001
                msg = ""
            self._claude_log(uid, feature, 0, 0, 0)
            nl = {401: "De API-sleutel voor Claude klopt niet of is ingetrokken.",
                  403: "Deze API-sleutel mag dit niet (controleer de rechten in de Anthropic Console).",
                  404: "Het gekozen Claude-model bestaat niet (meer). Kies een ander model onder Beheer › Claude.",
                  429: "Even te veel verzoeken aan Claude. Probeer het over een minuut opnieuw.",
                  529: "Claude is op dit moment erg druk. Probeer het zo opnieuw."}.get(e.code)
            if e.code == 400 and "credit" in msg.lower():
                nl = "Het tegoed van het Anthropic-account is op. Vul het aan in de Anthropic Console."
            raise RuntimeError(nl or f"Claude gaf een fout ({e.code}): {msg[:200]}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise RuntimeError(f"Claude is niet bereikbaar vanaf de server ({getattr(e, 'reason', e)}).") from None
        text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
        us = j.get("usage") or {}
        self._claude_log(uid, feature, us.get("input_tokens", 0), us.get("output_tokens", 0), 1)
        return text, us

    def _claude_log(self, uid, feature, tin, tout, ok):
        try:
            with _lock, _conn() as c:
                c.execute("INSERT INTO claude_usage(user_id,at,feature,in_tok,out_tok,ok) VALUES(?,?,?,?,?,?)",
                          (uid, time.time(), feature, tin, tout, ok))
        except sqlite3.Error:
            pass

    def claude_run(self, feature, mail_id=None, extra=None):
        """Claude-functies: summary, reply, translate, suggest, extract, improve. Alleen de gevraagde mail gaat naar Claude."""
        extra = extra or {}
        with _conn() as c:
            u = self._user(c)
            st = self._claude_status(c, u)
        if not st["configured"]:
            raise RuntimeError("Claude is nog niet ingesteld. De beheerder vult de API-sleutel in onder Beheer › Claude.")
        if not u.get("claude_on"):
            raise PermissionError("Claude staat voor jou nog niet aan. Vraag de beheerder (Beheer › Claude).")
        if st["limit"] and st["used"] >= st["limit"]:
            raise RuntimeError(f"Je maandlimiet voor Claude ({st['limit']} verzoeken) is bereikt. Vraag de beheerder om de limiet te verhogen.")
        cp = u["prefs"]["claude"]
        m = self._get_raw(mail_id) if mail_id else None
        mailtxt = ""
        if m:
            mailtxt = (f"Van: {m.get('from_name')} <{m.get('from_addr')}>\nAan: {m.get('to_addr')}\n"
                       + (f"CC: {m.get('cc')}\n" if m.get("cc") else "")
                       + f"Datum: {m.get('date')}\nOnderwerp: {m.get('subject')}\n\n{_text(m.get('body') or '')[:12000]}")
        base = ("Je bent een assistent in het mailprogramma van een stickerbedrijf (Plakzicht Mail). "
                "Antwoord in het Nederlands tenzij anders gevraagd. Verzin geen feiten, prijzen of datums die niet in de gegevens staan.")
        if feature == "summary":
            text, _ = self._claude_call(base, "Vat deze e-mail samen in maximaal 4 korte regels die elk met '- ' beginnen. "
                                        "Noem wat de afzender wil, eventuele vragen, nummers en deadlines.\n\n" + mailtxt, 500, "samenvatten", u)
            return {"html": _lines_html(text)}
        if feature == "reply":
            pz = (m or {}).get("plakzicht") or {}
            if pz.get("pending"):
                with _conn() as c:
                    pz = self._pz_for(c, m)
            ctx = []
            if pz.get("order"):
                o = pz["order"]
                stp = ", ".join(f"{x['naam']}: {x['status']}" for x in o.get("productie") or [])
                ver = o.get("verzending") or {}
                ctx.append(f"Order {o['nr']} voor {o['klant']}: {o.get('omschrijving') or ''}; status in de webshop: {o.get('status') or 'onbekend'}; "
                           f"uiterlijk verzenden {o.get('due') or 'onbekend'}; leverdatum {o.get('leverdatum') or 'onbekend'}; "
                           f"drukproef: {(o.get('proof') or {}).get('tekst') or 'geen'}; productie: {stp or 'nog niet gepland'}"
                           + (f"; on hold: {o['on_hold']['status']}" if o.get("on_hold") else "")
                           + (f"; verzending: {ver.get('status') or ver.get('stand')}" + (f", track & trace {ver['track_url']}" if ver.get("track_url") else "") if ver else "") + ".")
            if pz.get("offerte"):
                o = pz["offerte"]
                ctx.append(f"Offerte {o['nr']} voor {o['klant']}: {o.get('omschrijving') or ''}, status {o.get('status') or 'onbekend'}"
                           + (f", geldig tot {o['geldig_tot']}" if o.get("geldig_tot") else "") + ".")
            if pz.get("klant") and not ctx:
                ctx.append(f"Afzender is klant in Plakzicht: {pz['klant']['naam']}.")
            tone = {"zakelijk": "zakelijk en vriendelijk", "formeel": "formeel", "informeel": "informeel en hartelijk", "kort": "zo kort mogelijk"}[cp["tone"]]
            lang = "in dezelfde taal als de mail" if cp["lang"] == "mail" else "in het Nederlands"
            prompt = (f"Schrijf een antwoord op deze e-mail namens {u['name']}. Toon: {tone}; spreek de lezer aan met '{cp['aanhef']}'. Schrijf {lang}. "
                      "Geef alleen de tekst van het antwoord (aanhef, inhoud en groet), zonder onderwerp en zonder handtekening met contactgegevens. "
                      "Scheid alinea's met een lege regel. Als informatie ontbreekt, schrijf dan [aanvullen] op die plek.\n"
                      + (f"Extra aanwijzingen van de gebruiker: {cp['extra']}\n" if cp.get("extra") else "")
                      + (f"Wat het antwoord moet zeggen: {extra.get('instructions')}\n" if extra.get("instructions") else "")
                      + ("\nGegevens uit Plakzicht:\n" + "\n".join(ctx) + "\n" if ctx else "\n(Geen order of offerte gekoppeld.)\n")
                      + "\nDe e-mail:\n" + mailtxt)
            text, _ = self._claude_call(base, prompt, 1200, "antwoord", u)
            return {"html": _paras_html(text)}
        if feature == "translate":
            lang = extra.get("lang") or "Nederlands"
            src = extra.get("text") or mailtxt
            if not src.strip():
                raise ValueError("Er is geen tekst om te vertalen.")
            text, _ = self._claude_call(base, f"Vertaal de volgende tekst naar het {lang}. Geef alleen de vertaling, behoud alinea's "
                                        "(gescheiden door een lege regel).\n\n" + src[:15000], 3000, "vertalen", u)
            return {"html": _paras_html(text), "lang": lang}
        if feature == "improve":
            how = {"verbeter": "Verbeter spelling, grammatica en zinsbouw; houd de betekenis en toon gelijk.",
                   "korter": "Maak de tekst korter en duidelijker; houd alle inhoud die ertoe doet.",
                   "formeler": "Maak de toon formeler.", "vriendelijker": "Maak de toon vriendelijker en persoonlijker."}.get(extra.get("how"), "Verbeter de tekst.")
            src = extra.get("text") or ""
            if not src.strip():
                raise ValueError("Schrijf eerst wat tekst.")
            text, _ = self._claude_call(base, how + " Geef alleen de nieuwe tekst, alinea's gescheiden door een lege regel.\n\n" + src[:15000], 2000, "verbeteren", u)
            return {"html": _paras_html(text)}
        if feature == "suggest":
            with _conn() as c:
                labs = _rows(c.execute("SELECT id, name, color FROM labels ORDER BY name"))
                mb = self._mb(c, u, m["mailbox_id"])
                fl = self._folders(c, mb)
            folders = [f for f in fl if f["wk"] not in ("deleted", "junk", "drafts", "sent")]
            fpath = {}
            byid = {f["id"]: f for f in fl}
            for f in folders:
                parts, p = [f["name"]], f["parent"]
                while p and p in byid:
                    parts.insert(0, byid[p]["name"]); p = byid[p]["parent"]
                fpath[" / ".join(parts)] = f["id"]
            prompt = ("Kies voor deze e-mail de passende labels en de beste map. Antwoord alleen met JSON in de vorm "
                      '{"labels": ["naam"], "map": "pad of leeg", "reden": "één korte zin"}.\n'
                      f"Beschikbare labels: {json.dumps([l['name'] for l in labs], ensure_ascii=False)}\n"
                      f"Beschikbare mappen: {json.dumps(list(fpath), ensure_ascii=False)}\n\nDe e-mail:\n" + mailtxt)
            text, _ = self._claude_call(base, prompt, 400, "voorstellen", u)
            j = _json_from(text)
            names = {l["name"].lower(): l for l in labs}
            out_l = [names[x.lower()] for x in j.get("labels") or [] if isinstance(x, str) and x.lower() in names]
            fid = fpath.get(j.get("map") or "")
            return {"labels": out_l, "folder": {"mb": mb["id"], "id": fid, "name": j.get("map")} if fid else None,
                    "reason": str(j.get("reden") or "")[:300]}
        if feature == "extract":
            prompt = ("Haal uit deze e-mail de gegevens voor een offerte-aanvraag van een stickerbedrijf. Antwoord alleen met JSON: "
                      '{"Klant/bedrijf": "", "Contactpersoon": "", "E-mail": "", "Telefoon": "", "Product": "", "Aantal": "", '
                      '"Afmeting": "", "Materiaal/afwerking": "", "Gewenste leverdatum": "", "Afleveradres": "", "Opmerkingen": ""}. '
                      "Laat een waarde leeg als het niet in de mail staat.\n\nDe e-mail:\n" + mailtxt)
            text, _ = self._claude_call(base, prompt, 700, "gegevens", u)
            j = _json_from(text)
            return {"fields": [[k, str(v)] for k, v in j.items() if v not in (None, "")]}
        raise ValueError("Onbekende Claude-functie.")

    # -- agenda (van de aangemelde Microsoft-accounts; in de demo nagebootst)
    def _cal_accounts(self, c, u):
        """Agenda's die deze gebruiker mag zien: van accounts waarvan hij de eigen mailbox mag openen (beheerder: alle)."""
        if CFG["auth"] != "user":
            return []
        mine = set(self._mb_ids(c, u))
        out = []
        for a in CFG["accounts"]:
            addrs = {x.lower() for x in (a.get("mail"), a.get("upn")) if x}
            rows = c.execute("SELECT id, address, graph_id FROM mailboxes").fetchall()
            own = [r[0] for r in rows if (a.get("oid") and r[2] == a.get("oid")) or r[1].lower() in addrs]
            if u["role"] == "beheerder" or any(mid in mine for mid in own):
                out.append(a)
        return out

    def _cal_client(self, c, u, aid):
        acct = next((a for a in self._cal_accounts(c, u) if a["id"] == aid), None)
        if not acct:
            raise PermissionError("Geen toegang tot deze agenda.")
        return MsCalendar(client_for_account(aid).g)

    @staticmethod
    def _cal_err(e, acct_name=""):
        if isinstance(e, GraphError) and e.status in (401, 403):
            return (f"Agenda van {acct_name} niet beschikbaar: het account heeft nog geen toestemming voor de agenda. "
                    "Zet in Beheer › Microsoft-koppeling de agenda aan en meld het account opnieuw aan.")
        return nl_error(e) if isinstance(e, GraphError) else str(e)

    def cal_info(self):
        with _conn() as c:
            u = self._user(c)
            if not self._is_ms():
                return {"mode": "demo", "calendars": [{"id": "demo|1", "name": "Agenda (demo)", "color": "#1f6fb2", "account": "Demo", "can_edit": True, "default": True}],
                        "errors": [], "enabled": True}
            accts = self._cal_accounts(c, u)
        if not CFG.get("calendar"):
            return {"mode": "microsoft", "calendars": [], "errors": [], "enabled": False, "no_accounts": False}
        cals, errors = [], []
        palette = ["#1f6fb2", "#1f6f54", "#a15c00", "#6a3fa0", "#b3261e", "#0f766e", "#44504a"]
        for i, a in enumerate(accts):
            try:
                for j, k in enumerate(MsCalendar(client_for_account(a["id"]).g).calendars()):
                    col = k.get("hexColor") or palette[(i * 2 + j) % len(palette)]
                    cals.append({"id": f"{a['id']}|{k['id']}", "name": k.get("name") or "Agenda", "color": col, "account": a.get("name") or a["upn"],
                                 "upn": a["upn"], "can_edit": bool(k.get("canEdit", True)), "default": bool(k.get("isDefaultCalendar"))})
            except (GraphError, RuntimeError) as e:
                errors.append({"account": a.get("name") or a["upn"], "error": self._cal_err(e, a.get("name") or a["upn"])})
        return {"mode": "microsoft", "calendars": cals, "errors": errors, "enabled": bool(CFG.get("calendar")),
                "no_accounts": not accts}

    @staticmethod
    def _ev_time(t):
        return ((t or {}).get("dateTime") or "")[:16]

    def _ev_out(self, c, aid_cal, e, color=None):
        org = ((e.get("organizer") or {}).get("emailAddress") or {})
        text = (e.get("subject") or "") + "\n" + (e.get("bodyPreview") or "") + "\n" + _text(((e.get("body") or {}).get("content")) or "")
        d = _detect(c, e.get("subject"), text)
        out = {"id": f"{aid_cal.split('|')[0]}|{e['id']}", "cal": aid_cal, "subject": e.get("subject") or "(geen onderwerp)",
               "start": self._ev_time(e.get("start")), "end": self._ev_time(e.get("end")), "allday": bool(e.get("isAllDay")),
               "location": ((e.get("location") or {}).get("displayName")) or "", "organizer": org.get("name") or org.get("address") or "",
               "is_organizer": bool(e.get("isOrganizer", True)), "attendees": [((x.get("emailAddress") or {}).get("address") or "") for x in e.get("attendees") or []],
               "preview": (e.get("bodyPreview") or "")[:200], "web": e.get("webLink") or "", "show_as": e.get("showAs") or "busy",
               "recurring": e.get("type") in ("occurrence", "exception"), "cancelled": bool(e.get("isCancelled")),
               "reminder": e.get("reminderMinutesBeforeStart") if e.get("isReminderOn") else None,
               "online": ((e.get("onlineMeeting") or {}).get("joinUrl")) or "", "order_nr": d["order_nr"], "offerte_nr": d["offerte_nr"]}
        if "body" in e:
            out["body"] = (e.get("body") or {}).get("content") or ""
        return out

    def cal_events(self, start, end, cal_ids):
        """Afspraken tussen start en end (JJJJ-MM-DDTUU:MM, Nederlandse tijd) in de gekozen agenda's."""
        with _conn() as c:
            u = self._user(c)
            if not self._is_ms():
                rows = _rows(c.execute("SELECT * FROM demo_events WHERE start < ? AND end > ? ORDER BY start", (end, start)))
                out = []
                for r in rows:
                    d = _detect(c, r["subject"], r["body"])
                    out.append({"id": f"demo|{r['id']}", "cal": "demo|1", "subject": r["subject"], "start": r["start"], "end": r["end"],
                                "allday": bool(r["allday"]), "location": r["location"] or "", "organizer": r["organizer"] or u["name"], "is_organizer": True,
                                "attendees": [x for x in (r["attendees"] or "").split(",") if x], "preview": _text(r["body"] or "")[:200], "web": "",
                                "show_as": r["show_as"] or "busy", "recurring": False, "cancelled": False, "reminder": r["reminder"], "online": "",
                                "order_nr": d["order_nr"], "offerte_nr": d["offerte_nr"]})
                return {"events": out, "errors": []}
            allowed = {a["id"] for a in self._cal_accounts(c, u)}
        events, errors = [], []
        for cid in cal_ids or []:
            aid, _, kid = str(cid).partition("|")
            if aid not in allowed:
                continue
            try:
                items = MsCalendar(client_for_account(aid).g).view(kid, start + ":00", end + ":00")
                with _conn() as c:
                    events += [self._ev_out(c, cid, e) for e in items if not e.get("isCancelled")]
            except (GraphError, RuntimeError) as e:
                errors.append(self._cal_err(e))
        return {"events": events, "errors": errors}

    def cal_event(self, eid):
        with _conn() as c:
            u = self._user(c)
            aid, _, gid = str(eid).partition("|")
            if not self._is_ms():
                r = c.execute("SELECT * FROM demo_events WHERE id=?", (int(gid),)).fetchone()
                if not r:
                    raise Gone("Deze afspraak bestaat niet meer.")
                ev = self.cal_events(r["start"], r["end"], ["demo|1"])["events"]
                out = next((x for x in ev if x["id"] == eid), None) or {}
                out["body"] = r["body"] or ""
                return out
            cal = self._cal_client(c, u, aid)
        e = self._ms_call(lambda: cal.get(gid))
        with _conn() as c:
            return self._ev_out(c, f"{aid}|?", e)

    def cal_save(self, data):
        """Afspraak maken of wijzigen. data: id?, cal, subject, start, end, allday, location, body (html), attendees, reminder, show_as, order_nr."""
        subject = (data.get("subject") or "").strip() or "(geen onderwerp)"
        start, end, allday = data.get("start") or "", data.get("end") or "", bool(data.get("allday"))
        try:
            s_dt, e_dt = dt.datetime.fromisoformat(start), dt.datetime.fromisoformat(end)
        except ValueError:
            raise ValueError("Begin- en eindtijd kloppen niet.") from None
        if allday:
            s_dt = s_dt.replace(hour=0, minute=0)
            e_dt = e_dt.replace(hour=0, minute=0)
            if e_dt <= s_dt:
                e_dt = s_dt + dt.timedelta(days=1)
        if e_dt <= s_dt:
            raise ValueError("Het einde moet na het begin liggen.")
        body = data.get("body") or ""
        order = (data.get("order_nr") or "").strip().upper()
        if order and order not in _text(body).upper() and order not in subject.upper():
            body += f"<p>Plakzicht: {'order' if order.isdigit() else 'offerte'} {html.escape(order)}</p>"
        attendees = [a.strip() for a in re.split(r"[;,\s]+", data.get("attendees") or "") if "@" in a]
        reminder = data.get("reminder")
        reminder = int(reminder) if str(reminder or "").lstrip("-").isdigit() and int(reminder) >= 0 else None
        show_as = data.get("show_as") if data.get("show_as") in ("free", "tentative", "busy", "oof", "workingElsewhere") else "busy"
        fmt = lambda x: x.strftime("%Y-%m-%dT%H:%M")
        with _lock, _conn() as c:
            u = self._user(c)
            if not self._is_ms():
                vals = (subject, fmt(s_dt), fmt(e_dt), 1 if allday else 0, (data.get("location") or "").strip(), body, ",".join(attendees), reminder, show_as)
                if data.get("id"):
                    c.execute("UPDATE demo_events SET subject=?,start=?,end=?,allday=?,location=?,body=?,attendees=?,reminder=?,show_as=? WHERE id=?",
                              (*vals, int(str(data["id"]).partition("|")[2])))
                    return data["id"]
                return "demo|" + str(c.execute("INSERT INTO demo_events(subject,start,end,allday,location,body,attendees,reminder,show_as,organizer) "
                                               "VALUES(?,?,?,?,?,?,?,?,?,?)", (*vals, u["name"])).lastrowid)
        ev = {"subject": subject, "isAllDay": allday,
              "start": {"dateTime": fmt(s_dt) + ":00", "timeZone": CAL_TZ}, "end": {"dateTime": fmt(e_dt) + ":00", "timeZone": CAL_TZ},
              "location": {"displayName": (data.get("location") or "").strip()}, "body": {"contentType": "HTML", "content": body},
              "attendees": [{"emailAddress": {"address": a}, "type": "required"} for a in attendees], "showAs": show_as,
              "isReminderOn": reminder is not None}
        if reminder is not None:
            ev["reminderMinutesBeforeStart"] = reminder
        with _conn() as c:
            u = self._user(c)
            if data.get("id"):
                aid, _, gid = str(data["id"]).partition("|")
                cal = self._cal_client(c, u, aid)
                self._ms_call(lambda: cal.update(gid, ev))
                return data["id"]
            aid, _, kid = str(data.get("cal") or "").partition("|")
            cal = self._cal_client(c, u, aid)
        try:
            new = cal.create(kid, ev)
        except GraphError as e:
            raise RuntimeError(self._cal_err(e)) from None
        return f"{aid}|{new['id']}"

    def cal_delete(self, eid):
        aid, _, gid = str(eid).partition("|")
        with _lock, _conn() as c:
            u = self._user(c)
            if not self._is_ms():
                c.execute("DELETE FROM demo_events WHERE id=?", (int(gid),))
                return True
            cal = self._cal_client(c, u, aid)
        self._ms_call(lambda: cal.delete(gid))
        return True

    def cal_orders(self, start, end):
        """Plakzicht-laag: verzenddatums van orders in deze periode."""
        with _conn() as c:
            self._user(c)
            api = pz_api()
            if api:
                try:
                    return [{"nr": o["nummer"], "klant": o.get("klant") or "", "due": o["uiterlijk_verzenden"], "status": o.get("status")}
                            for o in api.ship_dates(start[:10], end[:10]) if not o.get("verzonden")]
                except PlakzichtError:
                    return []
            return _rows(c.execute("SELECT nr, klant, due, materiaal, proof FROM pz_orders WHERE due >= ? AND due < ? ORDER BY due",
                                   (start[:10], end[:10])))

    # -- koppeling met Plakzicht (beheer)
    def plakzicht_config(self):
        with _conn() as c:
            self._user(c, admin=True)
        p = CFG.get("plakzicht") or {}
        return {"url": p.get("url") or "", "open": p.get("open") or "", "has_key": bool(p.get("key")), "mode": CFG["mode"],
                "live": bool(pz_api()), "protected": _is_protected(p.get("key"))}

    def save_plakzicht_config(self, data):
        with _conn() as c:
            self._user(c, admin=True)
        url = (data.get("url") or "").strip().rstrip("/")
        opn = (data.get("open") or "").strip().rstrip("/")
        for u in (url, opn):
            if u and not re.match(r"^https?://[^\s/]+", u):
                raise ValueError("Een adres begint met http:// of https://, bijvoorbeeld http://192.168.1.10:5000.")
        with _cfg_lock:
            p = dict(CFG.get("plakzicht") or {})
            p.update({"url": url, "open": opn})
            if data.get("remove"):
                p.pop("key", None)
            elif (data.get("key") or "").strip():
                p["key"] = _protect(data["key"].strip())
            CFG["plakzicht"] = p
            save_config(CFG)
        _PZ["sig"] = None
        return self.plakzicht_config()

    def plakzicht_test(self):
        with _conn() as c:
            self._user(c, admin=True)
        p = CFG.get("plakzicht") or {}
        if not p.get("url") or not p.get("key"):
            raise ValueError("Vul eerst het adres en de API-sleutel in en klik op Opslaan.")
        api = PlakzichtApi(p["url"], _unprotect(p["key"]))
        try:
            st = api.status()
        except PlakzichtError as e:
            raise RuntimeError(str(e)) from None
        note = "" if CFG["mode"] == "microsoft" else " Let op: in de demo-stand blijft de nagebootste Plakzicht in gebruik; na overschakelen naar Microsoft 365 wordt de echte gebruikt."
        return (f"Verbonden met {st.get('programma', 'Plakzicht')} (versie {st.get('versie', '?')}): "
                f"{st.get('orders', 0)} orders en {st.get('offertes', 0)} offertes beschikbaar.{note}")

    def set_calendar_enabled(self, on):
        with _conn() as c:
            self._user(c, admin=True)
        with _cfg_lock:
            CFG["calendar"] = bool(on)
            save_config(CFG)
        return self.ms_config()


# ---------------------------------------------------------------- samenwerken: live bijwerken, aanwezigheid, oppakken, logboek
class Gone(RuntimeError):
    """De mail bestaat niet (meer) op deze plek: intussen verplaatst of verwijderd."""


class Bus:
    """Stuurt wijzigingen direct naar alle open schermen (Server-Sent Events)."""

    def __init__(self):
        self.subs = {}
        self.lock = threading.Lock()
        self._allowed = {}

    def subscribe(self, uid):
        import queue
        q = queue.Queue(maxsize=1000)
        with self.lock:
            self.subs[id(q)] = (q, uid)
        return q

    def unsubscribe(self, q):
        with self.lock:
            self.subs.pop(id(q), None)

    def _mailboxes_of(self, uid):
        hit = self._allowed.get(uid)
        if hit and time.time() - hit[0] < 30:
            return hit[1]
        try:
            with _conn() as c:
                u = c.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
                if not u:
                    ids = set()
                elif u["role"] == "beheerder":
                    ids = {r[0] for r in c.execute("SELECT id FROM mailboxes")}
                else:
                    ids = {r[0] for r in c.execute("SELECT mailbox_id FROM user_mailboxes WHERE user_id=?", (uid,))}
        except sqlite3.Error:
            ids = set()
        self._allowed[uid] = (time.time(), ids)
        return ids

    def publish(self, ev, mailbox_ids=None, only_uid=None):
        mbs = {int(m) for m in (mailbox_ids or []) if m is not None}
        with self.lock:
            subs = list(self.subs.values())
        for q, uid in subs:
            if only_uid is not None and uid != only_uid:
                continue
            if mbs and not (mbs & self._mailboxes_of(uid)):
                continue
            try:
                q.put_nowait(ev)
            except Exception:  # noqa: BLE001 - volle wachtrij: scherm haalt bij de volgende melding alles opnieuw op
                pass


BUS = Bus()
PRESENCE = {}             # mail-sleutel -> {user_id: {"name", "state", "t", "mb"}}
PRESENCE_TTL = 50
_plock = threading.Lock()


def _mailbox_of_key(key):
    key = str(key)
    if ":" in key:
        return int(key.split(":", 1)[0])
    try:
        with _conn() as c:
            r = c.execute("SELECT mailbox_id FROM mails WHERE id=?", (int(key),)).fetchone()
        return r[0] if r else None
    except (sqlite3.Error, ValueError):
        return None


def log_activity(key, uid, name, action, detail=""):
    with _conn() as c:
        c.execute("INSERT INTO mail_activity(key,user_id,user_name,action,detail,at) VALUES(?,?,?,?,?,?)",
                  (str(key), uid, name, action, detail, time.time()))


def rekey(old, new):
    """Microsoft geeft een mail soms een nieuw ID (verplaatsen tussen mailboxen): logboek en oppakken meenemen."""
    if str(old) == str(new):
        return
    with _conn() as c:
        c.execute("UPDATE mail_activity SET key=? WHERE key=?", (str(new), str(old)))
        c.execute("UPDATE OR IGNORE mail_claims SET key=? WHERE key=?", (str(new), str(old)))
    with _plock:
        if str(old) in PRESENCE:
            PRESENCE[str(new)] = PRESENCE.pop(str(old))


def presence_of(keys, exclude_uid=None):
    now = time.time()
    out = {}
    with _plock:
        for k in keys:
            who = PRESENCE.get(str(k)) or {}
            for uid in [u for u, v in who.items() if now - v["t"] > PRESENCE_TTL]:
                who.pop(uid, None)
            lst = [{"name": v["name"], "state": v["state"]} for u, v in who.items() if u != exclude_uid]
            if lst:
                out[str(k)] = lst
    return out


def collab_info(c, keys, me):
    """Per mail: wie heeft hem opgepakt, wie heeft beantwoord, wie kijkt nu."""
    keys = [str(k) for k in keys]
    out = {k: {} for k in keys}
    if not keys:
        return out
    for i in range(0, len(keys), 500):
        part = keys[i:i + 500]
        q = ",".join("?" * len(part))
        for r in c.execute(f"SELECT key, user_id, user_name, at FROM mail_claims WHERE key IN ({q})", part):
            out[r[0]]["claim"] = {"name": r[2], "mine": r[1] == me, "at": r[3]}
        for r in c.execute(f"SELECT key, user_name, action, MAX(at) FROM mail_activity WHERE key IN ({q}) "
                           f"AND action IN ('beantwoord','doorgestuurd') GROUP BY key", part):
            out[r[0]]["replied"] = {"name": r[1], "action": r[2], "at": r[3]}
    for k, lst in presence_of(keys, exclude_uid=me).items():
        out[k]["busy"] = lst
    return out


def gone_message(key, me):
    """Uitleg als een mail er niet meer is: door wie en waarheen (uit het logboek)."""
    try:
        with _conn() as c:
            r = c.execute("SELECT user_id, user_name, action, detail, at FROM mail_activity WHERE key=? ORDER BY at DESC LIMIT 1",
                          (str(key),)).fetchone()
            job = c.execute("SELECT user_name FROM move_jobs WHERE key=? AND status IN ('wacht','bezig')", (str(key),)).fetchone()
    except sqlite3.Error:
        r = job = None
    if job:
        return f"Deze mail wordt al verplaatst door {job[0]}. De lijst is bijgewerkt."
    if r and r[0] != me and r[2] in ("verplaatst", "gearchiveerd", "verwijderd"):
        t = dt.datetime.fromtimestamp(r[4]).strftime("%H:%M")
        return f"Deze mail is intussen al {r[2]} door {r[1]}{(' ' + r[3]) if r[3] else ''} ({t}). De lijst is bijgewerkt."
    return "Deze mail is intussen verplaatst of verwijderd (misschien door een collega of in Outlook). De lijst is bijgewerkt."


# Welke acties gelogd en doorgegeven worden
def _track(action_name, log_action, detail_fn=None):
    orig = getattr(Api, action_name)

    def wrapper(self, mail_id, *args):
        key = str(mail_id)
        src = _mailbox_of_key(key)
        try:
            result = orig(self, mail_id, *args)
        except Gone:
            raise Gone(gone_message(key, self._uid)) from None
        except GraphError as e:
            if e.status == 404:
                raise Gone(gone_message(key, self._uid)) from None
            raise
        except (RuntimeError, PermissionError) as e:
            if "intussen" in str(e) or "Niet gevonden bij Microsoft" in str(e) or str(e) == "Geen toegang tot deze mail.":
                if src is None or "Niet gevonden" in str(e):
                    raise Gone(gone_message(key, self._uid)) from None
            raise
        new_key = result["id"] if isinstance(result, dict) and result.get("id") else key
        if isinstance(result, dict) and result.get("queued"):
            new_key = key
        rekey(key, new_key)
        mbs = {src}
        if action_name == "move_mail" and args:
            mbs.add(int(args[0]))
        if log_action and self._uid:
            try:
                with _conn() as c:
                    u = c.execute("SELECT name FROM users WHERE id=?", (self._uid,)).fetchone()
                    detail = detail_fn(self, c, args, result) if detail_fn else ""
                if not (isinstance(result, dict) and result.get("queued")):
                    log_activity(new_key, self._uid, u[0] if u else "?", log_action, detail)
            except Exception:  # noqa: BLE001 - logboek mag een actie nooit laten mislukken
                pass
        BUS.publish({"t": "mail", "mb": sorted(m for m in mbs if m), "key": key, "new": new_key, "by": self._uid}, mbs)
        return result
    wrapper.__name__ = action_name
    wrapper.__doc__ = orig.__doc__
    setattr(Api, action_name, wrapper)


def _detail_move(self, c, args, result):
    mb = c.execute("SELECT display FROM mailboxes WHERE id=?", (int(args[0]),)).fetchone()
    folder = args[1] if len(args) > 1 else "inbox"
    fname = folder
    try:
        f = next((x for x in (CACHE.folders(int(args[0])) if CFG["mode"] == "microsoft" else _demo_folders(c, int(args[0])))
                  if x["id"] == folder), None)
        fname = f["name"] if f else folder
    except Exception:  # noqa: BLE001
        pass
    return f"naar {mb[0] if mb else '?'} › {fname}"


def _detail_label(self, c, args, result):
    lab = c.execute("SELECT name FROM labels WHERE id=?", (int(args[0]),)).fetchone()
    return f"{'+' if args[1] else '−'} {lab[0] if lab else '?'}"


def install_tracking():
    _track("move_mail", "verplaatst", _detail_move)
    _track("archive_mail", "gearchiveerd")
    _track("delete_mail", "verwijderd")
    _track("set_label", "label", _detail_label)
    _track("set_flag", "vlag", lambda self, c, a, r: "aan" if a[0] else "uit")
    _track("set_read", None)
    _track("link_mail", "gekoppeld", lambda self, c, a, r: a[0] or "ontkoppeld")
    _track("get_mail", None)
    _track("set_followup", "opvolgen", lambda self, c, a, r: {"today": "vandaag", "tomorrow": "morgen", "thisweek": "deze week",
                                                              "nextweek": "volgende week", "nodate": "zonder datum", "complete": "voltooid",
                                                              "clear": "uit"}.get(a[0], a[0]))
    _track("report_junk", "gemeld", lambda self, c, a, r: {"junk": "als ongewenst", "phishing": "als phishing", "notjunk": "als geen ongewenste e-mail"}.get(a[0] if a else "junk", ""))


# ---------------------------------------------------------------- wachtrij: verplaatsen tussen mailboxen
_jobs_wake = threading.Event()


def job_worker():
    """Verwerkt 'verplaatsen naar een andere mailbox' op de achtergrond, met opnieuw proberen."""
    while True:
        _jobs_wake.wait(timeout=5)
        _jobs_wake.clear()
        if CFG["mode"] != "microsoft" or DB != DBS["microsoft"]:
            continue
        try:
            with _conn() as c:
                jobs = _rows(c.execute("SELECT * FROM move_jobs WHERE status='wacht' AND (retry_at IS NULL OR retry_at<=?) ORDER BY id",
                                       (time.time(),)))
        except sqlite3.Error:
            continue
        for job in jobs:
            with _conn() as c:
                c.execute("UPDATE move_jobs SET status='bezig', attempts=attempts+1 WHERE id=?", (job["id"],))
            api = Api()
            api._uid = job["user_id"]
            try:
                res = api._move_cross_now(job["key"], job["dst_mb"], job["folder"])
                new_key = res["id"]
                rekey(job["key"], new_key)
                detail = ""
                try:
                    with _conn() as c:
                        detail = _detail_move(api, c, [job["dst_mb"], job["folder"]], res)
                except Exception:  # noqa: BLE001
                    pass
                log_activity(new_key, job["user_id"], job["user_name"], "verplaatst", detail)
                with _conn() as c:
                    c.execute("UPDATE move_jobs SET status='klaar', done=?, new_key=?, error=? WHERE id=?",
                              (time.time(), new_key, " ".join(res.get("warnings") or []) or None, job["id"]))
                BUS.publish({"t": "mail", "mb": [job["src_mb"], job["dst_mb"]], "key": job["key"], "new": new_key, "by": job["user_id"]},
                            [job["src_mb"], job["dst_mb"]])
                BUS.publish({"t": "job", "ok": True, "warnings": res.get("warnings") or [], "subject": job["subject"],
                             "msg": f"Verplaatst: “{job['subject']}” {detail}"}, only_uid=job["user_id"])
            except Exception as e:  # noqa: BLE001
                msg = nl_error(e) if isinstance(e, GraphError) else str(e)
                final = job["attempts"] + 1 >= 3 or isinstance(e, (Gone, PermissionError)) or (isinstance(e, GraphError) and e.status in (403, 404))
                with _conn() as c:
                    c.execute("UPDATE move_jobs SET status=?, error=?, retry_at=? WHERE id=?",
                              ("fout" if final else "wacht", msg, time.time() + 30 * (job["attempts"] + 1), job["id"]))
                if final:
                    BUS.publish({"t": "mail", "mb": [job["src_mb"]], "key": job["key"]}, [job["src_mb"]])
                    BUS.publish({"t": "job", "ok": False, "subject": job["subject"],
                                 "msg": f"Verplaatsen van “{job['subject']}” is niet gelukt: {msg} De mail staat nog in de oude map."},
                                only_uid=job["user_id"])


def pending_keys():
    try:
        with _conn() as c:
            return {r[0]: r[1] for r in c.execute("SELECT key, user_name FROM move_jobs WHERE status IN ('wacht','bezig')")}
    except sqlite3.Error:
        return {}


# ---------------------------------------------------------------- back-up
BACKUP_DIR = os.path.join(DATA, "backups")
BACKUP_KEEP = 14


def backup_now():
    """Kopie van de databases en config.json in backups\\JJJJ-MM-DD_UUMM (laatste 14 bewaard)."""
    import shutil
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    target = os.path.join(BACKUP_DIR, stamp)
    os.makedirs(target, exist_ok=True)
    for name, path in DBS.items():
        if os.path.exists(path):
            src = sqlite3.connect(path)
            dst = sqlite3.connect(os.path.join(target, os.path.basename(path)))
            with dst:
                src.backup(dst)  # veilig, ook terwijl de server draait
            src.close()
            dst.close()
    if os.path.exists(CONFIG):
        shutil.copy2(CONFIG, os.path.join(target, "config.json"))
    olds = sorted(d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d)))
    for d in olds[:-BACKUP_KEEP]:
        shutil.rmtree(os.path.join(BACKUP_DIR, d), ignore_errors=True)
    return stamp


def backups_list():
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted((d for d in os.listdir(BACKUP_DIR) if os.path.isdir(os.path.join(BACKUP_DIR, d))), reverse=True)


def backup_worker():
    """Elke nacht om 02:30 (en bij opstarten als de laatste ouder is dan een dag)."""
    time.sleep(120)
    while True:
        last = backups_list()
        age = None
        if last:
            try:
                age = time.time() - dt.datetime.strptime(last[0], "%Y-%m-%d_%H%M").timestamp()
            except ValueError:
                pass
        now = dt.datetime.now()
        if age is None or age > 26 * 3600 or (now.hour == 2 and now.minute >= 30 and age > 3600):
            _quiet(backup_now)
        time.sleep(600)


# ---------------------------------------------------------------- server
SESSION_IDLE = 12 * 3600          # na 12 uur niets doen opnieuw inloggen (tenzij 'ingelogd blijven')
NOT_API = {"download_eml"}        # alleen via /download
_fails = {}                       # ip -> [tijden van mislukte logins]
TRUST_PROXY = os.environ.get("PLAKZICHT_TRUST_PROXY") == "1"


def _cookies(handler):
    out = {}
    for part in (handler.headers.get("Cookie") or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k:
            out[k] = v
    return out


def _client_ip(handler):
    """Adres van de pc. Achter Cloudflare of een andere proxy (PLAKZICHT_TRUST_PROXY=1) het doorgegeven adres."""
    ip = handler.client_address[0]
    if TRUST_PROXY:
        import ipaddress
        try:
            internal = ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback
        except ValueError:
            internal = False
        if internal:
            fwd = handler.headers.get("CF-Connecting-IP") or (handler.headers.get("X-Forwarded-For") or "").split(",")[0]
            if fwd.strip():
                return fwd.strip()
    return ip


def _https(handler):
    return handler.headers.get("X-Forwarded-Proto", "").lower() == "https" or '"https"' in (handler.headers.get("Cf-Visitor") or "")


def _cookie(handler, name, value, max_age=None):
    c = f"{name}={value}; HttpOnly; SameSite=Lax; Path=/"
    if max_age is not None:
        c += f"; Max-Age={int(max_age)}"
    if _https(handler):
        c += "; Secure"
    handler._out_cookies.append(c)


# -- ingelogd blijven
def _remember_days(c):
    try:
        return max(0, min(365, int(_settings(c).get("remember_days") or 0)))
    except ValueError:
        return 0


def _keep_hash(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


def keep_new(uid, device, ip):
    """Nieuw 'ingelogd blijven' voor dit apparaat. Geeft (cookiewaarde, dagen) of (None, 0) als het uit staat.
    In de database staat alleen een hash; het cookie zelf is de sleutel."""
    with _lock, _conn() as c:
        days = _remember_days(c)
        if not days:
            return None, 0
        kid, sec, now = secrets.token_urlsafe(9), secrets.token_urlsafe(32), time.time()
        c.execute("INSERT INTO remember(id,user_id,hash,created,last,device,ip) VALUES(?,?,?,?,?,?,?)",
                  (kid, uid, _keep_hash(sec), now, now, device or "", ip))
        c.execute("DELETE FROM remember WHERE last < ?", (now - days * 86400,))
    return f"{kid}.{sec}", days


def keep_check(token):
    """Geldig 'ingelogd blijven'-cookie? Geeft (user_id, id, dagen) of (None, None, 0). Verlengt bij gebruik."""
    kid, _, sec = (token or "").partition(".")
    if not kid or not sec:
        return None, None, 0
    with _conn() as c:
        r = c.execute("SELECT * FROM remember WHERE id=?", (kid,)).fetchone()
        days = _remember_days(c)
        now = time.time()
        if not r or not days or r["last"] < now - days * 86400 or not secrets.compare_digest(r["hash"], _keep_hash(sec)):
            return None, None, 0
        if now - r["last"] > 600:
            c.execute("UPDATE remember SET last=? WHERE id=?", (now, kid))
    return r["user_id"], kid, days


def keep_drop(kid):
    if kid:
        with _lock, _conn() as c:
            c.execute("DELETE FROM remember WHERE id=?", (kid,))


def _drop_sessions(uid, keep_ids=None, keep_api=None):
    """Lopende sessies van een gebruiker beëindigen. keep_ids: alleen sessies van deze apparaten; keep_api: deze niet."""
    for k, v in list(SESSIONS.items()):
        a = v["api"]
        if a._uid == uid and a is not keep_api and (keep_ids is None or a._keep_id in keep_ids):
            SESSIONS.pop(k, None)


def _session(handler, create):
    jar = _cookies(handler)
    sid = jar.get("pmsid")
    now = time.time()
    for k in [k for k, v in list(SESSIONS.items()) if now - v["last"] > SESSION_IDLE]:
        SESSIONS.pop(k, None)
    if sid in SESSIONS:
        SESSIONS[sid]["last"] = now
        return sid, SESSIONS[sid], False
    keep = jar.get("pmkeep")
    if keep:  # na een herstart van de pc of de server: weer aanmelden met 'ingelogd blijven'
        uid, kid, days = keep_check(keep)
        if uid:
            api = Api()
            api._uid, api._keep_id = uid, kid
            sid = secrets.token_urlsafe(32)
            SESSIONS[sid] = {"api": api, "last": now}
            _cookie(handler, "pmsid", sid)
            _cookie(handler, "pmkeep", keep, days * 86400)  # looptijd van het cookie meeschuiven
            return sid, SESSIONS[sid], False
        _cookie(handler, "pmkeep", "", 0)  # verlopen of ingetrokken: cookie weghalen
    if not create:
        return None, None, False
    sid = secrets.token_urlsafe(32)
    SESSIONS[sid] = {"api": Api(), "last": now}
    _cookie(handler, "pmsid", sid)
    return sid, SESSIONS[sid], True


def make_handler():
    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=UI, **k)

        def log_message(self, *a):
            pass

        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".webmanifest": "application/manifest+json",
                          ".js": "text/javascript", ".svg": "image/svg+xml"}

        def setup(self):
            super().setup()
            self._out_cookies = []

        def end_headers(self):
            for c in self._out_cookies:
                self.send_header("Set-Cookie", c)
            self._out_cookies = []
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            super().end_headers()

        def list_directory(self, path):
            self.send_error(404)

        def do_GET(self):
            if self.path == "/":
                self.send_response(302); self.send_header("Location", "/index.html"); self.end_headers(); return
            if self.path == "/health":  # voor Docker en de werkplek-app: draait de server?
                data = json.dumps({"ok": True, "app": "plakzicht-mail", "version": VERSION}).encode()
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data); return
            if self.path.startswith("/download/eml"):
                return self._download()
            if self.path.startswith("/events"):
                return self._events()
            return super().do_GET()

        def _events(self):
            """Live meldingen naar het scherm (Server-Sent Events)."""
            import queue
            _, sess, _ = _session(self, False)
            uid = sess["api"]._uid if sess else None
            if not uid:
                self.send_response(403); self.send_header("Content-Length", "0"); self.end_headers(); return
            q = BUS.subscribe(uid)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                self.wfile.write(b"retry: 3000\n\n"); self.wfile.flush()
                while True:
                    try:
                        ev = q.get(timeout=15)
                        self.wfile.write(b"data: " + json.dumps(ev).encode() + b"\n\n")
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    if not any(v["api"]._uid == uid for v in list(SESSIONS.values())):
                        break  # uitgelogd
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                BUS.unsubscribe(q)

        def _download(self):
            import urllib.parse as up
            _, sess, _ = _session(self, False)
            mid = dict(up.parse_qsl(up.urlparse(self.path).query)).get("id", "")
            try:
                if not sess:
                    raise PermissionError("Niet ingelogd.")
                sess["api"]._ip = _client_ip(self)
                name, data = sess["api"].download_eml(mid)
            except Exception as e:  # noqa: BLE001
                msg = str(e).encode()
                self.send_response(403 if isinstance(e, PermissionError) else 500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers(); self.wfile.write(msg); return
            self.send_response(200)
            self.send_header("Content-Type", "message/rfc822")
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + up.quote(name))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            name = self.path.split("/api/", 1)[-1]
            ip = _client_ip(self)
            try:
                # Alleen de eigen pagina mag de API gebruiken: andere websites kunnen deze kop niet meesturen.
                if self.headers.get("X-Plakzicht") != "1":
                    raise PermissionError("Geweigerd.")
                if not self.path.startswith("/api/") or name.startswith("_") or name in NOT_API or not callable(getattr(Api, name, None)):
                    raise AttributeError("Onbekende functie.")
                n = int(self.headers.get("Content-Length") or 0)
                if n > 20_000_000:
                    raise ValueError("Verzoek te groot.")
                args = json.loads(self.rfile.read(n) or b"[]")
                sid, sess, new = _session(self, True)
                api = sess["api"]
                api._ip = ip
                if name == "login":
                    recent = [t for t in _fails.get(ip, []) if time.time() - t < 600]
                    if len(recent) >= 10:
                        raise PermissionError("Te vaak een verkeerd wachtwoord. Probeer het over 10 minuten opnieuw.")
                    try:
                        result = api.login(*args)
                    except PermissionError:
                        _fails[ip] = recent + [time.time()]
                        raise
                    # nieuwe sessie-id na inloggen
                    SESSIONS.pop(sid, None)
                    sid = secrets.token_urlsafe(32)
                    SESSIONS[sid] = {"api": api, "last": time.time()}
                    self._out_cookies = [c for c in self._out_cookies if not c.startswith("pmsid=")]
                    _cookie(self, "pmsid", sid)
                    keep_drop(api._keep_id)  # eventueel oud 'ingelogd blijven' van dit apparaat vervalt
                    api._keep_id = None
                    want, device = api._keep_req or (False, "")
                    api._keep_req = None
                    token, days = keep_new(api._uid, device, ip) if want else (None, 0)
                    if token:
                        api._keep_id = token.split(".", 1)[0]
                        _cookie(self, "pmkeep", token, days * 86400)
                    else:
                        _cookie(self, "pmkeep", "", 0)
                else:
                    result = getattr(api, name)(*args)
                if name == "logout":
                    keep_drop(api._keep_id)
                    api._keep_id = None
                    SESSIONS.pop(sid, None)
                    _cookie(self, "pmkeep", "", 0)
                body = {"ok": True, "result": result}
            except Exception as e:  # noqa: BLE001 - fout gaat terug naar de interface
                body = {"ok": False, "error": str(e)}
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return H


def serve(host, port):
    srv = ThreadingHTTPServer((host, port), make_handler())
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def lan_addresses():
    out = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        out.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            out.add(info[4][0])
    except OSError:
        pass
    return sorted(a for a in out if not a.startswith("127."))


class DesktopBridge:
    """Alleen voor het desktopvenster: vensters openen en links in de gewone browser."""

    def __init__(self, base):
        self.base = base

    def popout(self, mail_id, title="Mail"):
        import webview
        import urllib.parse as up
        webview.create_window(f"{title} - Plakzicht Mail", f"{self.base}/index.html?popout={up.quote(str(mail_id))}",
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


def _arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


install_tracking()


def main():
    if "--version" in sys.argv:
        print(VERSION)
        return
    import signal
    try:  # Docker/Unraid stopt de container met SIGTERM: netjes afsluiten
        signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    except (ValueError, AttributeError):
        pass
    set_db_for_mode(CFG["mode"])
    init_db()
    start_sync()
    threading.Thread(target=job_worker, name="verplaatsen", daemon=True).start()
    threading.Thread(target=backup_worker, name="backup", daemon=True).start()
    port = int(_arg("--port", os.environ.get("PLAKZICHT_PORT") or CFG.get("port") or 8765))
    if "--server" in sys.argv or IN_DOCKER or (FROZEN and "--desktop" not in sys.argv):
        if not IN_DOCKER and (sys.stdout is None or "--log" in sys.argv):  # als dienst (zonder venster): naar server.log
            logf = open(os.path.join(DATA, "server.log"), "a", buffering=1, encoding="utf-8")
            sys.stdout = sys.stderr = logf
            print(f"--- gestart {dt.datetime.now():%Y-%m-%d %H:%M}")
        host = _arg("--host", CFG.get("host") or "0.0.0.0")
        serve(host, port)
        print("Plakzicht Mail server draait. Open op een pc in het netwerk:")
        for a in (lan_addresses() if host in ("0.0.0.0", "") else [host]):
            print(f"   http://{a}:{port}")
        print(f"Op deze pc: http://localhost:{port}" if not IN_DOCKER else f"Gegevens: {DATA} · versie {VERSION}")
        if not IN_DOCKER:
            print("Laat dit venster open; sluiten = server stoppen.")
        try:
            while True:
                time.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            return
    host = "0.0.0.0" if "--network" in sys.argv else "127.0.0.1"
    try:
        serve(host, port)
    except OSError:
        print(f"Poort {port} is al in gebruik. Draait Plakzicht Mail al? Kies een andere poort met --port.")
        raise
    base = f"http://127.0.0.1:{port}"
    if "--browser" in sys.argv:
        print("Plakzicht Mail draait op", base, "(sluit dit venster om te stoppen)")
        if "--no-open" not in sys.argv:
            webbrowser.open(base + "/index.html")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return
    try:
        import webview
    except ImportError:
        print("pywebview is niet geïnstalleerd; Plakzicht Mail opent nu in de browser.")
        print("Installeer het met:  python -m pip install pywebview")
        webbrowser.open(base + "/index.html")
        while True:
            time.sleep(3600)
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True
    except (AttributeError, TypeError):
        pass
    webview.create_window("Plakzicht Mail", base + "/index.html", js_api=DesktopBridge(base),
                          width=1400, height=880, min_size=(1000, 640))
    webview.start(private_mode=False)


if __name__ == "__main__":
    main()
