# Plakzicht Mail – werkafspraken voor Claude

Plakzicht Mail is het gedeelde mailprogramma van Stickerwinkel: Microsoft 365-mailboxen via Microsoft Graph, eigen gebruikers,
en orders/offertes uit Plakzicht (alleen lezen). Python-server zonder framework (`ThreadingHTTPServer`) + SQLite, als Docker-container
op Unraid; werkplekken via de Windows-app (`werkplek/`) of de browser. Eigenaar: Sven.

## Werkafspraken
- **Antwoord altijd in het Nederlands.** Teksten in de app zijn ook Nederlands.
- **Pas code schrijven na een expliciete "go" van Sven.** Eerst voorstel/vragen, wijzigingen verzamelen, dan in één update bouwen.
  Een kleine hotfix waar Sven zelf direct om vraagt, telt als go.
- Lever op als **pull request** met een korte, Nederlandse titel en beschrijving (wat er verandert en wat Sven zelf nog moet doen).
  Niet zelf samenvoegen in `main`.

## Grenzen (niet zonder nieuw besluit van Sven)
- Plakzicht Mail **schrijft niets naar Plakzicht**: alleen lezen via de API van Plakzicht (`/api/mail/v1/…`).
- Microsoft: alleen de gedelegeerde rechten die nu gebruikt worden (mail, gedeelde mailboxen, versturen, agenda).
- Gebruikers zien alleen de mailboxen die de beheerder ze geeft; rechten altijd op de server controleren (`_user`, `_mb_ids`).

## Geheimen
- Nooit wachtwoorden, API-sleutels, refresh-tokens, tunneltokens of `secrets.key` in code, commits, logs of de chat.
- Geheimen in `config.json` altijd via `_protect()`/`_unprotect()` (`enc1:`); nieuwe geheime instellingen ook in `_secret_refs()`.
- Geheimen worden nooit teruggestuurd naar de interface (alleen "ingesteld ja/nee").
- *Ingelogd blijven*: in de database alleen een hash van de sleutel (`remember.hash`); het cookie is `HttpOnly`.

## Code
- `app.py`: API-methoden op `Api` (alles zonder `_` is aanroepbaar vanuit de interface), schema in `SCHEMA`, nieuwe kolommen via
  `init_db` (bestaande databases moeten blijven werken), instellingen in `settings`/`DEFAULT_SETTINGS`, per gebruiker in `users.prefs`.
- Gegevens altijd in `DATA` (gegevensmap), nooit naast de code: in Docker en de Windows-installatie is de programmamap alleen-lezen.
- Nieuwe Python-module? Ook in `Dockerfile` en `.dockerignore` (de test `test_installatie` controleert dat).
- Interface: `ui/app.js` (geen framework), `ui/style.css`. Controleer de layout op telefoonbreedte (390 px) en breed scherm.

## Testen
- `python tests/run_all.py` (± 1 min); één test: `python tests/run_all.py test_werkplek`.
- Nieuwe functionaliteit krijgt een test in `tests/suite/` en een plek in `TESTS` in `tests/run_all.py`.
- Elke pull request draait de tests en een proefbouw van de Docker-image (`.github/workflows/tests.yml`).

## Uitrol
- `main` → `ghcr.io/seipenbusch/plakzicht-mail:test` + Windows-setup bij *Releases › Nieuwste testversie*.
- *Actions › Versie vrijgeven* → `:live` + vaste release. Op Unraid: *Compose › plakzicht-mail › Update Stack* (`docs/UNRAID.md`).
- Wijzigt er iets in `deploy/unraid/` (compose of `.env`-voorbeeld), meld dan expliciet wat Sven op Unraid moet aanpassen;
  die bestanden worden daar niet automatisch bijgewerkt.
