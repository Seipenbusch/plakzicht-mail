<!--
Beheerdersdeel van de handleiding: alleen zichtbaar voor beheerders (de server geeft dit bestand alleen aan beheerders).
Zelfde opbouw als handleiding.md.
-->

# Beheer

## Beheer: overzicht {#beheer}
trefwoorden: beheerder, admin, instellingen beheer, beheerscherm
plek: beheer

Als beheerder zie je rechtsboven **Beheer**. Daar staan de tabbladen:

- **Gebruikers**: wie mag inloggen en bij welke mailboxen.
- **Microsoft-mailboxen**: welke mailboxen er gekoppeld zijn.
- **Labels**, **Handtekeningen** en **Sjablonen** voor iedereen.
- **Herkenning en Plakzicht**: koppeling met Plakzicht en het herkennen van order- en offertenummers.
- **Microsoft-koppeling** en **Claude**.
- **Server en back-up**.

Een beheerder ziet alle mailboxen, alle regels en kan mails vrijgeven die een ander heeft opgepakt.

## Gebruikers beheren {#gebruikers}
trefwoorden: gebruiker toevoegen, medewerker, account, rechten, toegang mailbox, nieuwe collega, wachtwoord resetten, verwijderen, afmelden
plek: adm:users

**Beheer › Gebruikers › + Gebruiker aanmaken**:

- **Naam** (zoals collega's hem zien) en **Gebruikersnaam** (om in te loggen).
- **Rol**: *Gebruiker*, of *Beheerder* (ziet alles).
- Welke **mailboxen** hij mag zien. Rechten worden op de server gecontroleerd.
- Een wachtwoord.

Wachtwoord vergeten: vul een nieuw wachtwoord in. Dat meldt hem ook overal af.
Laptop of telefoon kwijt: **Overal afmelden**. Uit dienst: **Verwijderen**.

## Mailboxen koppelen {#mailboxen}
trefwoorden: mailbox toevoegen, gedeelde mailbox, persoonlijke mailbox, koppelen, ontkoppelen, lokale kopie, periode, synchroniseren, bijwerken
plek: adm:mailboxes

**Beheer › Microsoft-mailboxen › Mailbox koppelen**: vul het mailadres in en kies *Gedeelde mailbox* of *Persoonlijke mailbox*. Het programma zoekt zelf met welk aangemeld Microsoft-account de mailbox bereikbaar is.

- De server houdt van elke mailbox een **lokale kopie** bij en werkt die elke minuut bij. Per mailbox kies je hoe ver terug; oudere mail blijft bij Microsoft.
- **Bijwerken**: nu meteen bijwerken. **Opnieuw**: de lokale kopie wissen en opnieuw ophalen (bij rare verschillen met Outlook).
- **Ontkoppelen** haalt alleen de koppeling weg; de mail in Microsoft blijft staan.

Vergeet niet bij **Gebruikers** aan te vinken wie bij de nieuwe mailbox mag.

## Microsoft-koppeling {#microsoft}
trefwoorden: microsoft 365, office 365, account aanmelden, devicelogin, code, tenant, client id, demo, overschakelen, afmelden account
plek: adm:ms

**Beheer › Microsoft-koppeling**:

- **Aanmelden** van een Microsoft-account: je krijgt een code voor *microsoft.com/devicelogin*. Je kunt meerdere accounts toevoegen; elk account kan alleen bij mailboxen waar het zelf rechten op heeft.
- **Eigen mailbox koppelen** voegt de mailbox van dat account toe.
- **Stand**: *Overschakelen naar Microsoft 365* of *Terug naar de demo*.

Werkt aanmelden met een code niet (voorwaardelijke toegang)? Gebruik dan **Aanmelden via deze browser** op de pc waar de server draait.

## Labels, handtekeningen en sjablonen voor iedereen {#beheer-algemeen}
trefwoorden: algemene handtekening, label beheren, kleur label, sjabloon mailbox, standaard handtekening mailbox
plek: adm:labels, adm:sigs, adm:tpls

- **Labels**: naam en kleur; met *Hoort bij gebruiker* maak je een persoonlijk label (bijvoorbeeld *Medewerker A*).
- **Handtekeningen**: de algemene handtekening per mailbox (*Automatisch gebruiken bij mailbox*). Iemand met een eigen handtekening krijgt die eerst.
- **Sjablonen**: alle sjablonen per mailbox. Iedereen met toegang tot een mailbox kan die ook zelf maken en wijzigen. Persoonlijke sjablonen van medewerkers staan hier niet.

## Plakzicht en herkenning {#herkenning}
trefwoorden: plakzicht koppeling, api-sleutel, ordernummer herkennen, patroon, reguliere expressie, offerte herkennen, verbinding testen
plek: adm:detect

**Beheer › Herkenning en Plakzicht**:

- **Koppeling met Plakzicht**: het adres van Plakzicht in het netwerk (niet app.plakzicht.nl) en de API-sleutel uit Plakzicht. **Verbinding testen** controleert of het werkt. Plakzicht Mail leest alleen.
- **Herkennen in mails**: de patronen voor order- en offertenummers. Met **Uitproberen** test je een voorbeeldtekst. **Opslaan en mails opnieuw nalopen** past het toe op bestaande mail.

## Claude instellen {#beheer-claude}
trefwoorden: anthropic, api-sleutel claude, kosten, limiet, model, verbruik per gebruiker
plek: adm:claude

**Beheer › Claude**: de API-sleutel van Anthropic, het model en de prijzen (dan zie je de kosten per gebruiker). Bij **Per gebruiker** stel je een limiet per maand in (0 = geen limiet); elk verzoek telt als één.

## Server, back-up en bijwerken {#server}
trefwoorden: back-up, backup, herstellen, update, nieuwe versie, unraid, docker, update stack, ingelogd blijven dagen, server, versie
plek: adm:server

**Beheer › Server en back-up**:

- **Back-up**: elke nacht om 02:30 automatisch; de laatste 14 blijven bewaard. **Nu back-up maken** voor een tussendoor-back-up. Bewaar de sleutel van de versleutelde geheimen (`secrets.key`) apart.
- **Ingelogd blijven**: na hoeveel dagen zonder gebruik iemand weer moet inloggen (0 = uit).
- **Werkplekken**: het adres waarmee collega's Plakzicht Mail openen, en hoe ze de app installeren.

**Nieuwe versie uitrollen**:

1. Op GitHub de pull request samenvoegen; *Actions › Versie vrijgeven*.
2. Op Unraid: *Docker › Compose › plakzicht-mail › Update Stack*.
3. Alleen als dat bij de versie staat: de nieuwe `PlakzichtMail-setup.exe` op de Windows-pc's installeren.

## Afspraken in de handleiding {#afspraken-beheren}
trefwoorden: afspraken, eigen artikel, handleiding aanpassen, bedrijfsafspraken, werkwijze, toevoegen, wijzigen
plek: help:afspraken

Onder **Afspraken** in de handleiding zet je jullie eigen werkwijze, bijvoorbeeld *wie pakt welke mailbox op* of *hoe reageren we op een klacht*. Alle medewerkers zien en doorzoeken ze; alleen beheerders kunnen ze maken en wijzigen.

1. Open de handleiding (**?** rechtsboven of `F1`) › **Afspraken** › **+ Nieuwe afspraak**.
2. Titel, trefwoorden (waarop ze het moeten kunnen vinden) en de tekst.
3. Opmaak in de tekst: `**vet**`, `*schuin*`, regels die beginnen met `- ` worden een lijstje, `1. ` een genummerde lijst, en `> ` een tip.
