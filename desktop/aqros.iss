; Inno Setup — Air Quality Research OS の Windows インストーラー
; CI（.github/workflows/desktop.yml）で  iscc /DAppVersion=<ver> desktop\aqros.iss  として作る。
; 管理者権限なし（利用者ごと）でインストールし、スタートメニューと任意でデスクトップにショートカットを作る。
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{67912C86-F854-4F8B-9DA2-CE40A70FFB51}
AppName=Air Quality Research OS
AppVersion={#AppVersion}
AppPublisher=Air Quality Research OS
DefaultDirName={localappdata}\Programs\AQROS
DefaultGroupName=Air Quality Research OS
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist_desktop
OutputBaseFilename=AQROS-{#AppVersion}-windows-x64-setup
SetupIconFile=assets\aqros.ico
UninstallDisplayIcon={app}\AQROS.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build_desktop\dist\AQROS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Air Quality Research OS"; Filename: "{app}\AQROS.exe"
Name: "{group}\{cm:UninstallProgram,Air Quality Research OS}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Air Quality Research OS"; Filename: "{app}\AQROS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AQROS.exe"; Description: "{cm:LaunchProgram,Air Quality Research OS}"; Flags: nowait postinstall skipifsilent
