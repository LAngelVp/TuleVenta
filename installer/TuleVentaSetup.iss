#define AppName "TuleVenta"
#ifndef AppVersion
  #error "Compila mediante build_installer.bat para obtener app/version.py."
#endif
#define AppPublisher "TuleVenta"
#define AppExeName "TuleVenta.exe"
#define AppDistDir "..\dist\TuleVenta"
#define InstallerOutputDir "output"
#ifndef PostgreSqlVersionMajor
  #error "Compila mediante build_installer.bat para verificar PostgreSQL portable."
#endif
#define PostgreSqlPortableDir "third_party\postgresql-portable"

#ifnexist AppDistDir + "\" + AppExeName
  #error "No se encontro el ejecutable principal. Genera primero dist\TuleVenta\TuleVenta.exe antes de compilar el instalador."
#endif

#ifnexist PostgreSqlPortableDir + "\bin\initdb.exe"
  #error "No se encontro initdb.exe dentro de installer\third_party\postgresql-portable."
#endif

#ifnexist PostgreSqlPortableDir + "\bin\pg_ctl.exe"
  #error "No se encontro pg_ctl.exe dentro de installer\third_party\postgresql-portable."
#endif

#ifnexist PostgreSqlPortableDir + "\bin\psql.exe"
  #error "No se encontro psql.exe dentro de installer\third_party\postgresql-portable."
#endif

#ifnexist PostgreSqlPortableDir + "\bin\pg_isready.exe"
  #error "No se encontro pg_isready.exe dentro de installer\third_party\postgresql-portable."
#endif

