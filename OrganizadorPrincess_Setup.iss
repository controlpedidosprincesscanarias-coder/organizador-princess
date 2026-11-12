; ================================================================
;  Organizador de Escritorio y Agenda Princess
;  Instalador — v{#MyAppVersion}
;  © VAMA 2026 · Central de Compras Princess, Canarias
; ================================================================

#define MyAppName    "Organizador Princess"
#define MyAppVersion "4.18.60"
#define MyAppExe     "OrganizadorPrincess.exe"
#define MyAppID      "OrganizadorPrincess"
#define MyAssets     SourcePath + "assets"
#define MyDist       SourcePath + "dist"
#define MyManual     SourcePath + "Manual_Usuario_OrganizadorPrincess.pdf"
#define MyManualAdmin SourcePath + "docs\Manual_Administrador_OrganizadorPrincess.pdf"
; Notas de la versión — nombres FIJOS, no llevan el número de versión.
; En cada release solo hay que actualizar el CONTENIDO de estos dos
; ficheros (carpeta release_notes\), nunca hay que tocar esta ruta:
;   - release_notes_actual.txt  → solo lo nuevo de ESTA versión (se
;     muestra en el instalador justo al terminar).
;   - release_notes.md          → historial completo acumulado (copia
;     local permanente, no se muestra en el instalador).
#define MyReleaseNotesActual SourcePath + "release_notes\release_notes_actual.txt"

; ----------------------------------------------------------------
;  Configuración general
; ----------------------------------------------------------------
[Setup]
AppId={#MyAppID}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Central de Compras Princess — Canarias
AppPublisherURL=https://
AppSupportURL=https://
AppUpdatesURL=https://

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist_installer
OutputBaseFilename=OrganizadorPrincess_Setup_{#MyAppVersion}

SetupIconFile={#MyAssets}\logo.ico
UninstallDisplayIcon={app}\{#MyAppExe}

; Muestra las novedades de ESTA versión justo al terminar de instalar
; (antes de la pantalla final). Ruta fija — solo cambia el contenido
; del .txt en cada release, nunca esta línea.
InfoAfterFile={#MyReleaseNotesActual}

; Imágenes del wizard
WizardImageFile={#MyAssets}\corona.png
WizardSmallImageFile={#MyAssets}\corona.png

WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
LanguageDetectionMethod=none
PrivilegesRequired=admin
UsedUserAreasWarning=no
DisableProgramGroupPage=yes
DisableDirPage=no
DisableReadyMemo=no
RestartApplications=no

; ----------------------------------------------------------------
;  Idioma
; ----------------------------------------------------------------
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

; ----------------------------------------------------------------
;  Mensajes personalizados (minimalistas)
; ----------------------------------------------------------------
[Messages]
SetupAppTitle={#MyAppName}

WelcomeLabel1=Instalación de {#MyAppName}
WelcomeLabel2=Versión {#MyAppVersion} · © VAMA 2026%n%nEsta aplicación es de uso interno exclusivo del Departamento de Central de Compras Princess en Canarias.

SelectDirLabel3=Elige la carpeta de instalación o acepta la ruta por defecto.

PreparingDesc=Preparando la instalación...
InstallingLabel=Instalando, por favor espera...

FinishedHeadingLabel=Instalación completada
FinishedLabel={#MyAppName} {#MyAppVersion} está listo para usarse.%n%n© VAMA 2026 · Central de Compras Princess

UninstallAppFullTitle=Desinstalar {#MyAppName}
ConfirmUninstall=¿Confirmas que deseas desinstalar {#MyAppName}?

ButtonInstall=Instalar
ButtonFinish=Finalizar

; ----------------------------------------------------------------
;  Archivos
; ----------------------------------------------------------------
[Files]
Source: "{#MyDist}\{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyDist}\*";           DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyManual}";             DestDir: "{app}"; Flags: ignoreversion
Source: "{#MyManualAdmin}";        DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; Copia local permanente de las novedades — queda en el PC como
; referencia sin depender de GitHub ni de conexión a internet.
; release_notes.md ya trae el historial completo acumulado (es el
; mismo fichero que se mantiene a mano en cada release).
Source: "{#SourcePath}release_notes\release_notes.md";        DestDir: "{app}\release_notes"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#MyReleaseNotesActual}";                              DestDir: "{app}\release_notes"; Flags: ignoreversion skipifsourcedoesntexist

; ----------------------------------------------------------------
;  Accesos directos
; ----------------------------------------------------------------
[Icons]
Name: "{group}\{#MyAppName}";              Filename: "{app}\{#MyAppExe}"
Name: "{group}\Desinstalar {#MyAppName}";  Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}";      Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon
Name: "{group}\Manual de Usuario";           Filename: "{app}\Manual_Usuario_OrganizadorPrincess.pdf"
Name: "{group}\Manual de Administrador";     Filename: "{app}\Manual_Administrador_OrganizadorPrincess.pdf"

; ----------------------------------------------------------------
;  (v4.18.52) Enlace organizadorprincess:// — el botón «Abrir el Organizador» del aviso de
;  Control Pedidos (v12.34.26) lo abre desde el navegador. El navegador pregunta la primera vez
;  si se permite abrirlo. Se borra al desinstalar.
; ----------------------------------------------------------------
[Registry]
Root: HKCR; Subkey: "organizadorprincess"; ValueType: string; ValueName: ""; ValueData: "URL:Organizador Princess"; Flags: uninsdeletekey
Root: HKCR; Subkey: "organizadorprincess"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCR; Subkey: "organizadorprincess\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"",0"
Root: HKCR; Subkey: "organizadorprincess\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExe}"" ""%1"""

; ----------------------------------------------------------------
;  Tareas opcionales
; ----------------------------------------------------------------
[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; Flags: unchecked

; ----------------------------------------------------------------
;  Ejecutar al finalizar
; ----------------------------------------------------------------
[Run]
Filename: "{app}\{#MyAppExe}"; \
  Description: "Iniciar {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent
;  (v4.18.20) Instalación de un clic desde «Actualizar ahora» (/SILENT): al terminar se vuelve
;  a abrir el Organizador solo, con el usuario normal y no como administrador.
;  (v4.18.40) A través de cmd, quitando las variables internas de PyInstaller que este instalador
;  hereda del Organizador viejo (_PYI_*, _MEIPASS2) y con PYINSTALLER_RESET_ENVIRONMENT=1. Sin eso,
;  el nuevo buscaba Python en la carpeta temporal _MEI… del viejo, ya borrada al cerrarse:
;  «Failed to load Python DLL» (v4.18.38). Así se arregla también al actualizar desde la v4.18.38.
Filename: "{cmd}"; \
  Parameters: "/c set ""_PYI_APPLICATION_HOME_DIR="" & set ""_PYI_ARCHIVE_FILE="" & set ""_PYI_PARENT_PROCESS_LEVEL="" & set ""_PYI_SPLASH_IPC="" & set ""_MEIPASS2="" & set ""PYINSTALLER_RESET_ENVIRONMENT=1"" & start """" /D ""{app}"" ""{app}\{#MyAppExe}"""; \
  Flags: nowait runhidden runasoriginaluser; Check: WizardSilent

; ----------------------------------------------------------------
;  Limpieza al desinstalar
; ----------------------------------------------------------------
[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{userappdata}\{#MyAppID}"

; ----------------------------------------------------------------
;  Limpieza de __pycache__ antes de empaquetar
;  (Inno Setup ejecuta esto antes de compilar el instalador)
; ----------------------------------------------------------------
[PreCompile]
; Borra todos los directorios __pycache__ del proyecto
Name: "cmd.exe"; Parameters: "/c for /d /r ""{src}"" %%C in (__pycache__) do if exist ""%%C"" rmdir /s /q ""%%C"""; Flags: runhidden

; ================================================================
;  CÓDIGO PASCAL — Bloqueo por máquina (1 instalación por versión)
; ================================================================
[Code]

{ ── Cierre forzado antes de instalar ───────────────────────────────────── }
{ (v4.18.32) SIN «/T»: con «Actualizar ahora» este instalador lo abre el propio Organizador,
  así que Windows lo cuenta como proceso hijo suyo. «/T» (cerrar también los hijos) cerraba
  el instalador junto con el Organizador: se cerraba la versión actual y no se instalaba
  ni se abría la nueva. Sin «/T» se cierran todos los OrganizadorPrincess.exe igualmente. }
{ (v4.18.38) Primero se le pide que se cierre (sin /F: el Organizador recibe el cierre de la ventana,
  guarda la agenda y se cierra) y solo si a los 4 s sigue abierto se fuerza con /F. Antes se forzaba
  directamente, y si lo pillaba escribiendo config.json o agenda.json el archivo quedaba vacío. }
procedure KillOrganizador();
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/IM OrganizadorPrincess.exe', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
  Sleep(4000);
  Exec('taskkill.exe', '/F /IM OrganizadorPrincess.exe', '', SW_HIDE,
       ewWaitUntilTerminated, ResultCode);
  Sleep(2000);
end;

{ Genera un identificador único combinando nombre de equipo + usuario }
function GetMachineID(): String;
begin
  Result := GetComputerNameString + '-' + GetUserNameString;
end;

{ Verifica que el instalador no haya sido activado en otro equipo }
function InitializeSetup(): Boolean;
var
  RegPath:    String;
  CurrentID:  String;
  StoredID:   String;
begin
  KillOrganizador();  { Matar proceso ANTES de que Inno Setup detecte archivos en uso }
  Sleep(2000);
  RegPath   := 'Software\{#MyAppID}\{#MyAppVersion}';
  CurrentID := GetMachineID();

  { Primera ejecución: registrar este equipo }
  if not RegQueryStringValue(HKCU, RegPath, 'MachineID', StoredID) then
  begin
    RegWriteStringValue(HKCU, RegPath, 'MachineID', CurrentID);
    Result := True;
    Exit;
  end;

  { Equipo registrado coincide → permitir }
  if StoredID = CurrentID then
  begin
    Result := True;
    Exit;
  end;

  { Equipo diferente → bloquear }
  MsgBox(
    'Este instalador ya fue activado en otro equipo.' + #13#10#13#10 +
    'Cada versión solo puede instalarse en un único ordenador.' + #13#10 +
    'Contacta con el Dpto. Central de Compras para obtener una nueva versión.',
    mbError, MB_OK
  );
  Result := False;
end;
