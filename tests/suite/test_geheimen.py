"""Geheimen in config.json: versleuteld met secrets.key (enc1:), oude waarden worden omgezet, gegevensmap via PLAKZICHT_DATA."""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import ROOT, Client, Server, ok, stop_all  # noqa: E402

data = tempfile.mkdtemp(prefix="pm-sec-")
# een oude configuratie (vorige versie op Linux/zonder DPAPI: 'plain:'), plus een Windows-waarde die hier niet te lezen is
old = {"mode": "demo", "auth": "user", "tenant": "t", "client_id": "c", "secret": "",
       "accounts": [{"id": "a1", "upn": "sven@x.nl", "name": "Sven", "refresh": "plain:rt-geheim"},
                    {"id": "a2", "upn": "anna@x.nl", "name": "Anna", "refresh": "dpapi:AAAA"}],
       "claude_key": "plain:sk-ant-test", "plakzicht": {"url": "http://pz", "key": "plain:pmk_123", "open": ""}}
json.dump(old, open(os.path.join(data, "config.json"), "w"))

srv = Server(data)
try:
    cfg = json.load(open(os.path.join(data, "config.json")))
    assert os.path.exists(os.path.join(data, "secrets.key"))
    assert cfg["accounts"][0]["refresh"].startswith("enc1:") and "rt-geheim" not in json.dumps(cfg)
    assert cfg["claude_key"].startswith("enc1:") and cfg["plakzicht"]["key"].startswith("enc1:")
    assert cfg["accounts"][1]["refresh"] == "dpapi:AAAA", "onleesbare Windows-waarde blijft staan"
    ok("oude waarden omgezet naar enc1:, secrets.key aangemaakt in de gegevensmap")
    if os.name != "nt":
        assert oct(os.stat(os.path.join(data, "secrets.key")).st_mode & 0o777) == "0o600"
        ok("secrets.key alleen leesbaar voor de server")

    # ontsleutelen werkt in de app zelf
    code = ("import app, json; c = app.CFG; print(app._unprotect(c['accounts'][0]['refresh']), app._unprotect(c['claude_key']));"
            "\ntry:\n    app._unprotect(c['accounts'][1]['refresh'])\nexcept app.SecretUnreadable as e:\n    print('FOUT', e)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env={**os.environ, "PLAKZICHT_DATA": data},
                         capture_output=True, text=True, timeout=60).stdout
    assert "rt-geheim sk-ant-test" in out and "FOUT" in out and "Windows" in out, out
    ok("ontsleutelen werkt; Windows-waarde geeft een duidelijke melding")

    # verkeerde sleutel (bijv. back-up teruggezet zonder secrets.key)
    other = tempfile.mkdtemp(prefix="pm-sec2-")
    json.dump(cfg, open(os.path.join(other, "config.json"), "w"))
    out = subprocess.run([sys.executable, "-c", code.replace("print(app._unprotect(c['accounts'][0]['refresh']), app._unprotect(c['claude_key']));",
                                                            "\ntry:\n    app._unprotect(c['claude_key'])\nexcept app.SecretUnreadable as e:\n    print('SLEUTEL', e)\n")],
                         cwd=ROOT, env={**os.environ, "PLAKZICHT_DATA": other}, capture_output=True, text=True, timeout=60).stdout
    assert "SLEUTEL" in out and "secrets.key" in out, out
    ok("andere secrets.key: duidelijke melding in plaats van een crash")

    # sleutel via omgevingsvariabele (Docker-geheim)
    from cryptography.fernet import Fernet
    k = Fernet.generate_key().decode()
    third = tempfile.mkdtemp(prefix="pm-sec3-")
    json.dump({"mode": "demo", "claude_key": "plain:sk-x"}, open(os.path.join(third, "config.json"), "w"))
    out = subprocess.run([sys.executable, "-c", "import app; print(app.CFG['claude_key'][:5], app._unprotect(app.CFG['claude_key']))"],
                         cwd=ROOT, env={**os.environ, "PLAKZICHT_DATA": third, "PLAKZICHT_SECRETS_KEY": k}, capture_output=True, text=True, timeout=60).stdout
    assert out.split() == ["enc1:", "sk-x"] and not os.path.exists(os.path.join(third, "secrets.key")), out
    assert Fernet(k.encode()).decrypt(json.load(open(os.path.join(third, "config.json")))["claude_key"][5:].encode()) == b"sk-x"
    ok("PLAKZICHT_SECRETS_KEY gebruikt (geen bestand nodig)")

    # alles in de gegevensmap, niets in de programmamap
    c = Client(srv.base)
    c.call("login", "beheerder", "demo")
    st = c.call("backup_make")
    assert os.path.isdir(os.path.join(data, "backups", st)) and os.path.exists(os.path.join(data, "mail_demo.db"))
    assert not os.path.exists(os.path.join(data, "backups", st, "secrets.key")), "sleutel hoort niet in de back-up"
    info = c.call("backup_info")
    assert info["data"] == data and info["docker"] is False
    ok("database, back-ups en sleutel in de gegevensmap; sleutel niet in de back-up")

    s, body = Client(srv.base).get("/health")
    assert s == 200 and json.loads(body)["ok"] is True
    ok("/health antwoordt")
    print("OK")
finally:
    srv.close()
    stop_all()
