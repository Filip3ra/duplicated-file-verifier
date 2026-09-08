#define MyAppName "dupcheck"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "Filipi Maciel"
#define MyAppURL "https://github.com/Filip3ra"
#define MyAppExeName "dupcheck.exe"

[Setup]
AppId={{8E4F2C91-6A17-4B5E-9D33-1C7A0F8B42E6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\dupcheck
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=dupcheck-setup-{#MyAppVersion}
SetupIconFile=..\src\duplicate_verifier\assets\dupcheck-icon-png.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\dist\dupcheck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\dupcheck"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "Verificador de arquivos duplicados"
Name: "{autodesktop}\dupcheck"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\dupcheck (terminal)"; Filename: "{app}\dupcheck-cli.exe"; WorkingDir: "{app}"; Comment: "dupcheck no terminal"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir o dupcheck agora"; Flags: nowait postinstall skipifsilent
