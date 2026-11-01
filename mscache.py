"""Lokale kopie van de Microsoft-mailboxen (vergelijkbaar met Outlooks .ost-bestand).

De server houdt per mailbox de mappen en de berichtenlijsten bij in SQLite en
werkt die op de achtergrond bij met Microsoft Graph delta-query's: alleen wat
er sinds de vorige keer veranderd is wordt opgehaald. De inhoud van de nieuwste
mails wordt vooraf opgehaald, zodat openen direct gaat. Lijsten, zoeken en
filters komen uit de lokale kopie.
"""
import datetime as dt
import json
import sqlite3
import threading
import time
import traceback

from graph import GraphError, nl_error

SCHEMA = """
CREATE TABLE IF NOT EXISTS ms_folders(
  mailbox_id INTEGER, id TEXT, name TEXT, parent TEXT, wk TEXT, unread INTEGER, total INTEGER,
  depth INTEGER, has_children INTEGER, pos INTEGER, PRIMARY KEY(mailbox_id, id));
CREATE TABLE IF NOT EXISTS ms_msgs(
  mailbox_id INTEGER, id TEXT, folder_id TEXT, received TEXT, is_read INTEGER, flagged INTEGER,
  cats TEXT, search TEXT, data TEXT, body TEXT, body_at REAL, PRIMARY KEY(mailbox_id, id));
CREATE INDEX IF NOT EXISTS ms_msgs_folder ON ms_msgs(mailbox_id, folder_id, received);
CREATE TABLE IF NOT EXISTS ms_sync(
  mailbox_id INTEGER, folder_id TEXT, delta TEXT, synced_at REAL, days INTEGER, PRIMARY KEY(mailbox_id, folder_id));
CREATE TABLE IF NOT EXISTS ms_status(
  mailbox_id INTEGER PRIMARY KEY, last_ok REAL, last_try REAL, error TEXT, busy INTEGER DEFAULT 0);
"""

PREFETCH_BODIES = 150         # per ronde (elke minuut) maximaal zoveel mails met inhoud ophalen per mailbox
# Hoeveel mail offline bewaren (dagen; 0 = alles), zoals de schuifregelaar in Outlook
PERIODS = [(7, "1 week"), (14, "2 weken"), (30, "1 maand"), (90, "3 maanden"), (180, "6 maanden"),
           (365, "1 jaar"), (730, "2 jaar"), (1825, "5 jaar"), (0, "Alles")]
DEFAULT_DAYS = 90


def cutoff(days):
    """Begindatum van de bewaarperiode (ISO, UTC), of None voor alles."""
    if not days:
        return None
    d = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=int(days))
    return d.strftime("%Y-%m-%dT00:00:00Z")
BODY_MAX = 3_000_000          # grotere mails niet vooraf bewaren
INTERVAL = 60                 # seconden tussen volledige synchronisatierondes (alle mappen)
QUICK = 15                    # seconden tussen snelle rondes: Postvak IN en mappen die iemand bekijkt
HOT_FOR = 180                 # een bekeken map blijft zo lang 'snel' bijgewerkt


def _addr(m, k):
    return ", ".join((r.get("emailAddress") or {}).get("address", "") for r in m.get(k) or [])


DATA_KEYS = ("id", "subject", "from", "toRecipients", "ccRecipients", "receivedDateTime", "isRead",
             "bodyPreview", "categories", "flag", "hasAttachments", "parentFolderId", "importance")


def _incomplete(m):
    """Microsoft stuurt bij een wijziging soms alleen de gewijzigde velden (bv. alleen 'gelezen')."""
    return not m.get("receivedDateTime")


def _row(mailbox_id, m):
    frm = (m.get("from") or {}).get("emailAddress") or {}
    cats = m.get("categories") or []
    search = " ".join([m.get("subject") or "", frm.get("name") or "", frm.get("address") or "",
                       _addr(m, "toRecipients"), m.get("bodyPreview") or ""]).lower()
    data = {k: m.get(k) for k in DATA_KEYS}
    return (mailbox_id, m["id"], m.get("parentFolderId"), m.get("receivedDateTime") or "",
            1 if m.get("isRead") else 0, 1 if (m.get("flag") or {}).get("flagStatus") == "flagged" else 0,
            "|" + "|".join(c.lower() for c in cats) + "|", search, json.dumps(data))


