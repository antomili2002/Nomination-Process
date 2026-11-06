; Inno Setup script - compiled by packaging\build.ps1 when Inno Setup 6 is installed.
#define AppName "Scenario Delta Report Generator"
#define AppVersion "0.1.0"
#define AppPublisher "Antonio Militello"
#define AppExe "ScenarioDeltaReport.exe"

[Setup]
AppId={{6E1C2B7A-3F4D-4C8E-9B1A-5D2E7F3A9C10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppCopyright=Copyright (c) 2026 Antonio Militello
DefaultDirName={localappdata}\Programs\ScenarioDeltaReport
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=ScenarioDeltaReport-Setup-{#AppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\ScenarioDeltaReport\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\ScenarioDeltaReport"
