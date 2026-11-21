#define MyAppName "ELG Downloader"
#define MyAppVersion "1.4"
#define MyAppPublisher "ELG"
#define MyAppExeName "ELG_Downloader.exe"

[Setup]
AppId={{E1B46651-3F89-4EE8-AF67-8BC30C4CFC97}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ELG Downloader
DefaultGroupName=ELG Downloader
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\Setup_Output
OutputBaseFilename=ELG_Downloader_Setup_V1.4
SetupIconFile=..\assets\ELG_Downloader.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=1.4.0.0
VersionInfoCompany=ELG
VersionInfoDescription=ELG Downloader Setup
VersionInfoProductName=ELG Downloader
VersionInfoProductVersion=1.4

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
Name: "installffmpeg"; Description: "Instalar/atualizar FFmpeg via winget (recomendado)"; GroupDescription: "Dependências:"; Flags: checkedonce
Name: "installdeno"; Description: "Instalar/atualizar Deno via winget para suporte ampliado ao YouTube"; GroupDescription: "Dependências:"; Flags: checkedonce

[Files]
Source: "..\dist\ELG_Downloader.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ELG_YTDLP_Helper.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\ELG_Downloader.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\ELG Downloader"; Filename: "{app}\ELG_Downloader.exe"; WorkingDir: "{app}"; IconFilename: "{app}\ELG_Downloader.exe"
Name: "{autodesktop}\ELG Downloader"; Filename: "{app}\ELG_Downloader.exe"; WorkingDir: "{app}"; IconFilename: "{app}\ELG_Downloader.exe"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/c winget install --id Gyan.FFmpeg -e --accept-package-agreements --accept-source-agreements --silent"; StatusMsg: "Instalando FFmpeg..."; Flags: runhidden waituntilterminated skipifdoesntexist; Tasks: installffmpeg
Filename: "{cmd}"; Parameters: "/c winget install --id DenoLand.Deno -e --accept-package-agreements --accept-source-agreements --silent"; StatusMsg: "Instalando Deno..."; Flags: runhidden waituntilterminated skipifdoesntexist; Tasks: installdeno
Filename: "{app}\ELG_Downloader.exe"; Description: "Abrir ELG Downloader"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\assets"
