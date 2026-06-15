#ifndef SourceDir
  #error SourceDir must be defined
#endif
#ifndef OutputDir
  #error OutputDir must be defined
#endif
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define MyAppId "{{D9E95F72-7C1A-4E12-B606-0C4B54F09C92}"
#define MyAppName "Ontology Machine"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
DefaultDirName={localappdata}\Programs\Ontology Machine
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
CloseApplications=yes
OutputDir={#OutputDir}
OutputBaseFilename=OntologyMachine-AllInOne-Setup-{#AppVersion}
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\icons\ontology-machine.ico
SetupIconFile={#SourceDir}\icons\ontology-machine.ico

[Tasks]
Name: "desktop_shortcuts"; Description: "Desktop-Ordner mit Ontology Machine Verknuepfungen"

[Dirs]
Name: "{autodesktop}\{#MyAppName}"; Tasks: desktop_shortcuts
Name: "{app}\00 - Orchestrator\state"
Name: "{app}\00 - Orchestrator\config"
Name: "{app}\01 - Optimizer\state"
Name: "{app}\01 - Optimizer\logs"
Name: "{app}\02 - Interpreter\config"
Name: "{app}\02 - Interpreter\state"
Name: "{app}\02 - Interpreter\logs"
Name: "{app}\03 - Validator\state"
Name: "{app}\03 - Validator\config"
Name: "{app}\04 - Normalizer\state"
Name: "{app}\04 - Normalizer\config"
Name: "{app}\05 - Corpus Builder\state"
Name: "{app}\06 - Edit Suite\state"
Name: "{app}\07 - MCP Server\state"
Name: "{app}\07 - MCP Server\config"
Name: "{app}\08 - Semantic Control Kernel\state"
Name: "{app}\08 - Semantic Control Kernel\config"
Name: "{localappdata}\Enterprise Stack\Client Frontend\config"
Name: "{localappdata}\Enterprise Stack\Client Frontend\state"
Name: "{localappdata}\Enterprise Stack\Client Frontend\logs"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "00 - Orchestrator\config\*,03 - Validator\config\*,04 - Normalizer\config\*,07 - MCP Server\config\*,08 - Semantic Control Kernel\config\*"
Source: "{#SourceDir}\00 - Orchestrator\config\*"; DestDir: "{app}\00 - Orchestrator\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SourceDir}\03 - Validator\config\*"; DestDir: "{app}\03 - Validator\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SourceDir}\04 - Normalizer\config\*"; DestDir: "{app}\04 - Normalizer\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SourceDir}\07 - MCP Server\config\*"; DestDir: "{app}\07 - MCP Server\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SourceDir}\08 - Semantic Control Kernel\config\*"; DestDir: "{app}\08 - Semantic Control Kernel\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist skipifsourcedoesntexist
Source: "{#SourceDir}\The Machine Doku PDF\Quickstart_Handbook.pdf"; DestDir: "{autodesktop}\{#MyAppName}"; Flags: ignoreversion; Tasks: desktop_shortcuts

[Icons]
Name: "{autoprograms}\{#MyAppName}\Start Orchestrator"; Filename: "{app}\Start Orchestrator.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icons\orchestrator.ico"
Name: "{autoprograms}\{#MyAppName}\Start Client Frontend"; Filename: "{app}\Start Client Frontend.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icons\client-frontend.ico"
Name: "{autoprograms}\{#MyAppName}\Configure Client Frontend"; Filename: "{app}\Configure Client Frontend.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icons\frontend-config.ico"
Name: "{autoprograms}\{#MyAppName}\Extractor Tools\Article Archive Extractor"; Filename: "{app}\Extractor_Tools\Article Archive Extractor\Start Article Archive Extractor.bat"; WorkingDir: "{app}\Extractor_Tools\Article Archive Extractor"; IconFilename: "{app}\icons\article-extractor.ico"
Name: "{autoprograms}\{#MyAppName}\Extractor Tools\YouTube Transcript Extractor"; Filename: "{app}\Extractor_Tools\YouTube Transcript Extractor\Start YouTube Transcript Extractor.bat"; WorkingDir: "{app}\Extractor_Tools\YouTube Transcript Extractor"; IconFilename: "{app}\icons\youtube-transcript.ico"
Name: "{autoprograms}\{#MyAppName}\Extractor Tools\Audio Transcription Extractor"; Filename: "{app}\Extractor_Tools\Audio Transcription Extractor\Start Audio Transcription Extractor.bat"; WorkingDir: "{app}\Extractor_Tools\Audio Transcription Extractor"; IconFilename: "{app}\icons\audio-transcription.ico"
Name: "{autodesktop}\{#MyAppName}\Start Orchestrator"; Filename: "{app}\Start Orchestrator.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icons\orchestrator.ico"; Tasks: desktop_shortcuts
Name: "{autodesktop}\{#MyAppName}\Start Client Frontend"; Filename: "{app}\Start Client Frontend.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icons\client-frontend.ico"; Tasks: desktop_shortcuts
Name: "{autodesktop}\{#MyAppName}\Configure Client Frontend"; Filename: "{app}\Configure Client Frontend.bat"; WorkingDir: "{app}"; IconFilename: "{app}\icons\frontend-config.ico"; Tasks: desktop_shortcuts
Name: "{autodesktop}\{#MyAppName}\Article Archive Extractor"; Filename: "{app}\Extractor_Tools\Article Archive Extractor\Start Article Archive Extractor.bat"; WorkingDir: "{app}\Extractor_Tools\Article Archive Extractor"; IconFilename: "{app}\icons\article-extractor.ico"; Tasks: desktop_shortcuts
Name: "{autodesktop}\{#MyAppName}\YouTube Transcript Extractor"; Filename: "{app}\Extractor_Tools\YouTube Transcript Extractor\Start YouTube Transcript Extractor.bat"; WorkingDir: "{app}\Extractor_Tools\YouTube Transcript Extractor"; IconFilename: "{app}\icons\youtube-transcript.ico"; Tasks: desktop_shortcuts
Name: "{autodesktop}\{#MyAppName}\Audio Transcription Extractor"; Filename: "{app}\Extractor_Tools\Audio Transcription Extractor\Start Audio Transcription Extractor.bat"; WorkingDir: "{app}\Extractor_Tools\Audio Transcription Extractor"; IconFilename: "{app}\icons\audio-transcription.ico"; Tasks: desktop_shortcuts

[Code]
procedure DeleteMutableData();
begin
  DelTree(ExpandConstant('{app}\00 - Orchestrator\state'), True, True, True);
  DelTree(ExpandConstant('{app}\00 - Orchestrator\config'), True, True, True);
  DelTree(ExpandConstant('{app}\01 - Optimizer\state'), True, True, True);
  DelTree(ExpandConstant('{app}\01 - Optimizer\logs'), True, True, True);
  DelTree(ExpandConstant('{app}\02 - Interpreter\config'), True, True, True);
  DelTree(ExpandConstant('{app}\02 - Interpreter\state'), True, True, True);
  DelTree(ExpandConstant('{app}\02 - Interpreter\logs'), True, True, True);
  DelTree(ExpandConstant('{app}\03 - Validator\state'), True, True, True);
  DelTree(ExpandConstant('{app}\03 - Validator\config'), True, True, True);
  DelTree(ExpandConstant('{app}\04 - Normalizer\state'), True, True, True);
  DelTree(ExpandConstant('{app}\04 - Normalizer\config'), True, True, True);
  DelTree(ExpandConstant('{app}\05 - Corpus Builder\state'), True, True, True);
  DelTree(ExpandConstant('{app}\06 - Edit Suite\state'), True, True, True);
  DelTree(ExpandConstant('{app}\07 - MCP Server\state'), True, True, True);
  DelTree(ExpandConstant('{app}\07 - MCP Server\config'), True, True, True);
  DelTree(ExpandConstant('{app}\08 - Semantic Control Kernel\state'), True, True, True);
  DelTree(ExpandConstant('{app}\08 - Semantic Control Kernel\config'), True, True, True);
  DelTree(ExpandConstant('{localappdata}\Enterprise Stack\Client Frontend'), True, True, True);
end;

procedure DeleteInstallRoot();
begin
  DelTree(ExpandConstant('{app}'), True, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then begin
    DeleteMutableData();
    DeleteInstallRoot();
  end;
end;
