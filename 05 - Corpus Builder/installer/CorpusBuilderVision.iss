#ifndef SourceDir
  #error SourceDir must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppId "{{8F8546C4-2C45-45F6-9A86-60A5A6708E5E}"
#define MyAppName "Corpus Builder Vision"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
DefaultDirName={localappdata}\Programs\Corpus Builder Vision
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
OutputBaseFilename=CorpusBuilderVision-Setup-{#AppVersion}
UninstallDisplayName={#MyAppName}

[Dirs]
Name: "{app}\output"; Flags: uninsneveruninstall
Name: "{app}\state"; Flags: uninsneveruninstall

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Code]
procedure DeleteMutableData();
begin
  DelTree(ExpandConstant('{app}\output'), True, True, True);
  DelTree(ExpandConstant('{app}\state'), True, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then begin
    if MsgBox(
      'Auch output und state loeschen?',
      mbConfirmation,
      MB_YESNO or MB_DEFBUTTON2
    ) = IDYES then begin
      DeleteMutableData();
    end;
  end;
end;
