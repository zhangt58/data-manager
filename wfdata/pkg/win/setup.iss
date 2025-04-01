; SEE THE DOCUMENTATION FOR DETAILS ON CREATING .ISS SCRIPT FILES!

#define MyAppName "DM-Wave"
#define MyAppVersion "0.9.9-1"
#define MyAppPublisher "FRIB, MSU"
#define MyAppURL "https://stash.frib.msu.edu/projects/PHYAPP/repos/phantasy-apps"
#define OutputName "DataManager-Wave"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\{#MyAppName}
DefaultGroupName=Data Manager
AllowNoIcons=yes
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
OutputDir=.\output
OutputBaseFilename={#OutputName}_{#MyAppVersion}
SetupIconFile=.\icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\dm-wave\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "run-dm-app.bat"; DestDir: "{app}"
Source: ".\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Run]
// User selected... these files are shown for launch after everything is done
Filename: "{app}\run-dm-app.bat"; WorkingDir: "{app}"; Description: View BCM/BPM waveform data in DM-Wave; Flags: postinstall runascurrentuser skipifsilent;

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\run-dm-app.bat"; WorkingDir: "{app}"; Comment: "Launch {#MyAppName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\Support Website"; Filename: "https://wikihost.frib.msu.edu/AcceleratorPhysics/doku.php?id=data:linacdata"; Comment: "Visit Wiki Page"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Comment: "Remove {#MyAppName}"
