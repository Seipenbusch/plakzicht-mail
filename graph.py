"""Koppeling met Microsoft 365 via Microsoft Graph.

Twee manieren, allebei met een app-registratie in Microsoft Entra ID:
- Aanmelden met Microsoft (aanbevolen): de beheerder meldt zich één keer aan met
  zijn eigen account (gedelegeerde machtigingen, PKCE, geen clientgeheim). Het
  programma ziet dan precies de mailboxen waar dat account in Exchange recht op heeft.
- App-registratie met clientgeheim (toepassingsmachtigingen): het programma werkt
  namens zichzelf; beperk de toegang dan met Exchange RBAC voor applicaties.
Medewerkers hebben in beide gevallen geen eigen Microsoft-login nodig.

Alleen de Python-standaardbibliotheek wordt gebruikt.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

GRAPH = os.environ.get("PLAKZICHT_GRAPH_URL", "https://graph.microsoft.com/v1.0").rstrip("/")
LOGIN = os.environ.get("PLAKZICHT_LOGIN_URL", "https://login.microsoftonline.com").rstrip("/")

# Graph-naam, interne sleutel, volgorde bovenaan de mappenlijst
WELLKNOWN = [("inbox", "inbox"), ("drafts", "drafts"), ("sentitems", "sent"), ("deleteditems", "deleted"),
             ("archive", "archive"), ("junkemail", "junk")]
SEL_LIST = ("id,subject,from,toRecipients,ccRecipients,receivedDateTime,isRead,bodyPreview,"
            "categories,flag,hasAttachments,parentFolderId,importance")
SEL_FULL = SEL_LIST + ",body,replyTo,sentDateTime,internetMessageId"
FOLDER_SEL = "id,displayName,parentFolderId,childFolderCount,unreadItemCount,totalItemCount"
MAX_FOLDERS = 1500
G = "https://graph.microsoft.com/"
DELEGATED_SCOPES = " ".join(["offline_access", "openid", "profile", G + "User.Read", G + "Mail.ReadWrite",
                             G + "Mail.ReadWrite.Shared", G + "Mail.Send", G + "Mail.Send.Shared"])
CALENDAR_SCOPES = DELEGATED_SCOPES + " " + G + "Calendars.ReadWrite"
CAL_TZ = "W. Europe Standard Time"
CAL_SEL = ("id,subject,start,end,isAllDay,location,organizer,attendees,bodyPreview,webLink,isOrganizer,showAs,categories,"
           "type,seriesMasterId,isCancelled,reminderMinutesBeforeStart,isReminderOn,onlineMeeting,isOnlineMeeting")


class GraphError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code = status, code
        super().__init__(message)


def nl_error(e):
    """Microsoft-foutmelding in begrijpelijk Nederlands."""
    if not isinstance(e, GraphError):
        return f"Verbinding met Microsoft mislukt: {e}"
    c, s, t = e.code or "", e.status, str(e)
    if c == "config":
        return t
    if "AADSTS7000218" in t:
        return "Zet in de app-registratie onder Verificatie 'Openbare clientstromen toestaan' op Ja."
    if "AADSTS500113" in t:
        return "Er is geen omleidings-URI ingesteld. Voeg in de app-registratie onder Verificatie › Mobiele en desktoptoepassingen http://localhost toe."
    if c == "authorization_declined":
        return "Aanmelden geweigerd of geannuleerd."
    if c == "expired_token":
        return "De code is verlopen (na 15 minuten). Start het aanmelden opnieuw."
    if "AADSTS50097" in t or "AADSTS53003" in t or "AADSTS530" in t:
        return ("Aanmelden is geblokkeerd door een beleid voor voorwaardelijke toegang in jullie Microsoft-omgeving "
                "(bijvoorbeeld 'apparaatcodestroom blokkeren'). Gebruik aanmelden via de browser op de server, of pas het beleid aan.")
    if "AADSTS50011" in t:
        return "De omleidings-URI klopt niet. Voeg onder Verificatie › Mobiele en desktoptoepassingen http://localhost toe."
    if "AADSTS700016" in t:
        return "Deze client-ID bestaat niet in deze tenant. Controleer client-ID en tenant-ID."
    if "AADSTS65001" in t or "consent" in t.lower() and c in ("invalid_grant", "interaction_required", "consent_required"):
        return "De machtigingen zijn nog niet goedgekeurd. Klik in de app-registratie op 'Beheerderstoestemming verlenen' en meld opnieuw aan."
    if c in ("invalid_grant", "interaction_required"):
        return "De aanmelding bij Microsoft is verlopen of ingetrokken. Meld je opnieuw aan in Beheer › Microsoft-koppeling."
    if c == "ErrorSendAsDenied":
        return "Dit account mag niet versturen namens deze mailbox. Geef in Exchange het recht 'Verzenden als' voor die mailbox."
    if c in ("invalid_client", "unauthorized_client") or "AADSTS7000215" in t:
        return "Microsoft weigert de inloggegevens van de app. Controleer client-ID en clientgeheim (verlopen?)."
    if "AADSTS90002" in str(e) or c == "invalid_request" and "tenant" in str(e).lower():
        return "De tenant-ID klopt niet."
    if c in ("ErrorAccessDenied", "Authorization_RequestDenied", "AccessDenied") or s == 403:
        return ("Microsoft geeft geen toegang tot deze mailbox. Bij aanmelden met je account: geef dat account in Exchange "
                "'Volledige toegang' op de mailbox (dat kan tot een uur duren). Bij een app met clientgeheim: controleer "
                "Mail.ReadWrite met beheerderstoestemming en het toegangsbereik van de app.")
    if c in ("ErrorInvalidUser", "MailboxNotEnabledForRESTAPI", "ResourceNotFound") or (s == 404 and "User" in str(e)):
        return "Deze mailbox bestaat niet of is niet bereikbaar via Microsoft Graph."
    if c == "ErrorItemNotFound" or s == 404:
        return "Niet gevonden bij Microsoft. Misschien is het intussen verplaatst of verwijderd; vernieuw de lijst."
    if c == "ErrorFolderExists":
        return "Er bestaat al een map met die naam op deze plek."
    if s == 401:
        return "Microsoft weigert de toegang (401). Controleer de app-registratie."
    return f"Microsoft gaf een fout ({s} {c}): {e}"


def _token_request(tenant, form):
    url = f"{LOGIN}/{urllib.parse.quote(tenant)}/oauth2/v2.0/token"
    try:
        rq = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode(), method="POST")
        with urllib.request.urlopen(rq, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read())
        except ValueError:
            j = {}
        raise GraphError(e.code, j.get("error", ""), (j.get("error_description") or str(e)).split("\r\n")[0])
    except urllib.error.URLError as e:
        raise GraphError(0, "network", f"Kan Microsoft niet bereiken ({e.reason}).")


def _id_claims(id_token):
    try:
        part = id_token.split(".")[1]
        return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
    except (IndexError, ValueError):
        return {}


class Graph:
    """secret = app met clientgeheim; refresh_token = aangemeld met een account (on_refresh bewaart een nieuw token)."""

    def __init__(self, tenant, client_id, secret=None, refresh_token=None, on_refresh=None, scope=None):
        if not (tenant and client_id):
            raise GraphError(0, "config", "De Microsoft-koppeling is nog niet ingesteld (tenant-ID en client-ID).")
        if not (secret or refresh_token):
            raise GraphError(0, "config", "Er is nog niemand aangemeld bij Microsoft. Klik in Beheer › Microsoft-koppeling op 'Aanmelden met Microsoft'."
                             if secret is None else "Er is nog geen clientgeheim ingevuld.")
        self.tenant, self.client_id, self.secret = tenant.strip(), client_id.strip(), secret
        self.refresh_token, self.on_refresh = refresh_token, on_refresh
        self._scope = scope or DELEGATED_SCOPES
        self._tok, self._exp = None, 0
        self._tlock = threading.Lock()

    def token(self):
        with self._tlock:
            if self._tok and time.time() < self._exp - 120:
                return self._tok
            if self.secret:
                j = _token_request(self.tenant, {"client_id": self.client_id, "client_secret": self.secret,
                                                 "grant_type": "client_credentials", "scope": G + ".default"})
            else:
                j = _token_request(self.tenant, {"client_id": self.client_id, "grant_type": "refresh_token",
                                                 "refresh_token": self.refresh_token, "scope": self._scope})
                new = j.get("refresh_token")
                if new and new != self.refresh_token:
                    self.refresh_token = new
                    if self.on_refresh:
                        self.on_refresh(new)
            self._tok, self._exp = j["access_token"], time.time() + int(j.get("expires_in", 3600))
            return self._tok

    # -- verzoek met herhalen bij drukte
    def req(self, method, path, body=None, params=None, absolute=False, tz=False):
        url = path if absolute else GRAPH + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(5):
            headers = {"Authorization": "Bearer " + self.token(),
                       "Prefer": 'IdType="ImmutableId", outlook.body-content-type="html", odata.maxpagesize=100'
                                 + (f', outlook.timezone="{CAL_TZ}"' if tz else ''),
                       "Accept": "application/json"}
            if data is not None:
                headers["Content-Type"] = "application/json"
            rq = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(rq, timeout=60) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                if e.code in (429, 503, 504) and attempt < 4:
                    time.sleep(min(30, int(e.headers.get("Retry-After") or 2 ** attempt)))
                    continue
                if e.code == 401 and attempt == 0:
                    self._tok = None
                    continue
                try:
                    j = json.loads(e.read()).get("error", {})
                except ValueError:
                    j = {}
                raise GraphError(e.code, j.get("code", ""), j.get("message", str(e)))
            except urllib.error.URLError as e:
                if attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                raise GraphError(0, "network", f"Kan Microsoft niet bereiken ({e.reason}).")
        raise GraphError(429, "TooManyRequests", "Microsoft is even te druk; probeer het zo opnieuw.")

    def scopes(self):
        """Machtigingen in het huidige toegangstoken (voor foutmeldingen)."""
        try:
            part = self.token().split(".")[1]
            j = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))
            return (j.get("scp") or " ".join(j.get("roles") or [])).split()
        except Exception:  # noqa: BLE001
            return []

    def raw(self, path):
        """Ruwe inhoud ophalen (bijv. de MIME-tekst van een bericht voor .eml)."""
        for attempt in range(3):
            rq = urllib.request.Request(GRAPH + path, headers={"Authorization": "Bearer " + self.token()})
            try:
                with urllib.request.urlopen(rq, timeout=120) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code in (429, 503, 504) and attempt < 2:
                    time.sleep(min(30, int(e.headers.get("Retry-After") or 2 ** attempt)))
                    continue
                try:
                    j = json.loads(e.read()).get("error", {})
                except ValueError:
                    j = {}
                raise GraphError(e.code, j.get("code", ""), j.get("message", str(e)))
            except urllib.error.URLError as e:
                raise GraphError(0, "network", f"Kan Microsoft niet bereiken ({e.reason}).")

    def paged(self, path, params=None, limit=None, tz=False):
        out, url, absolute = [], path, False
        while url:
            j = self.req("GET", url, params=None if absolute else params, absolute=absolute, tz=tz)
            out += j.get("value", [])
            if limit and len(out) >= limit:
                return out[:limit]
            url, absolute = j.get("@odata.nextLink"), True
        return out


def _u(address):
    return "/users/" + urllib.parse.quote(address)


def _q(s):
    return (s or "").replace("'", "''")


class MsMail:
    """Mailboxen, mappen en berichten bij Microsoft 365."""

    def __init__(self, graph):
        self.g = graph
        self._wk = {}       # adres -> {folderId: sleutel}
        self._fc = {}       # adres -> (tijd, mappen)
        self._lock = threading.Lock()

    # -- mappen
    def wellknown(self, address):
        if address not in self._wk:
            wk = {}
            for gname, key in WELLKNOWN:
                try:
                    wk[self.g.req("GET", f"{_u(address)}/mailFolders/{gname}", params={"$select": "id"})["id"]] = key
                except GraphError as e:
                    if e.status not in (404, 400):
                        raise
            self._wk[address] = wk
        return self._wk[address]

    def invalidate(self, *addresses):
        with self._lock:
            for a in addresses:
                self._fc.pop(a, None)

    def folders(self, address, max_age=20):
        """Platte lijst in boomvolgorde: id, name, parent, wk, unread, total, depth, has_children."""
        with self._lock:
            hit = self._fc.get(address)
        if hit and time.time() - hit[0] < max_age:
            return hit[1]
        wk = self.wellknown(address)
        top = self.g.paged(f"{_u(address)}/mailFolders", {"$top": 100, "$select": FOLDER_SEL})
        children, count = {}, len(top)

        def load(parent_id):
            nonlocal count
            if count > MAX_FOLDERS:
                return []
            kids = self.g.paged(f"{_u(address)}/mailFolders/{parent_id}/childFolders", {"$top": 100, "$select": FOLDER_SEL})
            count += len(kids)
            return kids

        order = [k for _, k in WELLKNOWN]
        out = []

        def walk(nodes, depth, parent):
            if depth == 0:
                nodes = sorted(nodes, key=lambda f: (order.index(wk[f["id"]]) if f["id"] in wk else 99, f["displayName"].lower()))
            else:
                nodes = sorted(nodes, key=lambda f: f["displayName"].lower())
            for f in nodes:
                out.append({"id": f["id"], "name": f["displayName"], "parent": parent, "wk": wk.get(f["id"], ""),
                            "unread": f.get("unreadItemCount", 0), "total": f.get("totalItemCount", 0),
                            "depth": depth, "has_children": f.get("childFolderCount", 0) > 0})
                if f.get("childFolderCount", 0) > 0 and depth < 12:
                    if f["id"] not in children:
                        children[f["id"]] = load(f["id"])
                    walk(children[f["id"]], depth + 1, f["id"])

        walk(top, 0, None)
        with self._lock:
            self._fc[address] = (time.time(), out)
        return out

    def create_folder(self, address, parent_id, name):
        path = f"{_u(address)}/mailFolders" + (f"/{parent_id}/childFolders" if parent_id else "")
        f = self.g.req("POST", path, {"displayName": name})
        self.invalidate(address)
        return f["id"]

    def rename_folder(self, address, folder_id, name):
        self.g.req("PATCH", f"{_u(address)}/mailFolders/{folder_id}", {"displayName": name})
        self.invalidate(address)

    def delete_folder(self, address, folder_id):
        # Bij Microsoft gaat een verwijderde map (met inhoud) naar Verwijderde items.
        self.g.req("DELETE", f"{_u(address)}/mailFolders/{folder_id}")
        self.invalidate(address)

    def move_folder(self, address, folder_id, dest_id):
        self.g.req("POST", f"{_u(address)}/mailFolders/{folder_id}/move", {"destinationId": dest_id})
        self.invalidate(address)

    # -- berichten
    def list_since(self, address, folder_id, since=None):
        """Alle mails in een map vanaf een datum (zonder delta; reserve als delta niet mag)."""
        p = {"$top": 100, "$select": SEL_LIST, "$orderby": "receivedDateTime desc"}
        if since:
            p["$filter"] = f"receivedDateTime ge {since}"
        return self.g.paged(f"{_u(address)}/mailFolders/{folder_id}/messages", p)

    def list(self, address, folder_id, filt=None, search=None, top=50, before=None):
        p = {"$top": top, "$select": SEL_LIST}
        if search:
            p["$search"] = '"' + search.replace('"', "") + '"'
        else:
            p["$orderby"] = "receivedDateTime desc"
            conds = ["receivedDateTime lt " + before if before else "receivedDateTime ge 1900-01-01T00:00:00Z"]
            extra = {"ongelezen": "isRead eq false", "gemarkeerd": "flag/flagStatus eq 'flagged'"}.get(filt)
            if extra:
                conds.append(extra)
            if before or extra:
                p["$filter"] = " and ".join(conds)
        return self.g.req("GET", f"{_u(address)}/mailFolders/{folder_id}/messages", params=p).get("value", [])

    def list_category(self, address, name, top=50):
        p = {"$top": top, "$select": SEL_LIST, "$filter": f"categories/any(c:c eq '{_q(name)}')"}
        items = self.g.req("GET", f"{_u(address)}/messages", params=p).get("value", [])
        return sorted(items, key=lambda m: m.get("receivedDateTime") or "", reverse=True)

    def sizes(self, address, folder_id, since=None):
        """Grootte van de berichten in een map (PR_MESSAGE_SIZE), als {id: bytes}."""
        p = {"$top": 100, "$select": "id", "$expand": "singleValueExtendedProperties($filter=id eq 'Integer 0x0E08')"}
        if since:
            p["$filter"] = f"receivedDateTime ge {since}"
        out = {}
        for m in self.g.paged(f"{_u(address)}/mailFolders/{folder_id}/messages", p):
            for x in m.get("singleValueExtendedProperties") or []:
                try:
                    out[m["id"]] = int(x.get("value"))
                except (TypeError, ValueError):
                    pass
        return out

    def get(self, address, mid, full=True):
        return self.g.req("GET", f"{_u(address)}/messages/{mid}", params={"$select": SEL_FULL if full else SEL_LIST})

    def inline_images(self, address, mid, html):
        """Vervang src="cid:..." door de ingesloten afbeelding, zodat logo's en plaatjes in de mail zichtbaar zijn."""
        if "cid:" not in (html or ""):
            return html
        try:
            atts = self.g.paged(f"{_u(address)}/messages/{mid}/attachments", {"$top": 50})
        except GraphError:
            return html
        for a in atts:
            cid, data = (a.get("contentId") or "").strip("<>"), a.get("contentBytes")
            if cid and data and a.get("size", 0) < 2_000_000 and (a.get("contentType") or "").startswith("image/"):
                html = html.replace(f"cid:{cid}", f"data:{a['contentType']};base64,{data}")
        return html

    def patch(self, address, mid, data):
        return self.g.req("PATCH", f"{_u(address)}/messages/{mid}", data)

    def move(self, address, mid, dest):
        """dest = map-id of een vaste naam zoals 'deleteditems' of 'archive'."""
        m = self.g.req("POST", f"{_u(address)}/messages/{mid}/move", {"destinationId": dest})
        self.invalidate(address)
        return m

    def delete(self, address, mid):
        self.g.req("DELETE", f"{_u(address)}/messages/{mid}")
        self.invalidate(address)

    def copy_to_other_mailbox(self, src, mid, dst, dest_folder, target=None):
        """Microsoft kan niet rechtstreeks tussen mailboxen verplaatsen. Daarom: bericht (met bijlagen)
        opnieuw aanmaken in de doelmailbox als gewoon ontvangen bericht. Geeft (nieuw id, waarschuwingen)."""
        m = self.get(src, mid)
        props = [{"id": "Integer 0x0E07", "value": "1"}]  # geen concept; 'gelezen' zetten we hieronder goed
        if m.get("receivedDateTime"):
            props.append({"id": "SystemTime 0x0E06", "value": m["receivedDateTime"]})
        if m.get("sentDateTime"):
            props.append({"id": "SystemTime 0x0039", "value": m["sentDateTime"]})
        new = {k: m[k] for k in ("subject", "body", "from", "toRecipients", "ccRecipients", "replyTo", "importance",
                                 "categories", "flag") if m.get(k) is not None}
        new["singleValueExtendedProperties"] = props
        t = target or self  # schrijven in de doelmailbox gebeurt met het account van die mailbox
        created = t.g.req("POST", f"{_u(dst)}/mailFolders/{dest_folder}/messages", new)
        nid, warnings = created["id"], []
        try:
            if m.get("hasAttachments") or 'src="cid:' in (m.get("body") or {}).get("content", ""):
                atts = self.g.paged(f"{_u(src)}/messages/{mid}/attachments", {"$top": 50})
                for a in atts:
                    kind = a.get("@odata.type", "")
                    if kind != "#microsoft.graph.fileAttachment":
                        warnings.append(f"Bijlage '{a.get('name')}' (een ingesloten item) kon niet worden meegenomen.")
                        continue
                    if a.get("size", 0) < 3_000_000 and a.get("contentBytes"):
                        body = {"@odata.type": kind, "name": a.get("name"), "contentType": a.get("contentType"),
                                "contentBytes": a["contentBytes"], "isInline": a.get("isInline", False)}
                        if a.get("contentId"):
                            body["contentId"] = a["contentId"]
                        t.g.req("POST", f"{_u(dst)}/messages/{nid}/attachments", body)
                    else:
                        self._upload_large(src, mid, a, dst, nid, t)
            if not m.get("isRead"):
                t.patch(dst, nid, {"isRead": False})
        except GraphError as e:
            warnings.append("Niet alle bijlagen konden worden meegenomen: " + nl_error(e))
        t.invalidate(dst)
        return nid, warnings

    def _upload_large(self, src, mid, a, dst, nid, t=None):
        t = t or self
        raw = self.g.req("GET", f"{_u(src)}/messages/{mid}/attachments/{a['id']}")
        data = base64.b64decode(raw.get("contentBytes") or "")
        sess = t.g.req("POST", f"{_u(dst)}/messages/{nid}/attachments/createUploadSession",
                          {"AttachmentItem": {"attachmentType": "file", "name": a.get("name"), "size": len(data),
                                              "isInline": a.get("isInline", False), "contentId": a.get("contentId")}})
        url, step = sess["uploadUrl"], 3_276_800  # veelvoud van 320 KiB
        for start in range(0, len(data), step):
            chunk = data[start:start + step]
            rq = urllib.request.Request(url, data=chunk, method="PUT", headers={
                "Content-Type": "application/octet-stream", "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{start + len(chunk) - 1}/{len(data)}"})
            urllib.request.urlopen(rq, timeout=120).read()

    def send(self, address, subject, html, to, cc):
        # Afbeeldingen die als data-URI in de tekst staan (bijv. logo in de handtekening) worden
        # inline-bijlagen; veel mailprogramma's tonen data-URI's anders niet.
        atts, n = [], 0

        def repl(mo):
            nonlocal n
            n += 1
            cid = f"img{n}@plakzicht"
            atts.append({"@odata.type": "#microsoft.graph.fileAttachment", "name": f"afbeelding{n}.{mo.group(1).split('/')[-1].split('+')[0]}",
                         "contentType": mo.group(1), "contentBytes": mo.group(2), "isInline": True, "contentId": cid})
            return f'src="cid:{cid}"'

        html = re.sub(r'src="data:(image/[a-z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)"', repl, html, flags=re.I)
        rcpt = lambda s: [{"emailAddress": {"address": a}} for a in re.split(r"[;,\s]+", s or "") if "@" in a]
        msg = {"subject": subject, "body": {"contentType": "HTML", "content": html}, "toRecipients": rcpt(to)}
        if rcpt(cc):
            msg["ccRecipients"] = rcpt(cc)
        if atts:
            msg["attachments"] = atts
        self.g.req("POST", f"{_u(address)}/sendMail", {"message": msg, "saveToSentItems": True})
        self.invalidate(address)

    def mime(self, address, mid):
        return self.g.raw(f"{_u(address)}/messages/{mid}/$value")

    def delta_start(self, address, folder_id, since=None):
        """since = ISO-datum: alleen mails vanaf die datum (Outlook-stijl 'offline bewaren')."""
        p = {"$select": SEL_LIST}
        if since:
            p["$filter"] = f"receivedDateTime ge {since}"
            p["$orderby"] = "receivedDateTime desc"
        return f"{GRAPH}{_u(address)}/mailFolders/{folder_id}/messages/delta?" + urllib.parse.urlencode(p, quote_via=urllib.parse.quote)

    def delta_page(self, url):
        return self.g.req("GET", url, absolute=True)

    def check_mailbox(self, address):
        return self.g.req("GET", f"{_u(address)}/mailFolders/inbox", params={"$select": "id,displayName,totalItemCount"})