[Setup]
DisableDirPage=yes
AppId={{E6D786A1-8D53-4DDF-BE93-EF6A3C2937A1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Se instala en la carpeta del usuario actual para NO requerir Administrador
DefaultDirName={userappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; MODO SIN ADMINISTRADOR
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#InstallerOutputDir}
OutputBaseFilename=TuleVenta-Update-v{#AppVersion}-windows-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\app\Source\Icons\logos\TuleVentaIcon.ico
UninstallDisplayIcon={app}\{#AppExeName}
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "third_party\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#AppDistDir}\*"; DestDir: "{app}"; Excludes: "data\*,datos\*.json,_internal\datos\*.json,PostgreSQL*\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#AppDistDir}\_internal\datos\*.json"; DestDir: "{app}\_internal\datos"; Flags: onlyifdoesntexist skipifsourcedoesntexist
Source: "{#PostgreSqlPortableDir}\*"; DestDir: "{app}\PostgreSQL{#PostgreSqlVersionMajor}"; Excludes: "data,data\*,logfile,*.log"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: PostgreSqlCopyNeeded

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Escribe en HKCU apuntando a la ruta universal de ProgramData esperada por Python
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "TULEVENTA_DB_CONFIG_PATH"; ValueData: "{commonappdata}\TuleVenta\configuracion_bd.json"; Flags: preservestringtype uninsdeletevalue; Check: not ExistingInstallation

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Instalando dependencias de sistema (Visual C++)..."; Flags: waituntilterminated; Check: not ExistingInstallation
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent unchecked; Check: CanLaunchApplication

[UninstallRun]
; Apaga la BD portátil antes de desinstalar
Filename: "{app}\PostgreSQL{#PostgreSqlVersionMajor}\bin\pg_ctl.exe"; Parameters: "stop -D ""{app}\data"" -m fast -w -t 120"; Flags: runhidden waituntilterminated skipifdoesntexist

[Code]
function SetEnvironmentVariable(lpName, lpValue: String): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';

var
  InstallationChecked: Boolean;
  InstallationWasExisting: Boolean;
  InstallDirReady: Boolean;
  PostgreSqlCopyRequired: Boolean;
  PostgreSqlPage: TWizardPage;
  PgPort: String;
  PgSuperUser: String;
  PgSuperPassword: String;
  PgAppDatabase: String;
  PgAppUser: String;
  PgAppPassword: String;
  PgBootstrapOk: Boolean;

  // Controles de interfaz para la página personalizada (2 columnas)
  EdtPgPort: TNewEdit;
  EdtPgSuperUser: TNewEdit;
  EdtPgSuperPassword: TPasswordEdit;
  EdtPgAppDatabase: TNewEdit;
  EdtPgAppUser: TNewEdit;
  EdtPgAppPassword: TPasswordEdit;

function Q(const S: String): String;
begin
  Result := '"' + S + '"';
end;

function InitializeSetup(): Boolean;
begin
  // Nunca expandir {app} durante la inicializacion del wizard.
  InstallDirReady := False;
  InstallationChecked := False;
  Result := True;
end;

function IsPortValid(const Value: String): Boolean;
var
  PortNumber: Integer;
begin
  PortNumber := StrToIntDef(Value, -1);
  Result := (PortNumber > 0) and (PortNumber <= 65535);
end;

function GetInstallDir(): String;
begin
  // {app} no existe todavia cuando Inno evalua ShouldSkipPage/InitializeWizard.
  // Mientras no este listo usamos la misma ruta de DefaultDirName.
  if InstallDirReady then
    Result := ExpandConstant('{app}')
  else
    Result := ExpandConstant('{userappdata}\{#AppName}');
end;

function GetPostgreSqlInstallDir(): String;
begin
  Result := GetInstallDir() + '\PostgreSQL{#PostgreSqlVersionMajor}';
end;

function GetPostgreSqlDataDir(): String;
begin
  Result := GetInstallDir() + '\data';
end;

function GetPsqlPath(): String;
begin
  Result := GetPostgreSqlInstallDir() + '\bin\psql.exe';
end;

function GetInitDbPath(): String;
begin
  Result := GetPostgreSqlInstallDir() + '\bin\initdb.exe';
end;

function GetPgCtlPath(): String;
begin
  Result := GetPostgreSqlInstallDir() + '\bin\pg_ctl.exe';
end;

function GetPgIsReadyPath(): String;
begin
  Result := GetPostgreSqlInstallDir() + '\bin\pg_isready.exe';
end;

function PostgreSqlBinariesInstalled(): Boolean;
begin
  Result := FileExists(GetPgCtlPath()) and
    FileExists(GetInitDbPath()) and
    FileExists(GetPsqlPath()) and
    FileExists(GetPgIsReadyPath());
end;

function PostgreSqlCopyNeeded(): Boolean;
begin
  Result := PostgreSqlCopyRequired;
end;

function GetPostgreSqlLogFile(): String;
begin
  Result := GetInstallDir() + '\postgresql.log';
end;

function GetDbConfigPath(): String;
begin
  // Guarda el archivo de configuración directamente donde lo espera tu App Python
  Result := ExpandConstant('{commonappdata}\TuleVenta\configuracion_bd.json');
end;

function ExistingInstallation(): Boolean;
var
  DataDir: String;
  BaseDir: String;
begin
  if InstallationChecked then
  begin
    Result := InstallationWasExisting;
    Exit;
  end;
  BaseDir := GetInstallDir();
  DataDir := GetPostgreSqlDataDir();
  Result := FileExists(DataDir + '\PG_VERSION') or
    FileExists(BaseDir + '\{#AppExeName}') or
    FileExists(GetDbConfigPath()) or
    FileExists(BaseDir + '\datos\configuracion_bd.json') or
    FileExists(BaseDir + '\PostgreSQL{#PostgreSqlVersionMajor}\data\PG_VERSION') or
    FileExists(ExpandConstant('{commonappdata}\TuleVenta\data\PG_VERSION'));
  InstallationWasExisting := Result;
  InstallationChecked := True;
end;

procedure CargarValoresPostgreSql();
begin
  PgPort := Trim(EdtPgPort.Text);
  PgSuperUser := Lowercase(Trim(EdtPgSuperUser.Text));
  PgSuperPassword := Trim(EdtPgSuperPassword.Text);
  PgAppDatabase := Lowercase(Trim(EdtPgAppDatabase.Text));
  PgAppUser := Lowercase(Trim(EdtPgAppUser.Text));
  PgAppPassword := Trim(EdtPgAppPassword.Text);
end;

function ValidarPaginaPostgreSql(): Boolean;
begin
  CargarValoresPostgreSql();
  Result := True;

  if not IsPortValid(PgPort) then
  begin
    MsgBox('El puerto de PostgreSQL debe ser un numero entre 1 y 65535.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if Length(PgSuperPassword) = 0 then
  begin
    MsgBox('La contrasena superadministrador es obligatoria.', mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if Length(PgAppPassword) = 0 then
  begin
    MsgBox('La contrasena de la aplicacion es obligatoria.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
end;

function WriteDbConfig(var ErrorText: String): Boolean;
var
  JsonText: String;
  ConfigDir: String;
begin
  if FileExists(GetDbConfigPath()) then
  begin
    Result := True;
    Exit;
  end;
  ConfigDir := ExpandConstant('{commonappdata}\TuleVenta');
  if not DirExists(ConfigDir) then
    ForceDirectories(ConfigDir);

  // Escribe la estructura completa con la clave database_url para la app Python
  JsonText := '{' + #13#10 +
    '  "database_url": "postgresql+psycopg2://' + PgAppUser + ':' + PgAppPassword + '@127.0.0.1:' + PgPort + '/' + PgAppDatabase + '",' + #13#10 +
    '  "driver": "postgresql+psycopg2",' + #13#10 +
    '  "host": "127.0.0.1",' + #13#10 +
    '  "port": ' + PgPort + ',' + #13#10 +
    '  "database": "' + PgAppDatabase + '",' + #13#10 +
    '  "username": "' + PgAppUser + '",' + #13#10 +
    '  "password": "' + PgAppPassword + '",' + #13#10 +
    '  "options": {}' + #13#10 +
    '}' + #13#10;

  Result := SaveStringToFile(GetDbConfigPath(), JsonText, False);
  if not Result then
    ErrorText := 'No se pudo escribir la configuracion de base de datos en: ' + GetDbConfigPath();
end;

function InstallPostgreSql(var ErrorText: String): Boolean;
begin
  Result := FileExists(GetInitDbPath()) and FileExists(GetPgCtlPath()) and FileExists(GetPsqlPath());

  if not Result then
    ErrorText := 'No se encontraron los ejecutables de PostgreSQL en ' + GetPostgreSqlInstallDir();
end;

function ExecNativeProgram(const Filename, Params: String; var ResultCode: Integer): Boolean;
var
  BinDir: String;
begin
  BinDir := GetPostgreSqlInstallDir() + '\bin';
  SetEnvironmentVariable('PATH', BinDir + ';' + GetEnv('PATH'));
  Result := Exec(Filename, Params, BinDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function ConfigurePostgreSqlUserMode(var ErrorText: String): Boolean;
var
  ResultCode: Integer;
  DataDir: String;
  LogFile: String;
  SqlScript: String;
  SqlFile: String;
  PgInstallDir: String;
  InitParams: String;
begin
  Result := False;
  DataDir := GetPostgreSqlDataDir();
  LogFile := GetPostgreSqlLogFile();
  PgInstallDir := GetPostgreSqlInstallDir();
  SqlFile := PgInstallDir + '\setup.sql';

  if DirExists(DataDir) then
  begin
    ErrorText := 'La carpeta data ya existe; no se inicializara ni borrara.';
    Exit;
  end;

  // 2. Inicializar con autenticación 'trust' para admitir cualquier contraseña ingresada por el usuario
  InitParams := '-D ' + Q(DataDir) + ' -U postgres -A trust -E UTF8 --locale=C';

  if not ExecNativeProgram(GetInitDbPath(), InitParams, ResultCode) or (ResultCode <> 0) then
  begin
    ErrorText := 'Error al inicializar la base de datos (Codigo: ' + IntToStr(ResultCode) + ')';
    Exit;
  end;

  // 3. Iniciar el motor en modo PORTÁTIL
  ExecNativeProgram(GetPgCtlPath(), 'stop -D ' + Q(DataDir) + ' -m fast', ResultCode);

  if not ExecNativeProgram(GetPgCtlPath(), 'start -D ' + Q(DataDir) + ' -l ' + Q(LogFile) + ' -o "-p ' + PgPort + '" -w', ResultCode) or (ResultCode <> 0) then
  begin
    ErrorText := 'Error al iniciar el motor PostgreSQL (Codigo: ' + IntToStr(ResultCode) + ')';
    Exit;
  end;

  // 4. Configurar contraseñas, usuario de app y base de datos con psql.exe
  SqlScript :=
    'ALTER USER postgres WITH PASSWORD ''' + PgSuperPassword + ''';' + #13#10 +
    'DO $$ ' +
    'BEGIN ' +
    '  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = ''' + PgAppUser + ''') THEN ' +
    '    CREATE USER ' + PgAppUser + ' WITH PASSWORD ''' + PgAppPassword + '''; ' +
    '  END IF; ' +
    'END $$;' + #13#10 +
    'SELECT ''CREATE DATABASE "' + PgAppDatabase + '" OWNER ' + PgAppUser + ''' ' +
    'WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = ''' + PgAppDatabase + ''')\gexec';

  SaveStringToFile(SqlFile, SqlScript, False);

  SetEnvironmentVariable('PGPASSWORD', PgSuperPassword);
  if not ExecNativeProgram(GetPsqlPath(), '-h 127.0.0.1 -p ' + PgPort + ' -U postgres -d postgres -f ' + Q(SqlFile), ResultCode) or (ResultCode <> 0) then
  begin
    ErrorText := 'Error al estructurar la BD con psql.exe (Codigo: ' + IntToStr(ResultCode) + ')';
    DeleteFile(SqlFile);
    Exit;
  end;

  DeleteFile(SqlFile);
  Result := True;
end;

function CanLaunchApplication(): Boolean;
begin
  Result := PgBootstrapOk;
end;

procedure InitializeWizard();
var
  LblIntro: TNewStaticText;
  LblPgPort, LblPgSuperUser: TNewStaticText;
  LblPgSuperPassword, LblPgAppDatabase: TNewStaticText;
  LblPgAppUser, LblPgAppPassword: TNewStaticText;
  ColWidth, ColGap, LeftColX, RightColX: Integer;
  TopY, RowSpacing, LabelOffset: Integer;
begin
  PgBootstrapOk := False;

  PostgreSqlPage := CreateCustomPage(
    wpWelcome,
    'Instancia local de PostgreSQL',
    'Configura la base de datos local de TuleVenta'
  );

  // Texto descriptivo superior equivalente al SubCaption de CreateInputQueryPage
  LblIntro := TNewStaticText.Create(PostgreSqlPage);
  LblIntro.Parent := PostgreSqlPage.Surface;
  LblIntro.Left := 0;
  LblIntro.Top := 0;
  LblIntro.Width := PostgreSqlPage.SurfaceWidth;
  LblIntro.AutoSize := True;
  LblIntro.WordWrap := True;
  LblIntro.Caption := 'El instalador configurara la base de datos en modo local para tu usuario.';

  // Calculo dinamico de geometria en 2 columnas adaptable a DPI (100%, 125%, 150%)
  ColGap := ScaleX(16);
  ColWidth := (PostgreSqlPage.SurfaceWidth - ColGap) div 2;
  LeftColX := 0;
  RightColX := ColWidth + ColGap;

  TopY := LblIntro.Top + LblIntro.Height + ScaleY(16);
  LabelOffset := ScaleY(18);
  RowSpacing := ScaleY(54);

  // ==================== FILA 1 ====================
  // Columna 1: Puerto PostgreSQL
  LblPgPort := TNewStaticText.Create(PostgreSqlPage);
  LblPgPort.Parent := PostgreSqlPage.Surface;
  LblPgPort.Left := LeftColX;
  LblPgPort.Top := TopY;
  LblPgPort.Width := ColWidth;
  LblPgPort.Caption := 'Puerto PostgreSQL:';

  EdtPgPort := TNewEdit.Create(PostgreSqlPage);
  EdtPgPort.Parent := PostgreSqlPage.Surface;
  EdtPgPort.Left := LeftColX;
  EdtPgPort.Top := TopY + LabelOffset;
  EdtPgPort.Width := ColWidth;
  EdtPgPort.Text := '5432';

  // Columna 2: Usuario administrador
  LblPgSuperUser := TNewStaticText.Create(PostgreSqlPage);
  LblPgSuperUser.Parent := PostgreSqlPage.Surface;
  LblPgSuperUser.Left := RightColX;
  LblPgSuperUser.Top := TopY;
  LblPgSuperUser.Width := ColWidth;
  LblPgSuperUser.Caption := 'Usuario administrador:';

  EdtPgSuperUser := TNewEdit.Create(PostgreSqlPage);
  EdtPgSuperUser.Parent := PostgreSqlPage.Surface;
  EdtPgSuperUser.Left := RightColX;
  EdtPgSuperUser.Top := TopY + LabelOffset;
  EdtPgSuperUser.Width := ColWidth;
  EdtPgSuperUser.Text := 'postgres';

  // ==================== FILA 2 ====================
  TopY := TopY + RowSpacing;

  // Columna 1: Contraseña administrador
  LblPgSuperPassword := TNewStaticText.Create(PostgreSqlPage);
  LblPgSuperPassword.Parent := PostgreSqlPage.Surface;
  LblPgSuperPassword.Left := LeftColX;
  LblPgSuperPassword.Top := TopY;
  LblPgSuperPassword.Width := ColWidth;
  LblPgSuperPassword.Caption := 'Contrasena administrador:';

  EdtPgSuperPassword := TPasswordEdit.Create(PostgreSqlPage);
  EdtPgSuperPassword.Parent := PostgreSqlPage.Surface;
  EdtPgSuperPassword.Left := LeftColX;
  EdtPgSuperPassword.Top := TopY + LabelOffset;
  EdtPgSuperPassword.Width := ColWidth;
  EdtPgSuperPassword.Text := '';

  // Columna 2: Base de datos aplicación
  LblPgAppDatabase := TNewStaticText.Create(PostgreSqlPage);
  LblPgAppDatabase.Parent := PostgreSqlPage.Surface;
  LblPgAppDatabase.Left := RightColX;
  LblPgAppDatabase.Top := TopY;
  LblPgAppDatabase.Width := ColWidth;
  LblPgAppDatabase.Caption := 'Base de datos aplicacion:';

  EdtPgAppDatabase := TNewEdit.Create(PostgreSqlPage);
  EdtPgAppDatabase.Parent := PostgreSqlPage.Surface;
  EdtPgAppDatabase.Left := RightColX;
  EdtPgAppDatabase.Top := TopY + LabelOffset;
  EdtPgAppDatabase.Width := ColWidth;
  EdtPgAppDatabase.Text := 'TuleVenta';

  // ==================== FILA 3 ====================
  TopY := TopY + RowSpacing;

  // Columna 1: Usuario aplicación
  LblPgAppUser := TNewStaticText.Create(PostgreSqlPage);
  LblPgAppUser.Parent := PostgreSqlPage.Surface;
  LblPgAppUser.Left := LeftColX;
  LblPgAppUser.Top := TopY;
  LblPgAppUser.Width := ColWidth;
  LblPgAppUser.Caption := 'Usuario aplicacion:';

  EdtPgAppUser := TNewEdit.Create(PostgreSqlPage);
  EdtPgAppUser.Parent := PostgreSqlPage.Surface;
  EdtPgAppUser.Left := LeftColX;
  EdtPgAppUser.Top := TopY + LabelOffset;
  EdtPgAppUser.Width := ColWidth;
  EdtPgAppUser.Text := 'tuleventa_app';

  // Columna 2: Contraseña aplicación
  LblPgAppPassword := TNewStaticText.Create(PostgreSqlPage);
  LblPgAppPassword.Parent := PostgreSqlPage.Surface;
  LblPgAppPassword.Left := RightColX;
  LblPgAppPassword.Top := TopY;
  LblPgAppPassword.Width := ColWidth;
  LblPgAppPassword.Caption := 'Contrasena aplicacion:';

  EdtPgAppPassword := TPasswordEdit.Create(PostgreSqlPage);
  EdtPgAppPassword.Parent := PostgreSqlPage.Surface;
  EdtPgAppPassword.Left := RightColX;
  EdtPgAppPassword.Top := TopY + LabelOffset;
  EdtPgAppPassword.Width := ColWidth;
  EdtPgAppPassword.Text := '';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = PostgreSqlPage.ID then
    Result := ValidarPaginaPostgreSql();
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = PostgreSqlPage.ID) and ExistingInstallation;
end;

function ReadPgMajorFromDataDir(const DataDir: String): String;
var
  Contents: AnsiString;
begin
  Result := '';
  if LoadStringFromFile(DataDir + '\PG_VERSION', Contents) then
    Result := Trim(Contents);
end;

function GetPgCtlForDataDir(const BaseDir, DataDir: String): String;
var
  Major: String;
begin
  Result := '';
  Major := ReadPgMajorFromDataDir(DataDir);
  if Major <> '' then
    Result := BaseDir + '\PostgreSQL' + Major + '\bin\pg_ctl.exe';
  if (Result = '') or (not FileExists(Result)) then
    Result := BaseDir + '\PostgreSQL{#PostgreSqlVersionMajor}\bin\pg_ctl.exe';
  if not FileExists(Result) then
    Result := '';
end;

function GetConfiguredPgPort(): String;
var
  Contents: AnsiString;
  Text: String;
  Position: Integer;
  Index: Integer;
begin
  Result := '';
  if FileExists(GetDbConfigPath()) and LoadStringFromFile(GetDbConfigPath(), Contents) then
  begin
    Text := Contents;
    Position := Pos('"port"', Text);
    if Position > 0 then
    begin
      Index := Position + Length('"port"');
      while (Index <= Length(Text)) and (Text[Index] <> ':') do
        Index := Index + 1;
      if Index <= Length(Text) then
      begin
        Index := Index + 1;
        while (Index <= Length(Text)) and (Pos(Copy(Text, Index, 1), '0123456789') = 0) do
          Index := Index + 1;
        while (Index <= Length(Text)) and (Pos(Copy(Text, Index, 1), '0123456789') > 0) do
        begin
          Result := Result + Copy(Text, Index, 1);
          Index := Index + 1;
        end;
      end;
    end;
  end;

  if Result = '' then
  begin
    if PgPort <> '' then
      Result := PgPort
    else
      Result := '5432';
  end;
end;

function WaitForPostgreSqlReady(const Port: String; TimeoutSeconds: Integer): Boolean;
var
  Attempt: Integer;
  PgIsReady: String;
  ResultCode: Integer;
begin
  Result := False;
  PgIsReady := GetPgIsReadyPath();
  if (Port = '') or (not FileExists(PgIsReady)) then
    Exit;

  for Attempt := 1 to TimeoutSeconds * 2 do
  begin
    if Exec(PgIsReady, '-h 127.0.0.1 -p ' + Port + ' -t 2',
        GetPostgreSqlInstallDir() + '\bin', SW_HIDE, ewWaitUntilTerminated,
        ResultCode) and (ResultCode = 0) then
    begin
      Result := True;
      Exit;
    end;
    Sleep(500);
  end;
end;

function StartPortablePostgreSql(var ErrorText: String): Boolean;
var
  DataDir, LogFile, PgCtl, BinDir, Port: String;
  ResultCode: Integer;
begin
  Result := False;
  DataDir := GetPostgreSqlDataDir();
  LogFile := GetPostgreSqlLogFile();
  Port := GetConfiguredPgPort();

  if not FileExists(DataDir + '\PG_VERSION') then
  begin
    ErrorText := 'No se encontro una carpeta de datos valida en ' + DataDir;
    Exit;
  end;

  PgCtl := GetPgCtlForDataDir(GetInstallDir(), DataDir);
  if PgCtl = '' then
  begin
    ErrorText := 'No se encontro pg_ctl.exe para PostgreSQL en ' + GetInstallDir();
    Exit;
  end;

  BinDir := ExtractFileDir(PgCtl);
  if not Exec(PgCtl, 'status -D ' + Q(DataDir), BinDir, SW_HIDE,
      ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
  begin
    if not Exec(PgCtl, 'start -D ' + Q(DataDir) + ' -l ' + Q(LogFile) +
        ' -o ' + Q('-p ' + Port) + ' -w -t 60', BinDir, SW_HIDE,
        ewWaitUntilTerminated, ResultCode) or (ResultCode <> 0) then
    begin
      ErrorText := 'No se pudo iniciar PostgreSQL (Codigo: ' + IntToStr(ResultCode) + ').';
      Exit;
    end;
  end;

  if not WaitForPostgreSqlReady(Port, 30) then
  begin
    ErrorText := 'PostgreSQL no respondio en 127.0.0.1:' + Port +
      ' despues de 30 segundos.';
    Exit;
  end;

  Result := True;
end;

procedure FinalizarPostgreSqlPortable();
var
  ErrorText: String;
begin
  PgBootstrapOk := False;

  if ExistingInstallation then
  begin
    if not PostgreSqlBinariesInstalled() then
    begin
      MsgBox('No se encontraron los binarios de PostgreSQL en ' +
        GetPostgreSqlInstallDir() + #13#10#13#10 +
        'Vuelve a ejecutar el instalador para reparar la instalacion.',
        mbCriticalError, MB_OK);
      Exit;
    end;

    if not StartPortablePostgreSql(ErrorText) then
    begin
      MsgBox(ErrorText, mbCriticalError, MB_OK);
      Exit;
    end;

    PgBootstrapOk := True;
    Exit;
  end;

  CargarValoresPostgreSql();

  if not InstallPostgreSql(ErrorText) then
  begin
    MsgBox(ErrorText, mbCriticalError, MB_OK);
    Exit;
  end;

  if not ConfigurePostgreSqlUserMode(ErrorText) then
  begin
    MsgBox(ErrorText, mbCriticalError, MB_OK);
    Exit;
  end;

  if not WaitForPostgreSqlReady(PgPort, 30) then
  begin
    MsgBox('PostgreSQL se inicio pero no respondio en 127.0.0.1:' + PgPort +
      ' despues de 30 segundos.', mbCriticalError, MB_OK);
    Exit;
  end;

  if not WriteDbConfig(ErrorText) then
  begin
    MsgBox(ErrorText, mbCriticalError, MB_OK);
    Exit;
  end;

  PgBootstrapOk := True;
end;

procedure DetenerPostgreSqlPortable(const BaseDir: String);
var
  DataDir, PgCtl: String;
  ResultCode: Integer;
begin
  DataDir := BaseDir + '\data';
  if not FileExists(DataDir + '\PG_VERSION') then
    Exit;

  PgCtl := GetPgCtlForDataDir(BaseDir, DataDir);
  if PgCtl = '' then
    Exit;

  Exec(PgCtl, 'stop -D ' + Q(DataDir) + ' -m fast -w -t 30', BaseDir,
    SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function DetenerProcesosInstalacion(const BaseDir: String): Boolean;
var
  ScriptFile, Script, PowerShell: String;
  ResultCode: Integer;
begin
  Result := False;
  ScriptFile := ExpandConstant('{tmp}\tuleventa_stop_processes.ps1');
  Script :=
    'param([string]$Root)' + #13#10 +
    '$ErrorActionPreference = ''SilentlyContinue''' + #13#10 +
    '$Root = [System.IO.Path]::GetFullPath($Root)' + #13#10 +
    'Get-Process -Name TuleVenta,postgres -ErrorAction SilentlyContinue | ' +
    'Where-Object { $_.Path -and $_.Path.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase) } | ' +
    'Stop-Process -Force -ErrorAction SilentlyContinue' + #13#10 +
    'Start-Sleep -Milliseconds 500' + #13#10;

  if not SaveStringToFile(ScriptFile, Script, False) then
    Exit;

  PowerShell := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Result := Exec(PowerShell, '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ' +
    Q(ScriptFile) + ' -Root ' + Q(BaseDir), '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  DeleteFile(ScriptFile);

  // Respaldo para el ejecutable principal si PowerShell no estuviera disponible.
  if not Result then
    Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM TuleVenta.exe', '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function IsProtectedInstallEntry(const Name: String): Boolean;
var
  LowerName: String;
begin
  LowerName := Lowercase(Name);
  Result := (CompareText(Name, 'data') = 0) or
    (CompareText(Name, 'datos') = 0) or
    (CompareText(Name, 'configuracion_bd.json') = 0) or
    (CompareText(Name, 'postgresql.log') = 0) or
    (Pos('postgresql', LowerName) = 1) or
    (Pos('unins', LowerName) = 1);
end;

procedure CleanInstallContents(const Dir: String);
var
  FindRec: TFindRec;
  Name, FullPath: String;
begin
  if not FindFirst(Dir + '\*', FindRec) then
    Exit;
  try
    repeat
      Name := FindRec.Name;
      if (Name <> '.') and (Name <> '..') and (not IsProtectedInstallEntry(Name)) then
      begin
        FullPath := Dir + '\' + Name;
        if DirExists(FullPath) then
        begin
          // _internal se limpia por dentro para conservar _internal\datos.
          if CompareText(Name, '_internal') = 0 then
            CleanInstallContents(FullPath)
          else
            DelTree(FullPath, True, True, True);
        end
        else
          DeleteFile(FullPath);
      end;
    until not FindNext(FindRec);
  finally
    FindClose(FindRec);
  end;
end;

procedure LimpiarInstalacionAnterior(const BaseDir: String);
begin
  // Protege data\, datos\, _internal\datos, PostgreSQL* y el desinstalador.
  if DirExists(BaseDir) then
    CleanInstallContents(BaseDir);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Index: Integer;
  UpdateOnly, AutomaticMode: Boolean;
  BaseDir: String;
begin
  Result := '';
  InstallDirReady := True;
  BaseDir := GetInstallDir();

  // Recalcular con el {app} real; ShouldSkipPage pudo haber usado la ruta por defecto.
  InstallationChecked := False;
  InstallationWasExisting := ExistingInstallation();
  InstallationChecked := True;

  // Se calcula una sola vez antes de [Files]: la condicion Check se evalua
  // por cada archivo y no debe cambiar mientras se copia PostgreSQL.
  PostgreSqlCopyRequired := not PostgreSqlBinariesInstalled();

  UpdateOnly := False;
  for Index := 1 to ParamCount do
    if CompareText(ParamStr(Index), '/UPDATEONLY') = 0 then
      UpdateOnly := True;
  AutomaticMode := UpdateOnly or WizardSilent;

  if UpdateOnly and (not ExistingInstallation or
      not FileExists(BaseDir + '\{#AppExeName}')) then
  begin
    Result := 'No hay una instalacion existente valida; actualizacion cancelada.';
    Exit;
  end;

  if WizardSilent and (not UpdateOnly) and (not ExistingInstallation) then
  begin
    Result := 'La instalacion inicial requiere configurar PostgreSQL en modo interactivo.';
    Exit;
  end;

  if ExistingInstallation then
  begin
    if not AutomaticMode then
    begin
      if MsgBox('Se detecto una instalacion anterior de TuleVenta.' + #13#10#13#10 +
          'Se cerrara TuleVenta, se detendra PostgreSQL y se limpiaran los binarios anteriores.' + #13#10 +
          'La base de datos (data) y tus datos (datos) se conservaran.' + #13#10#13#10 +
          'Deseas continuar con la instalacion?',
          mbConfirmation, MB_YESNO) <> IDYES then
      begin
        Result := 'Instalacion cancelada por el usuario.';
        Exit;
      end;
    end;

    DetenerPostgreSqlPortable(BaseDir);
    DetenerProcesosInstalacion(BaseDir);
    Sleep(1000);
    if not AutomaticMode then
      LimpiarInstalacionAnterior(BaseDir);
  end
  else
  begin
    // Limpieza preventiva de restos de una instalacion interrumpida.
    DetenerProcesosInstalacion(BaseDir);
    Sleep(1000);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    FinalizarPostgreSqlPortable();
end;