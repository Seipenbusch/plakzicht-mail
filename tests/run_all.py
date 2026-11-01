"""Alle tests draaien: python tests/run_all.py  (of één test: python tests/run_all.py test_werkplek)

Elke test start zijn eigen Plakzicht Mail-server in een tijdelijke gegevensmap, met waar nodig een
nagebootste Microsoft Graph. De interfacetest (test_interface) draait alleen als Playwright er is."""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = [
    "test_ingelogd_blijven",
    "test_geheimen",
    "test_proxy",
    "test_mscache_halve_wijzigingen",
    "test_microsoft",
    "test_werkplek",
    "test_installatie",
    "test_interface",
    "test_mobiel",
]


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("-")]
    todo = [t for t in TESTS if not want or t in want]
    unknown = set(want) - set(TESTS)
    if unknown:
        print("Onbekende test:", ", ".join(sorted(unknown)))
        return 2
    failed = []
    t_all = time.time()
    for t in todo:
        print(f"\n▶ {t}")
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, "suite", t + ".py")], cwd=os.path.dirname(HERE), timeout=600)
        print(f"  {'OK' if r.returncode == 0 else 'MISLUKT'} ({time.time() - t0:.0f} s)")
        if r.returncode:
            failed.append(t)
    print(f"\n{len(todo) - len(failed)} van {len(todo)} geslaagd in {time.time() - t_all:.0f} s")
    if failed:
        print("Mislukt:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
