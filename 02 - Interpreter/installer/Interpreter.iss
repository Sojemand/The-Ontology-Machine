#ifndef SourceDir
  #error SourceDir must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppId "{{F9A3AEAB-29CF-4568-B6E8-8B0D49D8A4A8}"
#define MyAppName "Interpreter"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
DefaultDirName={localappdata}\Enterprise Stack\Interpreter\app
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
OutputBaseFilename=Interpreter-Setup-{#AppVersion}
UninstallDisplayName={#MyAppName}

[Dirs]
Name: "{localappdata}\Enterprise Stack\Interpreter\config"; Flags: uninsneveruninstall
Name: "{localappdata}\Enterprise Stack\Interpreter\state"; Flags: uninsneveruninstall
Name: "{localappdata}\Enterprise Stack\Interpreter\output"; Flags: uninsneveruninstall
Name: "{localappdata}\Enterprise Stack\Interpreter\logs"; Flags: uninsneveruninstall

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Code]
procedure DeleteMutableData();
begin
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Interpreter\config'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Interpreter\state'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Interpreter\output'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Interpreter\logs'), True, True, True);
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
