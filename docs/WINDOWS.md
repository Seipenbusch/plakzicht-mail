# Plakzicht Mail op Windows

`PlakzichtMail-setup.exe` bevat Python en alle onderdelen; er hoeft niets vooraf geïnstalleerd te zijn.

**Downloaden:** github.com › *plakzicht-mail* › **Releases** › *Plakzicht Mail &lt;versie&gt;* › `PlakzichtMail-setup.exe`.
(De nieuwste, nog niet vrijgegeven versie staat bij *Nieuwste testversie*.)

Windows waarschuwt de eerste keer voor een *onbekende uitgever* (het programma is niet ondertekend): **Meer info › Toch uitvoeren**.

## Keuzes tijdens de installatie

| Keuze | Wat er op de pc komt |
|---|---|
| **Werkplek** (meestal) | De Plakzicht Mail-app: een eigen venster naar de server. Er draait verder niets op de pc. |
| **Server en app** | De server als achtergronddienst (start met de pc, ook zonder ingelogde gebruiker) plus de app. Gegevens in `C:\ProgramData\Plakzicht Mail`. Handig om te testen; de echte server staat op Unraid. |
| **Alleen server** | Alleen de dienst. |

Bij *Werkplek* vraagt de installatie twee adressen:
- **Adres in het bedrijfsnetwerk**, bijv. `http://192.168.1.20:8765` (het IP-adres van Unraid);
- **Internetadres**: `https://mail.plakzicht.nl`.

De app probeert bij het starten eerst het netwerkadres (op kantoor, snel) en anders het internetadres (thuis of onderweg). Via internet vraagt Cloudflare eerst om aan te melden; daarna het gewone inlogscherm. Vink **Ingelogd blijven op deze computer** aan, dan hoeft dat na een herstart niet opnieuw.

Adressen wijzigen: in de app **Mijn instellingen › Apparaten › Serveradressen van deze app wijzigen**.

## Op alle werkplekken tegelijk (stil)

```
PlakzichtMail-setup.exe /VERYSILENT /TYPE=werkplek /LOKAAL=http://192.168.1.20:8765 /INTERNET=https://mail.plakzicht.nl
```
Bijvoorbeeld via een script of Intune (*Win32-app*). Met `/TASKS=desktopicon` komt er ook een snelkoppeling op het bureaublad.

## Bijwerken en verwijderen

- **Bijwerken**: de nieuwe `PlakzichtMail-setup.exe` uitvoeren; instellingen en (bij de server) gegevens blijven staan. Voor werkplekken is dat zelden nodig: het scherm komt altijd van de server, dus na een update van de server heeft iedereen meteen de nieuwe versie.
- **Verwijderen**: *Instellingen › Apps › Plakzicht Mail*. De gegevens van een server in `C:\ProgramData\Plakzicht Mail` blijven staan (zelf weghalen als je ze echt niet meer nodig hebt).

## Server op deze pc (als je *Server en app* kiest)

- Dienst: *Taakplanner › Plakzicht Mail server* (als SYSTEM, start met de pc, herstart bij problemen). Meldingen in `C:\ProgramData\Plakzicht Mail\server.log`.
- Firewall: met het vinkje tijdens de installatie mogen andere pc's in het netwerk erbij (poort 8765, alleen privé- en domeinnetwerken).
- Geheimen staan versleuteld met `C:\ProgramData\Plakzicht Mail\secrets.key`: bewaar die apart.

## Zonder installatie (ontwikkelen)

Met Python 3.10+ kun je ook vanuit de broncode starten: `Start server.bat` (server) of `werkplek\Start Plakzicht Mail.bat` (app). Gegevens staan dan in de programmamap.
