#ifndef SourceDir
  #error SourceDir must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppId "{{7B9A6E6E-5E4B-4C84-9D7D-1F5EED4F1323}"
#define MyAppName "Optimizer"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
DefaultDirName={localappdata}\Enterprise Stack\Optimizer\app
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
OutputBaseFilename=Optimizer-Setup-{#AppVersion}
UninstallDisplayName={#MyAppName}

[Dirs]
Name: "{localappdata}\Enterprise Stack\Optimizer\config"; Flags: uninsneveruninstall
Name: "{localappdata}\Enterprise Stack\Optimizer\state"; Flags: uninsneveruninstall
Name: "{localappdata}\Enterprise Stack\Optimizer\output"; Flags: uninsneveruninstall
Name: "{localappdata}\Enterprise Stack\Optimizer\logs"; Flags: uninsneveruninstall

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Code]
procedure DeleteMutableData();
begin
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Optimizer\config'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Optimizer\state'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Optimizer\output'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Optimizer\logs'), True, True, True);
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
