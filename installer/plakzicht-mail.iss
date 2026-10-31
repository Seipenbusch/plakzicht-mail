; Plakzicht Mail – installatieprogramma voor Windows (Inno Setup 6).
; Wordt gebouwd door GitHub Actions (bouwen.yml). Bevat Python en alle onderdelen: er hoeft niets vooraf geïnstalleerd te zijn.
;
; Keuzes tijdens de installatie:
;   Werkplek          – alleen de Plakzicht Mail-app (venster naar de server)
;   Server en app     – de server als dienst op deze pc, plus de app
;   Alleen server     – alleen de server als dienst
;
; Stil installeren (bijv. op alle werkplekken tegelijk):
;   PlakzichtMail-setup.exe /VERYSILENT /TYPE=werkplek /LOKAAL=http://192.168.1.20:8765 /INTERNET=https://mail.plakzicht.nl

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0.0"
#endif
#ifndef MyAppLabel
  #define MyAppLabel MyAppVersion
#endif
#define MyAppName "Plakzicht Mail"
#define ClientExe "Plakzicht Mail.exe"
#define ServerExe "Plakzicht Mail server.exe"

[Setup]
AppId={{FFD92DD9-21FC-49CA-8B4C-5D1D1B9D3CFF}
AppName={#MyAppName}
AppVersion={#MyAppLabel}
AppVerName={#MyAppName} {#MyAppLabel}
AppPublisher=Stickerwinkel
VersionInfoVersion={#MyAppVersion}
DefaultDirName={autopf}\Plakzicht Mail
DefaultGroupName=Plakzicht Mail
DisableProgramGroupPage=yes
DisableDirPage=auto
OutputDir=..\dist
OutputBaseFilename=PlakzichtMail-setup
SetupIconFile=icoon.ico
UninstallDisplayIcon={app}\{#ClientExe}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ShowLanguageDialog=no
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "nl"; MessagesFile: "compiler:Languages\Dutch.isl"

[Types]
Name: "werkplek"; Description: "Werkplek: alleen de Plakzicht Mail-app"
Name: "server"; Description: "Server en app op deze pc"
Name: "alleenserver"; Description: "Alleen de server (als dienst)"

[Components]
Name: "app"; Description: "Plakzicht Mail-app (eigen venster)"; Types: werkplek server
Name: "server"; Description: "Plakzicht Mail-server (draait op de achtergrond, start met de pc)"; Types: server alleenserver

[Tasks]
Name: "desktopicon"; Description: "Snelkoppeling op het bureaublad"; Components: app
Name: "firewall"; Description: "Andere pc's in het netwerk toegang geven tot de server (Windows Firewall, poort 8765)"; Components: server

[Files]
Source: "..\dist\Plakzicht Mail\*"; DestDir: "{app}"; Components: app; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\dist\Plakzicht Mail server\*"; DestDir: "{app}\server"; Components: server; Flags: recursesubdirs createallsubdirs ignoreversion

[Dirs]
Name: "{commonappdata}\Plakzicht Mail"; Components: server

[Icons]
Name: "{autoprograms}\Plakzicht Mail"; Filename: "{app}\{#ClientExe}"; Components: app
Name: "{autodesktop}\Plakzicht Mail"; Filename: "{app}\{#ClientExe}"; Tasks: desktopicon
Name: "{autoprograms}\Plakzicht Mail-server (beheer in de browser)"; Filename: "http://localhost:8765/"; Components: server and not app
Name: "{autoprograms}\Plakzicht Mail-server gegevens"; Filename: "{commonappdata}\Plakzicht Mail"; Components: server

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\server\dienst.ps1"" installeer-firewall ""{app}\server\{#ServerExe}"""; Flags: runhidden waituntilterminated; Components: server; Tasks: firewall; StatusMsg: "Server instellen als dienst..."
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\server\dienst.ps1"" installeer ""{app}\server\{#ServerExe}"""; Flags: runhidden waituntilterminated; Components: server; Tasks: not firewall; StatusMsg: "Server instellen als dienst..."
Filename: "{app}\{#ClientExe}"; Description: "Plakzicht Mail nu openen"; Flags: nowait postinstall skipifsilent runasoriginaluser; Components: app

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\server\dienst.ps1"" verwijder"; Flags: runhidden waituntilterminated; RunOnceId: "DienstWeg"; Components: server

[UninstallDelete]
Type: files; Name: "{app}\werkplek-standaard.json"

[Code]
var
  AdresPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  AdresPage := CreateInputQueryPage(wpSelectTasks,
    'Adres van de server', 'Waar staat de Plakzicht Mail-server?',
    'De app probeert eerst het adres in het bedrijfsnetwerk (snel, op kantoor) en anders het internetadres (thuis of onderweg). ' +
    'Laat een veld leeg als je het niet gebruikt. Wijzigen kan later in de app: Mijn instellingen › Apparaten.');
  AdresPage.Add('Adres in het bedrijfsnetwerk, bijvoorbeeld http://192.168.1.20:8765', False);
  AdresPage.Add('Internetadres, bijvoorbeeld https://mail.plakzicht.nl', False);
  AdresPage.Values[0] := ExpandConstant('{param:LOKAAL|}');
  AdresPage.Values[1] := ExpandConstant('{param:INTERNET|https://mail.plakzicht.nl}');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = AdresPage.ID) and not WizardIsComponentSelected('app');
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { server op deze pc: lokaal adres alvast invullen }
  if (CurPageID = AdresPage.ID) and (AdresPage.Values[0] = '') and WizardIsComponentSelected('server') then
    AdresPage.Values[0] := 'http://localhost:8765';
end;

function CleanAddr(S: String): String;
begin
  Result := Trim(S);
  StringChangeEx(Result, '"', '', True);
  StringChangeEx(Result, '\', '/', True);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Json, Lokaal: String;
begin
  if (CurStep = ssPostInstall) and WizardIsComponentSelected('app') then
  begin
    Lokaal := CleanAddr(AdresPage.Values[0]);
    if (Lokaal = '') and WizardIsComponentSelected('server') then
      Lokaal := 'http://localhost:8765';
    Json := '{' + #13#10 +
            '  "lokaal": "' + Lokaal + '",' + #13#10 +
            '  "internet": "' + CleanAddr(AdresPage.Values[1]) + '"' + #13#10 + '}' + #13#10;
    SaveStringToFile(ExpandConstant('{app}\werkplek-standaard.json'), Json, False);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  RC: Integer;
begin
  { bij bijwerken: draaiende server eerst stoppen, zodat de bestanden vervangen kunnen worden }
  Exec(ExpandConstant('{sys}\schtasks.exe'), '/End /TN "Plakzicht Mail server"', '', SW_HIDE, ewWaitUntilTerminated, RC);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM "{#ServerExe}"', '', SW_HIDE, ewWaitUntilTerminated, RC);
  Result := '';
end;