class MailCache:
    def __init__(self, db_path_fn, client_fn, mailboxes_fn, on_change=None, on_new=None):
        """db_path_fn(): pad naar de database; client_fn(mailbox): MsMail voor die mailbox (of GraphError);
        mailboxes_fn(): lijst met gekoppelde mailboxen (dicts met id en address)."""
        self.db_path_fn, self.client_fn, self.mailboxes_fn = db_path_fn, client_fn, mailboxes_fn
        self.on_change = on_change or (lambda mailbox_id, kind="mail": None)
        self.on_new = on_new or (lambda mailbox_id, msgs: None)  # nieuwe mail in Postvak IN (voor meldingen)
        self._hot = {}                        # (mailbox_id, folder_id) -> laatst bekeken
        self._wake = threading.Event()
        self._urgent = []                     # (mailbox_id, folder_id) die voorrang krijgen
        self._ulock = threading.Lock()
        self._mlocks = {}                     # per mailbox één synchronisatie tegelijk
        self._thread = None
        self._stop = threading.Event()

    # -- database
    def conn(self):
        c = sqlite3.connect(self.db_path_fn(), timeout=30)
        c.row_factory = sqlite3.Row
        return c

    def init(self):
        with self.conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)
            if "days" not in [r[1] for r in c.execute("PRAGMA table_info(ms_sync)")]:
                c.execute("ALTER TABLE ms_sync ADD COLUMN days INTEGER")
            if "warn" not in [r[1] for r in c.execute("PRAGMA table_info(ms_status)")]:
                c.execute("ALTER TABLE ms_status ADD COLUMN warn TEXT")
            if "size" not in [r[1] for r in c.execute("PRAGMA table_info(ms_msgs)")]:
                c.execute("ALTER TABLE ms_msgs ADD COLUMN size INTEGER")

    def _mlock(self, mid):
        with self._ulock:
            return self._mlocks.setdefault(mid, threading.Lock())

    # -- achtergrondsynchronisatie
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="mailsync", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake.set()

    def kick(self, mailbox_id=None, folder_id=None):
        """Zo snel mogelijk (deze map van) deze mailbox bijwerken."""
        if mailbox_id is not None:
            with self._ulock:
                self._urgent.append((int(mailbox_id), folder_id))
        self._wake.set()

    def touch(self, mailbox_id, folder_id):
        """Iemand bekijkt deze map: de komende minuten vaker bijwerken."""
        self._hot[(int(mailbox_id), folder_id)] = time.time()

    def _quick_round(self, mbs):
        now = time.time()
        for (mid, fid), t in list(self._hot.items()):
            if now - t > HOT_FOR:
                self._hot.pop((mid, fid), None)
        for mb in mbs.values():
            if self._stop.is_set():
                return
            with self.conn() as c:
                inbox = c.execute("SELECT id FROM ms_folders WHERE mailbox_id=? AND wk='inbox'", (mb["id"],)).fetchone()
            folders = {inbox[0]} if inbox else set()
            folders |= {fid for (mid, fid) in self._hot if mid == mb["id"]}
            for fid in folders:
                self._safe(mb, only_folder=fid)

    def _loop(self):
        last_full = last_quick = 0
        while not self._stop.is_set():
            self._wake.wait(timeout=5)
            self._wake.clear()
            if self._stop.is_set():
                return
            with self._ulock:
                urgent, self._urgent = self._urgent, []
            mbs = {m["id"]: m for m in self.mailboxes_fn()}
            for mid, fid in dict.fromkeys(urgent):
                if mid in mbs:
                    self._safe(mbs[mid], only_folder=fid)
            if time.time() - last_full >= INTERVAL:
                last_full = last_quick = time.time()
                for mb in mbs.values():
                    if self._stop.is_set():
                        return
                    self._safe(mb)
            elif time.time() - last_quick >= QUICK:
                last_quick = time.time()
                self._quick_round(mbs)

    def _safe(self, mb, only_folder=None):
        try:
            self.sync_mailbox(mb, only_folder=only_folder)
        except Exception as e:  # noqa: BLE001 - nooit de synchronisatie laten stoppen
            msg = nl_error(e) if isinstance(e, GraphError) else str(e) if type(e).__name__ == "SecretUnreadable" else f"{type(e).__name__}: {e}"
            if isinstance(e, GraphError) and e.status == 403:
                try:
                    sc = [x for x in self.client_fn(mb).g.scopes() if x.lower().startswith("mail.")]
                    msg += (" Machtigingen van het gebruikte account: " + (", ".join(sc) if sc else "geen Mail-machtigingen") + "."
                            + ("" if any(x.lower() == "mail.readwrite.shared" for x in sc) else
                               " Mail.ReadWrite.Shared ontbreekt: voeg die toe in de app-registratie, verleen beheerderstoestemming en meld het account opnieuw aan."))
                except Exception:  # noqa: BLE001
                    pass
            if not isinstance(e, GraphError):
                traceback.print_exc()
            with self.conn() as c:
                c.execute("INSERT INTO ms_status(mailbox_id,last_try,error,busy) VALUES(?,?,?,0) "
                          "ON CONFLICT(mailbox_id) DO UPDATE SET last_try=excluded.last_try, error=excluded.error, busy=0",
                          (mb["id"], time.time(), msg))

    def sync_mailbox(self, mb, only_folder=None):
        lock = self._mlock(mb["id"])
        with lock:
            ms = self.client_fn(mb)
            with self.conn() as c:
                c.execute("INSERT INTO ms_status(mailbox_id,last_try,busy) VALUES(?,?,1) "
                          "ON CONFLICT(mailbox_id) DO UPDATE SET last_try=excluded.last_try, busy=1", (mb["id"], time.time()))
            if only_folder:
                try:
                    self.sync_folder(mb, ms, only_folder)
                except GraphError:
                    pass  # wordt bij de volgende volledige ronde gemeld
                with self.conn() as c:
                    c.execute("UPDATE ms_status SET busy=0 WHERE mailbox_id=?", (mb["id"],))
                return
            folders = self.refresh_folders(mb, ms)
            order = {"inbox": 0, "sent": 1, "archive": 2, "drafts": 3, "deleted": 4, "junk": 5}
            skipped, inbox_err = [], None
            for f in sorted(folders, key=lambda f: (order.get(f["wk"], 9), f["depth"])):
                if self._stop.is_set():
                    return
                try:
                    self.sync_folder(mb, ms, f["id"])
                except GraphError as e:
                    if e.status in (0, 401, 429) or e.code in ("invalid_grant", "interaction_required", "config"):
                        raise  # verbinding of aanmelding: hele mailbox
                    skipped.append(f"{f['name']} ({'geen toegang' if e.status == 403 else nl_error(e).split('.')[0]})")
                    if f["wk"] == "inbox":
                        inbox_err = e
            self.prune(mb)
            self.prefetch_bodies(mb, ms)
            self.fill_sizes(mb, ms)
            if inbox_err:  # Postvak IN lukt niet: dat is een echte fout
                raise inbox_err
            with self.conn() as c:
                c.execute("UPDATE ms_status SET last_ok=?, error=NULL, warn=?, busy=0 WHERE mailbox_id=?",
                          (time.time(), ("Overgeslagen mappen: " + "; ".join(skipped)) if skipped else None, mb["id"]))

    def refresh_folders(self, mb, ms=None):
        ms = ms or self.client_fn(mb)
        folders = ms.folders(mb["address"], max_age=0)
        with self.conn() as c:
            before = [(r[0], r[1], r[2]) for r in c.execute("SELECT id, name, parent FROM ms_folders WHERE mailbox_id=? ORDER BY pos", (mb["id"],))]
        if before and before != [(f["id"], f["name"], f["parent"]) for f in folders]:
            self.on_change(mb["id"], "folders")
        with self.conn() as c:
            c.execute("DELETE FROM ms_folders WHERE mailbox_id=?", (mb["id"],))
            c.executemany("INSERT INTO ms_folders VALUES(?,?,?,?,?,?,?,?,?,?)",
                          [(mb["id"], f["id"], f["name"], f["parent"], f["wk"], f["unread"], f["total"], f["depth"],
                            1 if f["has_children"] else 0, i) for i, f in enumerate(folders)])
            ids = {f["id"] for f in folders}
            gone = [r[0] for r in c.execute("SELECT folder_id FROM ms_sync WHERE mailbox_id=?", (mb["id"],)) if r[0] not in ids]
            for fid in gone:
                c.execute("DELETE FROM ms_sync WHERE mailbox_id=? AND folder_id=?", (mb["id"], fid))
                c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND folder_id=?", (mb["id"], fid))
        return folders

    @staticmethod
    def days_of(mb):
        d = mb.get("cache_days")
        return DEFAULT_DAYS if d is None else int(d)

    def sync_folder(self, mb, ms, folder_id):
        try:
            return self._sync_delta(mb, ms, folder_id)
        except GraphError as e:
            if e.status not in (400, 403, 501):
                raise
        # Delta-query niet toegestaan voor deze map/mailbox: dan de hele map (binnen de periode) opnieuw ophalen
        days = self.days_of(mb)
        items = ms.list_since(mb["address"], folder_id, cutoff(days))
        ids = {m["id"] for m in items}
        fresh = []
        with self.conn() as c:
            known = c.execute("SELECT 1 FROM ms_sync WHERE mailbox_id=? AND folder_id=?", (mb["id"], folder_id)).fetchone()
            for m in items:
                m.setdefault("parentFolderId", folder_id)
                if self._upsert(c, mb["id"], m) == 2 and known:
                    fresh.append(m)
            for (mid,) in c.execute("SELECT id FROM ms_msgs WHERE mailbox_id=? AND folder_id=?", (mb["id"], folder_id)).fetchall():
                if mid not in ids:
                    c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND id=?", (mb["id"], mid))
            c.execute("INSERT OR REPLACE INTO ms_sync(mailbox_id,folder_id,delta,synced_at,days) VALUES(?,?,?,?,?)",
                      (mb["id"], folder_id, "list", time.time(), days))
        self.on_change(mb["id"])
        self._announce(mb["id"], folder_id, fresh)

    def _sync_delta(self, mb, ms, folder_id):
        days = self.days_of(mb)
        with self.conn() as c:
            r = c.execute("SELECT delta, days FROM ms_sync WHERE mailbox_id=? AND folder_id=?", (mb["id"], folder_id)).fetchone()
        if r and r["delta"] and r["delta"] != "list" and (r["days"] if r["days"] is not None else DEFAULT_DAYS) == days:
            url, first = r["delta"], False
        else:  # eerste keer, of de bewaarperiode is gewijzigd: opnieuw met het nieuwe datumfilter
            url, first = ms.delta_start(mb["address"], folder_id, cutoff(days)), True
        seen = set()
        for attempt in range(2):
            try:
                while url:
                    j = ms.delta_page(url)
                    up, rm = [], []
                    for m in j.get("value", []):
                        if "@removed" in m:
                            rm.append(m["id"])
                        else:
                            m.setdefault("parentFolderId", folder_id)
                            up.append(m)
                            seen.add(m["id"])
                    changed, fresh, partial = 0, [], []
                    with self.conn() as c:
                        for mid in rm:
                            changed += c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND id=? AND folder_id=?", (mb["id"], mid, folder_id)).rowcount
                        for m in up:
                            r = self._upsert(c, mb["id"], m)
                            if r == 3:
                                partial.append(m)
                                continue
                            changed += 1 if r else 0
                            if r == 2 and not first:
                                fresh.append(m)
                    for m in partial:  # onvolledig binnengekomen: het hele bericht los ophalen
                        full = self._fetch(mb, ms, m["id"])
                        if full:
                            full.setdefault("parentFolderId", folder_id)
                            with self.conn() as c:
                                r = self._upsert(c, mb["id"], full)
                            changed += 1 if r in (1, 2) else 0
                            if r == 2 and not first:
                                fresh.append(full)
                    if changed:
                        self.on_change(mb["id"])
                    self._announce(mb["id"], folder_id, fresh)
                    nxt, delta = j.get("@odata.nextLink"), j.get("@odata.deltaLink")
                    if delta:
                        with self.conn() as c:
                            if first:  # volledige ronde: wat niet meer terugkwam bestaat niet meer
                                have = [x[0] for x in c.execute("SELECT id FROM ms_msgs WHERE mailbox_id=? AND folder_id=?", (mb["id"], folder_id))]
                                for mid in have:
                                    if mid not in seen:
                                        c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND id=?", (mb["id"], mid))
                            c.execute("INSERT OR REPLACE INTO ms_sync(mailbox_id,folder_id,delta,synced_at,days) VALUES(?,?,?,?,?)",
                                      (mb["id"], folder_id, delta, time.time(), days))
                    url = nxt
                self.repair(mb, ms, folder_id)
                return
            except GraphError as e:
                # verlopen synchronisatiestand: opnieuw vanaf het begin
                if attempt == 0 and (e.status == 410 or "SyncState" in (e.code or "") or "syncState" in str(e)):
                    url, first, seen = ms.delta_start(mb["address"], folder_id, cutoff(days)), True, set()
                    continue
                if e.status == 404 and e.code in ("ErrorItemNotFound", "ErrorFolderNotFound", "ResourceNotFound"):
                    with self.conn() as c:  # map bestaat niet meer
                        c.execute("DELETE FROM ms_sync WHERE mailbox_id=? AND folder_id=?", (mb["id"], folder_id))
                        c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND folder_id=?", (mb["id"], folder_id))
                    return
                raise

    def _upsert(self, c, mailbox_id, m, body=None):
        """Bericht opslaan; geeft 1 als er iets nieuws of anders is, anders 0."""
        old = c.execute("SELECT data FROM ms_msgs WHERE mailbox_id=? AND id=?", (mailbox_id, m["id"])).fetchone()
        if old is not None:
            # alleen de velden overnemen die Microsoft meestuurt; de rest (onderwerp, afzender, datum) blijft staan
            try:
                base = json.loads(old[0]) or {}
            except ValueError:
                base = {}
            base.update({k: v for k, v in m.items() if k in DATA_KEYS})
            m = base
        elif _incomplete(m):
            return 3  # onvolledig en nog niet bekend: eerst het hele bericht ophalen
        row = _row(mailbox_id, m)
        same = old is not None and old[0] == row[-1]
        c.execute("INSERT INTO ms_msgs(mailbox_id,id,folder_id,received,is_read,flagged,cats,search,data) VALUES(?,?,?,?,?,?,?,?,?) "
                  "ON CONFLICT(mailbox_id,id) DO UPDATE SET folder_id=excluded.folder_id, received=excluded.received, "
                  "is_read=excluded.is_read, flagged=excluded.flagged, cats=excluded.cats, search=excluded.search, data=excluded.data", row)
        if body is not None:
            self.store_body(c, mailbox_id, m["id"], body)
        return 2 if old is None else 0 if same else 1  # 2 = nieuw bericht, 3 = onvolledig (niet opgeslagen)

    @staticmethod
    def _fetch(mb, ms, mid):
        try:
            return ms.get(mb["address"], mid, full=False)
        except GraphError:
            return None

    def repair(self, mb, ms, folder_id, limit=25):
        """Berichten die eerder zonder onderwerp/datum zijn opgeslagen opnieuw ophalen (of weghalen als ze niet meer bestaan)."""
        with self.conn() as c:
            ids = [r[0] for r in c.execute("SELECT id FROM ms_msgs WHERE mailbox_id=? AND folder_id=? AND (received IS NULL OR received='') LIMIT ?",
                                           (mb["id"], folder_id, limit))]
        if not ids:
            return 0
        fixed = 0
        for mid in ids:
            try:
                full = ms.get(mb["address"], mid, full=False)
            except GraphError as e:
                if e.status == 404:
                    with self.conn() as c:
                        c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND id=?", (mb["id"], mid))
                    fixed += 1
                continue
            if full and full.get("receivedDateTime"):
                full.setdefault("parentFolderId", folder_id)
                with self.conn() as c:
                    self._upsert(c, mb["id"], full)
                fixed += 1
        if fixed:
            self.on_change(mb["id"])
        return fixed

    def _announce(self, mb_id, folder_id, msgs):
        """Nieuwe, ongelezen en recente mails in Postvak IN doorgeven (voor de meldingen)."""
        if not msgs:
            return
        with self.conn() as c:
            wk = c.execute("SELECT wk FROM ms_folders WHERE mailbox_id=? AND id=?", (mb_id, folder_id)).fetchone()
        if not wk or wk[0] != "inbox":
            return
        recent = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        new = [m for m in msgs if not m.get("isRead") and (m.get("receivedDateTime") or "") >= recent]
        if new:
            try:
                self.on_new(mb_id, new)
            except Exception:  # noqa: BLE001 - meldingen mogen de synchronisatie nooit stoppen
                traceback.print_exc()

    def store_body(self, c, mailbox_id, mid, html):
        if html is not None and len(html) <= BODY_MAX:
            c.execute("UPDATE ms_msgs SET body=?, body_at=? WHERE mailbox_id=? AND id=?", (html, time.time(), mailbox_id, mid))

    def prune(self, mb):
        """Mails buiten de bewaarperiode uit de kopie halen (bij Microsoft blijven ze gewoon staan)."""
        since = cutoff(self.days_of(mb))
        if since:
            with self.conn() as c:
                c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND received<>'' AND received < ?", (mb["id"], since))

    def prefetch_bodies(self, mb, ms):
        # Inhoud van alle mails binnen de bewaarperiode, nieuwste eerst, per ronde een portie (geen ongewenste e-mail)
        with self.conn() as c:
            todo = [r[0] for r in c.execute("SELECT m.id FROM ms_msgs m JOIN ms_folders f ON f.mailbox_id=m.mailbox_id AND f.id=m.folder_id "
                                            "WHERE m.mailbox_id=? AND m.body IS NULL AND f.wk NOT IN ('junk','deleted') "
                                            "ORDER BY m.received DESC LIMIT ?", (mb["id"], PREFETCH_BODIES))]
        for mid in todo:
            if self._stop.is_set():
                return
            try:
                raw = ms.get(mb["address"], mid)
            except GraphError as e:
                if e.status == 404:
                    with self.conn() as c:
                        c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND id=?", (mb["id"], mid))
                    continue
                if e.status in (400, 403):
                    continue  # deze mail overslaan; wordt bij openen rechtstreeks opgehaald
                raise
            html = ms.inline_images(mb["address"], mid, (raw.get("body") or {}).get("content", ""))
            with self.conn() as c:
                self.store_body(c, mb["id"], mid, html)

    def fill_sizes(self, mb, ms, max_folders=4):
        """Grootte van nieuwe berichten ophalen (voor de kolom Grootte); per ronde een paar mappen."""
        with self.conn() as c:
            todo = [(r[0], r[1]) for r in c.execute(
                "SELECT folder_id, MIN(received) FROM ms_msgs WHERE mailbox_id=? AND size IS NULL GROUP BY folder_id LIMIT ?",
                (mb["id"], max_folders))]
        for fid, since in todo:
            if self._stop.is_set():
                return
            try:
                got = ms.sizes(mb["address"], fid, (since or "")[:10] + "T00:00:00Z" if since else None)
            except GraphError as e:
                if e.status in (400, 403, 501):  # niet ondersteund: niet steeds opnieuw proberen
                    with self.conn() as c:
                        c.execute("UPDATE ms_msgs SET size=-1 WHERE mailbox_id=? AND folder_id=? AND size IS NULL", (mb["id"], fid))
                    continue
                raise
            with self.conn() as c:
                c.executemany("UPDATE ms_msgs SET size=? WHERE mailbox_id=? AND id=?", [(v, mb["id"], k) for k, v in got.items()])
                c.execute("UPDATE ms_msgs SET size=-1 WHERE mailbox_id=? AND folder_id=? AND size IS NULL AND received>=?",
                          (mb["id"], fid, since or ""))

    # -- lezen uit de kopie
    def folders(self, mailbox_id):
        with self.conn() as c:
            rows = [dict(r) for r in c.execute("SELECT * FROM ms_folders WHERE mailbox_id=? ORDER BY pos", (mailbox_id,))]
            synced = {r[0] for r in c.execute("SELECT folder_id FROM ms_sync WHERE mailbox_id=? AND delta IS NOT NULL", (mailbox_id,))}
            counts = {r[0]: (r[1], r[2]) for r in c.execute(
                "SELECT folder_id, SUM(is_read=0), COUNT(*) FROM ms_msgs WHERE mailbox_id=? GROUP BY folder_id", (mailbox_id,))}
        for f in rows:
            f["has_children"] = bool(f["has_children"])
            if f["id"] in synced:
                # ongelezen uit de kopie: klopt direct na lezen of verplaatsen. Totaal van Microsoft (ook oudere mail
                # buiten de bewaarperiode), maar nooit minder dan wat er in de kopie staat.
                un, tot = counts.get(f["id"], (0, 0))
                f["unread"], f["total"] = un or 0, max(f.get("total") or 0, tot or 0)
            f["synced"] = f["id"] in synced
        return rows

    def is_synced(self, mailbox_id, folder_id):
        with self.conn() as c:
            return bool(c.execute("SELECT 1 FROM ms_sync WHERE mailbox_id=? AND folder_id=? AND delta IS NOT NULL",
                                  (mailbox_id, folder_id)).fetchone())

    SORT_SQL = {
        "date": "received", "from": "lower(json_extract(data,'$.from.emailAddress.name'))",
        "to": "lower(json_extract(data,'$.toRecipients[0].emailAddress.address'))",
        "subject": "lower(json_extract(data,'$.subject'))", "size": "coalesce(size, length(coalesce(body,'')))",
        "importance": "(CASE json_extract(data,'$.importance') WHEN 'high' THEN 2 WHEN 'low' THEN 0 ELSE 1 END)",
        "read": "is_read", "att": "coalesce(json_extract(data,'$.hasAttachments'),0)", "cats": "cats", "flag": "flagged",
        "due": "coalesce(json_extract(data,'$.flag.dueDateTime.dateTime'),'')"}

    def list(self, mailbox_ids, folder_id=None, filt=None, search=None, category=None, limit=500, sort=None, desc=True):
        where, args = [f"mailbox_id IN ({','.join('?' * len(mailbox_ids))})"], list(mailbox_ids)
        if folder_id:
            where.append("folder_id=?"); args.append(folder_id)
        if category:
            where.append("cats LIKE ?"); args.append("%|" + category.lower() + "|%")
        if filt == "ongelezen":
            where.append("is_read=0")
        elif filt == "gemarkeerd":
            where.append("flagged=1")
        elif filt == "bijlage":
            where.append("json_extract(data,'$.hasAttachments')=1")
        if search:
            for word in search.lower().split()[:6]:
                where.append("(search LIKE ? OR lower(coalesce(body,'')) LIKE ?)"); args += ["%" + word + "%"] * 2
        col = self.SORT_SQL.get(sort or "date", "received")
        order = f"{col} {'DESC' if desc else 'ASC'}" + (", received DESC" if col != "received" else "")
        out = []
        with self.conn() as c:
            for r in c.execute(f"SELECT mailbox_id, data, size, length(coalesce(body,'')) AS blen FROM ms_msgs "
                               f"WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ?", (*args, limit)):
                m = json.loads(r["data"])
                m["_size"] = r["size"] if r["size"] and r["size"] > 0 else (r["blen"] or None)
                out.append((r["mailbox_id"], m))
        return out

    def get(self, mailbox_id, mid):
        with self.conn() as c:
            r = c.execute("SELECT data, body, size FROM ms_msgs WHERE mailbox_id=? AND id=?", (mailbox_id, mid)).fetchone()
        if not r:
            return None, None
        d = json.loads(r["data"])
        if r["size"] and r["size"] > 0:
            d["_size"] = r["size"]
        return d, r["body"]

    # -- kopie bijwerken na een actie (de volgende delta-ronde bevestigt het)
    def patch(self, mailbox_id, mid, changes):
        data, body = self.get(mailbox_id, mid)
        if not data:
            return
        data.pop("_size", None)
        data.update(changes)
        with self.conn() as c:
            self._upsert(c, mailbox_id, data)

    def moved(self, mailbox_id, old_id, new_msg):
        data, body = self.get(mailbox_id, old_id)
        size = (data or {}).pop("_size", None)
        with self.conn() as c:
            c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND id=?", (mailbox_id, old_id))
            if new_msg and new_msg.get("id"):
                merged = dict(data or {})
                merged.update({k: v for k, v in new_msg.items() if k in (
                    "id", "subject", "from", "toRecipients", "ccRecipients", "receivedDateTime", "isRead", "bodyPreview",
                    "categories", "flag", "hasAttachments", "parentFolderId")})
                self._upsert(c, mailbox_id, merged)
                if body:
                    self.store_body(c, mailbox_id, merged["id"], body)
                if size:
                    c.execute("UPDATE ms_msgs SET size=? WHERE mailbox_id=? AND id=?", (size, mailbox_id, merged["id"]))

    def removed(self, mailbox_id, mid):
        with self.conn() as c:
            c.execute("DELETE FROM ms_msgs WHERE mailbox_id=? AND id=?", (mailbox_id, mid))

    def status(self, mailbox_id):
        with self.conn() as c:
            r = c.execute("SELECT * FROM ms_status WHERE mailbox_id=?", (mailbox_id,)).fetchone()
            n = c.execute("SELECT COUNT(*), SUM(body IS NOT NULL), SUM(length(coalesce(body,''))+length(data)), MIN(received) "
                          "FROM ms_msgs WHERE mailbox_id=?", (mailbox_id,)).fetchone()
            nf = c.execute("SELECT COUNT(*) FROM ms_sync WHERE mailbox_id=? AND delta IS NOT NULL", (mailbox_id,)).fetchone()[0]
            tf = c.execute("SELECT COUNT(*) FROM ms_folders WHERE mailbox_id=?", (mailbox_id,)).fetchone()[0]
        out = dict(r) if r else {"last_ok": None, "last_try": None, "error": None, "busy": 0}
        out.update({"mails": n[0] or 0, "bodies": n[1] or 0, "bytes": n[2] or 0, "oldest": n[3], "folders_synced": nf, "folders": tf})
        return out

    def reset_window(self, mailbox_id):
        """Bewaarperiode gewijzigd: alle mappen opnieuw synchroniseren met het nieuwe filter (kopie blijft staan)."""
        with self.conn() as c:
            c.execute("UPDATE ms_sync SET days=-1 WHERE mailbox_id=?", (mailbox_id,))

    def clear(self, mailbox_id):
        with self.conn() as c:
            for t in ("ms_msgs", "ms_sync", "ms_folders", "ms_status"):
                c.execute(f"DELETE FROM {t} WHERE mailbox_id=?", (mailbox_id,))
