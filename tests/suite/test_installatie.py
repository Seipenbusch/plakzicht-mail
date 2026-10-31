"""Geïnstalleerde Windows-versie (PyInstaller) nagebootst: interface uit de ingepakte map, gegevens in ProgramData,
ingebakken versienummer, en standaard als server starten. Plus: de bestanden voor installatie en Docker kloppen."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from helpers import ROOT, free_port, ok, wait_port  # noqa: E402

bundle = tempfile.mkdtemp(prefix="pm-bundle-")
shutil.copytree(os.path.join(ROOT, "ui"), os.path.join(bundle, "ui"))
with open(os.path.join(bundle, "versie_build.py"), "w") as f:
    f.write("PLAKZICHT_VERSION = '2026.10.31-7'\n")
progdata = tempfile.mkdtemp(prefix="pm-progdata-")
port = free_port()
boot = f"""
import sys, runpy
sys.frozen = True
sys._MEIPASS = {bundle!r}
sys.path.insert(0, {bundle!r}); sys.path.insert(1, {ROOT!r})
sys.argv = ['Plakzicht Mail server.exe', '--port', '{port}', '--host', '127.0.0.1']
runpy.run_path({os.path.join(ROOT, 'app.py')!r}, run_name='__main__')
"""
env = {k: v for k, v in os.environ.items() if not k.startswith("PLAKZICHT_")}
env["PROGRAMDATA"] = progdata
p = subprocess.Popen([sys.executable, "-c", boot], env=env, cwd=tempfile.gettempdir(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
try:
    wait_port(port)
    import urllib.request
    h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/health").read())
    assert h["version"] == "2026.10.31-7", h
    page = urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html").read().decode()
    assert "manifest.webmanifest" in page
    assert os.path.exists(os.path.join(progdata, "Plakzicht Mail", "mail_demo.db"))
    ok("bevroren: start zonder --server als server, interface uit het pakket, gegevens in ProgramData, versie ingebakken")
except Exception:
    p.terminate()
    print(p.communicate(timeout=5)[0].decode()[-3000:])
    raise
finally:
    if p.poll() is None:
        p.terminate()
        p.wait(5)

# installatiebestanden
iss = open(os.path.join(ROOT, "installer", "plakzicht-mail.iss"), encoding="utf-8").read()
for needle in ("Dutch.isl", "werkplek-standaard.json", "{param:LOKAAL|}", "{param:INTERNET|https://mail.plakzicht.nl}", "dienst.ps1",
               "Plakzicht Mail server.exe", "Plakzicht Mail.exe", "/TYPE=werkplek"):
    assert needle in iss, needle
assert re.search(r"AppId=\{\{[0-9A-F-]{36}\}", iss)
ok("installatiescript: types, adrespagina, stille installatie en dienst")

wf = open(os.path.join(ROOT, ".github", "workflows", "bouwen.yml"), encoding="utf-8").read()
for name in ('--name "Plakzicht Mail"', '--name "Plakzicht Mail server"', 'installer/plakzicht-mail.iss', "installer/dienst.ps1", '--add-data "ui;ui"'):
    assert name in wf, name
ok("bouwstraat maakt beide programma's en het installatieprogramma")

docker = open(os.path.join(ROOT, "Dockerfile"), encoding="utf-8").read()
ign = open(os.path.join(ROOT, ".dockerignore"), encoding="utf-8").read()
for f in ("app.py", "graph.py", "mscache.py", "plakzicht.py"):
    assert f in docker and "!" + f in ign, f
mods = {m for m in re.findall(r"^from (\w+) import|^import (\w+)", open(os.path.join(ROOT, "app.py")).read(), re.M) for m in m if m}
local = {m for m in mods if os.path.exists(os.path.join(ROOT, m + ".py"))} - {"versie_build"}
assert local <= {"graph", "mscache", "plakzicht"}, f"nieuwe module {local} ook in Dockerfile en .dockerignore zetten"
ok("Dockerfile bevat alle modules")
print("OK")
