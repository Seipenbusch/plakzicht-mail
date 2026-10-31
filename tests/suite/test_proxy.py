"""Achter Cloudflare (PLAKZICHT_TRUST_PROXY=1): echte adressen van de pc's voor het blokkeren na foute wachtwoorden
en in de apparatenlijst. Zonder die instelling wordt een meegestuurd adres genegeerd."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import Client, Server, expect_error, ok, stop_all  # noqa: E402

srv = Server(env={"PLAKZICHT_TRUST_PROXY": "1"})
try:
    bad = Client(srv.base, headers={"CF-Connecting-IP": "203.0.113.7"})
    for _ in range(10):
        expect_error(lambda: bad.call("login", "beheerder", "fout"), "klopt niet")
    expect_error(lambda: bad.call("login", "beheerder", "demo"), "te vaak")
    good = Client(srv.base, headers={"CF-Connecting-IP": "198.51.100.20"})
    good.call("login", "beheerder", "demo", True, "Mac · Safari")
    ok("blokkade na foute wachtwoorden geldt per echt adres, niet voor iedereen achter Cloudflare")
    dev = good.call("my_devices")["devices"][0]
    assert dev["ip"] == "198.51.100.20", dev
    ok("apparatenlijst toont het echte adres")
    assert good.call("backup_info")["trust_proxy"] is True
finally:
    srv.close()

srv = Server()
try:
    spoof = Client(srv.base, headers={"CF-Connecting-IP": "203.0.113.9"})
    spoof.call("login", "beheerder", "demo", True, "Windows · Edge")
    assert spoof.call("my_devices")["devices"][0]["ip"] == "127.0.0.1"
    ok("zonder PLAKZICHT_TRUST_PROXY wordt een meegestuurd adres genegeerd")
    print("OK")
finally:
    srv.close()
    stop_all()
