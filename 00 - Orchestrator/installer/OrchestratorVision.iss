#ifndef SourceDir
  #error SourceDir must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppId "{{98A3CFB9-A8C1-4F81-94D5-A8C5E87A4D7B}"
#define MyAppName "Vision Pipeline Orchestrator"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
DefaultDirName={localappdata}\Programs\Vision Pipeline\00 - Orchestrator
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UsePreviousAppDir=yes
UsePreviousGroup=yes
DisableProgramGroupPage=yes
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=no
OutputDir={#OutputDir}
OutputBaseFilename=OrchestratorVision-Setup-{#AppVersion}
UninstallDisplayName={#MyAppName}

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung anlegen"; Flags: unchecked

[Dirs]
Name: "{app}\state"; Flags: uninsneveruninstall
Name: "{app}\config"; Flags: uninsneveruninstall

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "config\*"
Source: "{#SourceDir}\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\run.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Code]
procedure DeleteMutableData();
begin
  DelTree(ExpandConstant('{app}\state'), True, True, True);
  DelTree(ExpandConstant('{app}\config'), True, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then begin
    if MsgBox(
      'Auch state und config loeschen?',
      mbConfirmation,
      MB_YESNO or MB_DEFBUTTON2
    ) = IDYES then begin
      DeleteMutableData();
    end;
  end;
end;
