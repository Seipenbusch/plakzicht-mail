"""Koppeling met Plakzicht (alleen lezen).

Plakzicht heeft een kleine API voor Plakzicht Mail (Plakzicht › Instellingen › Plakzicht Mail). Hiermee
vraagt het mailprogramma orders en offertes op voor het paneel naast een mail. Er wordt niets gewijzigd.
Antwoorden worden een paar minuten bewaard, zodat Plakzicht (en Marello daarachter) niet bij elke mail
opnieuw wordt bevraagd.
"""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

PREFIX = "/api/mail/v1"
TTL = {"order": 120, "offerte": 120, "klant": 300, "zoek": 30, "verzend": 300, "status": 10}
MISS_TTL = 300   # 'niet gevonden' ook even onthouden


class PlakzichtError(Exception):
    pass


class PlakzichtApi:
    def __init__(self, url, key, timeout=10):
        self.url = (url or "").rstrip("/")
        self.key = key or ""
        self.timeout = timeout
        self._cache = {}
        self._lock = threading.Lock()

    def _get(self, kind, path, params=None, ttl=None):
        """GET op de API; geeft het JSON-antwoord, of None bij 'niet gevonden'."""
        if not self.url or not self.key:
            raise PlakzichtError("De koppeling met Plakzicht is nog niet ingesteld (Beheer › Herkenning en Plakzicht).")
        full = self.url + PREFIX + path + ("?" + urllib.parse.urlencode(params) if params else "")
        now = time.time()
        with self._lock:
            hit = self._cache.get(full)
            if hit and now - hit[0] < hit[2]:
                return hit[1]
        rq = urllib.request.Request(full, headers={"Authorization": "Bearer " + self.key, "Accept": "application/json",
                                                   "User-Agent": "PlakzichtMail/1.0"})
        try:
            with urllib.request.urlopen(rq, timeout=self.timeout) as r:
                ctype = r.headers.get("Content-Type", "")
                raw = r.read()
            if "json" not in ctype:
                raise PlakzichtError("Plakzicht gaf geen geldig antwoord. Klopt het adres? Gebruik het adres in het netwerk, "
                                     "niet het adres achter Cloudflare Access.")
            data = json.loads(raw)
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read()).get("fout") or ""
            except ValueError:
                msg = ""
            if e.code == 404:
                with self._lock:
                    self._cache[full] = (now, None, MISS_TTL)
                return None
            raise PlakzichtError({
                401: "Plakzicht weigert de API-sleutel. Maak in Plakzicht › Instellingen › Plakzicht Mail een nieuwe sleutel en vul die hier in.",
                403: msg or "Plakzicht staat deze koppeling niet toe (staat de koppeling aan, klopt het toegestane adres?).",
                429: msg or "Even te veel verzoeken aan Plakzicht; probeer het zo opnieuw.",
                502: msg or "Plakzicht kon Marello niet bereiken.",
                503: msg or "Plakzicht is nog niet klaar (Marello niet ingesteld).",
            }.get(e.code, f"Plakzicht gaf een fout ({e.code}). {msg}".strip())) from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise PlakzichtError(f"Plakzicht is niet bereikbaar op {self.url} ({getattr(e, 'reason', e)}).") from None
        except ValueError:
            raise PlakzichtError("Plakzicht gaf een onleesbaar antwoord.") from None
        with self._lock:
            self._cache[full] = (now, data, ttl or TTL.get(kind, 60))
            if len(self._cache) > 3000:   # niet eindeloos groeien
                for k in sorted(self._cache, key=lambda k: self._cache[k][0])[:1000]:
                    self._cache.pop(k, None)
        return data

    def clear(self):
        with self._lock:
            self._cache.clear()

    # -- functies
    def status(self):
        return self._get("status", "/status", ttl=0.1)

    def order(self, nr):
        return self._get("order", "/order/" + urllib.parse.quote(str(nr).strip()))

    def quote(self, nr):
        return self._get("offerte", "/offerte/" + urllib.parse.quote(str(nr).strip()))

    def search(self, q):
        return self._get("zoek", "/zoek", {"q": q}) or {"orders": [], "offertes": []}

    def customer(self, email):
        return self._get("klant", "/klant", {"email": email})

    def ship_dates(self, van, tot):
        return (self._get("verzend", "/verzenddatums", {"van": van, "tot": tot}) or {}).get("orders", [])