# ---------------------------------------------------------------- agenda
class MsCalendar:
    """Agenda van het aangemelde account (/me). Tijden in Nederlandse tijd."""

    def __init__(self, g):
        self.g = g

    def calendars(self):
        return self.g.paged("/me/calendars", {"$select": "id,name,color,hexColor,canEdit,isDefaultCalendar,owner", "$top": 50})

    def view(self, cal_id, start, end):
        return self.g.paged(f"/me/calendars/{cal_id}/calendarView", {"startDateTime": start, "endDateTime": end, "$select": CAL_SEL,
                                                                    "$top": 200, "$orderby": "start/dateTime"}, limit=1000, tz=True)

    def get(self, eid):
        return self.g.req("GET", f"/me/events/{eid}", params={"$select": CAL_SEL + ",body"}, tz=True)

    def create(self, cal_id, ev):
        return self.g.req("POST", f"/me/calendars/{cal_id}/events", ev, tz=True)

    def update(self, eid, ev):
        return self.g.req("PATCH", f"/me/events/{eid}", ev, tz=True)

    def delete(self, eid):
        self.g.req("DELETE", f"/me/events/{eid}")


# ---------------------------------------------------------------- aanmelden met Microsoft (PKCE)
class SignIn:
    """Meldt een account aan via de standaardbrowser. Microsoft stuurt de browser terug naar
    http://localhost:<poort>/ op deze pc; daar vangt een tijdelijk servertje de code op."""

    TIMEOUT = 300

    def __init__(self, tenant, client_id, scope=None):
        self._scope = scope or DELEGATED_SCOPES
        if not (tenant and client_id):
            raise GraphError(0, "config", "Vul eerst tenant-ID en client-ID in en klik op Opslaan.")
        self.tenant, self.client_id = tenant.strip(), client_id.strip()
        self.status = {"state": "waiting", "message": "Wachten op aanmelden in de browser…"}
        self.result = None
        self._verifier = secrets.token_urlsafe(64)
        self._state = secrets.token_urlsafe(16)
        self._servers = []

    def start(self):
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self._verifier.encode()).digest()).decode().rstrip("=")
        me = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
                if "code" not in q and "error" not in q:
                    self.send_response(404); self.end_headers(); return
                ok, msg = me._finish(q)
                body = (f"<!doctype html><meta charset=utf-8><title>Plakzicht Mail</title>"
                        f"<body style=\"font:16px system-ui;padding:40px;color:#1d2320\"><h2 style=\"color:{'#1f6f54' if ok else '#b3261e'}\">"
                        f"{'Aangemeld' if ok else 'Aanmelden mislukt'}</h2><p>{msg}</p>"
                        f"<p>Je kunt dit venster sluiten en teruggaan naar Plakzicht Mail.</p></body>").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                threading.Thread(target=me.stop, daemon=True).start()

        srv = HTTPServer(("127.0.0.1", 0), H)
        port = srv.server_address[1]
        self._servers.append(srv)
        try:  # ook IPv6, want 'localhost' kan naar ::1 gaan
            class H6(HTTPServer):
                address_family = socket.AF_INET6
            self._servers.append(H6(("::1", port), H))
        except OSError:
            pass
        for s in self._servers:
            threading.Thread(target=s.serve_forever, daemon=True).start()
        t = threading.Timer(self.TIMEOUT, self._timeout)
        t.daemon = True
        t.start()
        self.redirect = f"http://localhost:{port}"  # zonder pad, zodat het overeenkomt met de geregistreerde http://localhost
        return f"{LOGIN}/{urllib.parse.quote(self.tenant)}/oauth2/v2.0/authorize?" + urllib.parse.urlencode({
            "client_id": self.client_id, "response_type": "code", "redirect_uri": self.redirect,
            "response_mode": "query", "scope": self._scope, "state": self._state,
            "code_challenge": challenge, "code_challenge_method": "S256", "prompt": "select_account"},
            quote_via=urllib.parse.quote)

    def _finish(self, q):
        if self.status["state"] != "waiting":
            return False, "Deze aanmelding is al afgerond."
        if q.get("state") != self._state:
            self.status = {"state": "error", "message": "Ongeldig antwoord van Microsoft (state klopt niet). Probeer opnieuw."}
            return False, self.status["message"]
        if "error" in q:
            e = GraphError(400, q.get("error", ""), q.get("error_description", ""))
            msg = "Aanmelden geannuleerd." if q.get("error") == "access_denied" and "AADSTS65004" in q.get("error_description", "") else nl_error(e)
            self.status = {"state": "error", "message": msg}
            return False, msg
        try:
            j = _token_request(self.tenant, {"client_id": self.client_id, "grant_type": "authorization_code",
                                             "code": q["code"], "redirect_uri": self.redirect,
                                             "code_verifier": self._verifier, "scope": self._scope})
        except GraphError as e:
            self.status = {"state": "error", "message": nl_error(e)}
            return False, self.status["message"]
        if not j.get("refresh_token"):
            self.status = {"state": "error", "message": "Microsoft gaf geen blijvende aanmelding terug (offline_access ontbreekt)."}
            return False, self.status["message"]
        cl = _id_claims(j.get("id_token", ""))
        account = cl.get("preferred_username") or cl.get("upn") or cl.get("email") or ""
        self.result = {"refresh_token": j["refresh_token"], "account": account, "name": cl.get("name") or account}
        self.status = {"state": "ok", "message": f"Aangemeld als {self.result['name']} ({account}).", "account": account}
        return True, self.status["message"]

    def _timeout(self):
        if self.status["state"] == "waiting":
            self.status = {"state": "error", "message": "Er is binnen 5 minuten niet aangemeld. Probeer het opnieuw."}
        self.stop()

    def stop(self):
        for s in self._servers:
            try:
                s.shutdown(); s.server_close()
            except Exception:  # noqa: BLE001
                pass
        self._servers = []


