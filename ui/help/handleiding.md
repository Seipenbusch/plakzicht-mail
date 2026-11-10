<!--
Handleiding van Plakzicht Mail (voor iedereen). Zo is dit bestand opgebouwd:
  # Onderwerp
  ## Titel van het artikel {#vaste-id}
  trefwoorden: woorden waarop je het ook moet kunnen vinden
  plek: scherm-id's waar een ?-knop naar dit artikel wijst (bijv. my:tpl, adm:tpls, regels)
  Daarna gewone tekst: alinea's, lijstjes met "- " of "1. ", **vet**, *schuin*, `toets`, [link](#id), > tip.
Elke nieuwe functie krijgt hier een stukje; tests/suite/test_handleiding.py controleert de opbouw.
-->

# Aan de slag

## Wat is Plakzicht Mail? {#over}
trefwoorden: uitleg, overzicht, begin, outlook, programma, wat kan het

Plakzicht Mail is ons gedeelde mailprogramma. Je ziet de mailboxen waar je bij mag (bijvoorbeeld info@ en je eigen mailbox), met naast elke mail de gegevens uit Plakzicht: order, productie, drukproef en verzending.

- Alles staat op de server: op elke pc, Mac, telefoon of tablet zie je dezelfde mail, labels en instellingen.
- Wat je doet, gebeurt ook in Outlook en andersom (verplaatsen, gelezen, vlaggen, categorieën).
- Collega's zien of iemand een mail al heeft opgepakt of aan het beantwoorden is.
- Plakzicht wordt alleen gelezen: Plakzicht Mail verandert nooit iets in Plakzicht.

Het scherm bestaat uit vier delen: links de **mappen en labels**, dan de **maillijst**, het **leesvenster** en rechts het **Plakzicht-paneel**. Bovenin staat het **lint** met de knoppen.

> Zoek je iets? Typ in het zoekveld hierboven gewoon wat je wilt doen, bijvoorbeeld "bijlage", "map maken" of "afwezig".

## Inloggen en ingelogd blijven {#inloggen}
trefwoorden: aanmelden, wachtwoord, uitloggen, afmelden, cloudflare, sessie, onthouden, opnieuw inloggen
plek: my:dev

1. Open Plakzicht Mail (de Windows-app, of **mail.plakzicht.nl** in de browser).
2. Buiten kantoor vraagt Cloudflare eerst om aan te melden met je werkadres; daarna zie je het inlogscherm.
3. Vul je gebruikersnaam en wachtwoord in. Laat **Ingelogd blijven op deze computer** aangevinkt op je eigen apparaat.

Uitloggen doe je met **Uitloggen** rechtsboven (op de telefoon: je initialen › Uitloggen).

Waar je ingelogd blijft, zie je in **Mijn instellingen › Apparaten**. Daar kun je een apparaat afmelden, bijvoorbeeld als je telefoon kwijt is. Een tijd niet gebruikt? Dan vraagt Plakzicht Mail weer om je wachtwoord.

## Wachtwoord wijzigen {#wachtwoord}
trefwoorden: password, nieuw wachtwoord, vergeten, wijzigen
plek: my:pw

Klik rechtsboven op je naam › **Mijn instellingen › Wachtwoord**. Vul je huidige en je nieuwe wachtwoord in.

Wachtwoord vergeten? Vraag de beheerder om een nieuw wachtwoord. Je wordt dan op alle apparaten afgemeld.

## Op je computer: Windows-app {#windows}
trefwoorden: installeren, setup, exe, app, vastlopen, traag, start niet, verbinden, logbestand, werkplek

Op Windows gebruik je de app **Plakzicht Mail** (installatie met `PlakzichtMail-setup.exe`, kies *Werkplek*).

- Bij het starten zie je een opstartplaatje en daarna *Verbinden met de server…*. Op kantoor verbindt de app via het netwerk, thuis via internet.
- Lukt verbinden niet, dan zie je waarom, met **Opnieuw proberen** en **Logbestand openen**. Stuur dat logbestand naar de beheerder als het blijft misgaan.
- Links in mails openen in je gewone browser.
- Serveradressen aanpassen: **Mijn instellingen › Apparaten**.

## Op een Mac of in de browser {#mac}
trefwoorden: apple, safari, chrome, edge, browser, als app installeren, dock

Op een Mac werk je in de browser: open **https://mail.plakzicht.nl**. Je kunt het als app installeren:

- **Chrome / Edge**: rechts in de adresbalk het icoon *Installeren* › **Installeren**.
- **Safari** (macOS 14 of nieuwer): **Archief › Zet in Dock**.

Meldingen aanzetten: zie [Meldingen bij nieuwe mail](#meldingen).

## Op je telefoon of tablet {#telefoon}
trefwoorden: mobiel, iphone, android, ipad, app op beginscherm, installeren, smartphone
plek: my:mob

Open **https://mail.plakzicht.nl** op je telefoon en zet hem als app op je beginscherm:

- **iPhone / iPad** (Safari): **Deel** › **Zet op beginscherm**. Open hem voortaan via het icoon.
- **Android** (Chrome): menu **⋮** › **App installeren**.

Zo werkt het op de telefoon:

- **☰** linksboven: mappen, mailboxen, labels en favorieten.
- Tik op een mail om hem te lezen; terug met **←** of de terugknop van je telefoon.
- **Nieuwe mail**: de ronde knop rechtsonder.
- Meerdere mails: **lang drukken** op een mail, daarna andere mails aantikken. Onderin verschijnen de acties.
- Je initialen rechtsboven: agenda, instellingen, handleiding, uitloggen.
- Op een tablet staan de lijst en de mail naast elkaar.

## Vegen op de telefoon {#vegen}
trefwoorden: swipe, schuiven, veeg, links, rechts, archiveren, ongedaan maken
plek: my:mob

Veeg een mail in de lijst opzij en laat los:

- naar **links**: standaard **archiveren**;
- naar **rechts**: standaard **gelezen/ongelezen**.

Archiveren en verwijderen kun je 5 seconden **ongedaan maken**.

Zelf kiezen wat vegen doet: **Mijn instellingen › Mobiel**. Per richting kun je kiezen uit niets, archiveren, verwijderen, gelezen/ongelezen, vlag, beantwoorden, oppakken, label kiezen of verplaatsen. De keuze geldt op al je telefoons en tablets.

# Mail lezen en ordenen

## Het scherm en het lint {#scherm}
trefwoorden: knoppen, lint, ribbon, tabbladen, start, beeld, menu, meer opties, drie puntjes

Bovenin staat het **lint** met vier tabbladen:

- **Start**: nieuwe mail, verwijderen, archiveren, verplaatsen, beantwoorden, toewijzen, snelle stappen, vlag, categoriseren, filteren, voorlezen, Claude.
- **Beeld**: hoe de lijst eruitziet (kolommen of compact, regelhoogte, scheidingsbalken, sorteren), waar je antwoordt, meldingen, Plakzicht-paneel en zijbalk.
- **Plakzicht**: koppelen aan een order, order openen, afspraak maken, regels, opslaan als .eml, eigen venster.
- **Claude**: samenvatten, antwoord voorstellen, vertalen en meer.

Is het venster smal, dan verdwijnen eerst de teksten bij minder belangrijke knoppen en daarna komen knoppen onder **⋯** (meer opties) rechts in het lint.

Met de **rechtermuisknop** op een mail, map of label krijg je alle acties voor dat onderdeel.

## Mail openen en lezen {#lezen}
trefwoorden: openen, leesvenster, eigen venster, dubbelklik, volgende mail, pijltjes, inladen, afbeeldingen

- **Klik** op een mail om hem rechts in het leesvenster te lezen.
- **Dubbelklik** (of `Enter`) opent de mail in een **eigen venster**.
- Met de pijltjes `↑` en `↓` ga je naar de vorige of volgende mail.
- Een vette mail is ongelezen. Een mail wordt gelezen zodra je hem opent.

Links in een mail openen in een nieuw tabblad. Noemt de linktekst een ander adres dan waar de link echt heen gaat, dan vraagt Plakzicht Mail eerst of je hem wilt openen. Ga met de muis op een link staan om het echte adres te zien.

## Zoeken in je mail {#zoeken}
trefwoorden: zoekbalk, vinden, zoek, oudere mail, ordernummer, klant, afzender, onderwerp
plek: zoeken

Typ in het zoekveld bovenin. Plakzicht Mail zoekt meteen in de **map of het label dat open staat**: in het onderwerp, de afzender, de tekst en op ordernummer of klant.

- Meerdere woorden: alle woorden moeten voorkomen.
- Zoeken in een andere map? Klik eerst op die map.
- Mails ouder dan de periode die de server bewaart, staan bij Microsoft. Onderaan de lijst staat dan **Ook in oudere mails zoeken bij Microsoft**.
- Zoeken op een **order of offerte** met alle mails erbij: zie [Orders zoeken](#orders).
- Een persoon of mailadres zoeken: **Personen zoeken** of **Adresboek** in het lint.

## Filteren en sorteren {#filteren}
trefwoorden: filter, ongelezen, met vlag, bijlage, sorteren, volgorde, oud nieuw, alleen
plek: filter

Boven de lijst staan snelle filters (**Alle**, **Ongelezen**, **Met vlag**, **Zonder order**). In het lint onder **E-mail filteren** staan ze allemaal:

- Alle, Ongelezen, Met vlag, Met bijlage
- Vermeld (@): mails waarin jouw naam met @ staat
- Opgepakt door mij, Nog niet opgepakt
- Zonder order: mails die nog niet aan een order of offerte gekoppeld zijn

**Sorteren**: klik op de knop *Datum ↓* boven de lijst, of **Beeld › Sorteren**. In de kolommenweergave klik je op de kop van een kolom.

## Weergave van de lijst {#weergave}
trefwoorden: kolommen, compact, regelhoogte, dichtheid, scheidingsbalken, groeperen, per dag, layout
plek: my:view

Op het tabblad **Beeld**:

- **Kolommen** of **Compact** (twee regels per mail).
- **Smal / Middel / Breed**: hoeveel ruimte er tussen de regels zit.
- **Scheidingsbalken**: balken per dag (Vandaag, Gisteren, …) of per waarde van de kolom waarop je sorteert.
- **Kolommen kiezen**: welke kolommen je ziet. *Standaardkolommen en -breedtes* zet alles terug.
- **Antwoorden: in leesvenster** of **volledig scherm**.

Onderaan de lijst staat hoeveel mails er zijn, hoeveel ongelezen, en hoeveel je hebt geselecteerd.

## Kolombreedtes aanpassen {#kolombreedtes}
trefwoorden: breedte, smaller, breder, slepen, kolom, zijbalk, scherm, onthouden, terugzetten
plek: my:view, kolommen

Sleep de dunne lijn tussen twee delen (zijbalk, lijst, leesvenster, Plakzicht) naar links of rechts. **Dubbelklik** op de lijn zet die kolom terug naar de standaardbreedte. Kolommen in de lijst sleep je aan de rand van de kolomkop.

- De breedtes worden bewaard **per scherm**. Op de laptop kun je dus andere breedtes hebben dan op het grote scherm op kantoor.
- Is het venster even smal, dan past alles zich aan zonder dat je instelling verloren gaat.
- Terug naar standaard op dit scherm: **Mijn instellingen › Weergave › Kolombreedtes op dit scherm herstellen**.

## Licht of donker {#thema}
trefwoorden: dark mode, donkere modus, licht, kleur, thema, nacht, automatisch
plek: my:view

Klik rechtsboven op de knop met de zon/maan (naast het belletje) en kies **Licht**, **Donker** of **Automatisch** (volgt je computer). Je keuze geldt op al je apparaten.

## Meerdere mails tegelijk {#selecteren}
trefwoorden: selecteren, meerdere, alles selecteren, ctrl, shift, bulk, tegelijk, selectie

- `Ctrl` + klik: mail erbij of eraf.
- `Shift` + klik: alles tussen twee mails.
- `Ctrl+A`: alle mails in de lijst. `Esc` heft de selectie op.
- Op de telefoon: **lang drukken**, daarna andere mails aantikken.

Daarna werken verwijderen, archiveren, verplaatsen, gelezen, vlag, label en toewijzen voor alle geselecteerde mails tegelijk. Onderaan de lijst staat hoeveel je hebt geselecteerd, met **Opheffen**.

## Sneltoetsen {#sneltoetsen}
trefwoorden: toetsenbord, shortcuts, ctrl, toetsen, sneller werken, keyboard

| Toets | Wat |
|---|---|
| `Ctrl+N` | Nieuwe mail |
| `Ctrl+R` | Beantwoorden |
| `Ctrl+Shift+R` | Allen beantwoorden |
| `Ctrl+F` | Doorsturen |
| `Ctrl+Q` / `Ctrl+U` | Gelezen / ongelezen |
| `Delete` | Verwijderen |
| `Backspace` | Archiveren |
| `Insert` | Vlag aan/uit |
| `↑` / `↓` | Vorige / volgende mail |
| `Shift+↑` / `Shift+↓` | Selectie uitbreiden |
| `Ctrl+A` | Alles selecteren |
| `Esc` | Selectie opheffen, venster sluiten |
| `Enter` | Mail in eigen venster |
| `F1` | Deze handleiding |

## Archiveren, verwijderen en verplaatsen {#verplaatsen}
trefwoorden: archief, prullenbak, weggooien, verplaatsen, slepen, map, terugzetten, definitief, leegmaken

- **Archiveren** (`Backspace`): naar de map Archief van die mailbox.
- **Verwijderen** (`Delete`): naar Verwijderde items. In Verwijderde items verwijder je **definitief**.
- **Verplaatsen**: kies een map in het lint, of **sleep** de mail naar een map, label of favoriet links.
- Verkeerd verwijderd? Open **Verwijderde items** en verplaats de mail terug.
- Map **Verwijderde items** of **Ongewenste e-mail** helemaal leegmaken: pijltje naast *Verwijderen* › **Map leegmaken…** Dat kun je niet ongedaan maken.

## Mappen maken en beheren {#mappen}
trefwoorden: map maken, nieuwe map, submap, hernoemen, map verwijderen, map verplaatsen, folder
plek: mappen

Klik met de **rechtermuisknop** op een map (telefoon: lang drukken in het mappenmenu):

- **Nieuwe submap…**, **Hernoemen…**, **Map verplaatsen naar**, **Map verwijderen…**
- **Teller**: hoeveel mails je bij de map ziet (zie [Tellers](#tellers)).
- **Toevoegen aan favorieten**.

Een nieuwe map bovenaan een mailbox: rechtermuisknop op de mailbox › **Nieuwe map…**, of **+ Nieuwe map** onder de mappen. Mappen zijn dezelfde als in Outlook.

## Favorieten {#favorieten}
trefwoorden: favoriet, ster, bovenaan, snel, vastzetten, vaak gebruikt

Zet mappen, mailboxen of labels die je vaak gebruikt bovenaan:

1. Rechtermuisknop op de map, mailbox of label (telefoon: lang drukken).
2. **Toevoegen aan favorieten**.

Ze staan dan bovenin onder **FAVORIETEN** én op hun gewone plek. Volgorde aanpassen: slepen, of via de rechtermuisknop **Omhoog/Omlaag**. Mails naar een favoriet slepen verplaatst ze. Je favorieten zijn van jou en gelden op elk apparaat.

## Tellers bij mappen {#tellers}
trefwoorden: aantal, teller, ongelezen, totaal, getal, cijfer, hoeveel mails
plek: my:view, tellers

Standaard zie je bij een map hoeveel mails er **ongelezen** zijn. Per map kun je kiezen: ongelezen, totaal, beide of geen.

- Rechtermuisknop op de map › **Teller**, of
- **Mijn instellingen › Weergave › Tellers per map**.

## Labels (categorieën) {#labels}
trefwoorden: label, categorie, categoriseren, kleur, tag, etiket
plek: labels

Labels zijn de categorieën uit Outlook. Een mail kan meerdere labels hebben.

- Label geven: **Categoriseren** in het lint, of sleep de mail naar het label links.
- Label weghalen: klik op het **×** in het label boven de mail.
- Nieuw label: **Categoriseren › Nieuw label…**
- Alle mails met een label: klik links op het label.

## Vlag en opvolgen {#vlag}
trefwoorden: vlag, opvolgen, herinnering, later, vandaag, morgen, volgende week, voltooid, to do
plek: vlag

**Opvolgen** in het lint (of `Insert`) zet een vlag. Met het pijltje ernaast kies je wanneer: **Vandaag**, **Morgen**, **Deze week**, **Volgende week**, **Zonder datum** of **Aangepast…** Daar staan ook **Markeren als voltooid** en **Vlag wissen**.

Alle mails met een vlag: filter **Met vlag**.

## Ongewenste mail en phishing melden {#melden}
trefwoorden: spam, phishing, ongewenst, verdacht, nep, oplichting, junk, virus

Lijkt een mail verdacht? Klik niet op links of bijlagen. Kies **Melden** in het lint:

- **Ongewenste e-mail**: naar de map Ongewenste e-mail.
- **Phishing**: ook naar Ongewenste e-mail; laat het bij twijfel de beheerder weten.
- **Geen ongewenste e-mail**: een mail die ten onrechte in Ongewenste e-mail staat, terug naar Postvak IN.

## Oudere mail {#ouder}
trefwoorden: oud, oude mails, archief van vorig jaar, ophalen, niet gevonden, ontbreekt, microsoft

De server bewaart per mailbox een kopie van de laatste periode (bijvoorbeeld 30 dagen); die mails openen direct. Oudere mails staan bij Microsoft. Onderaan de lijst staat dan **Oudere mails ophalen bij Microsoft** (bij zoeken: **Ook in oudere mails zoeken bij Microsoft**).

## Voorlezen en opslaan {#voorlezen}
trefwoorden: voorlezen, horen, spraak, opslaan, eml, bewaren, downloaden, exporteren

- **Voorlezen** (tabblad Start): de mail wordt voorgelezen. Nog eens klikken = **Stoppen**.
- **Opslaan als .eml** (tabblad Plakzicht): de mail als bestand, bijvoorbeeld om in een dossier te bewaren of door te geven.

# Schrijven en beantwoorden

## Nieuwe mail schrijven {#schrijven}
trefwoorden: nieuwe mail, opstellen, versturen, verzenden, van, aan, cc, mailbox kiezen, afzender
plek: schrijven

1. Klik op **Nieuwe e-mail** (of `Ctrl+N`). Met het pijltje ernaast kies je meteen uit welke mailbox.
2. Kies bij **Van** de mailbox waaruit je verstuurt.
3. Vul **Aan** in; het adresboek vult mee terwijl je typt. **CC** voor wie mee moet lezen.
4. Schrijf je mail. Je handtekening staat er al onder.
5. **Versturen**.

Opmaak (vet, kleur, lijstjes, link, afbeelding) zit in de balk boven de tekst. Een order koppelen kan bij **Order**: zie [Koppelen aan een order](#koppelen).

## Beantwoorden en doorsturen {#beantwoorden}
trefwoorden: antwoorden, reply, allen beantwoorden, doorsturen, forward, re, fw, leesvenster, volledig scherm

- **Beantwoorden** (`Ctrl+R`), **Allen beantwoorden** (`Ctrl+Shift+R`), **Doorsturen** (`Ctrl+F`).
- Of je in het leesvenster of op het volledige scherm antwoordt, kies je met **Beeld › Antwoorden**.
- Is een collega dezelfde mail al aan het beantwoorden, dan zie je dat boven de mail. Overleg even om dubbele antwoorden te voorkomen.

## Concepten {#concepten}
trefwoorden: concept, draft, opslaan, later verder, niet verstuurd, kwijt, weggooien

Wat je aan het schrijven bent, blijft bewaard als je weggaat. In de lijst staat er **[Concept]** bij de mail. Open de mail opnieuw (of klik op het concept) om verder te schrijven.

Concept niet meer nodig? Klik op de **prullenbak** naast *Versturen*.

## Handtekeningen {#handtekeningen}
trefwoorden: handtekening, signature, ondertekening, logo, naam onder mail, afsluiting
plek: my:sig

Je handtekening komt automatisch onder elke mail. Welke:

1. je eigen handtekening voor die mailbox,
2. anders je eigen standaard,
3. anders de algemene handtekening van de mailbox.

Eigen handtekening maken: **Mijn instellingen › Handtekeningen**. Gebruik `{naam}` voor je naam en `{mailbox}` voor het mailadres. Tijdens het schrijven kun je onder de mail een andere handtekening kiezen.

## Sjablonen gebruiken {#sjablonen}
trefwoorden: sjabloon, template, standaardtekst, vaste tekst, standaardantwoord, snel antwoorden, bouwsteen
plek: sjabloon

Een sjabloon is een vaste tekst die je in een mail invoegt.

1. Klik in het opstelscherm op **Sjabloon** (telefoon: het knopje met het documentje).
2. Zoek en kies een sjabloon. Je ziet je eigen sjablonen en die van de mailbox waaruit je mailt.
3. De tekst komt op de plek van de cursor, boven je handtekening. Bijlagen uit het sjabloon gaan mee.

Snel: rechtermuisknop op een mail › **Beantwoorden met sjabloon** (telefoon: lang drukken).

**Gele plekken**: wat Plakzicht Mail niet weet (bijvoorbeeld een ordernummer als de mail nog niet aan een order gekoppeld is) staat geel gemarkeerd, zoals **[Ordernummer]**. Typ eroverheen. Staan er bij versturen nog gele plekken, dan vraagt Plakzicht Mail eerst of je toch wilt versturen.

> Een sjabloon wordt nooit vanzelf verstuurd. Lees de mail altijd even na.

## Sjablonen maken {#sjablonen-maken}
trefwoorden: sjabloon maken, nieuw sjabloon, invulvelden, voornaam, ordernummer, bijlage toevoegen, sjabloon wijzigen, verwijderen
plek: my:tpl

**Mijn instellingen › Sjablonen › + Nieuw sjabloon**.

- **Voor**: *Alleen ik*, of *Iedereen met* een mailbox. Mailbox-sjablonen kan iedereen met toegang tot die mailbox gebruiken en wijzigen.
- **Onderwerp** (optioneel): wordt gebruikt bij een nieuwe mail; bij beantwoorden blijft het onderwerp staan.
- **Invulvelden**: klik op een veld om het op de plek van de cursor te zetten. Bij het invoegen wordt het ingevuld:
  - `{voornaam}`, `{naam}`, `{email}` van de ontvanger;
  - `{mijn_naam}`, `{mailbox}`, `{datum}`;
  - uit Plakzicht: `{klant}`, `{ordernummer}`, `{orderstatus}`, `{verzenddatum}`, `{track_trace}`, `{offertenummer}`, `{offertestatus}`.
- **Bijlagen**: bijvoorbeeld de leveringsvoorwaarden, samen hooguit 2,5 MB.

Snel een sjabloon van een tekst die je net schreef: in het opstelscherm **Sjabloon › Deze tekst opslaan als sjabloon…**

## Personen zoeken en adresboek {#adresboek}
trefwoorden: adresboek, contact, contactpersoon, mailadres opzoeken, collega, klant zoeken, personen
plek: adresboek

- **Personen zoeken** (lint): zoek op naam, bedrijf of mailadres.
- **Adresboek**: iedereen met wie gemaild is, en de klanten uit Plakzicht.
- Bij **Aan** en **CC** vult het adresboek vanzelf aan terwijl je typt.

# Samenwerken

## Oppakken en toewijzen {#toewijzen}
trefwoorden: oppakken, claimen, toewijzen, collega, wie doet wat, vrijgeven, verdelen, taak, assign
plek: toewijzen

Zo weet iedereen wie een mail afhandelt:

- **Toewijzen › Zelf oppakken**: jouw initialen staan bij de mail.
- **Toewijzen › Toewijzen aan collega**: kies een collega; die krijgt een melding.
- **Vrijgeven**: de mail is weer van niemand. Alleen de beheerder kan een mail vrijgeven die een ander heeft opgepakt.

Filters: **Opgepakt door mij** en **Nog niet opgepakt**.

## Zien wat collega's doen {#meekijken}
trefwoorden: collega, tegelijk, dubbel antwoord, oogje, pennetje, bezig, open, live

Bij een mail zie je de initialen van collega's die hem ook open hebben (oogje) of hem aan het **beantwoorden** zijn (pennetje). Boven de mail staat dat ook in tekst. Zo voorkom je dat een klant twee antwoorden krijgt.

Wijzigingen van collega's (gelezen, verplaatst, label, oppakken) zie je meteen, zonder te verversen.

## Vermeldingen (@) {#vermelding}
trefwoorden: vermeld, at, @, genoemd, mention, naam in mail

Staat jouw voornaam met een @ ervoor in een mail (bijvoorbeeld *@sven*), dan zie je een **@** bij die mail. Met het filter **Vermeld (@)** zie je al die mails.

## Snelle stappen {#snelle-stappen}
trefwoorden: snelle stap, quick step, automatisch, één klik, meerdere acties, behandeld, macro
plek: my:qs

Een snelle stap doet meerdere dingen met één klik, bijvoorbeeld *gelezen + label Afgehandeld + naar Archief*.

- Gebruiken: **Snelle stappen** in het lint. De eerste twee staan er ook als eigen knop.
- Maken of wijzigen: **Snelle stappen › Snelle stappen beheren…** (of **Mijn instellingen › Snelle stappen**).

Mogelijke acties: gelezen/ongelezen, vlag of opvolgen, oppakken/vrijgeven, labels, verplaatsen, doorsturen, beantwoorden met een vaste tekst of een nieuwe mail beginnen.

## Regels {#regels}
trefwoorden: regel, automatisch sorteren, filter, automatisch verplaatsen, inkomende mail, label automatisch
plek: regels

Regels doen automatisch iets met nieuwe mail in Postvak IN, van boven naar beneden.

1. Klik bovenin op **Regels** › **Nieuwe regel**, of op een mail: **Plakzicht › Regel maken** (vult de afzender al in).
2. Kies **Geldt voor** (alle mailboxen of één).
3. **Als alle voorwaarden kloppen**: bijvoorbeeld *Afzender bevat @leverancier.nl*, of *Plakzicht-koppeling heeft geen order*.
4. **Dan**: verplaatsen, label toevoegen, als gelezen markeren, vlag zetten.
5. **Opslaan**. Met **Nu toepassen op Postvak IN** pas je hem ook toe op mail die er al staat.

Met de schakelaar zet je een regel aan of uit; met ↑ en ↓ verander je de volgorde.

> Let op: op de Microsoft-mailboxen worden regels nu nog niet automatisch uitgevoerd (dat staat ook bovenaan het scherm *Regels*). Gebruik zolang **Nu toepassen op Postvak IN**.

# Plakzicht

## Het Plakzicht-paneel {#plakzicht}
trefwoorden: order, plakzicht, productie, drukproef, verzending, track en trace, klant, paneel rechts, status
plek: plakzicht

Staat er een ordernummer of offertenummer in een mail, dan herkent Plakzicht Mail dat en toont rechts het **Plakzicht-paneel**:

- de order of offerte, met product, productiestappen en drukproef;
- **Uiterlijk verzenden** en de verzending (met track & trace);
- **Klant in Plakzicht**: andere orders en offertes van de klant, en *Mails met deze klant*;
- **Bekijken**: opent de order in Plakzicht.

Op de telefoon staat dit als balk boven de mail; tik erop voor alles.

Paneel verbergen of tonen: **Beeld › Plakzicht verbergen**.

## Koppelen aan een order {#koppelen}
trefwoorden: koppelen, order koppelen, offerte koppelen, ontkoppelen, verkeerde order, andere order, geen order
plek: koppelen

Niet herkend of de verkeerde order? 

- **Plakzicht › Koppelen aan order** in het lint, of **Andere koppelen** in het paneel. Zoek op ordernummer, offerte of klant.
- **Ontkoppelen** haalt de koppeling weg.
- Bij een nieuwe mail of antwoord kun je bij **Order** een order kiezen (**Wijzigen** / **Weghalen**).

Mails zonder koppeling vind je met het filter **Zonder order**.

## Orders zoeken {#orders}
trefwoorden: order zoeken, offerte zoeken, alle mails van een order, ordernummer, klant opzoeken
plek: orders

Klik bovenin op **Orders** (of **Plakzicht › Order zoeken**). Zoek op ordernummer, offerte of klant. Je ziet de gegevens uit Plakzicht en **alle mails bij die order of offerte**, uit alle mailboxen waar je bij mag.

## Afspraak maken vanuit een mail {#afspraak-uit-mail}
trefwoorden: afspraak, agenda, vergadering, plannen, uitnodiging vanuit mail

Op een mail: **Afspraak** in het lint (of **Plakzicht › Afspraak maken**). Het onderwerp, de afzender als genodigde, de order en een verwijzing naar de mail staan er al in. Zie ook [Agenda](#agenda).

# Agenda en meldingen

## Agenda {#agenda}
trefwoorden: agenda, kalender, afspraak, vergadering, uitnodiging, herinnering, dag, week, maand, verzenddatum, afwezig
plek: agenda

Klik bovenin op **Agenda** (telefoon: je initialen › Agenda).

- Weergave: **Dag**, **Werkweek**, **Week**, **Maand** of **Lijst**. Op de telefoon: lijst of dag.
- **Verzenddatums van orders** aanvinken: je ziet ook wanneer orders uiterlijk verzonden moeten worden.
- **Nieuwe afspraak** (telefoon: **+ Afspraak**): onderwerp, begin en einde (of hele dag), locatie, genodigden (zij krijgen een uitnodiging), herinnering en of je **vrij**, **bezet**, **voorlopig** of **afwezig** bent.
- Klik op een afspraak om hem te bekijken, te wijzigen of te verwijderen.

Je ziet de agenda's van de Microsoft-accounts waar je bij mag.

## Meldingen bij nieuwe mail {#meldingen}
trefwoorden: melding, notificatie, geluid, pop-up, belletje, nieuwe mail, geen melding, push
plek: my:notify

- Snel aan of uit: het **belletje** rechtsboven.
- Instellen: **Mijn instellingen › Meldingen**: aan/uit, **Met geluid**, voor welke mailboxen, en *Ook een melding van het systeem* (ook als Plakzicht Mail op de achtergrond staat).

Goed om te weten:

- Een melding komt alleen voor nieuwe, ongelezen mail in Postvak IN, tot ongeveer 15 seconden na binnenkomst.
- Geen geluid? Klik eerst één keer ergens in het venster; browsers spelen pas geluid af nadat je het venster hebt gebruikt.
- Op de telefoon komen meldingen zolang de app open is of nog maar kort op de achtergrond staat.

# Claude

## Claude: hulp bij mail {#claude}
trefwoorden: claude, ai, kunstmatige intelligentie, samenvatten, antwoord voorstellen, vertalen, assistent, slim
plek: my:claude, claude

Claude is een AI-assistent die helpt met mail. Op het tabblad **Claude** in het lint (of **Start › Claude**):

- **Samenvatten**: de mail in een paar regels.
- **Antwoord voorstellen**: een concept-antwoord, met de gegevens van de gekoppelde order of offerte.
- **Vertalen**: naar Nederlands, Engels, Duits, Frans, Spaans of Pools.
- **Label en map voorstellen**.
- **Gegevens uit aanvraag**: haalt klant, contactpersoon, product, aantal, afmeting, materiaal, leverdatum en afleveradres uit een offerteaanvraag.

Tijdens het schrijven (knop met het sterretje): **Tekst verbeteren**, **Formeler**, **Vriendelijker**, **Korter maken**, **Mijn tekst vertalen** en **Antwoord laten schrijven**.

> Claude verstuurt nooit zelf iets. Een voorgesteld antwoord komt als concept in je editor; lees het altijd na. Alleen de mail waar je op klikt gaat naar Claude.

## Mijn Claude-instellingen {#claude-instellingen}
trefwoorden: toon, je of u, formeel, informeel, taal, aanwijzingen, claude instellen, verbruik, limiet
plek: my:claude

**Mijn instellingen › Claude**:

- **Toon** van voorgestelde antwoorden (bijvoorbeeld zakelijk en vriendelijk, formeel, informeel, zo kort mogelijk).
- **Aanspreken met** je of u.
- **Taal** van het antwoord.
- **Extra aanwijzingen**, bijvoorbeeld "noem altijd de levertijd".

Daar zie je ook hoeveel verzoeken je deze maand hebt gedaan. Staat Claude uit of is de limiet bereikt, dan zie je dat bij de knoppen.

# Problemen

## Een mail is weg {#mail-weg}
trefwoorden: kwijt, verdwenen, weg, niet te vinden, verplaatst, collega, verwijderd

- Kijk in **Verwijderde items** en **Archief**.
- Zoek in de map waar je hem verwacht; denk aan [oudere mail](#ouder).
- Heeft een collega hem verplaatst, dan zie je de melding *Deze mail is intussen door een collega verplaatst of verwijderd*.
- Staat er een filter aan (bijvoorbeeld *Ongelezen*)? Kies **Alle**.

## Het scherm doet raar of is niet bijgewerkt {#verversen}
trefwoorden: vastgelopen, hangt, niet bijgewerkt, verversen, herladen, oude versie, update, fout, wit scherm

1. Klik op het rondje **Vernieuwen** boven de lijst.
2. Helpt dat niet: herlaad het venster met `F5` (in de Windows-app: sluiten en opnieuw openen).
3. Na een update van Plakzicht Mail hoef je meestal niets te doen; het scherm komt van de server.
4. Blijft het misgaan? Meld het bij de beheerder, met wat je deed en een schermafbeelding.

Windows-app start niet of hangt: zie [Windows-app](#windows).

## Geen melding of geen geluid {#geen-melding}
trefwoorden: geen melding, geen geluid, stil, notificatie werkt niet, piep

- Staat het **belletje** rechtsboven aan?
- Staat de mailbox aan in **Mijn instellingen › Meldingen**?
- Geluid: klik één keer in het venster (browsers vereisen dat).
- Systeemmeldingen: sta ze toe in de browser en in Windows/macOS (*Systeeminstellingen › Berichtgeving*).
- Meldingen werken alleen via **https://mail.plakzicht.nl**, niet via het lokale adres in de browser.
