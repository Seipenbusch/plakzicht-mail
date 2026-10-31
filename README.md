# Plakzicht Mail

Gedeelde mail voor de stickerwinkel: Microsoft 365-mailboxen (via Microsoft Graph) met eigen gebruikers, labels, toewijzen, agenda,
Claude, en orders en offertes uit [Plakzicht](https://github.com/Seipenbusch/Plakzicht) naast elke mail (alleen lezen).

| Waar | Hoe |
|---|---|
| **Server** | Docker op Unraid – [docs/UNRAID.md](docs/UNRAID.md). Lokaal `http://<unraid>:8765`, via internet `https://mail.plakzicht.nl` (Cloudflare Tunnel + Access). |
| **Windows** | `PlakzichtMail-setup.exe` (Releases), keuze *Werkplek* of *Server en app* – [docs/WINDOWS.md](docs/WINDOWS.md). |
| **Mac** | In de browser, als app te installeren – [docs/MAC.md](docs/MAC.md). |

Gebruik van de app zelf: [LEESMIJ.txt](LEESMIJ.txt).

## Ontwikkelen

```
pip install -r requirements.txt          # server
python app.py --server                   # http://localhost:8765 (demo: beheerder / demo)
python tests/run_all.py                  # alle tests (± 1 min); één test: python tests/run_all.py test_werkplek
```

- `app.py` – server, API, schema en migraties (`init_db`), sessies en *ingelogd blijven*, back-ups.
- `graph.py` – Microsoft Graph · `mscache.py` – lokale kopie en synchronisatie · `plakzicht.py` – Plakzicht-API (alleen lezen).
- `ui/` – scherm (`index.html`, `app.js`, `style.css`), app-profiel (`manifest.webmanifest`, `sw.js`, `icons/`).
- `werkplek/werkplek.py` – de Windows-app (venster, kiest zelf lokaal of internet).
- `installer/` – Inno Setup-script, dienst en icoon · `deploy/unraid/` – compose en `.env`-voorbeeld.
- Tests in `tests/suite/`, met nagebootste Microsoft Graph (`tests/fakegraph.py`) en Claude (`tests/fakeclaude.py`).

Gegevens staan in de **gegevensmap**: `PLAKZICHT_DATA` (Docker: `/data`), bij de Windows-installatie `C:\ProgramData\Plakzicht Mail`,
anders de programmamap. Geheimen in `config.json` zijn versleuteld (`enc1:`) met `secrets.key` of `PLAKZICHT_SECRETS_KEY`.

| Omgevingsvariabele | Betekenis |
|---|---|
| `PLAKZICHT_DATA` | gegevensmap |
| `PLAKZICHT_PORT` | poort (standaard 8765) |
| `PLAKZICHT_SECRETS_KEY` | sleutel voor geheimen (in plaats van `secrets.key`) |
| `PLAKZICHT_TRUST_PROXY=1` | achter Cloudflare: `CF-Connecting-IP` gebruiken voor het echte adres |
| `PLAKZICHT_DOCKER=1` | in de container (zet de image zelf) |

## Bouwen en vrijgeven

- **Pull request** → tests en een proefbouw van de Docker-image (`tests.yml`).
- **main** → tests, `ghcr.io/seipenbusch/plakzicht-mail:test`, en `PlakzichtMail-setup.exe` bij *Releases › Nieuwste testversie* (`bouwen.yml`).
- **Actions › Versie vrijgeven** → dezelfde image als `:live` en de setup als vaste release (`vrijgeven.yml`).
