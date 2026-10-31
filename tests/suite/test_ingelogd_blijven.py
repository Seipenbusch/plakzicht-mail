"""Ingelogd blijven: na een herstart van de pc (nieuwe browser met alleen het cookie) en van de server."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import Client, Server, expect_error, ok, stop_all  # noqa: E402


def fresh(srv, keep_from=None):
    """Nieuwe browser na een herstart: alleen het 'ingelogd blijven'-cookie is er nog."""
    c = Client(srv.base)
    if keep_from:
        c.set_cookie("pmkeep", keep_from.cookie("pmkeep"), keep_from)
    return c


srv = Server()
try:
    a = Client(srv.base)
    info = a.call("app_info")
    assert info["remember"] == 30, info
    ok("standaard: ingelogd blijven aan, 30 dagen")

    # zonder vinkje: geen blijvend cookie
    a.call("login", "medewerker-a", "demo", False, "Windows · Edge")
    assert not a.cookie("pmkeep")
    assert "Max-Age" not in str(a.raw("state")[1])
    expect_error(lambda: fresh(srv).call("state"), "niet ingelogd")
    ok("zonder vinkje blijft niemand ingelogd")

    # met vinkje
    a = Client(srv.base)
    _, cookies = a.raw("login", "medewerker-a", "demo", True, "Windows · Plakzicht Mail-app")
    keep = [c for c in cookies if c.startswith("pmkeep=")][0]
    assert "HttpOnly" in keep and "Max-Age=2592000" in keep and "Secure" not in keep, keep
    assert a.cookie("pmkeep").count(".") == 1
    ok("met vinkje: HttpOnly-cookie voor 30 dagen")

    b = fresh(srv, a)
    st = b.call("state")
    assert st["user"]["username"] == "medewerker-a"
    assert b.cookie("pmsid"), "na herstel hoort er een nieuwe sessie te zijn"
    ok("nieuwe browser met alleen het cookie is direct ingelogd")

    srv.restart()
    c = fresh(srv, a)
    assert c.call("state")["user"]["username"] == "medewerker-a"
    ok("ook na een herstart van de server")

    # het cookie zelf staat niet in de database, alleen een hash
    import sqlite3
    db = sqlite3.connect(os.path.join(srv.data, "mail_demo.db"))
    token = a.cookie("pmkeep")
    row = db.execute("SELECT id, hash, device FROM remember").fetchone()
    assert token.split(".")[1] not in row[1] and row[0] == token.split(".")[0] and row[2] == "Windows · Plakzicht Mail-app"
    ok("database bevat alleen een hash van de sleutel")

    # vervalst cookie
    bad = Client(srv.base)
    bad.set_cookie("pmkeep", token.split(".")[0] + ".verkeerd", a)
    expect_error(lambda: bad.call("state"), "niet ingelogd")
    ok("vervalst cookie werkt niet")

    # tweede apparaat, apparatenlijst
    m = Client(srv.base)
    m.call("login", "medewerker-a", "demo", True, "Mac · Safari")
    d = m.call("my_devices")
    assert len(d["devices"]) == 2 and [x["device"] for x in d["devices"] if x["current"]] == ["Mac · Safari"], d
    ok("apparatenlijst toont beide apparaten, 'dit apparaat' gemarkeerd")

    # één apparaat afmelden: de Windows-app moet opnieuw inloggen, ook de lopende sessie
    win_id = [x["id"] for x in d["devices"] if not x["current"]][0]
    m.call("device_logout", win_id)
    expect_error(lambda: c.call("state"), "niet ingelogd")
    expect_error(lambda: fresh(srv, a).call("state"), "niet ingelogd")
    assert m.call("state")["user"]["username"] == "medewerker-a"
    ok("apparaat afmelden werkt direct, ook voor de open sessie")

    # wachtwoord wijzigen meldt andere apparaten af, dit apparaat niet
    w = Client(srv.base)
    w.call("login", "medewerker-a", "demo", True, "Windows · Chrome")
    w_saved = fresh(srv, w)
    m.call("change_password", "demo", "nieuw-wachtwoord")
    expect_error(lambda: w.call("state"), "niet ingelogd")
    expect_error(lambda: w_saved.call("state"), "niet ingelogd")
    assert m.call("state") and fresh(srv, m).call("state")
    ok("wachtwoord wijzigen: andere apparaten afgemeld, dit apparaat blijft")

    # beheerder meldt medewerker overal af
    adm = Client(srv.base)
    adm.call("login", "beheerder", "demo", False, "")
    uid = m.call("state")["user"]["id"]
    users = adm.call("admin_data")["users"]
    assert [u["devices"] for u in users if u["id"] == uid] == [1]
    expect_error(lambda: m.call("user_logout_all", uid), "beheerder")
    m_saved = fresh(srv, m)
    adm.call("user_logout_all", uid)
    expect_error(lambda: m.call("state"), "niet ingelogd")
    expect_error(lambda: m_saved.call("state"), "niet ingelogd")
    ok("beheerder: overal afmelden")

    # uitloggen haalt het cookie weg
    x = Client(srv.base)
    x.call("login", "medewerker-b", "demo", True, "Mac · Chrome")
    saved = Client(srv.base)
    saved.set_cookie("pmkeep", x.cookie("pmkeep"), x)
    _, cookies = x.raw("logout")
    assert any(c.startswith("pmkeep=;") and "Max-Age=0" in c for c in cookies), cookies
    expect_error(lambda: saved.call("state"), "niet ingelogd")
    ok("uitloggen: cookie weg en ongeldig op de server")

    # uitzetten
    y = Client(srv.base)
    y.call("login", "medewerker-b", "demo", True, "Mac · Chrome")
    y_saved = fresh(srv, y)
    expect_error(lambda: adm.call("save_remember", 400), "365")
    adm.call("save_remember", 0)
    assert y.call("app_info")["remember"] == 0
    expect_error(lambda: y_saved.call("state"), "niet ingelogd")
    z = Client(srv.base)
    z.call("login", "medewerker-b", "demo", True, "Mac · Chrome")
    assert not z.cookie("pmkeep")
    ok("op 0 gezet: niemand blijft ingelogd, vinkje heeft geen effect")

    # korte termijn: verlopen na zoveel dagen zonder gebruik
    adm.call("save_remember", 1)
    q = Client(srv.base)
    q.call("login", "medewerker-b", "demo", True, "Mac · Chrome")
    db.execute("UPDATE remember SET last=?", (time.time() - 2 * 86400,))
    db.commit()
    expect_error(lambda: fresh(srv, q).call("state"), "niet ingelogd")
    ok("verloopt na het ingestelde aantal dagen zonder gebruik")

    # https achter Cloudflare: Secure-cookie
    h = Client(srv.base, headers={"X-Forwarded-Proto": "https"})
    _, cookies = h.raw("login", "medewerker-b", "demo", True, "Mac · Chrome")
    assert all("Secure" in c for c in cookies if c.startswith(("pmkeep=", "pmsid="))), cookies
    ok("via https: cookies met Secure")
    print("OK")
finally:
    srv.close()
    stop_all()
