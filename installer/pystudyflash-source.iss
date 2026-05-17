#define MyAppName "pyStudyFlash"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "pyStudyFlash Developer"

[Setup]
AppId={{E7D6E167-2E4B-498A-90CE-A7977D78A6C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\pyStudyFlash.vbs
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir=output
OutputBaseFilename=pyStudyFlash-source-setup-{#MyAppVersion}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\pystudyflash.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\client.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\cursor.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app_paths.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\start.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\classes\*.py"; DestDir: "{app}\classes"; Flags: ignoreversion
Source: "..\cursors\*"; DestDir: "{app}\cursors"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "install_env.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "pyStudyFlash.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "launcher.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "wheelhouse\*"; DestDir: "{app}\wheelhouse"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Dirs]
Name: "{app}\sets"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{win}\System32\wscript.exe"; Parameters: """{app}\pyStudyFlash.vbs"""; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{win}\System32\wscript.exe"; Parameters: """{app}\pyStudyFlash.vbs"""; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{win}\System32\wscript.exe"; Parameters: """{app}\pyStudyFlash.vbs"""; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  Params: String;
begin
  if CurStep = ssPostInstall then begin
    WizardForm.StatusLabel.Caption := 'Создание окружения Python и установка пакетов...';
    Params := '-NoProfile -ExecutionPolicy Bypass -File "' +
      ExpandConstant('{app}\install_env.ps1') + '" -AppDir "' +
      ExpandConstant('{app}') + '"';
    if not Exec(
      ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      Params,
      ExpandConstant('{app}'),
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode) then begin
      MsgBox('Не удалось запустить настройку Python-окружения.', mbError, MB_OK);
      Abort;
    end;
    if ResultCode <> 0 then begin
      MsgBox(
        'Не удалось установить Python-окружение и зависимости.' + #13#10 +
        'Подробности смотрите в файле install-env.log в папке установки.',
        mbError,
        MB_OK);
      Abort;
    end;
  end;
end;
