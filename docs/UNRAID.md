# Plakzicht Mail op Unraid

```
 wijziging (pull request) ──► tests ──► samenvoegen in main
                                              │
                         GitHub bouwt ghcr.io/seipenbusch/plakzicht-mail:test
                         + het Windows-installatieprogramma (Releases › Nieuwste testversie)
                                              │
                  Actions › Versie vrijgeven  (één knop)
                                              ▼
                         :live  +  Releases › Plakzicht Mail <versie> (setup.exe)
                                              │
                  Unraid › Docker › Compose › plakzicht-mail › Update Stack
                                              ▼
            lokaal  http://<unraid>:8765        internet  https://mail.plakzicht.nl
```

Eén container, gegevens in `/mnt/user/appdata/plakzicht-mail`. Wil je een versie eerst proberen: zet tijdelijk `KANAAL=test` in de `.env` en *Update Stack*; terug met `KANAAL=live`.

---

## Eenmalig: de container (± 10 minuten)

1. **Ophalen mag al.** Unraid is voor Plakzicht al aangemeld bij `ghcr.io` met een token met *read:packages*; dat geldt voor al je packages, dus ook voor `plakzicht-mail`. (Nieuwe Unraid? Terminal: `docker login ghcr.io -u <github-naam>` en het token als wachtwoord.)
2. **Eerst een versie vrijgeven**: github.com › *plakzicht-mail* › **Actions › Versie vrijgeven › Run workflow** (bron leeg). Daarna bestaat `:live`.
3. **Stack aanmaken**: tab *Docker* › onderaan *Compose* › **Add New Stack** › naam `plakzicht-mail`.
   - tandwiel › **Edit Stack › Compose File**: plak de inhoud van `deploy/unraid/docker-compose.yml`.
   - tandwiel › **Edit Stack › ENV FILE**: plak `deploy/unraid/.env.voorbeeld` en pas aan (de tunnelregels komen hieronder).
4. **Gegevens overzetten** (van de Windows-pc waar Plakzicht Mail nu draait) – zie *Verhuizen* hieronder. Nieuw beginnen kan ook: dan maak je in de app een nieuwe beheerder aan (eerste login `beheerder` / `demo`, direct wijzigen!).
5. **Starten**: *Compose Up*. Open `http://<ip-van-unraid>:8765`. In *Beheer › Server en back-up* zie je *Draait als: Docker* en de versie.

### Verhuizen van de Windows-pc

De aanmeldingen bij Microsoft en de API-sleutels waren op Windows versleuteld met het Windows-account; die kan Unraid niet lezen. De nieuwe versie zet ze om naar een eigen sleutel (`secrets.key`) die overal werkt:

1. Zet de nieuwe versie op de Windows-pc over de oude map heen (zip van deze versie) en start **Start server.bat** één keer. In de map verschijnt `secrets.key`; in `config.json` staan de geheimen nu als `enc1:…`. Sluit het venster (of: *Verwijder dienst.bat* als hij als dienst draaide).
2. Kopieer naar `\\unraid\appdata\plakzicht-mail\`: **`config.json`**, **`secrets.key`**, **`mail_microsoft.db`** en **`mail_demo.db`**. (De lokale kopie van de mail in `mail_microsoft.db` wordt anders gewoon opnieuw opgehaald.)
3. Terminal op Unraid: `chown -R 99:100 /mnt/user/appdata/plakzicht-mail` (de container draait als *nobody:users*).
4. *Compose Up*. Iedereen logt één keer opnieuw in (vinkje *Ingelogd blijven* aan).

Stap 1 overgeslagen? Dan werkt alles behalve de geheimen: meld in *Beheer › Microsoft-koppeling* de accounts opnieuw aan (met een code op microsoft.com/devicelogin) en vul de Claude- en Plakzicht-sleutel opnieuw in.

> Zet de share `appdata` daarna weer af voor anderen: de database bevat mail en klantgegevens.

---

## Via internet: mail.plakzicht.nl (Cloudflare)

plakzicht.nl staat al bij Cloudflare en Access is al ingericht voor Plakzicht (zie de Plakzicht-handleiding). Voor de mail:

### 1. Access (eerst, dan staat de mail geen moment open)
Cloudflare › **Zero Trust › Access › Applications** › applicatie *Plakzicht* › *Edit* › bij de domeinen een regel **`mail.plakzicht.nl`** toevoegen. Zelfde policy (alleen jullie), zelfde inlogmethode (bij voorkeur Microsoft Entra ID).
- *Session duration*: bijvoorbeeld **1 maand**, anders vraagt Cloudflare vaker om aanmelden dan Plakzicht Mail zelf.

### 2. Tunnel
Cloudflare › **Zero Trust › Networks › Tunnels › Create a tunnel › Cloudflared**, naam `plakzicht-mail`.
- *Install connector* › **Docker** › kopieer alleen het **token** (na `--token`).
- *Public hostname*: `mail.plakzicht.nl`, service **HTTP** `plakzicht-mail:8765`.

In de **ENV FILE** van de stack:
```
COMPOSE_PROFILES=tunnel
TUNNEL_TOKEN=<token>
```
*Compose Up* (of *Update Stack*). Er draait nu ook `plakzicht-mail-tunnel`; in Cloudflare staat de tunnel op *Healthy*.

**Controle:** open `https://mail.plakzicht.nl` in een privévenster → eerst Cloudflare, dan het inlogscherm van Plakzicht Mail. In *Beheer › Server* staat *Achter Cloudflare/proxy: ja*.

