#ifndef SourceDir
  #error SourceDir must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppId "{{A22E59F7-CE70-4B7E-9B53-50E99817E2B4}"
#define MyAppName "Validator Vision"
#define MyAppHome "{localappdata}\Enterprise Stack\Validator Vision"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
DefaultDirName={#MyAppHome}\app
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
OutputBaseFilename=ValidatorVision-Setup-{#AppVersion}
UninstallDisplayName={#MyAppName}

[Dirs]
Name: "{#MyAppHome}\config"; Flags: uninsneveruninstall
Name: "{#MyAppHome}\state"; Flags: uninsneveruninstall
Name: "{#MyAppHome}\output"; Flags: uninsneveruninstall
Name: "{#MyAppHome}\logs"; Flags: uninsneveruninstall

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#SourceDir}\config\config.json"; DestDir: "{#MyAppHome}\config"; Flags: ignoreversion onlyifdoesntexist

[Code]
procedure DeleteMutableData();
begin
  DelTree(ExpandConstant('{#MyAppHome}\config'), True, True, True);
  DelTree(ExpandConstant('{#MyAppHome}\state'), True, True, True);
  DelTree(ExpandConstant('{#MyAppHome}\output'), True, True, True);
  DelTree(ExpandConstant('{#MyAppHome}\logs'), True, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then begin
    if MsgBox(
      'Auch config, state, output und logs loeschen?',
      mbConfirmation,
      MB_YESNO or MB_DEFBUTTON2
    ) = IDYES then begin
      DeleteMutableData();
    end;
  end;
end;
