"""Hulpmiddelen voor de tests: een Plakzicht Mail-server starten in een eigen (tijdelijke) gegevensmap,
nagebootste Microsoft- en Claude-servers, en een eenvoudige client met cookies."""
import http.cookiejar
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(ROOT, "tests")
_PROCS = []


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def wait_port(port, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            socket.create_connection(("127.0.0.1", port), 0.3).close()
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"poort {port} komt niet op")


def start_proc(args, env=None, port=None, cwd=None):
    log = open(os.path.join(tempfile.gettempdir(), f"pm-test-{os.getpid()}-{len(_PROCS)}.log"), "w")
    p = subprocess.Popen(args, env={**os.environ, **(env or {})}, cwd=cwd or ROOT, stdout=log, stderr=subprocess.STDOUT)
    p.logfile = log.name
    _PROCS.append(p)
    if port:
        try:
            wait_port(port)
        except RuntimeError:
            print(open(log.name).read()[-3000:])
            raise
    return p


def stop(p):
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()


def stop_all():
    for p in _PROCS:
        stop(p)


class Server:
    """Plakzicht Mail in een eigen gegevensmap. restart() start hem opnieuw met dezelfde gegevens."""

    def __init__(self, data=None, env=None):
        self.data = data or tempfile.mkdtemp(prefix="pm-data-")
        self.env = {"PLAKZICHT_DATA": self.data, "PYTHONUNBUFFERED": "1", **(env or {})}
        self.port = free_port()
        self.p = None
        self.start()

    @property
    def base(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        self.p = start_proc([sys.executable, "app.py", "--server", "--host", "127.0.0.1", "--port", str(self.port)], self.env, self.port)

    def restart(self):
        stop(self.p)
        self.start()

    def log(self):
        return open(self.p.logfile).read()

    def close(self, remove=True):
        stop(self.p)
        if remove:
            shutil.rmtree(self.data, ignore_errors=True)


class Client:
    """Zoals de browser: cookies bewaren, API-aanroepen met de kop X-Plakzicht."""

    def __init__(self, base, headers=None):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.headers = headers or {}

    def raw(self, name, *args, headers=None):
        rq = urllib.request.Request(f"{self.base}/api/{name}", data=json.dumps(list(args)).encode(), method="POST",
                                    headers={"Content-Type": "application/json", "X-Plakzicht": "1", **self.headers, **(headers or {})})
        with self.op.open(rq, timeout=30) as r:
            return json.loads(r.read()), r.headers.get_all("Set-Cookie") or []

    def call(self, name, *args, **kw):
        j, _ = self.raw(name, *args, **kw)
        if not j["ok"]:
            raise ApiError(j["error"])
        return j["result"]

    def get(self, path):
        with self.op.open(self.base + path, timeout=10) as r:
            return r.status, r.read()

    def cookie(self, name):
        return next((c.value for c in self.jar if c.name == name), None)

    def cookies(self):
        return {c.name: c for c in self.jar}

    def set_cookie(self, name, value, like):
        """Cookie overnemen in een nieuwe client (zoals een browser die opnieuw is opgestart)."""
        c = like.cookies()[name] if isinstance(like, Client) else like
        import copy
        c2 = copy.copy(c)
        c2.value = value
        self.jar.set_cookie(c2)


class ApiError(Exception):
    pass


def expect_error(fn, contains=""):
    try:
        fn()
    except ApiError as e:
        assert contains.lower() in str(e).lower(), f"verwachtte '{contains}', kreeg '{e}'"
        return str(e)
    raise AssertionError(f"verwachtte een fout met '{contains}'")


def ok(msg):
    print("  ✓", msg)