> Liever geen extra tunnel? Voeg in de bestaande tunnel *plakzicht-live* een public hostname `mail.plakzicht.nl` toe met service **HTTP** `<ip-van-unraid>:8765`. Laat dan `COMPOSE_PROFILES` leeg.

Lokaal blijft gewoon werken via `http://<ip-van-unraid>:8765`. Via https (internet) werken ook de meldingen rechtsboven op de Mac en het installeren als app.

---

## Koppelingen controleren na de verhuizing

- **Microsoft**: *Beheer › Microsoft-koppeling* – accounts groen? Aanmelden gaat op de server altijd met een code (*Aanmelden met Microsoft* › code invullen op microsoft.com/devicelogin, vanaf elke pc of telefoon). Een omleidings-URI is niet nodig.
- **Plakzicht**: *Beheer › Herkenning en Plakzicht* – adres van Plakzicht **in het netwerk**, bijv. `http://<ip-van-unraid>:5000` (niet `app.plakzicht.nl`: dat zit achter Access). *Verbinding testen*. Had je in Plakzicht bij *Instellingen › Plakzicht Mail* toegestane IP-adressen ingevuld? Maak dat veld leeg of vul het adres in waarmee de container binnenkomt; de API-sleutel is de echte beveiliging.
- **Claude**: *Beheer › Claude* – *Verbinding testen*.

## Bijwerken

1. github.com › **Actions › Versie vrijgeven › Run workflow** (bron leeg = wat op test staat).
2. Unraid › *Docker › Compose* › `plakzicht-mail` › **Update Stack**. De mail is ± 10 seconden weg; wie *Ingelogd blijven* aan heeft, hoeft niet opnieuw in te loggen.

**Terug naar een vorige versie:** *Versie vrijgeven* met bron `build-<nummer>` (staat bij de run in *Bouwen (test)*) en daarna *Update Stack*.

## Back-ups

- Elke nacht om 02:30: `appdata/plakzicht-mail/backups/` (laatste 14). Zelf: *Beheer › Server en back-up › Nu back-up maken*.
- **`secrets.key`** staat bewust niet in die back-ups. Bewaar hem één keer apart (wachtwoordkluis). Zonder dat bestand moet je na het terugzetten de Microsoft-accounts en sleutels opnieuw invullen.
- Met de plugin **Appdata Backup** gaat de hele map (ook `secrets.key`) mee in je dagelijkse Unraid-back-up; zet die op een andere schijf of NAS.
- Terugzetten: *Compose Down*, `mail_microsoft.db` vervangen door die uit `backups/<datum>/`, *Compose Up*.

## Problemen

| Wat je ziet | Oplossing |
|---|---|
| *pull access denied* bij Update Stack | Token verlopen of geen `read:packages`: `docker login ghcr.io` opnieuw. Bestaat `:live` al (stap 2)? |
| Container start en stopt meteen | *Docker › plakzicht-mail › Logs*. Vaak rechten: `chown -R 99:100 /mnt/user/appdata/plakzicht-mail`. |
| "secrets.key hoort niet bij deze config.json" | De verkeerde of geen `secrets.key` meegekopieerd. Juiste terugzetten, of de geheimen opnieuw invullen. |
| "nog met Windows versleuteld" | Stap 1 van *Verhuizen* overgeslagen: accounts opnieuw aanmelden en sleutels opnieuw invullen. |
| mail.plakzicht.nl: *Error 1033* | Tunnelcontainer draait niet of token klopt niet: *Docker › plakzicht-mail-tunnel › Logs*. |
| mail.plakzicht.nl: *502* | Service in de tunnel moet `plakzicht-mail:8765` zijn (zelfde stack) of `<ip-van-unraid>:8765`. |
| Iedereen geblokkeerd na foute wachtwoorden | `PLAKZICHT_TRUST_PROXY: "1"` staat in de compose; staat die er niet, dan zien alle internetgebruikers er als één adres uit. |