class DeviceSignIn:
    """Aanmelden met een code (werkt vanaf elke pc of telefoon): ga naar microsoft.com/devicelogin
    en vul de code in. Vereist 'Openbare clientstromen toestaan' = Ja in de app-registratie."""

    def __init__(self, tenant, client_id, scope=None):
        self._scope = scope or DELEGATED_SCOPES
        if not (tenant and client_id):
            raise GraphError(0, "config", "Vul eerst tenant-ID en client-ID in en klik op Opslaan.")
        self.tenant, self.client_id = tenant.strip(), client_id.strip()
        self.status = {"state": "waiting", "message": "Wachten op aanmelden…"}
        self.result = None
        self._stop = threading.Event()

    def start(self):
        url = f"{LOGIN}/{urllib.parse.quote(self.tenant)}/oauth2/v2.0/devicecode"
        try:
            rq = urllib.request.Request(url, data=urllib.parse.urlencode({"client_id": self.client_id, "scope": self._scope}).encode(), method="POST")
            with urllib.request.urlopen(rq, timeout=30) as r:
                j = json.loads(r.read())
        except urllib.error.HTTPError as e:
            try:
                j = json.loads(e.read())
            except ValueError:
                j = {}
            raise GraphError(e.code, j.get("error", ""), (j.get("error_description") or str(e)).split("\r\n")[0])
        except urllib.error.URLError as e:
            raise GraphError(0, "network", f"Kan Microsoft niet bereiken ({e.reason}).")
        self._device, self._interval = j["device_code"], int(j.get("interval", 5))
        self._deadline = time.time() + int(j.get("expires_in", 900))
        self.status.update({"code": j["user_code"], "url": j.get("verification_uri", "https://microsoft.com/devicelogin")})
        threading.Thread(target=self._poll, daemon=True).start()
        return {"code": j["user_code"], "url": self.status["url"]}

    def _poll(self):
        while not self._stop.wait(self._interval):
            if time.time() > self._deadline:
                self.status = {"state": "error", "message": nl_error(GraphError(400, "expired_token", ""))}
                return
            try:
                j = _token_request(self.tenant, {"client_id": self.client_id, "device_code": self._device,
                                                 "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
            except GraphError as e:
                if e.code == "authorization_pending":
                    continue
                if e.code == "slow_down":
                    self._interval += 5
                    continue
                self.status = {"state": "error", "message": nl_error(e)}
                return
            if not j.get("refresh_token"):
                self.status = {"state": "error", "message": "Microsoft gaf geen blijvende aanmelding terug (offline_access ontbreekt)."}
                return
            cl = _id_claims(j.get("id_token", ""))
            account = cl.get("preferred_username") or cl.get("upn") or cl.get("email") or ""
            self.result = {"refresh_token": j["refresh_token"], "account": account, "name": cl.get("name") or account}
            self.status = {"state": "ok", "message": f"Aangemeld als {self.result['name']} ({account}).", "account": account}
            return

    def stop(self):
        self._stop.set()
