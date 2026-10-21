#define AppName "TuleVenta"
#define AppVersion "1.0.0"
#define AppPublisher "TuleVenta"
#define AppExeName "TuleVenta.exe"
#define AppDistDir "..\dist\TuleVenta"
#define InstallerOutputDir "output"
#define PostgreSqlVersionMajor "16"
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

[Setup]
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
OutputBaseFilename=TuleVenta-Setup-User
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\app\Source\Icons\logos\TuleVentaIcon.ico
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#AppDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PostgreSqlPortableDir}\*"; DestDir: "{app}\PostgreSQL{#PostgreSqlVersionMajor}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Escribe en HKCU apuntando a la ruta universal de ProgramData esperada por Python
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "TULEVENTA_DB_CONFIG_PATH"; ValueData: "{commonappdata}\TuleVenta\configuracion_bd.json"; Flags: preservestringtype uninsdeletevalue

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent unchecked; Check: CanLaunchApplication

[UninstallRun]
; Apaga la BD portátil antes de desinstalar
Filename: "{app}\PostgreSQL{#PostgreSqlVersionMajor}\bin\pg_ctl.exe"; Parameters: "stop -D ""{app}\data"" -m fast -w -t 120"; Flags: runhidden waituntilterminated skipifdoesntexist

[Code]
function SetEnvironmentVariable(lpName, lpValue: String): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';

var
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

function IsPortValid(const Value: String): Boolean;
var
  PortNumber: Integer;
begin
  PortNumber := StrToIntDef(Value, -1);
  Result := (PortNumber > 0) and (PortNumber <= 65535);
end;

function GetPostgreSqlInstallDir(): String;
begin
  Result := ExpandConstant('{app}\PostgreSQL{#PostgreSqlVersionMajor}');
end;

function GetPostgreSqlDataDir(): String;
begin
  Result := ExpandConstant('{app}\data');
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

function GetPostgreSqlLogFile(): String;
begin
  Result := ExpandConstant('{app}\postgresql.log');
end;

function GetDbConfigPath(): String;
begin
  // Guarda el archivo de configuración directamente donde lo espera tu App Python
  Result := ExpandConstant('{commonappdata}\TuleVenta\configuracion_bd.json');
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

  // 1. Limpieza de datos antiguos
  if DirExists(DataDir) then
    DelTree(DataDir, True, True, True);

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

procedure FinalizarPostgreSqlPortable();
var
  ErrorText: String;
begin
  CargarValoresPostgreSql();
  PgBootstrapOk := False;

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

  if not WriteDbConfig(ErrorText) then
  begin
    MsgBox(ErrorText, mbCriticalError, MB_OK);
    Exit;
  end;

  PgBootstrapOk := True;
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
    wpSelectDir,
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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    FinalizarPostgreSqlPortable();
end;